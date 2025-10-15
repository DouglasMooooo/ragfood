import os
import requests
from dotenv import load_dotenv

# 载入环境变量
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("❌ GROQ_API_KEY not found in .env")
    exit()

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "llama-3.1-8b-instant",
    "messages": [
        {"role": "user", "content": "Hello Groq, how are you today?"}
    ]
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    print("✅ Groq Cloud connection successful!")
    print("Response:\n", response.json()["choices"][0]["message"]["content"])
else:
    print("❌ Error:", response.status_code, response.text)
