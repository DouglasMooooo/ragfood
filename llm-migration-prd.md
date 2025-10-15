# LLM Migration Design Document
1. Overview

We are migrating the local Ollama inference pipeline to Groq Cloud for improved scalability, response speed, and reduced local dependency.

2. Architecture Comparison
Feature	Ollama (Local)	Groq Cloud (LLM API)
Model Access	Localhost 11434	Remote HTTPS API
Deployment	On-device	Cloud-hosted
Cost	Free (local)	Usage-based billing
Latency	Local CPU-bound	Optimized GPU inference
Authentication	None	API key (Bearer token)
Maintenance	Requires local model files	Managed automatically
3. Migration Objectives

Replace all Ollama API calls (localhost:11434) with Groq REST API.

Remove local Ollama dependencies.

Use environment variable GROQ_API_KEY for authentication.

Keep same RAG logic and Upstash Vector integration.

Maintain identical CLI UX (py rag_run.py).

4. Implementation Plan

Step 1 – Environment Setup
Add the following to .env:

GROQ_API_KEY="your_api_key_here"
GROQ_MODEL="llama-3.1-8b-instant"


Step 2 – Install Dependencies

pip install requests python-dotenv


Step 3 – Modify Code
Replace this：

response = requests.post("http://localhost:11434/api/generate", json={...})


With this：

response = requests.post(
  "https://api.groq.com/openai/v1/chat/completions",
  headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}", "Content-Type": "application/json"},
  json={
    "model": os.getenv("GROQ_MODEL"),
    "messages": [
      {"role": "system", "content": "You are a helpful AI assistant."},
      {"role": "user", "content": query_text}
    ]
  }
)

5. API Differences & Implications
Aspect	Ollama	Groq
Endpoint	/api/generate	/openai/v1/chat/completions
Payload format	prompt	messages (list of role-based entries)
Streaming	Optional	Supported via HTTP chunks
Authentication	None	Bearer token required
6. Error Handling Strategy
try:
  response = requests.post(...)
  response.raise_for_status()
except requests.exceptions.RequestException as e:
  print(f"❌ Groq API Error: {e}")


Add graceful exit on 401 Unauthorized and 429 Rate Limit Exceeded.

7. Performance Considerations

Groq Cloud runs on TPU/GPU hardware → much lower latency.

Network round trip adds ~50–100 ms.

No need for local CPU resources or model downloads.

8. Cost & Security

Usage-based billing (~$0.20 / 1M tokens as of 2025).

Keep API keys in .env and exclude from Git using .gitignore.