import logging
import json
from langchain_core.prompts import PromptTemplate
from ..state import GraphState
from ..llm_factory import get_best_model

logger = logging.getLogger(__name__)

def remediation_node(state: GraphState) -> GraphState:
    """
    Node 5: Generates remediation code patches for triaged vulnerabilities.
    """
    vulns = state.get("triaged_vulnerabilities", [])
    
    if not vulns:
        logger.info("[Remediation Node] No vulnerabilities to remediate.")
        state["remediation_patches"] = []
        return state
        
    logger.info("[Remediation Node] Generating remediation patches...")
    llm = get_best_model(temperature=0.3)
    
    prompt = PromptTemplate.from_template(
        """You are an expert Secure Developer. For each vulnerability provided below, 
generate a precise code patch to fix it.

VULNERABILITIES:
{vulnerabilities}

INSTRUCTIONS:
1. Understand the vulnerability context.
2. Provide the exact lines of code to replace or add.
3. Provide a brief explanation of the fix.
4. Output as JSON array.

JSON Format expected:
[
  {{
    "vuln_id": "the_id",
    "file_path": "path/to/file",
    "explanation": "Why this fixes the issue",
    "code_diff": "```diff\\n- old code\\n+ new code\\n```"
  }}
]
"""
    )
    
    try:
        formatted_prompt = prompt.format(vulnerabilities=json.dumps(vulns, indent=2))
        
        response = llm.invoke(formatted_prompt)
        content = response.content.replace("```json", "").replace("```", "").strip()
        patches = json.loads(content)
        
        state["remediation_patches"] = patches
        logger.info(f"[Remediation Node] Generated {len(patches)} patches.")
        
    except Exception as e:
        logger.error(f"[Remediation Node] Error during remediation: {str(e)}")
        state["errors"] = state.get("errors", []) + [f"Remediation failed: {str(e)}"]
        state["remediation_patches"] = []

    return state
