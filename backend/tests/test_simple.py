#!/usr/bin/env python
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Test imports
try:
    from scanners.sast.eslint_runner import run_eslint, parse_eslint_results
    print("ESLint imports OK")
except Exception as e:
    print(f"ESLint import failed: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)

# Test run_eslint on a test directory
print("\nTesting ESLint runner on a test directory...")

import tempfile
import shutil
test_dir = tempfile.mkdtemp(prefix='eslint_test_')
test_file = os.path.join(test_dir, 'test.js')

with open(test_file, 'w') as f:
    f.write('console.log("hello");\nvar x = 1;\n')

try:
    result = run_eslint(test_dir)
    print(f"ESLint result type: {type(result)}")
    print(f"ESLint result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
    
    if 'errors' in result:
        print(f"Error in ESLint: {result['errors']}")
    else:
        print(f"Result length: {len(result) if isinstance(result, (list, dict)) else 'N/A'}")
        
        # Count entries
        if isinstance(result, list):
            print(f"List with {len(result)} items")
        elif isinstance(result, dict):
            print(f"Dict with keys: {list(result.keys())}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    print(traceback.format_exc())
finally:
    shutil.rmtree(test_dir, ignore_errors=True)
