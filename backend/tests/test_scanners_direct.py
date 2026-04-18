#!/usr/bin/env python
"""Direct test of ESLint runner without using Django ORM"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

# Test imports
try:
    from scanners.sast.eslint_runner import run_eslint, parse_eslint_results
    print("[OK] ESLint imports OK")
except Exception as e:
    print(f"[FAIL] ESLint import failed: {e}")
    sys.exit(1)

# Test run_eslint on a real project (react)
print("\nTesting ESLint runner on a test directory...")

# Create a test file
import tempfile
test_dir = tempfile.mkdtemp(prefix='eslint_test_')
test_file = os.path.join(test_dir, 'test.js')

with open(test_file, 'w') as f:
    f.write("""
console.log('hello');
var x = 1;
""")

try:
    result = run_eslint(test_dir)
    print(f"ESLint result type: {type(result)}")
    print(f"ESLint result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
    
    if 'errors' in result:
        print(f"Error in ESLint: {result['errors']}")
    else:
        print(f"Result: {result}")
        
        # Try parsing
        vulnerabilities = parse_eslint_results(result, test_dir)
        print(f"Vulnerabilities found: {len(vulnerabilities)}")
        for v in vulnerabilities[:3]:
            print(f"  - {v['test_id']}: {v['issue_text']}")
        
except Exception as e:
    import traceback
    print(f"✗ Error: {e}")
    print(traceback.format_exc())
finally:
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)

# Test Semgrep similar
print("\n" + "="*50)
print("Testing Semgrep runner on a test directory...")

try:
    from scanners.sast.semgrep_runner import run_semgrep, parse_semgrep_results
    print("✓ Semgrep imports OK")
    
    # Create a test file
    test_dir = tempfile.mkdtemp(prefix='semgrep_test_')
    test_file = os.path.join(test_dir, 'test.py')
    
    with open(test_file, 'w') as f:
        f.write("""
import pickle
pickle.loads(user_input)
""")
    
    result = run_semgrep(test_dir)
    print(f"Semgrep result type: {type(result)}")
    print(f"Semgrep result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
    
    if 'errors' in result:
        print(f"Error in Semgrep: {result['errors']}")
    else:
        print(f"Results found: {len(result.get('results', []))}")
        
        # Try parsing
        vulnerabilities = parse_semgrep_results(result, test_dir)
        print(f"Vulnerabilities found: {len(vulnerabilities)}")
        
except Exception as e:
    import traceback
    print(f"✗ Error: {e}")
    print(traceback.format_exc())
finally:
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
