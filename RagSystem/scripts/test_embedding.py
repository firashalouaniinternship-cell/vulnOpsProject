import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

api_key = os.getenv("OPENROUTER_API_KEY")
embedding_model = os.getenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small")

print(f"API Key: {bool(api_key)}")
print(f"Embedding Model: {embedding_model}")

embeddings = OpenAIEmbeddings(
    model=embedding_model,
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=api_key
)

try:
    print("Testing Embedding...")
    vector = embeddings.embed_query("This is a test.")
    print(f"Success! Vector length: {len(vector)}")
except Exception as e:
    print(f"Error: {e}")
