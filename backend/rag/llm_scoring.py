import os
import json
import requests
import logging
import time
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _ollama_url() -> str:
    url = os.getenv("OLLAMA_API_URL", "")
    return url.replace("localhost", "127.0.0.1") if "localhost" in url else url


def _llm_config() -> dict:
    return {
        "provider": os.getenv("LLM_PROVIDER", "ollama").lower(),
        "ollama_url": _ollama_url(),
        "ollama_model": os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud"),
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "openrouter_model": os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free"),
    }


def _call_ollama(cfg: dict, messages: list, timeout: int = 300) -> str:
    data = {
        "model": cfg["ollama_model"],
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.3},
    }
    resp = requests.post(cfg["ollama_url"], json=data, timeout=timeout)
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "")


def _call_openrouter(cfg: dict, messages: list, timeout: int = 60) -> str:
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    data = {
        "model": cfg["openrouter_model"],
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    delay = 2
    for attempt in range(3):
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=data, timeout=timeout,
        )
        if resp.status_code == 429:
            time.sleep(delay)
            delay *= 2
            continue
        resp.raise_for_status()
        return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    return ""


def _parse_json(raw: str) -> dict | list:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:] if lines[0].startswith("```") else lines
        lines = lines[:-1] if lines and lines[-1].startswith("```") else lines
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        import re
        match = re.search(r'[\[{].*[\]}]', cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


def get_batch_llm_scores(vulns: list, context_summary: str, batch_size: int = 25) -> list:
    """
    Scores all vulnerabilities in batches of `batch_size` with a single LLM call per batch.
    Returns a list of {"score": float, "reasoning": str} in the same order as `vulns`.
    Falls back to score=0.5 for any vuln that fails.
    """
    if not vulns:
        return []

    cfg = _llm_config()
    results = [{"score": 0.5, "reasoning": "Non scoré"} for _ in vulns]

    for batch_start in range(0, len(vulns), batch_size):
        batch = vulns[batch_start: batch_start + batch_size]
        vuln_lines = []
        for i, v in enumerate(batch):
            snippet = v.get("code_snippet", "")
            line = f"[{i}] {v.get('test_name', '?')} | {v.get('severity', '?')} | {v.get('issue_text', '')[:120]}"
            if snippet:
                line += f" | code: {snippet[:80]}"
            vuln_lines.append(line)

        user_prompt = (
            f"Contexte du projet : {context_summary}\n\n"
            f"Donne un score de priorité (0.0–1.0) à chacune de ces {len(batch)} vulnérabilités.\n"
            "Réponds UNIQUEMENT avec un tableau JSON :\n"
            '[{"index":0,"score":0.85,"reasoning":"..."},{"index":1,"score":0.4,"reasoning":"..."},...]\n\n'
            "Vulnérabilités :\n" + "\n".join(vuln_lines)
        )
        messages = [
            {"role": "system", "content": "You are a security expert. Prioritize vulnerabilities. Reply only with valid JSON array."},
            {"role": "user", "content": user_prompt},
        ]

        try:
            if cfg["provider"] == "ollama":
                if not cfg["ollama_url"]:
                    logger.error("OLLAMA_API_URL manquant")
                    continue
                raw = _call_ollama(cfg, messages)
            elif cfg["provider"] == "openrouter":
                if not cfg["api_key"]:
                    logger.error("OPENROUTER_API_KEY manquant")
                    continue
                raw = _call_openrouter(cfg, messages)
            else:
                logger.error(f"LLM_PROVIDER inconnu: {cfg['provider']}")
                continue

            parsed = _parse_json(raw)
            if isinstance(parsed, dict) and "scores" in parsed:
                parsed = parsed["scores"]
            if not isinstance(parsed, list):
                logger.warning(f"Réponse batch LLM inattendue: {type(parsed)}")
                continue

            for item in parsed:
                idx = item.get("index")
                if idx is None or not (0 <= idx < len(batch)):
                    continue
                results[batch_start + idx] = {
                    "score": float(item.get("score", 0.5)),
                    "reasoning": item.get("reasoning", "Analyse IA"),
                }

        except Exception as e:
            logger.error(f"Batch LLM scoring failed (batch {batch_start}): {e}")

    return results

def get_direct_llm_score(test_name, issue_text, severity, context_summary, code_snippet=None):
    """Single-vuln scoring — delegates to the batch helper for consistency."""
    vuln = {
        "test_name": test_name,
        "issue_text": issue_text,
        "severity": severity,
        "code_snippet": code_snippet or "",
    }
    scores = get_batch_llm_scores([vuln], context_summary)
    return scores[0] if scores else {"score": 0.5, "reasoning": "Scoring failed"}


