import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.scans.defectdojo_utils import push_to_defectdojo
import tempfile
import json

def test_push():
    print("Testing DefectDojo Push...")
    
    # Create a dummy report in Bandit format
    report = {
        "generated_at": "2026-04-16T12:00:00Z",
        "results": [
            {
                "test_id": "B101",
                "test_name": "assert_used",
                "issue_text": "Use of assert detected.",
                "issue_severity": "LOW",
                "issue_confidence": "HIGH",
                "filename": "test.py",
                "line_number": 1,
                "line_range": [1],
                "code": "assert True",
                "more_info": "https://bandit.readthedocs.io/en/latest/blacklists/blacklist_calls.html#b101-assert-used"
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as tf:
        json.dump(report, tf)
        temp_path = tf.name
        
    try:
        # We use a apps.scans type that DefectDojo understands or our mapping handles
        # 'bandit' maps to 'Bandit Scan'
        success = push_to_defectdojo(temp_path, 'bandit')
        print(f"Push Success: {success}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    test_push()
