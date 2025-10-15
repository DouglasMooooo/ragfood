import os
import json
import numpy as np
from dotenv import load_dotenv
from upstash_vector import Index
from sentence_transformers import SentenceTransformer

# 加载环境变量
load_dotenv()

# 初始化
model = SentenceTransformer("all-MiniLM-L6-v2")
index = Index(
    url=os.getenv("UPSTASH_VECTOR_REST_URL"),
    token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
)

def create_embedding(text: str):
    """生成 384维嵌入并补齐到 1024维"""
    emb = model.encode(text)
    padded = np.pad(emb, (0, 1024 - len(emb)), 'constant')
    return padded.tolist()

print("=" * 60)
print("🔍 RAG 诊断测试")
print("=" * 60)

# 测试1: 检查向量维度
print("\n1️⃣ 测试向量生成:")
test_text = "I want to eat Asian food"
test_vector = create_embedding(test_text)
print(f"   文本: {test_text}")
print(f"   向量维度: {len(test_vector)}")
print(f"   向量前5个值: {test_vector[:5]}")

# 测试2: 尝试查询 Upstash
print("\n2️⃣ 测试 Upstash 查询:")
try:
    results = index.query(
        vector=test_vector,
        top_k=5,
        include_metadata=True,
        include_vectors=False
    )
    
    print(f"   查询成功!")
    print(f"   返回类型: {type(results)}")
    
    # 检查返回结构
    if isinstance(results, dict):
        print(f"   结果是字典，keys: {results.keys()}")
        matches = results.get("matches", [])
    elif hasattr(results, "matches"):
        print(f"   结果有 matches 属性")
        matches = results.matches
    else:
        print(f"   未知结构: {results}")
        matches = []
    
    print(f"   匹配数量: {len(matches)}")
    
    if matches:
        print(f"\n   ✅ 找到 {len(matches)} 个结果:")
        for i, m in enumerate(matches[:3]):
            score = getattr(m, "score", 0)
            print(f"      [{i+1}] ID: {m.id}, Score: {score:.4f}")
            if hasattr(m, 'metadata'):
                print(f"          Metadata keys: {m.metadata.keys() if m.metadata else 'None'}")
                if m.metadata:
                    print(f"          Region: {m.metadata.get('region', 'N/A')}")
                    print(f"          Type: {m.metadata.get('type', 'N/A')}")
                    text = m.metadata.get('text', 'N/A')
                    print(f"          Text: {text[:80]}..." if len(text) > 80 else f"          Text: {text}")
    else:
        print("   ❌ 没有找到任何匹配结果 (empty)")
        
except Exception as e:
    print(f"   ❌ 查询失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3: 检查 Upstash 索引信息
print("\n3️⃣ 测试索引信息:")
try:
    info = index.info()
    print(f"   索引信息: {info}")
except Exception as e:
    print(f"   获取索引信息失败: {e}")

# 测试4: 尝试获取一个已知ID
print("\n4️⃣ 测试获取单个向量 (ID=1):")
try:
    fetch_result = index.fetch(ids=["1"], include_metadata=True)
    print(f"   Fetch 结果类型: {type(fetch_result)}")
    print(f"   Fetch 结果: {fetch_result}")
    if fetch_result:
        print(f"   ✅ 成功获取 ID=1 的数据")
        if len(fetch_result) > 0:
            item = fetch_result[0]
            print(f"      Metadata: {item.metadata if hasattr(item, 'metadata') else 'N/A'}")
    else:
        print(f"   ⚠️ ID=1 不存在，数据库可能是空的")
except Exception as e:
    print(f"   ❌ Fetch 失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("诊断完成!")
print("=" * 60)
