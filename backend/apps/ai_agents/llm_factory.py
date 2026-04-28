import os
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from dotenv import load_dotenv

load_dotenv()

class LLMFactory:
    """Factory to get the best free LLM for AI Agents using LangChain."""

    @staticmethod
    def get_llm(temperature: float = 0.0):
        """Returns a LangChain LLM instance based on environment variables."""
        provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        
        if provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY is not set.")
            
            # Using one of the best free models on OpenRouter (Google Gemini Pro or Llama 3)
            # Defaulting to google/gemini-pro or meta-llama/llama-3-8b-instruct
            # Using gemini-1.5-pro or claude-3-haiku could also be good if they are free or cheap.
            model_name = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3-8b-instruct:free")
            
            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=temperature,
                max_tokens=2048,
                model_kwargs={
                    "extra_headers": {
                        "HTTP-Referer": "https://github.com/vulnops",
                        "X-Title": "VulnOps AI Agents"
                    }
                }
            )
            
        elif provider == "ollama":
            url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
            model_name = os.getenv("OLLAMA_MODEL", "llama3")
            
            return ChatOllama(
                base_url=url,
                model=model_name,
                temperature=temperature
            )
            
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

def get_best_model(temperature: float = 0.0):
    """Helper to instantiate the LLM."""
    return LLMFactory.get_llm(temperature=temperature)
