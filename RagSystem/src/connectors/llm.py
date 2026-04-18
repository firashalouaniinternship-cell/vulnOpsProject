import requests
import time
import json
import logging
from ..core.config import Config

logger = logging.getLogger(__name__)

class LLMConnector:
    """Handles communication with LLM providers (Ollama or OpenRouter)."""
    
    @staticmethod
    def call_llm(system_prompt, user_prompt, temperature=0.3, json_mode=False):
        """Routes the call to the configured provider with retry logic."""
        if Config.LLM_PROVIDER == "ollama":
            return LLMConnector._call_ollama(system_prompt, user_prompt, temperature, json_mode)
        else:
            return LLMConnector._call_openrouter(system_prompt, user_prompt, temperature, json_mode)

    @staticmethod
    def _call_ollama(system_prompt, user_prompt, temperature, json_mode):
        if not Config.OLLAMA_API_URL:
            return "Error: OLLAMA_API_URL not configured."
        
        # Windows stability handle
        url = Config.OLLAMA_API_URL.replace("localhost", "127.0.0.1") if "localhost" in Config.OLLAMA_API_URL else Config.OLLAMA_API_URL
        
        data = {
            "model": Config.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {"temperature": temperature}
        }
        if json_mode:
            data["format"] = "json"
            
        try:
            logger.info(f"Ollama call ({Config.OLLAMA_MODEL})...")
            response = requests.post(url, json=data, timeout=300)
            if response.status_code == 200:
                return response.json()["message"]["content"]
            return f"Ollama Error ({response.status_code}): {response.text}"
        except Exception as e:
            return f"Ollama Exception: {str(e)}"

    @staticmethod
    def _call_openrouter(system_prompt, user_prompt, temperature, json_mode):
        if not Config.OPENROUTER_API_KEY:
            return "Error: OPENROUTER_API_KEY not found."

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": Config.OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        if json_mode:
            data["response_format"] = {"type": "json_object"}

        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"OpenRouter call ({Config.OPENROUTER_MODEL}) - Attempt {attempt+1}")
                response = requests.post(url, headers=headers, json=data, timeout=300)
                
                if response.status_code == 429:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                    
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return f"API Error ({response.status_code}): {response.text}"
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return f"Request failed: {str(e)}"
        
        return "Error: Max retries reached for OpenRouter."
