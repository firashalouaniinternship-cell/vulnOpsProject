import json
import logging
from ..core.config import Config
from ..connectors.llm import LLMConnector

logger = logging.getLogger(__name__)

class RAGService:
    """Core service for RAG recommendations and scoring."""
    
    def __init__(self):
        from .ingestion_service import IngestionService
        self.ingestion = IngestionService()
        self.vector_db = self.ingestion.get_vector_db()

    def invoke(self, input_data):
        """Main entry point for getting a recommendation using real retrieval."""
        query = input_data.get("query", "")
        
        system_prompt = (
            "You are an elite Security Architect specializing in the OWASP Top 10 for LLMs. "
            "Analyze the vulnerability and provide a structured mitigation recommendation. "
            "Use the provided context from security documentation to back your advice. "
            "CRITICAL: Always identify which OWASP Top 10 for LLMs category (e.g., LLM01, LLM02) applies. "
            "Use Markdown formatting."
        )
        
        try:
            # Rechauffer la DB et chercher les documents pertinents
            logger.info(f"Performing similarity search for: {query[:50]}...")
            docs = self.vector_db.similarity_search(query, k=3)
            
            context_text = "\n\n".join([doc.page_content for doc in docs])
            full_user_prompt = f"CONTEXT FROM DOCUMENTATION:\n{context_text}\n\nUSER QUERY:\n{query}"
            
            result_text = LLMConnector.call_llm(system_prompt, full_user_prompt)
            
            if result_text.startswith("Error"):
                return {"result": result_text, "source_documents": []}
            
            return {
                "result": result_text,
                "source_documents": docs
            }
        except Exception as e:
            logger.error(f"RAG invocation failed: {e}")
            return {"result": f"Request failed: {str(e)}", "source_documents": []}

    def score_vulnerability(self, input_data):
        """Analyzes and priority-scores a vulnerability."""
        query = input_data.get("query", "")
        context = input_data.get("context", "General project")
        
        system_prompt = "You are a specialized Security Project Lead. Your goal is to prioritize vulnerabilities for developers."
        prompt = (
            f"You are an expert Security Analyst. Consider the project landscape and OTHER detected threats: {context}.\n\n"
            f"Analyze and PRIORITY-SCORE this specific vulnerability:\n{query}\n\n"
            "Assign a score between 0.0 and 1.0 (1.0 = top priority fix). "
            "Return ONLY a JSON object: {\"score\": 0.85, \"reasoning\": \"...\"}"
        )
        
        try:
            result_text = LLMConnector.call_llm(system_prompt, prompt, json_mode=True)
            if result_text.startswith("Error"):
                return {"score": 0.5, "reasoning": result_text}
                
            return json.loads(result_text)
        except Exception as e:
            logger.error(f"Vulnerability scoring failed: {e}")
            return {"score": 0.5, "reasoning": f"Scoring failed: {str(e)}"}
