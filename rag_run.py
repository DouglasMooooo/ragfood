import os
import json
import numpy as np
from dotenv import load_dotenv
from upstash_vector import Index
from openai import OpenAI
from groq import Groq
from sentence_transformers import SentenceTransformer

# =============================
# 0. 环境变量加载
# =============================
load_dotenv()
print("✅ Environment variables loaded.")

# 初始化客户端
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
index = Index(
    url=os.getenv("UPSTASH_VECTOR_REST_URL"),
    token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
)
print("✅ Connected to Upstash Vector index initialized.")

# =============================
# 1. 本地 SentenceTransformer 向量模型
# =============================
model = SentenceTransformer("all-MiniLM-L6-v2")

def create_embedding(text: str):
    """生成 384维嵌入并补齐到 1024维"""
    emb = model.encode(text)
    padded = np.pad(emb, (0, 1024 - len(emb)), 'constant')
    return padded.tolist()

# =============================
# 2. 上传数据
# =============================
def upload_food_data():
    file_path = "foods.json"
    if not os.path.exists(file_path):
        print("❌ foods.json not found.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        foods = json.load(f)

    print(f"⬆️ Uploading {len(foods)} food items to Upstash Vector...")

    for item in foods:
        try:
            text = item["text"]
            vector = create_embedding(text)
            index.upsert(vectors=[{
                "id": str(item["id"]),
                "vector": vector,
                "metadata": {
                    "text": text,  # ⭐ 保存完整文本描述
                    "region": item.get("region", ""),
                    "type": item.get("type", ""),
                    "name": item.get("name", ""),
                    "source": "foods.json"
                }
            }])
            print(f"✅ Uploaded: {item['id']}")
        except Exception as e:
            print(f"⚠️ Upload failed: {item['id']} - {e}")

    print("✅ Upload completed.")

# =============================
# 3. 查询 Upstash
# =============================
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

    # 统一兼容返回结构
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

# =============================
# 4. Groq 问答
# =============================
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

# =============================
# 5. 主循环
# =============================
if __name__ == "__main__":
    print("🤖 RAG is ready. Ask a question (type 'exit' to quit):")
    upload_choice = input("Upload foods.json to Upstash? (y/n): ").strip().lower()
    if upload_choice == "y":
        upload_food_data()

    while True:
        question = input("\nYou: ").strip()
        if question.lower() == "exit":
            print("👋 Goodbye!")
            break

        results = query_upstash(question)
        if not results:
            continue

        # 拼接上下文 - 直接从查询结果的metadata获取
        context_items = []
        for r in results:
            text = r.metadata.get('text', 'No description available')
            region = r.metadata.get('region', 'Unknown')
            food_type = r.metadata.get('type', 'Unknown')
            context_items.append(f"[{region} - {food_type}] {text}")
        
        context = "\n".join(context_items)
        print("\n🧠 Retrieved context:\n", context)

        answer = ask_groq(question, context)
        print("\n💬 Groq Answer:\n", answer)
