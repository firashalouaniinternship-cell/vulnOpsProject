from langgraph.graph import StateGraph, END
import logging
from .state import GraphState
from .nodes.analyzer import analyzer_node
from .nodes.selector import selector_node
from .nodes.execution import execution_node
from .nodes.triage import triage_node
from .nodes.remediation import remediation_node
from .nodes.reporting import reporting_node
from .nodes.auto_pr import auto_pr_node

logger = logging.getLogger(__name__)

def build_devsecops_graph():
    """
    Builds and compiles the LangGraph State Graph for the VulnOps Agentic workflow.
    """
    workflow = StateGraph(GraphState)
    
    # Define the nodes
    workflow.add_node("analyzer", analyzer_node)
    workflow.add_node("selector", selector_node)
    workflow.add_node("execution", execution_node)
    workflow.add_node("triage", triage_node)
    workflow.add_node("remediation", remediation_node)
    workflow.add_node("reporting", reporting_node)
    workflow.add_node("auto_pr", auto_pr_node)
    
    # Define the edges (flow)
    workflow.set_entry_point("analyzer")
    workflow.add_edge("analyzer", "selector")
    workflow.add_edge("selector", "execution")
    workflow.add_edge("execution", "triage")
    workflow.add_edge("triage", "remediation")
    workflow.add_edge("remediation", "reporting")
    workflow.add_edge("reporting", "auto_pr")
    workflow.add_edge("auto_pr", END)
    
    # Compile the graph
    app = workflow.compile()
    return app

# Singleton instance of the graph
devsecops_agent_app = build_devsecops_graph()
