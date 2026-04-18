import os
import sys
import json

# Add backend directory to path
sys.path.append(os.path.abspath('backend'))

from scanners.sast.eslint_runner import run_full_eslint_scan

# Test with a small public JS repo
repo_url = 'https://github.com/tj/n.git'
print(f"Testing full scan on {repo_url}")

result = run_full_eslint_scan(repo_url, 'mock_token', 'tj', 'n')

print("\n--- Scan Result ---")
print(f"Success: {result.get('success')}")
if result.get('success'):
    vuls = result.get('vulnerabilities', [])
    metrics = result.get('metrics', {})
    print(f"Found {len(vuls)} issues")
    print(f"Metrics: {metrics}")
    if vuls:
        print(f"First issue: {vuls[0]['issue_text']} at {vuls[0]['filename']}:{vuls[0]['line_number']}")
else:
    print(f"Error: {result.get('error')}")
