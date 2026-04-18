import os
import json
import requests
import logging
import time
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

logger = logging.getLogger(__name__)

def get_direct_llm_score(test_name, issue_text, severity, context_summary, code_snippet=None):
    """
    Appelle directement le LLM (Ollama ou OpenRouter) pour obtenir un score de priorité.
    Bypasse le système RAG pour plus de rapidité et de robustesse.
    """
    ollama_url = os.getenv("OLLAMA_API_URL")
    ollama_model = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
    api_key = os.getenv("OPENROUTER_API_KEY")
    openrouter_model = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    # Utiliser 127.0.0.1 pour plus de stabilité sur Windows si localhost est fourni
    if ollama_url and "localhost" in ollama_url:
        ollama_url = ollama_url.replace("localhost", "127.0.0.1")

    system_prompt = "You are a specialized Security Project Lead. Your goal is to prioritize vulnerabilities for developers."
    
    vuln_details = f"Vulnérabilité: {test_name}\nDescription: {issue_text}\nSévérité: {severity}"
    if code_snippet:
        vuln_details += f"\nCode Concerné:\n{code_snippet}"

    user_prompt = (
        f"En tant qu'expert en sécurité, analyse et donne un SCORE DE PRIORITÉ à cette vulnérabilité dans le contexte global du projet.\n\n"
        f"CONTEXTE DU PROJET (Autres menaces détectées) :\n{context_summary}\n\n"
        f"DÉTAILS DE LA VULNÉRABILITÉ À SCORER :\n{vuln_details}\n\n"
        "Donne un score entre 0.0 et 1.0 (1.0 = priorité absolue de correction).\n"
        "Le score doit être relatif aux autres menaces citées dans le contexte.\n"
        "Réponds UNIQUEMENT sous format JSON : {\"score\": 0.85, \"reasoning\": \"explication courte en français\"}"
    )

    if provider == "ollama":
        if not ollama_url:
            logger.error("Configuration OLLAMA_API_URL manquante pour le fournisseur: ollama")
            return {"score": 0.5, "reasoning": "Scoring failed: Missing OLLAMA configuration"}
        try:
            logger.info(f"Appel JSON Ollama ({ollama_model}) pour {test_name}...")
            data = {
                "model": ollama_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.3}
            }
            response = requests.post(ollama_url, json=data, timeout=300) # Timeout 5 min
            if response.status_code == 200:
                result = response.json().get("message", {}).get("content", "")
                if not result:
                     logger.warning("Réponse Ollama vide")
                     return {"score": 0.5, "reasoning": "Scoring failed: Empty response"}
                
                print(f"\n✅ Connecté avec succès au LLM (Local/Ollama - {ollama_model}) pour l'analyse de vulnérabilité !\n")
                
                cleaned_result = result.strip()
                if cleaned_result.startswith("```"):
                    lines = cleaned_result.splitlines()
                    if lines[0].startswith("```"): lines = lines[1:]
                    if lines and lines[-1].startswith("```"): lines = lines[:-1]
                    cleaned_result = "\n".join(lines).strip()
                
                try:
                    return json.loads(cleaned_result)
                except json.JSONDecodeError:
                    import re
                    match = re.search(r'\{.*\}', cleaned_result, re.DOTALL)
                    if match:
                        return json.loads(match.group())
                    raise
            else:
                logger.warning(f"Ollama a retourné une erreur {response.status_code}: {response.text}")
                return {"score": 0.5, "reasoning": f"Scoring failed: HTTP {response.status_code}"}
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON Ollama. Texte reçu: {response.text if 'response' in locals() else 'N/A'}")
            return {"score": 0.5, "reasoning": f"Scoring failed: Invalid JSON format"}
        except Exception as e:
            logger.error(f"Erreur lors de l'appel direct Ollama : {e}")
            return {"score": 0.5, "reasoning": f"Scoring failed: {str(e)}"}

    elif provider == "openrouter":
        if not api_key:
            logger.error("Configuration OPENROUTER_API_KEY manquante pour le fournisseur: openrouter")
            return {"score": 0.5, "reasoning": "Scoring failed: Missing OpenRouter configuration"}
        
        max_retries = 3
        retry_delay = 2 # seconds
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Appel JSON OpenRouter ({openrouter_model}) pour {test_name} (Tentative {attempt+1}/{max_retries})...")
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": openrouter_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": {"type": "json_object"}
                }
                response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
                
                if response.status_code == 429:
                    logger.warning(f"OpenRouter 429 (Rate Limit). Attente de {retry_delay}s avant retry...")
                    time.sleep(retry_delay)
                    retry_delay *= 2 # Backoff exponentiel
                    continue

                if response.status_code == 200:
                    result = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    print(f"\n✅ Connecté avec succès au LLM (OpenRouter - {openrouter_model}) pour l'analyse de vulnérabilité !\n")
                    
                    cleaned_result = result.strip()
                    if cleaned_result.startswith("```"):
                        lines = cleaned_result.splitlines()
                        if lines[0].startswith("```"): lines = lines[1:]
                        if lines and lines[-1].startswith("```"): lines = lines[:-1]
                        cleaned_result = "\n".join(lines).strip()

                    try:
                        return json.loads(cleaned_result)
                    except json.JSONDecodeError:
                        import re
                        match = re.search(r'\{.*\}', cleaned_result, re.DOTALL)
                        if match:
                            return json.loads(match.group())
                        raise
                else:
                    logger.warning(f"OpenRouter a retourné une erreur {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    return {"score": 0.5, "reasoning": f"Scoring failed: HTTP {response.status_code}"}
            except Exception as e:
                logger.error(f"Erreur lors de l'appel OpenRouter (Tentative {attempt+1}) : {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return {"score": 0.5, "reasoning": f"Scoring failed: OpenRouter {str(e)}"}
        
        return {"score": 0.5, "reasoning": "Scoring failed after multiple retries"}
    else:
        logger.error(f"LLM_PROVIDER inconnu: {provider}")
        return {"score": 0.5, "reasoning": f"Scoring failed: Unknown LLM_PROVIDER {provider}"}

    # Fallback technique si le flux normal échoue silencieusement
    return {"score": 0.5, "reasoning": "Scoring failed: Technical connection issue"}
