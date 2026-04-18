import os
import sys
import json

# Add backend directory to path
sys.path.append(os.path.abspath('backend'))

from scanners.sast.cppcheck_runner import run_cppcheck, parse_cppcheck_results

test_repo = os.path.abspath('tmp')
print(f"Testing Cppcheck on {test_repo}")

# Note: We expect this to fail if cppcheck is not installed, 
# but it will test our error handling and logic.
result = run_cppcheck(test_repo)

if 'errors' in result:
    print(f"Caught expected error: {result['errors']}")
elif 'xml' in result:
    print("Received XML output!")
    vulns = parse_cppcheck_results(result['xml'], test_repo)
    print(f"Found {len(vulns)} issues")
    for v in vulns:
        print(f"- {v['issue_text']} at {v['filename']}:{v['line_number']}")
else:
    print(f"Unexpected result: {result}")
