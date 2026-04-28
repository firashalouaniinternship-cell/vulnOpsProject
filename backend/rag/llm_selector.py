"""
Module pour intégrer Ollama (en priorité) ou OpenRouter pour choisir
automatiquement les scanners appropriés selon le mode de scan demandé.
"""
import os
import json
import logging
import requests
from typing import List, Dict, Optional, Set
from dotenv import load_dotenv

from scanners.registry import SCANNER_REGISTRY, LANGUAGE_TO_SCANNER, is_scanner_available

load_dotenv()

logger = logging.getLogger(__name__)

# Scanners autorisés par mode
_MODE_ALLOWED: dict[str, Optional[Set[str]]] = {
    'fast':     {'semgrep'},                    # toujours semgrep, pas de LLM
    'standard': {'semgrep', 'sonarcloud'},      # LLM choisit parmi ces deux
    'deep':     None,                           # LLM choisit parmi tous les scanners
}


class LLMSelector:
    """Utilise Ollama (ou OpenRouter en secours) pour choisir les scanners appropriés."""

    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.api_base = "https://openrouter.ai/api/v1"
        self.model = os.getenv('OPENROUTER_MODEL', 'mistral/mistral-7b-instruct')

        if not self.api_key and not os.getenv("OLLAMA_API_URL"):
            logger.warning("Neither OPENROUTER_API_KEY nor OLLAMA_API_URL set in environment variables")

    def suggest_scanners(
        self,
        languages: List[str],
        frameworks: Dict[str, List[str]],
        file_counts: Dict[str, int],
        structure_summary: str,
        scan_mode: str = 'standard',
    ) -> Dict:
        """
        Suggests SAST scanners based on project analysis and scan mode.

        scan_mode:
          - 'fast'     → always semgrep, no LLM call
          - 'standard' → LLM chooses from semgrep / sonarcloud only
          - 'deep'     → LLM chooses from all specialized scanners
        """
        allowed = _MODE_ALLOWED.get(scan_mode)

        # Fast mode: bypass LLM entirely
        if scan_mode == 'fast':
            logger.info("Fast mode: skipping LLM, using Semgrep directly")
            return {
                'selected_scanners': ['semgrep'],
                'reasoning': 'Fast mode — Semgrep covers 17+ languages with OWASP rules in under 2 minutes.',
                'confidence': 1.0,
                'source': 'mode:fast',
            }

        prompt = self._build_prompt(languages, frameworks, file_counts, structure_summary, allowed)
        try:
            response = self._call_llm(prompt)
            return self._parse_response(response, languages, frameworks, allowed)
        except Exception as e:
            logger.error(f"LLM selector error: {e}")
            return self._fallback_selection(languages, frameworks, allowed)

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    def _build_prompt(
        self,
        languages: List[str],
        frameworks: Dict[str, List[str]],
        file_counts: Dict[str, int],
        structure_summary: str,
        allowed_scanners: Optional[Set[str]],
    ) -> str:
        registry_subset = {
            k: v for k, v in SCANNER_REGISTRY.items()
            if allowed_scanners is None or k in allowed_scanners
        }
        scanner_info = "\n".join([
            f"- {key}: {meta.name} ({meta.language}) | {meta.description}"
            for key, meta in registry_subset.items()
        ])

        return f"""You are a code security scanner selection expert. Based on the project analysis below, \
select the BEST suited security scanners from the available options.

PROJECT ANALYSIS:
- Languages: {', '.join(languages) if languages else 'None detected'}
- Frameworks: {json.dumps(frameworks) if frameworks else 'None detected'}
- File Counts: {json.dumps(file_counts) if file_counts else 'None'}
- Summary: {structure_summary}

AVAILABLE SCANNERS:
{scanner_info}

SELECTION CRITERIA:
1. Match scanner language support with detected languages
2. Prioritize dedicated scanners for specific languages
3. Multi-language scanners (sonarcloud, semgrep) for diverse projects
4. Include at least 1 scanner for security analysis
5. Maximum 3 scanners for efficiency

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{{
    "selected_scanners": ["scanner1", "scanner2", ...],
    "reasoning": "Brief explanation of why these scanners were selected",
    "confidence": 0.95
}}

Return ONLY valid JSON, no markdown formatting."""

    def _call_llm(self, prompt: str) -> str:
        provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        ollama_url = os.getenv("OLLAMA_API_URL")
        ollama_model = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")

        if provider == "ollama":
            if not ollama_url:
                raise Exception("Missing OLLAMA_API_URL configuration")
            data = {
                "model": ollama_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.3},
            }
            response = requests.post(ollama_url, json=data, timeout=45)
            if response.status_code == 200:
                content = response.json()["message"]["content"].strip()
                logger.info(f"Ollama response received (model={ollama_model})")
                return content
            raise Exception(f"Ollama failed with status: {response.status_code}")

        elif provider == "openrouter":
            if not self.api_key:
                raise Exception("Missing OPENROUTER_API_KEY configuration")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/vulnops",
                "X-Title": "VulnOps Scanner Selection",
            }
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 500,
            }
            response = requests.post(f"{self.api_base}/chat/completions", headers=headers, json=data, timeout=30)
            response.raise_for_status()
            content = response.json().get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            logger.info(f"OpenRouter response received (model={self.model})")
            return content

        raise Exception(f"Unknown LLM_PROVIDER: {provider}")

    def _parse_response(
        self,
        response: str,
        languages: List[str],
        frameworks: Dict[str, List[str]],
        allowed_scanners: Optional[Set[str]],
    ) -> Dict:
        try:
            data = json.loads(response)
            selected = data.get('selected_scanners', [])
            reasoning = data.get('reasoning', 'No explanation provided')
            confidence = float(data.get('confidence', 0.5))

            valid = [
                s for s in selected
                if s in SCANNER_REGISTRY
                and (allowed_scanners is None or s in allowed_scanners)
            ]

            if not valid:
                logger.warning(f"No valid scanners in LLM response: {selected}")
                return self._fallback_selection(languages, frameworks, allowed_scanners)

            logger.info(f"LLM selected: {valid} (confidence={confidence:.2f})")
            return {
                'selected_scanners': valid,
                'reasoning': reasoning,
                'confidence': confidence,
                'source': 'ai',
            }
        except (json.JSONDecodeError, ValueError):
            logger.error(f"Failed to parse LLM response: {response[:200]}")
            return self._fallback_selection(languages, frameworks, allowed_scanners)

    def _fallback_selection(
        self,
        languages: List[str],
        frameworks: Dict[str, List[str]],
        allowed_scanners: Optional[Set[str]],
    ) -> Dict:
        logger.info("Using fallback scanner selection")
        selected = []

        for lang in languages:
            scanner = LANGUAGE_TO_SCANNER.get(lang)
            if scanner and scanner not in selected:
                if allowed_scanners is None or scanner in allowed_scanners:
                    selected.append(scanner)

        # Ensure at least one multi-language scanner
        for fallback in ('semgrep', 'sonarcloud'):
            if not selected:
                if allowed_scanners is None or fallback in allowed_scanners:
                    selected.append(fallback)
                    break

        if not selected:
            selected = ['semgrep']

        return {
            'selected_scanners': selected[:3],
            'reasoning': f"Auto-selected for: {', '.join(languages)}",
            'confidence': 0.7,
            'source': 'fallback',
        }
