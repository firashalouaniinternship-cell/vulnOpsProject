import os
import sys
import json

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from apps.scans.rag_utils import get_vulnerability_score

def test_scoring():
    print("Testing LLM Scoring...")
    test_name = "subprocess_popen_with_shell_equals_true"
    issue_text = "subprocess call with shell=True identified, security issue."
    severity = "HIGH"
    context = "Dépôt Python critique gérant des données bancaires."
    
    result = get_vulnerability_score(test_name, issue_text, severity, context)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    if "score" in result and 0 <= result["score"] <= 1:
        print("SUCCESS: Score is within [0, 1] range.")
    else:
        print("FAILURE: Invalid score format or range.")

if __name__ == "__main__":
    test_scoring()
