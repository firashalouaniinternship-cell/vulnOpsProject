import requests
import os
import json

# Minimal test for Ollama
url = "http://localhost:11434/api/chat"
model = "gemma4:31b-cloud"

data = {
    "model": model,
    "messages": [
        {"role": "user", "content": "Hello, answer with the word 'OK' only."}
    ],
    "stream": False
}

print(f"Testing connection to {url} with model {model}...")
try:
    response = requests.post(url, json=data, timeout=10)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response content:")
        print(response.json())
    else:
        print(f"Error Body: {response.text}")
except Exception as e:
    print(f"Connection failed: {e}")
