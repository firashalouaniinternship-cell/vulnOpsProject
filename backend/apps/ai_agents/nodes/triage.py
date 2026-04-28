import logging
import json
from langchain_core.prompts import PromptTemplate
from ..state import GraphState
from ..llm_factory import get_best_model

logger = logging.getLogger(__name__)

def triage_node(state: GraphState) -> GraphState:
    """
    Node 4: Triages vulnerabilities. Removes false positives and scores them based on project context.
    """
    raw_results = state.get("raw_scan_results", {})
    context = state.get("project_context", {})
    
    if not raw_results:
        logger.info("[Triage Node] No raw results to triage.")
        state["triaged_vulnerabilities"] = []
        return state
        
    logger.info("[Triage Node] Triaging vulnerabilities with LLM...")
    llm = get_best_model(temperature=0.2)
    
    prompt = PromptTemplate.from_template(
        """You are a senior Application Security Engineer. Review the following raw scan results 
from automated tools. Your job is to filter out obvious false positives and score the remaining 
vulnerabilities from 0.0 to 10.0 based on the actual project context.

PROJECT CONTEXT:
Languages: {languages}
Frameworks: {frameworks}
Summary: {summary}

RAW SCAN RESULTS:
{raw_results}

INSTRUCTIONS:
1. Identify false positives (e.g., test files, mock data, acceptable risks in context).
2. For REAL vulnerabilities, assign a unified CVSS-like score (0.0 to 10.0).
3. Return ONLY a JSON list of triaged vulnerabilities.

JSON Format expected:
[
  {{
    "id": "original_id",
    "scanner": "tool_name",
    "status": "real" or "false_positive",
    "justification": "Brief explanation",
    "severity": "CRITICAL" / "HIGH" / "MEDIUM" / "LOW",
    "score": 8.5
  }}
]
"""
    )
    
    try:
        formatted_prompt = prompt.format(
            languages=", ".join(context.get("languages", [])),
            frameworks=json.dumps(context.get("frameworks", {})),
            summary=context.get("structure_summary", ""),
            raw_results=json.dumps(raw_results, indent=2)
        )
        
        response = llm.invoke(formatted_prompt)
        content = response.content.replace("```json", "").replace("```", "").strip()
        triaged_data = json.loads(content)
        
        # Filter out false positives
        final_vulns = [v for v in triaged_data if v.get("status") == "real"]
        
        state["triaged_vulnerabilities"] = final_vulns
        logger.info(f"[Triage Node] Triaged down to {len(final_vulns)} real vulnerabilities.")
        
    except Exception as e:
        logger.error(f"[Triage Node] Error during triage: {str(e)}")
        state["errors"] = state.get("errors", []) + [f"Triage failed: {str(e)}"]
        state["triaged_vulnerabilities"] = [] # fallback empty

    return state
