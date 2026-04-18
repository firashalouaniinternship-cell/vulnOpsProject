import os
import sys
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.services.ingestion_service import IngestionService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IngestDocs")

def main():
    logger.info("Starting document ingestion process...")
    try:
        service = IngestionService()
        success = service.ingest_all()
        if success:
            logger.info("✅ All documents ingested successfully into ChromaDB.")
        else:
            logger.warning("⚠️ No documents were ingested. Check data/source_docs folder.")
    except Exception as e:
        logger.error(f"❌ Critical error during ingestion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
