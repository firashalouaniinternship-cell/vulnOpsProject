import subprocess
import os
import json
import json
import logging

logger = logging.getLogger(__name__)

# Paths
# rag_utils.py is in backend/rag/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # This is the 'backend' folder
PROJECT_ROOT = os.path.dirname(BASE_DIR) # This is the parent of 'backend'
RAG_SYSTEM_DIR = os.path.join(PROJECT_ROOT, "RagSystem")
RAG_VENV_PYTHON = os.path.join(RAG_SYSTEM_DIR, "venv", "Scripts", "python.exe")
RAG_LOGIC_SCRIPT = os.path.join(RAG_SYSTEM_DIR, "rag_logic.py")

def get_vulnerability_recommendation(test_name, issue_text, cwe=None, code_snippet=None):
    """
    Calls the RAG system to get a security recommendation.
    Uses subprocess to run the RAG logic in its own virtual environment.
    """
    query = f"Vulnerability: {test_name}. Description: {issue_text}."
    if cwe:
        query += f" CWE: {cwe}."
    if code_snippet:
        query += f"\nCode Context:\n```\n{code_snippet}\n```"
    query += "\n\nProvide a concise mitigation recommendation and mention the relevant OWASP Top 10 for LLMs category if applicable."

    # Using a small helper snippet to run the chain and print JSON
    helper_code = f"""
import os
import json
from rag_logic import get_rag_chain

chain = get_rag_chain()
result = chain.invoke({{"query": {json.dumps(query)}}})
output = {{
    "result": result["result"],
    "sources": [doc.metadata.get('page', 0) + 1 for doc in result["source_documents"]]
}}
print(json.dumps(output))
"""
    
    # Prepare environment with stabilization flags
    env = os.environ.copy()
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    
    try:
        logger.info(f"Starting RAG subprocess for query: {query[:50]}...")
        # Run the RAG logic
        process = subprocess.Popen(
            [RAG_VENV_PYTHON, "-c", helper_code],
            cwd=RAG_SYSTEM_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',  # Handle Windows-1252 chars gracefully
            env=env,
            bufsize=1 # Line buffered
        )
        logger.info(f"Waiting for RAG response (timeout=300s)...")
        stdout, stderr = process.communicate(timeout=300)
        stdout = stdout or ""
        stderr = stderr or ""
        
        if process.returncode != 0:
            logger.error(f"RAG subprocess error (code {process.returncode}): {stderr}")
            return {"error": "Failed to generate recommendation", "details": stderr}
        
        # Parse the JSON output from the script
        # We need to find the line that contains the JSON (in case there are warnings)
        last_line = ""
        for line in stdout.splitlines():
            if line.strip():
                last_line = line
            try:
                # Look for the JSON result object
                if '{"result":' in line:
                    return json.loads(line)
            except json.JSONDecodeError:
                continue
                
        if last_line:
            try:
                return json.loads(last_line)
            except json.JSONDecodeError:
                pass

        return {"error": "No valid JSON output from RAG system", "raw_stdout": stdout[:500]}

    except subprocess.TimeoutExpired:
        logger.error("RAG subprocess timed out")
        return {"error": "Recommendation generation timed out"}
    except Exception as e:
        logger.error(f"Unexpected error in rag_utils: {str(e)}")
        return {"error": str(e)}

def get_vulnerability_score(test_name, issue_text, severity, context_summary, code_snippet=None):
    """
    Calls the RAG system to get a security score (0-1).
    """
    query = f"Vulnerability: {test_name}. Description: {issue_text}. Scanner Severity: {severity}."
    if code_snippet:
        query += f"\nCode Context:\n```\n{code_snippet}\n```"
    
    # Helper to run the scoring
    helper_code = f"""
import os
import json
from rag_logic import get_rag_chain

chain = get_rag_chain()
result = chain.score_vulnerability({{
    "query": {json.dumps(query)},
    "context": {json.dumps(context_summary)}
}})
print(json.dumps(result))
"""
    
    env = os.environ.copy()
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    
    try:
        process = subprocess.Popen(
            [RAG_VENV_PYTHON, "-c", helper_code],
            cwd=RAG_SYSTEM_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',  # Handle Windows-1252 chars gracefully
            env=env
        )
        stdout, stderr = process.communicate(timeout=300)
        stdout = stdout or ""
        stderr = stderr or ""
        
        if process.returncode != 0:
            return {"score": 0.5, "reasoning": f"Subprocess error: {stderr}"}
        
        for line in stdout.splitlines():
            if '"score":' in line:
                return json.loads(line)
        
        return {"score": 0.5, "reasoning": "No score found in output"}

    except Exception as e:
        logger.error(f"Error in get_vulnerability_score: {e}")
        return {"score": 0.5, "reasoning": str(e)}
