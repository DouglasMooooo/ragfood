import os
import json
import numpy as np
from dotenv import load_dotenv
from upstash_vector import Index
from groq import Groq
from sentence_transformers import SentenceTransformer

# 加载环境变量
load_dotenv()

# 初始化
model = SentenceTransformer("all-MiniLM-L6-v2")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
index = Index(
    url=os.getenv("UPSTASH_VECTOR_REST_URL"),
    token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
)

def create_embedding(text: str):
    """生成 384维嵌入并补齐到 1024维"""
    emb = model.encode(text)
    padded = np.pad(emb, (0, 1024 - len(emb)), 'constant')
    return padded.tolist()

def query_upstash(query_text, top_k=5, threshold=0.1):
    """查询最相似的向量"""
    query_vector = create_embedding(query_text)

    try:
        results = index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            include_vectors=False
        )
    except Exception as e:
        print("❌ Query failed:", e)
        return []

    # 统一兼容返回结构 - 修复后
    matches = []
    if isinstance(results, list):
        # Upstash 直接返回列表
        matches = results
    elif isinstance(results, dict):
        matches = results.get("matches", [])
    elif hasattr(results, "matches"):
        matches = results.matches

    if not matches:
        print("⚠️ No relevant context found (empty).")
        return []

    # 打印调试信息
    print(f"\n🔍 Found {len(matches)} results:")
    for m in matches:
        score = getattr(m, "score", 0)
        print(f"  ID: {m.id}, Score: {score:.4f}")

    # 过滤相似度低的项
    valid = [m for m in matches if getattr(m, "score", 0) > threshold]
    if not valid:
        print(f"⚠️ No relevant context found (all scores below threshold {threshold}).")
        return []

    return valid

def ask_groq(question, context):
    """把上下文 + 问题交给 Groq 模型"""
    prompt = f"""
You are a food expert AI. Use only the provided context to answer.

Context:
{context}

Question: {question}
Answer:
"""
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Groq error: {e}"

# 测试查询
print("=" * 60)
print("🧪 测试 RAG 查询")
print("=" * 60)

question = "I wanna eat some Asian food today"
print(f"\n❓ Question: {question}")

results = query_upstash(question)

if results:
    # 拼接上下文
    context_items = []
    for r in results:
        text = r.metadata.get('text', 'No description available')
        region = r.metadata.get('region', 'Unknown')
        food_type = r.metadata.get('type', 'Unknown')
        context_items.append(f"[{region} - {food_type}] {text}")
    
    context = "\n".join(context_items)
    print("\n🧠 Retrieved context:")
    print(context)

    print("\n💬 Asking Groq...")
    answer = ask_groq(question, context)
    print("\n✅ Groq Answer:")
    print(answer)
else:
    print("\n❌ No results found")

print("\n" + "=" * 60)
