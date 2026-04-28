import logging
import json
from langchain_core.prompts import PromptTemplate
from ..state import GraphState
from ..llm_factory import get_best_model

logger = logging.getLogger(__name__)

def reporting_node(state: GraphState) -> GraphState:
    """
    Node 6: Aggregates everything into a professional final report.
    """
    context = state.get("project_context", {})
    vulns = state.get("triaged_vulnerabilities", [])
    patches = state.get("remediation_patches", [])
    
    logger.info("[Reporting Node] Generating final report...")
    llm = get_best_model(temperature=0.1)
    
    prompt = PromptTemplate.from_template(
        """You are a Lead DevSecOps Engineer. Write a professional executive summary 
and final markdown report for the security scan of this project.

PROJECT CONTEXT:
{context}

VULNERABILITIES (Triaged):
{vulns}

REMEDIATION PATCHES:
{patches}

INSTRUCTIONS:
1. Write a professional, structured Markdown report.
2. Include an Executive Summary.
3. List the vulnerabilities by severity.
4. Provide the code patches clearly.
5. Do NOT use any code blocks formatting for the whole response, just pure Markdown.
"""
    )
    
    try:
        formatted_prompt = prompt.format(
            context=json.dumps(context, indent=2),
            vulns=json.dumps(vulns, indent=2),
            patches=json.dumps(patches, indent=2)
        )
        
        response = llm.invoke(formatted_prompt)
        state["final_report"] = response.content
        logger.info("[Reporting Node] Final report generated successfully.")
        
    except Exception as e:
        logger.error(f"[Reporting Node] Error: {str(e)}")
        state["errors"] = state.get("errors", []) + [f"Reporting failed: {str(e)}"]
        state["final_report"] = "Error generating report."

    return state
