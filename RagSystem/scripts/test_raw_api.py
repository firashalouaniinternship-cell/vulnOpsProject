import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

api_key = os.getenv("OPENROUTER_API_KEY")
model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

print(f"API Key found: {bool(api_key)}")

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
data = {
    "model": model,
    "messages": [{"role": "user", "content": "Say hello"}]
}

try:
    print("Testing OpenRouter API with requests...")
    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()['choices'][0]['message']['content']}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
