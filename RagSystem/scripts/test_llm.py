import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

api_key = os.getenv("OPENROUTER_API_KEY")
model_name = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

print(f"API Key found: {bool(api_key)}")
print(f"Model: {model_name}")

llm = ChatOpenAI(
    model=model_name,
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=api_key
)

try:
    print("Testing LLM...")
    response = llm.invoke("Say hello")
    print(f"Response: {response.content}")
except Exception as e:
    print(f"Error: {e}")
