import os
import requests
import json
from dotenv import load_dotenv

# Load env
load_dotenv()

def test_ollama_connectivity():
    url = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
    model = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
    
    print(f"Testing Ollama at {url} with model {model}...")
    
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Say 'Ollama is working' if you can hear me."}
        ],
        "stream": False
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            print("✅ Success!")
            print(f"Response: {response.json()['message']['content']}")
        else:
            print(f"❌ Failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_ollama_connectivity()
