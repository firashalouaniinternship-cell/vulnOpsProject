import json
import logging
import os
import re
import requests

from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from ..models import Vulnerability

logger = logging.getLogger(__name__)


def _build_patch_prompt(vuln) -> str:
    return f"""You are an expert Secure Code Developer.
A security scanner reported the following vulnerability:

Vulnerability : {vuln.test_name} ({vuln.test_id})
Description   : {vuln.issue_text}
Severity      : {vuln.severity}
CWE           : {vuln.cwe or 'N/A'}
File          : {vuln.filename} (line {vuln.line_number})

Vulnerable code:
```
{vuln.code_snippet or '# Code snippet not available'}
```

Generate a precise, minimal remediation patch.
Return ONLY a valid JSON object with this exact structure (no markdown, no explanation outside JSON):
{{
  "file_path": "{vuln.filename}",
  "explanation": "One paragraph: why this code is vulnerable and what the fix does",
  "code_diff": "Show the fixed version of the vulnerable code with --- old / +++ new markers"
}}
"""


def _call_llm(prompt: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "ollama":
        url = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
        if "localhost" in url:
            url = url.replace("localhost", "127.0.0.1")
        model = os.getenv("OLLAMA_MODEL", "llama3")

        resp = requests.post(url, json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        }, timeout=300)

        if resp.status_code != 200:
            raise RuntimeError(f"Ollama HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json().get("message", {}).get("content", "{}")

    # OpenRouter fallback
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    model = os.getenv("OPENROUTER_MODEL", "google/gemma-2-9b-it:free")

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"]


def _parse_llm_json(raw: str) -> dict:
    cleaned = raw.strip()
    # Strip markdown code fences if present
    cleaned = re.sub(r'^```[a-z]*\n?', '', cleaned)
    cleaned = re.sub(r'```\s*$', '', cleaned).strip()
    return json.loads(cleaned)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def generate_patch(request, pk):
    """
    Generates a remediation code patch for a vulnerability.
    Returns: { patch: { file_path, explanation, code_diff } }
    """
    user_filter = request.user if request.user.is_authenticated else None
    try:
        vuln = Vulnerability.objects.get(pk=pk, scan__user=user_filter)
    except Vulnerability.DoesNotExist:
        return Response({'error': 'Vulnérabilité non trouvée'}, status=status.HTTP_404_NOT_FOUND)

    if vuln.is_dast:
        return Response(
            {'error': 'Les patches de code ne sont pas disponibles pour les vulnérabilités DAST'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        raw = _call_llm(_build_patch_prompt(vuln))
        patch = _parse_llm_json(raw)
        return Response({'patch': patch}, status=status.HTTP_200_OK)
    except json.JSONDecodeError:
        logger.error("LLM returned invalid JSON for patch generation")
        return Response(
            {'error': 'Le LLM n\'a pas retourné un JSON valide. Réessayez.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        logger.error(f"Patch generation failed for vuln {pk}: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
