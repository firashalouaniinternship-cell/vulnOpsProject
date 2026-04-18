import sys
import os
from rag_logic import get_rag_chain, setup_rag, PERSIST_DIRECTORY

def main():
    # Ensure database is initialized
    if not os.path.exists(PERSIST_DIRECTORY):
        print("Database not found. Initializing...")
        setup_rag()
    
    # Get the chain
    print("Initializing RAG chain...")
    chain = get_rag_chain()
    
    # Interactive loop
    print("\n--- OWASP Top 10 for LLMs RAG System ---")
    print("Type 'exit' to quit.\n")
    
    while True:
        try:
            query = input("Ask a question about OWASP Top 10 for LLMs: ")
        except EOFError:
            break
            
        if query.lower() in ['exit', 'quit', 'q']:
            break
        
        if not query.strip():
            continue
            
        print("\nSearching and generating answer...")
        try:
            # Using the chain - now returns a dict because return_source_documents=True
            result = chain.invoke({"query": query})
            response = result["result"]
            sources = result["source_documents"]
            
            print("-" * 50)
            print(f"ANSWER:\n{response}")
            print("-" * 50)
            
            if sources:
                # Extract unique page numbers
                pages = sorted(list(set([doc.metadata.get('page', 0) + 1 for doc in sources])))
                pages_str = ", ".join(map(str, pages))
                print(f"SOURCES: Page(s) {pages_str}")
            print("-" * 50 + "\n")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
