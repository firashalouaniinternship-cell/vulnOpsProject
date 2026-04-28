import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.ai_agents.state import GraphState
from apps.ai_agents.nodes.analyzer import analyzer_node
from apps.ai_agents.nodes.selector import selector_node
from apps.ai_agents.nodes.execution import execution_node
from apps.ai_agents.nodes.triage import triage_node
from apps.ai_agents.nodes.remediation import remediation_node
from apps.ai_agents.nodes.reporting import reporting_node
from apps.ai_agents.nodes.auto_pr import auto_pr_node
from apps.ai_agents.graph import devsecops_agent_app
from apps.ai_agents.standalone.chatbot_agent import chatbot_agent
from apps.ai_agents.standalone.pipeline_agent import pipeline_agent

def test_nodes_sequentially():
    print("========================================")
    print("🔍 TESTING NODES SEQUENTIALLY")
    print("========================================")
    
    # Initialize empty state
    state: GraphState = {
        "repo_url": "https://github.com/vulnops/test-repo",
        "repo_path": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "project_context": {},
        "selected_scanners": [],
        "raw_scan_results": {},
        "triaged_vulnerabilities": [],
        "remediation_patches": [],
        "final_report": "",
        "auto_pr_enabled": False,
        "pr_url": None,
        "errors": []
    }
    
    print("\n--- 1. Node Analyzer ---")
    state = analyzer_node(state)
    print(f"Context Detected: {state.get('project_context')}")
    if state.get("errors"):
        print(f"Errors: {state['errors']}")
        
    print("\n--- 2. Node Selector ---")
    state = selector_node(state)
    print(f"Selected Scanners (Verified): {state.get('selected_scanners')}")
    
    print("\n--- 3. Node Execution ---")
    state = execution_node(state)
    print(f"Raw Scan Results Keys: {list(state.get('raw_scan_results', {}).keys())}")
    
    print("\n--- 4. Node Triage ---")
    state = triage_node(state)
    print(f"Triaged Vulnerabilities: {len(state.get('triaged_vulnerabilities', []))} items")
    if state.get("triaged_vulnerabilities"):
        print(f"Sample: {state['triaged_vulnerabilities'][0]}")
    
    print("\n--- 5. Node Remediation ---")
    state = remediation_node(state)
    print(f"Generated Patches: {len(state.get('remediation_patches', []))} items")
    
    print("\n--- 6. Node Reporting ---")
    state = reporting_node(state)
    print(f"Final Report (first 100 chars): {state.get('final_report', '')[:100]}...")
    
    print("\n--- 7. Node Auto-PR ---")
    state = auto_pr_node(state)
    print(f"PR URL: {state.get('pr_url')}")

def test_full_graph():
    print("\n========================================")
    print("🚀 TESTING FULL LANGGRAPH WORKFLOW")
    print("========================================")
    
    initial_state = {
        "repo_url": "https://github.com/vulnops/test-repo",
        "repo_path": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "auto_pr_enabled": False
    }
    
    print("Invoking graph... (this might take a minute depending on LLM speed)")
    final_state = devsecops_agent_app.invoke(initial_state)
    
    print("Graph execution complete!")
    print(f"Triaged: {len(final_state.get('triaged_vulnerabilities', []))} vulns")
    print(f"Patches: {len(final_state.get('remediation_patches', []))} patches")
    print("Final Report preview:")
    print(final_state.get("final_report", "")[:200] + "...\n")

def test_standalone_agents():
    print("\n========================================")
    print("🤖 TESTING STANDALONE AGENTS")
    print("========================================")
    
    ctx = {
        "languages": ["Python", "JavaScript"],
        "frameworks": {"Python": ["Django"]},
        "structure_summary": "A typical Django backend with React frontend."
    }
    
    print("\n--- 1. Chatbot Agent ---")
    question = "What is the best way to secure my Django models from SQL injection?"
    print(f"Q: {question}")
    answer = chatbot_agent.chat(question, project_context=ctx)
    print(f"A: {answer[:200]}...")
    
    print("\n--- 2. Pipeline Architect Agent ---")
    yaml_out = pipeline_agent.generate_pipeline(project_context=ctx, branch="develop")
    print("Generated YAML preview:")
    print("\n".join(yaml_out.splitlines()[:10]) + "...\n")

if __name__ == "__main__":
    print("Starting AI Agents Test Suite...")
    try:
        test_nodes_sequentially()
        test_full_graph()
        test_standalone_agents()
        print("\n✅ All tests executed successfully!")
    except Exception as e:
        import traceback
        print(f"\n❌ Error occurred during tests: {e}")
        traceback.print_exc()
