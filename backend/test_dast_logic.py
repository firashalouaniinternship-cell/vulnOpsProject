import os
import sys
import tempfile
import shutil

# Add backend to path to import zaproxy_runner
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mocking some imports that zaproxy_runner might need that are not available in this script context
# Actually, it's better to just copy the logic or ensure it can run standalone

from scanners.dast.zaproxy_runner import check_dast_prerequisites

def test_prereqs():
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Testing in {tmpdir}")
        
        # Test 1: Empty dir
        res = check_dast_prerequisites(tmpdir)
        print("Empty dir:", res)
        assert res['ready'] == False
        assert 'Dockerfile' in res['missing']
        
        # Test 2: With Dockerfile
        with open(os.path.join(tmpdir, 'Dockerfile'), 'w') as f:
            f.write("FROM python:3.9")
        
        res = check_dast_prerequisites(tmpdir)
        print("With Dockerfile:", res)
        assert res['ready'] == True
        assert res['found']['dockerfile'] == True
        assert res['dockerfile_content'] == "FROM python:3.9"
        
        # Test 3: With OpenAPI
        with open(os.path.join(tmpdir, 'openapi.yaml'), 'w') as f:
            f.write("openapi: 3.0.0")
            
        res = check_dast_prerequisites(tmpdir)
        print("With Dockerfile + OpenAPI:", res)
        assert res['found']['openapi'] == True
        assert 'Spécification OpenAPI (ex: openapi.yaml)' not in res['missing']

if __name__ == "__main__":
    try:
        test_prereqs()
        print("\nVerification SUCCESSFUL!")
    except Exception as e:
        print(f"\nVerification FAILED: {e}")
        import traceback
        traceback.print_exc()
