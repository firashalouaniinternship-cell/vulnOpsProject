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

    # Paths — BASE_DIR is the RagSystem/ folder
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    CHROMA_DB_DIR = os.path.join(DATA_DIR, "chroma_db")
    SOURCE_DOCS_DIR = os.path.join(DATA_DIR, "source_docs")

    # OWASP Top 10 2021 — maps to the vulnerabilities found by SAST/SCA/DAST scanners
    # CWE IDs listed are the most common outputs of Bandit, Semgrep, ESLint, GoSec, etc.
    OWASP_WEB_MAP = {
        "A01": {
            "name": "Broken Access Control",
            "cwe": ["CWE-200", "CWE-201", "CWE-352", "CWE-639", "CWE-22"],
            "doc_file": "OWASP_A01_Broken_Access_Control.txt",
        },
        "A02": {
            "name": "Cryptographic Failures",
            "cwe": ["CWE-261", "CWE-296", "CWE-310", "CWE-319", "CWE-321", "CWE-326", "CWE-327", "CWE-328", "CWE-330"],
            "doc_file": "OWASP_A02_Cryptographic_Failures.txt",
        },
        "A03": {
            "name": "Injection",
            "cwe": ["CWE-20", "CWE-74", "CWE-77", "CWE-78", "CWE-79", "CWE-80", "CWE-88", "CWE-89", "CWE-90", "CWE-943"],
            "doc_file": "OWASP_A03_Injection.txt",
        },
        "A04": {
            "name": "Insecure Design",
            "cwe": ["CWE-73", "CWE-183", "CWE-209", "CWE-256", "CWE-501", "CWE-522"],
            "doc_file": "OWASP_A04_Insecure_Design.txt",
        },
        "A05": {
            "name": "Security Misconfiguration",
            "cwe": ["CWE-2", "CWE-11", "CWE-13", "CWE-15", "CWE-16", "CWE-260", "CWE-315", "CWE-520"],
            "doc_file": "OWASP_A05_Security_Misconfiguration.txt",
        },
        "A06": {
            "name": "Vulnerable and Outdated Components",
            "cwe": ["CWE-1035", "CWE-1104"],
            "doc_file": "OWASP_A06_Vulnerable_Components.txt",
        },
        "A07": {
            "name": "Identification and Authentication Failures",
            "cwe": ["CWE-255", "CWE-259", "CWE-287", "CWE-288", "CWE-290", "CWE-294", "CWE-295", "CWE-297", "CWE-300"],
            "doc_file": "OWASP_A07_Auth_Failures.txt",
        },
        "A08": {
            "name": "Software and Data Integrity Failures",
            "cwe": ["CWE-494", "CWE-502", "CWE-565", "CWE-784", "CWE-829", "CWE-830"],
            "doc_file": "OWASP_A08_Integrity_Failures.txt",
        },
        "A09": {
            "name": "Security Logging and Monitoring Failures",
            "cwe": ["CWE-117", "CWE-223", "CWE-532", "CWE-778"],
            "doc_file": "OWASP_A09_Logging_Failures.txt",
        },
        "A10": {
            "name": "Server-Side Request Forgery (SSRF)",
            "cwe": ["CWE-918"],
            "doc_file": "OWASP_A10_SSRF.txt",
        },
    }

    # CWE Top 25 Most Dangerous Software Weaknesses (2024)
    # These CWE IDs are the most frequently reported by Bandit, Semgrep, GoSec, ESLint, etc.
    CWE_TOP25_2024 = [
        "CWE-79",   # XSS
        "CWE-89",   # SQL Injection
        "CWE-78",   # OS Command Injection
        "CWE-22",   # Path Traversal
        "CWE-125",  # Out-of-bounds Read
        "CWE-787",  # Out-of-bounds Write
        "CWE-20",   # Improper Input Validation
        "CWE-416",  # Use After Free
        "CWE-190",  # Integer Overflow
        "CWE-502",  # Deserialization of Untrusted Data
        "CWE-476",  # NULL Pointer Dereference
        "CWE-287",  # Improper Authentication
        "CWE-434",  # Unrestricted File Upload
        "CWE-362",  # Race Condition
        "CWE-400",  # Uncontrolled Resource Consumption
        "CWE-611",  # XML External Entity (XXE)
        "CWE-918",  # SSRF
        "CWE-94",   # Code Injection
        "CWE-326",  # Inadequate Encryption Strength
        "CWE-327",  # Use of Broken Algorithm
        "CWE-532",  # Sensitive Info in Log
        "CWE-306",  # Missing Authentication for Critical Function
        "CWE-798",  # Hardcoded Credentials
        "CWE-276",  # Incorrect Default Permissions
        "CWE-770",  # Allocation of Resources Without Limits
    ]
