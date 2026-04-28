"""
Integrated RAG service — replaces the external RagSystem subprocess.

Architecture:
  - Thread-safe singleton with lazy model loading
  - ChromaDB stored in backend/data/chroma_db/
  - Embedding model: sentence-transformers/all-MiniLM-L6-v2 (local, free, no API key)
  - LLM: Ollama (local) or OpenRouter (cloud) — same provider as the rest of the backend
"""

import json
import logging
import os
import threading
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_BACKEND_DIR   = Path(__file__).resolve().parent.parent
_CHROMA_DB_DIR = str(_BACKEND_DIR / "data" / "chroma_db")
_SOURCE_DOCS_DIR = str(_BACKEND_DIR / "data" / "source_docs")

SYSTEM_PROMPT_RECOMMENDATION = (
    "You are a Senior Application Security Engineer specialized in code vulnerability remediation. "
    "You analyze findings from SAST scanners (Bandit, Semgrep, ESLint, GoSec, Brakeman, etc.), "
    "SCA tools (OWASP Dependency-Check), container scanners (Trivy), and DAST tools (OWASP ZAP). "
    "Use the OWASP Top 10 2021, OWASP Cheat Sheets, and CWE knowledge provided as context to give "
    "precise, actionable remediation advice grounded in official standards.\n\n"
    "You MUST follow this exact structure:\n\n"
    "### Analyse de la Vulnérabilité\n"
    "**Catégorie OWASP / CWE :** Identifiez la catégorie OWASP Top 10 2021 (ex: A03 - Injection) "
    "et le CWE correspondant (ex: CWE-89). Expliquez pourquoi cette faille est dangereuse.\n"
    "**Vecteur d'attaque :** Décrivez concrètement comment un attaquant exploiterait cette faille "
    "dans le contexte du code signalé par le scanner.\n\n"
    "### Remédiation\n"
    "**Bonnes pratiques :** Listez les principes de secure coding selon l'OWASP Cheat Sheet Series.\n"
    "**Exemple de code corrigé :** Fournissez un extrait de code sécurisé dans le langage détecté.\n"
    "**Références :** Citez les sources OWASP/CWE pertinentes.\n\n"
    "Répondez en français. Utilisez le format Markdown. Soyez précis et pédagogique."
)


