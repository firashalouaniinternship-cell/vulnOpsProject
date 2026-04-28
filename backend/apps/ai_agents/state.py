from typing import TypedDict, List, Dict, Any, Optional

class GraphState(TypedDict):
    """
    Represents the state of our DevSecOps Agentic workflow.
    """
    repo_url: Optional[str]
    repo_path: Optional[str]
    
    # Analyzer outputs
    project_context: Dict[str, Any]
    
    # Selector outputs
    selected_scanners: List[str]
    
    # Execution outputs (raw scanner results)
    raw_scan_results: Dict[str, Any]
    
    # Triage outputs
    triaged_vulnerabilities: List[Dict[str, Any]]
    
    # Remediation outputs
    remediation_patches: List[Dict[str, Any]]
    
    # Final report
    final_report: str
    
    # Auto PR flag
    auto_pr_enabled: bool
    pr_url: Optional[str]
    
    # Error tracking
    errors: List[str]
