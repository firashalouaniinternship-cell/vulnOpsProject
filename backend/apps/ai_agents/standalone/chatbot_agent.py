import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from ..llm_factory import get_best_model

logger = logging.getLogger(__name__)

class SecurityChatbotAgent:
    """
    Agent conversationnel pour assister l'utilisateur sur la sécurité 
    et l'aider à comprendre les vulnérabilités de son projet spécifique.
    """
    
    def __init__(self):
        self.llm = get_best_model(temperature=0.5)
        self.system_prompt = """You are 'VulnOps Assistant', a professional Application Security Expert.
Your job is to answer the user's questions regarding DevSecOps, vulnerabilities, and best practices.

Use the following project context to give precise, tailored answers:
PROJECT CONTEXT:
Languages: {languages}
Frameworks: {frameworks}
Summary: {summary}

If the user asks about a specific vulnerability, refer to this recent report context (if provided):
REPORT CONTEXT:
{report_context}

Be helpful, concise, and provide code examples where applicable.
"""
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{user_input}")
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()

    def chat(self, user_input: str, project_context: dict = None, report_context: str = "") -> str:
        """
        Gère une interaction de chat.
        :param user_input: La question de l'utilisateur.
        :param project_context: Le contexte du projet.
        :param report_context: Le rapport de scan le plus récent.
        """
        ctx = project_context or {}
        
        try:
            response = self.chain.invoke({
                "languages": ", ".join(ctx.get("languages", [])),
                "frameworks": str(ctx.get("frameworks", {})),
                "summary": ctx.get("structure_summary", "No specific context provided."),
                "report_context": report_context or "No recent scan report available.",
                "user_input": user_input
            })
            return response
            
        except Exception as e:
            logger.error(f"[ChatbotAgent] Error generating response: {str(e)}")
            return "Désolé, j'ai rencontré une erreur en tentant de traiter votre demande de sécurité."

# Singleton instance
chatbot_agent = SecurityChatbotAgent()
