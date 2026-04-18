import os
import sys
import django

# Configuration Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from scanners.sast.sonar_runner import run_full_sonar_scan, parse_sonar_results

# Test mock data parsing to verify logic without having Sonar Scanner installed
mock_issues = [
    {
        "key": "AXZQ123",
        "rule": "java:S1144",
        "severity": "CRITICAL",
        "component": "my-project:src/main/java/Main.java",
        "line": 42,
        "message": "Unused private method should be removed",
        "type": "CODE_SMELL"
    },
    {
        "key": "AXZQ124",
        "rule": "java:S2077",
        "severity": "BLOCKER",
        "component": "my-project:src/main/java/Auth.java",
        "line": 15,
        "message": "Formatting SQL queries is security-sensitive",
        "type": "VULNERABILITY",
        "textRange": {
            "startLine": 15,
            "endLine": 15
        }
    }
]

def run_tests():
    print("Test 1: Parsing Sonar results")
    vulns = parse_sonar_results(mock_issues)
    for v in vulns:
        print(f"[{v['severity']}] {v['filename']} L{v['line_number']}: {v['issue_text']}")
    
    assert len(vulns) == 2
    assert vulns[0]['severity'] == 'HIGH' # CRITICAL maps to HIGH
    assert vulns[1]['severity'] == 'HIGH' # BLOCKER maps to HIGH
    assert vulns[1]['filename'] == 'src/main/java/Auth.java'
    
    print("\nTest 2: Full scan flow (Should fail gracefully because no token/apps.scans)")
    result = run_full_sonar_scan("https://github.com/spring-projects/spring-petclinic.git", "mock_access_token", "spring-projects", "spring-petclinic")
    print(f"Result: {result}")
    assert result['success'] is False

if __name__ == "__main__":
    run_tests()
    print("Tests finished.")
