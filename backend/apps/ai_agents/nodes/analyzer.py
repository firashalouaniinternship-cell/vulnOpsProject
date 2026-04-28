import logging
from core.utils.project_analyzer import ProjectAnalyzer
from ..state import GraphState

logger = logging.getLogger(__name__)

def analyzer_node(state: GraphState) -> GraphState:
    """
    Node 1: Analyzes the project structure to detect languages and frameworks.
    Reuses the existing ProjectAnalyzer logic.
    """
    repo_path = state.get("repo_path")
    if not repo_path:
        state["errors"] = state.get("errors", []) + ["No repo_path provided for analysis."]
        return state
        
    logger.info(f"[Analyzer Node] Analyzing project structure at {repo_path}")
    
    try:
        analyzer = ProjectAnalyzer(repo_path)
        analysis_result = analyzer.analyze()
        
        # Merge the analysis into the state
        state["project_context"] = {
            "languages": analysis_result.get("languages", []),
            "frameworks": analysis_result.get("frameworks", {}),
            "file_counts": analysis_result.get("file_counts", {}),
            "structure_summary": analysis_result.get("structure_summary", "")
        }
        logger.info(f"[Analyzer Node] Detected languages: {state['project_context']['languages']}")
    except Exception as e:
        logger.error(f"[Analyzer Node] Error: {str(e)}")
        state["errors"] = state.get("errors", []) + [f"Analyzer failed: {str(e)}"]
        
    return state
