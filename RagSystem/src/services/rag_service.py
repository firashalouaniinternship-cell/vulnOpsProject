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
        """Main entry point for getting an enriched security recommendation."""
        query = input_data.get("query", "")

        system_prompt = (
            "You are a Senior Application Security Engineer specialized in code vulnerability remediation. "
            "You analyze findings produced by SAST scanners (Bandit, Semgrep, ESLint, GoSec, Brakeman, etc.), "
            "SCA tools (OWASP Dependency-Check), container scanners (Trivy), and DAST tools (OWASP ZAP). "
            "Use the OWASP Top 10 2021, OWASP Cheat Sheets, and CWE knowledge provided as context to give "
            "precise, actionable remediation advice grounded in official standards. "
            "You MUST follow this exact structure:\n\n"
            "### Analyse de la Vulnérabilité\n"
            "**Catégorie OWASP / CWE :** (Identifiez la catégorie OWASP Top 10 2021 (ex: A03 - Injection) "
            "et le CWE correspondant (ex: CWE-89). Expliquez pourquoi cette faille est dangereuse.)\n"
            "**Vecteur d'attaque :** (Décrivez concrètement comment un attaquant exploiterait cette faille "
            "dans le contexte du code signalé par le scanner.)\n\n"
            "### Remédiation\n"
            "**Bonnes pratiques :** (Listez les principes de secure coding à appliquer selon l'OWASP Cheat Sheet Series.)\n"
            "**Exemple de code corrigé :** (Fournissez un extrait de code sécurisé, dans le langage du scanner "
            "qui a détecté la faille si possible.)\n"
            "**Références :** (Citez les sources OWASP/CWE pertinentes.)\n\n"
            "Répondez en français. Utilisez le format Markdown. Soyez précis et pédagogique."
        )
        
        try:
            # Recherche de documents pertinents (k=5 pour plus de contexte)
            logger.info(f"Performing deep security similarity search for: {query[:50]}...")
            docs = self.vector_db.similarity_search(query, k=5)
            
            context_text = "\n\n".join([doc.page_content for doc in docs])
            full_user_prompt = (
                f"CONTEXTE DE SÉCURITÉ (OWASP/CWE/BEST PRACTICES):\n{context_text}\n\n"
                f"VULNÉRABILITÉ DÉTECTÉE À ANALYSER :\n{query}"
            )
            
            result_text = LLMConnector.call_llm(system_prompt, full_user_prompt)
            
            if result_text.startswith("Error"):
                return {"result": result_text, "source_documents": []}
            
            return {
                "result": result_text,
                "source_documents": [doc.metadata for doc in docs] # Return metadata instead of full docs for efficiency
            }
        except Exception as e:
            logger.error(f"RAG enriched invocation failed: {e}")
            return {"result": f"Enrichment failed: {str(e)}", "source_documents": []}


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
