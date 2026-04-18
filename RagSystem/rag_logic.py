"""
Proxy module for backward compatibility.
Redirects calls to the new modular architecture in src/services.
"""
import sys
import os

# Add src to path if needed
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.services.rag_service import RAGService
except ImportError:
    # Fallback if running from within src or other path issues
    from services.rag_service import RAGService

def get_rag_chain():
    """Returns the new RAGService instance which is compatible with the old SimpleChain."""
    return RAGService()

if __name__ == "__main__":
    import json
    chain = get_rag_chain()
    query = "Test query"
    print(json.dumps(chain.invoke({"query": query})))
