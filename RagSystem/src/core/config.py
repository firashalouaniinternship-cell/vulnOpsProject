import os
from dotenv import load_dotenv

# Load all potential .env sources
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', 'backend', '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

class Config:
    # LLM Settings
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()
    
    OLLAMA_API_URL = os.getenv("OLLAMA_API_URL")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
    
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-2-9b-it:free")
    OPENROUTER_EMBEDDING_MODEL = os.getenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small")
    
    # Paths
    # Current file is in RagSystem/src/core/config.py
    # BASE_DIR should be RagSystem folder
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    CHROMA_DB_DIR = os.path.join(DATA_DIR, "chroma_db")
    SOURCE_DOCS_DIR = os.path.join(DATA_DIR, "source_docs")
    
    # OWASP Top 10 for LLMs (v2025)
    OWASP_MAP = {
        "LLM01": {"name": "Prompt Injection", "pages": [5, 6]},
        "LLM02": {"name": "Insecure Output Handling", "pages": [7, 8]},
        "LLM03": {"name": "Training Data Poisoning", "pages": [9, 10]},
        "LLM04": {"name": "Model Denial of Service", "pages": [11, 12]},
        "LLM05": {"name": "Supply Chain Vulnerability", "pages": [13, 14]},
        "LLM06": {"name": "Sensitive Information Disclosure", "pages": [15, 16]},
        "LLM07": {"name": "Insecure Plugin Design", "pages": [17, 18]},
        "LLM08": {"name": "Excessive Agency", "pages": [19, 20]},
        "LLM09": {"name": "Overreliance", "pages": [21, 22]},
        "LLM10": {"name": "Model Theft", "pages": [23, 24]}
    }
