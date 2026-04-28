import logging
from langchain_core.prompts import PromptTemplate
from ..llm_factory import get_best_model

logger = logging.getLogger(__name__)

class PipelineArchitectAgent:
    """
    Agent responsable de la génération automatique de pipelines CI/CD (GitHub Actions)
    pour l'intégration du scan de sécurité VulnOps.
    """
    
    def __init__(self):
        self.llm = get_best_model(temperature=0.1)
        self.prompt = PromptTemplate.from_template(
            """You are a DevSecOps Automation Expert. The user wants to integrate a VulnOps 
automated security scanning pipeline via GitHub Actions for their repository.

PROJECT CONTEXT:
Languages: {languages}
Frameworks: {frameworks}
Branch: {branch}

INSTRUCTIONS:
Generate a valid YAML file for `.github/workflows/vulnops-scan.yml`.
The workflow should:
1. Trigger on push to {branch} and pull requests.
2. Checkout the code.
3. Call the VulnOps API endpoint (e.g., `curl -X POST https://api.vulnops.com/scans/trigger`)
   Or just run the relevant open-source scanners (Bandit, Semgrep, etc.) based on the languages detected.
4. Output ONLY the YAML content, no markdown blocks, no explanations.

Make it clean and professional.
"""
        )

    def generate_pipeline(self, project_context: dict, branch: str = "main") -> str:
        """
        Génère le YAML du pipeline.
        """
        try:
            formatted_prompt = self.prompt.format(
                languages=", ".join(project_context.get("languages", ["Unknown"])),
                frameworks=str(project_context.get("frameworks", {})),
                branch=branch
            )
            
            response = self.llm.invoke(formatted_prompt)
            yaml_content = response.content.replace("```yaml", "").replace("```", "").strip()
            
            logger.info("[PipelineArchitect] Generated GitHub Actions workflow.")
            return yaml_content
            
        except Exception as e:
            logger.error(f"[PipelineArchitect] Error generating pipeline: {str(e)}")
            return ""

# Singleton instance
pipeline_agent = PipelineArchitectAgent()
