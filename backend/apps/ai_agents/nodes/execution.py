import logging
from ..state import GraphState

logger = logging.getLogger(__name__)

def execution_node(state: GraphState) -> GraphState:
    """
    Node 3: Executes the selected scanners.
    In a full integration, this would call the actual classes in `backend/scanners/`
    or `backend/apps/scans/` and wait for their completion.
    """
    selected_scanners = state.get("selected_scanners", [])
    repo_path = state.get("repo_path")
    
    if not selected_scanners:
        logger.warning("[Execution Node] No scanners selected. Skipping execution.")
        state["raw_scan_results"] = {}
        return state
        
    logger.info(f"[Execution Node] Running scanners: {selected_scanners} on {repo_path}")
    
    # Placeholder for actual scanner execution logic
    # e.g., results = ScannerRunner(scanners=selected_scanners, path=repo_path).run_all()
    # For now we simulate an empty result structure to pass to the next node
    
    raw_results = {}
    for scanner in selected_scanners:
        raw_results[scanner] = {
            "vulnerabilities": [
                # Simulated vulnerability to show the flow
                {
                    "id": f"simulated-{scanner}-1",
                    "severity": "HIGH",
                    "file": "example.py" if scanner == "bandit" else "example.js",
                    "line": 42,
                    "description": "Simulated potential security issue."
                }
            ],
            "status": "success"
        }
        
    state["raw_scan_results"] = raw_results
    logger.info("[Execution Node] Scan execution complete.")
    
    return state
