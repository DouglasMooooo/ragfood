from upstash_vector import Index
from dotenv import load_dotenv
import os

load_dotenv()

index = Index(
    url=os.getenv("UPSTASH_VECTOR_REST_URL"),
    token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
)

# 查询并展示详细结果
res = index.query(
    data="apple",
    top_k=2,
    include_vectors=False,
    include_metadata=True
)

for item in res:
    print(f"🍏 ID: {item.id}")
    print(f"Score: {item.score}")
    print(f"Metadata: {item.metadata}")
    print(f"Data: {item.data}")
    print("----")
