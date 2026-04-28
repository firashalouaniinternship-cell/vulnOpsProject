"""
Builds the ChromaDB vector index from downloaded security documentation.
Run after download_security_docs.py.

Usage (from backend/ directory, venv activated):
    python scripts/ingest_docs.py
"""

import sys
import logging
from pathlib import Path

# Make backend/ importable when running this script directly
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SOURCE_DOCS_DIR = str(BACKEND_DIR / "data" / "source_docs")
CHROMA_DB_DIR   = str(BACKEND_DIR / "data" / "chroma_db")


def main():
    import os

    if not os.path.exists(SOURCE_DOCS_DIR) or not os.listdir(SOURCE_DOCS_DIR):
        logger.error(
            f"No source documents found in {SOURCE_DOCS_DIR}.\n"
            "Run  python scripts/download_security_docs.py  first."
        )
        sys.exit(1)

    file_count = len([f for f in os.listdir(SOURCE_DOCS_DIR) if os.path.isfile(os.path.join(SOURCE_DOCS_DIR, f))])
    logger.info(f"Found {file_count} source files in {SOURCE_DOCS_DIR}")
    logger.info("Loading RAG service…")

    from rag.rag_service import rag_service

    logger.info("Starting ingestion (embedding model will be downloaded on first run)…")
    success = rag_service.ingest_documents(source_dir=SOURCE_DOCS_DIR)

    if success:
        logger.info("=" * 55)
        logger.info(f"ChromaDB index built successfully → {CHROMA_DB_DIR}")
        logger.info("The RAG service is ready. Start the Django backend normally.")
        logger.info("=" * 55)
    else:
        logger.error("Ingestion failed — check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