class RAGService:
    """
    Thread-safe singleton.
    Heavy objects (embedding model, ChromaDB) are loaded lazily on first use.
    """

    _instance = None
    _instance_lock = threading.Lock()

    _model_lock = threading.Lock()
    _embedding_model = None
    _vector_db = None

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_embedding_model(self):
        if self._embedding_model is None:
            with self._model_lock:
                if self._embedding_model is None:
                    from langchain_huggingface import HuggingFaceEmbeddings
                    logger.info("RAG: loading embedding model (all-MiniLM-L6-v2)…")
                    self._embedding_model = HuggingFaceEmbeddings(
                        model_name="sentence-transformers/all-MiniLM-L6-v2",
                        model_kwargs={"device": "cpu"},
                        encode_kwargs={"normalize_embeddings": True},
                    )
                    logger.info("RAG: embedding model ready.")
        return self._embedding_model

    def _get_vector_db(self):
        if self._vector_db is None:
            with self._model_lock:
                if self._vector_db is None:
                    chroma_sqlite = os.path.join(_CHROMA_DB_DIR, "chroma.sqlite3")
                    if not os.path.exists(chroma_sqlite):
                        logger.warning(
                            f"RAG: ChromaDB not found at {_CHROMA_DB_DIR}. "
                            "Run backend/scripts/ingest_docs.py to build the index."
                        )
                        return None
                    from langchain_community.vectorstores import Chroma
                    logger.info(f"RAG: loading ChromaDB from {_CHROMA_DB_DIR}…")
                    self._vector_db = Chroma(
                        persist_directory=_CHROMA_DB_DIR,
                        embedding_function=self._get_embedding_model(),
                    )
                    logger.info("RAG: ChromaDB ready.")
        return self._vector_db

    def _call_llm(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        provider = os.getenv("LLM_PROVIDER", "ollama").lower()

        if provider == "ollama":
            url = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
            url = url.replace("localhost", "127.0.0.1")
            model = os.getenv("OLLAMA_MODEL", "llama3")

            data: dict = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.3},
            }
            if json_mode:
                data["format"] = "json"

            resp = requests.post(url, json=data, timeout=300)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama HTTP {resp.status_code}: {resp.text[:300]}")
            return resp.json()["message"]["content"]

        # OpenRouter
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        model = os.getenv("OPENROUTER_MODEL", "google/gemma-2-9b-it:free")
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            "temperature": 0.3,
        }
        if json_mode:
            data["response_format"] = {"type": "json_object"}

        delay = 2
        for attempt in range(3):
            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=data,
                    timeout=60,
                )
                if resp.status_code == 429:
                    time.sleep(delay)
                    delay *= 2
                    continue
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
                raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {resp.text[:200]}")
            except RuntimeError:
                raise
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1)

        raise RuntimeError("LLM call failed after all retries")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def invoke(self, input_data: dict) -> dict:
        """
        Returns a security recommendation for a vulnerability.
        Compatible with the old RagSystem chain.invoke() interface.
        """
        query = input_data.get("query", "")

        try:
            db = self._get_vector_db()

            if db:
                docs = db.similarity_search(query, k=5)
                context_text = "\n\n".join(d.page_content for d in docs)
                source_docs  = [d.metadata for d in docs]
                user_prompt  = (
                    f"CONTEXTE SÉCURITÉ (OWASP/CWE):\n{context_text}\n\n"
                    f"VULNÉRABILITÉ DÉTECTÉE:\n{query}"
                )
            else:
                source_docs = []
                user_prompt = f"VULNÉRABILITÉ DÉTECTÉE:\n{query}"

            result_text = self._call_llm(SYSTEM_PROMPT_RECOMMENDATION, user_prompt)

            return {
                "result": result_text,
                "source_documents": source_docs,
                "sources": [d.get("page", 0) + 1 for d in source_docs],
            }

        except Exception as e:
            logger.error(f"RAG invoke failed: {e}", exc_info=True)
            return {"result": f"Erreur RAG: {str(e)}", "source_documents": [], "sources": []}

    def chat_vulnerability(self, vulnerability_details: dict, message: str, chat_history: list = None) -> str:
        """
        Permet de discuter d'une vulnérabilité avec le contexte du code et du RAG.
        """
        chat_history = chat_history or []
        
        system_prompt = (
            "Vous are an expert Security Engineer. You are helping a developer understand and fix a vulnerability.\n"
            "CONTEXT OF THE FINDING:\n"
            f"- Test: {vulnerability_details.get('test_name')}\n"
            f"- Severity: {vulnerability_details.get('severity')}\n"
            f"- File: {vulnerability_details.get('filename')}\n"
            f"- Code snippet: {vulnerability_details.get('code_snippet')}\n\n"
            "Answer the user's questions accurately and suggest code improvements. Respond in French."
        )
        
        # Build history prompt
        history_text = ""
        for msg in chat_history:
            role = "USER" if msg.get('role') == 'user' else "ASSISTANT"
            history_text += f"{role}: {msg.get('content')}\n"
            
        user_prompt = f"{history_text}USER: {message}"
        
        return self._call_llm(system_prompt, user_prompt)

    def score_vulnerability(self, input_data: dict) -> dict:
        """
        Returns { score: float, reasoning: str } for a vulnerability.
        Compatible with the old RagSystem chain.score_vulnerability() interface.
        """
        query   = input_data.get("query",   "")
        context = input_data.get("context", "General project")

        system_prompt = (
            "You are a specialized Security Project Lead. "
            "Your goal is to prioritize vulnerabilities for developers."
        )
        user_prompt = (
            f"Project context and other detected threats: {context}\n\n"
            f"Analyze and PRIORITY-SCORE this vulnerability:\n{query}\n\n"
            'Assign a score between 0.0 and 1.0 (1.0 = top priority). '
            'Return ONLY valid JSON: {"score": 0.85, "reasoning": "..."}'
        )

        try:
            raw = self._call_llm(system_prompt, user_prompt, json_mode=True)
            return json.loads(raw)
        except Exception as e:
            logger.error(f"RAG scoring failed: {e}", exc_info=True)
            return {"score": 0.5, "reasoning": f"Scoring failed: {str(e)}"}

    def ingest_documents(self, source_dir: str = _SOURCE_DOCS_DIR) -> bool:
        """
        Loads all PDF/TXT/MD files from source_dir, splits them into chunks,
        and stores them in ChromaDB. Call this once after downloading source docs.
        """
        from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, TextLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_community.vectorstores import Chroma

        if not os.path.exists(source_dir) or not os.listdir(source_dir):
            logger.warning(f"RAG ingest: no files in {source_dir}")
            return False

        logger.info(f"RAG ingest: loading documents from {source_dir}…")
        documents = (
            DirectoryLoader(source_dir, glob="*.pdf", loader_cls=PyPDFLoader).load()
            + DirectoryLoader(source_dir, glob="*.txt", loader_cls=TextLoader,
                              loader_kwargs={"encoding": "utf-8"}).load()
            + DirectoryLoader(source_dir, glob="*.md",  loader_cls=TextLoader,
                              loader_kwargs={"encoding": "utf-8"}).load()
        )

        if not documents:
            logger.warning("RAG ingest: no documents found.")
            return False

        logger.info(f"RAG ingest: {len(documents)} documents — splitting…")
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.split_documents(documents)
        logger.info(f"RAG ingest: {len(chunks)} chunks — building ChromaDB…")

        os.makedirs(_CHROMA_DB_DIR, exist_ok=True)
        Chroma.from_documents(
            documents=chunks,
            embedding=self._get_embedding_model(),
            persist_directory=_CHROMA_DB_DIR,
        )

        # Reset cached DB so next call reloads the fresh index
        with self._model_lock:
            self._vector_db = None

        logger.info(f"RAG ingest: done — index saved to {_CHROMA_DB_DIR}")
        return True


# Module-level singleton — heavy objects are NOT loaded until first use
rag_service = RAGService()
