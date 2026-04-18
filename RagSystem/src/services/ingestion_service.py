import os
import logging
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from ..core.config import Config

logger = logging.getLogger(__name__)

class IngestionService:
    """Service to ingest documents into the ChromaDB vector store."""
    
    def __init__(self):
        self.embedding_model = OpenAIEmbeddings(
            model=Config.OPENROUTER_EMBEDDING_MODEL,
            openai_api_key=Config.OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1"
        )
        self.db_dir = Config.CHROMA_DB_DIR
        self.source_dir = Config.SOURCE_DOCS_DIR

    def ingest_all(self):
        """Loads, splits and indexes all documents in the source directory."""
        if not os.path.exists(self.source_dir):
            os.makedirs(self.source_dir)
            logger.warning(f"Source directory created: {self.source_dir}. Add documents here.")
            return False

        logger.info(f"Loading documents from {self.source_dir}...")
        
        # Support PDF and Text files
        pdf_loader = DirectoryLoader(self.source_dir, glob="*.pdf", loader_cls=PyPDFLoader)
        txt_loader = DirectoryLoader(self.source_dir, glob="*.txt", loader_cls=TextLoader)
        
        documents = pdf_loader.load() + txt_loader.load()
        
        if not documents:
            logger.warning("No documents found to ingest.")
            return False

        logger.info(f"Loaded {len(documents)} documents. Splitting into chunks...")
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            add_start_index=True
        )
        chunks = text_splitter.split_documents(documents)
        
        logger.info(f"Created {len(chunks)} chunks. Updating Vector Store at {self.db_dir}...")
        
        # Persist to disk
        vector_db = Chroma.from_documents(
            documents=chunks,
            embedding=self.embedding_model,
            persist_directory=self.db_dir
        )
        vector_db.persist()
        
        logger.info("Ingestion complete and persisted successfully.")
        return True

    def get_vector_db(self):
        """Returns the persisted Chroma vector store."""
        return Chroma(
            persist_directory=self.db_dir,
            embedding_function=self.embedding_model
        )
