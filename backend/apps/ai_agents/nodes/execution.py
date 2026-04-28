import logging
from ..state import GraphState
from services.orchestrator_service import OrchestratorService

logger = logging.getLogger(__name__)

def execution_node(state: GraphState) -> GraphState:
    """
    Node 3: Executes the selected scanners.
    Calls the actual OrchestratorService to run security tools.
    """
    selected_scanners = state.get("selected_scanners", [])
    repo_path = state.get("repo_path")
    
    if not selected_scanners:
        logger.warning("[Execution Node] No scanners selected. Skipping execution.")
        state["raw_scan_results"] = {}
        return state
        
    logger.info(f"[Execution Node] Running scanners: {selected_scanners} on {repo_path}")
    
    try:
        # Lancement réel des scanners via l'orchestrateur
        results = OrchestratorService.run_full_scan(
            target_path=str(repo_path),
            scanners=selected_scanners
        )
        
        # Groupement par scanner pour compatibilité avec les nœuds suivants
        raw_results = {}
        for scanner in selected_scanners:
            scanner_findings = [f for f in results if f.get('scanner_source') == scanner]
            raw_results[scanner] = {
                "vulnerabilities": scanner_findings,
                "status": "success"
            }
            
        state["raw_scan_results"] = raw_results
        logger.info(f"[Execution Node] Scan execution complete. Found {len(results)} total issues.")
        
    except Exception as e:
        logger.error(f"[Execution Node] Execution failed: {e}")
        state["raw_scan_results"] = {"error": str(e)}
        
    return state

