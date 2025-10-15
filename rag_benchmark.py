import os
import time
import json
import statistics as stats
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple

from dotenv import load_dotenv
from upstash_vector import Index
from sentence_transformers import SentenceTransformer
from groq import Groq
import numpy as np

load_dotenv()

# Initialize clients
index = Index(
    url=os.getenv("UPSTASH_VECTOR_REST_URL"),
    token=os.getenv("UPSTASH_VECTOR_REST_TOKEN"),
)
model = SentenceTransformer("all-MiniLM-L6-v2")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))


def create_embedding(text: str):
    emb = model.encode(text)
    padded = np.pad(emb, (0, 1024 - len(emb)), 'constant')
    return padded.tolist()


def upstash_query(query_text: str, top_k=5, threshold=0.1):
    qv = create_embedding(query_text)
    t0 = time.perf_counter()
    results = index.query(vector=qv, top_k=top_k, include_metadata=True, include_vectors=False)
    vec_ms = (time.perf_counter() - t0) * 1000

    matches = []
    if isinstance(results, list):
        matches = results
    elif isinstance(results, dict):
        matches = results.get("matches", [])
    elif hasattr(results, "matches"):
        matches = results.matches

    filtered = [m for m in matches if getattr(m, "score", 0) > threshold]
    return filtered, vec_ms


def ask_groq(question: str, context: str) -> Tuple[str, float]:
    prompt = f"""
You are a food expert AI. Use only the provided context to answer.
Keep it short and specific (2-5 sentences). If information is not in context, say what is missing.

Context:
{context}

Question: {question}
Answer:
"""
    t0 = time.perf_counter()
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
        )
        ans = resp.choices[0].message.content.strip()
    except Exception as e:
        ans = f"Groq error: {e}"
    llm_ms = (time.perf_counter() - t0) * 1000
    return ans, llm_ms


@dataclass
class QueryResult:
    query: str
    embed_ms: float
    vector_ms: float
    llm_ms: float
    total_ms: float
    top: List[Dict[str, Any]]
    answer: str


TEST_QUERIES = [
    # Semantic similarity
    "healthy Mediterranean options",
    "Thai coconut curry dishes",
    "Ethiopian spicy chicken stew",
    "Peruvian seafood appetizer with lime",
    "Greek baked eggplant casserole",
    
    # Multi-criteria
    "spicy vegetarian Asian dishes",
    "gluten-free vegan bowls high in fiber",
    "low-sodium tofu stir-fry",
    "pescatarian meals rich in protein",
    "non-vegetarian Moroccan main course with fruit",

    # Nutritional
    "high-protein low-carb foods",
    "omega-3 rich dishes",
    "low-calorie breakfast high fiber",

    # Cultural exploration
    "traditional comfort foods",
    "festival foods from China",
    "Ethiopian holiday dishes",

    # Cooking method
    "dishes that can be grilled",
    "slow-cooked stews",
    "baked casseroles",
]


def run_benchmark():
    results: List[QueryResult] = []
    for q in TEST_QUERIES:
        t_all0 = time.perf_counter()

        # Embedding time explicitly
        t0 = time.perf_counter()
        _ = create_embedding(q)
        embed_ms = (time.perf_counter() - t0) * 1000

        matches, vector_ms = upstash_query(q, top_k=5, threshold=0.1)
        context_items = []
        top_for_log = []
        for m in matches:
            meta = getattr(m, 'metadata', {}) or {}
            text = meta.get('text', '')
            region = meta.get('region', '')
            typ = meta.get('type', '')
            top_for_log.append({
                'id': m.id,
                'score': round(float(getattr(m, 'score', 0)), 4),
                'region': region,
                'type': typ,
                'preview': text[:120]
            })
            context_items.append(f"[{region or '-'} - {typ or '-'}] {text}")
        context = "\n".join(context_items)

        answer, llm_ms = ask_groq(q, context)
        total_ms = (time.perf_counter() - t_all0) * 1000

        results.append(QueryResult(
            query=q,
            embed_ms=round(embed_ms, 2),
            vector_ms=round(vector_ms, 2),
            llm_ms=round(llm_ms, 2),
            total_ms=round(total_ms, 2),
            top=top_for_log,
            answer=answer,
        ))

    return results


def summarize(results: List[QueryResult]):
    def series(attr):
        vals = [getattr(r, attr) for r in results]
        return {
            'avg_ms': round(stats.mean(vals), 2),
            'p95_ms': round(stats.quantiles(vals, n=20)[-1], 2) if len(vals) >= 5 else None,
            'min_ms': round(min(vals), 2),
            'max_ms': round(max(vals), 2),
        }

    timing = {
        'embedding': series('embed_ms'),
        'vector_query': series('vector_ms'),
        'llm': series('llm_ms'),
        'total': series('total_ms'),
    }

    return timing


def simple_quality_check(r: QueryResult) -> Dict[str, Any]:
    # Heuristic: count if answer mentions any region/type from top matches
    regions = set((t.get('region') or '').lower() for t in r.top if t.get('region'))
    types = set((t.get('type') or '').lower() for t in r.top if t.get('type'))
    ans_l = (r.answer or '').lower()
    hit_regions = [rg for rg in regions if rg and rg in ans_l]
    hit_types = [tp for tp in types if tp and tp in ans_l]
    return {
        'region_hits': hit_regions,
        'type_hits': hit_types,
        'signal': 'ok' if (hit_regions or hit_types) else 'weak'
    }


def main():
    results = run_benchmark()
    timing = summarize(results)

    # Print concise report
    print("\n===== RAG Benchmark Report =====")
    print(f"Total queries: {len(results)}")
    print("\nTiming (ms):")
    for k, v in timing.items():
        print(f"- {k}: avg={v['avg_ms']} p95={v['p95_ms']} min={v['min_ms']} max={v['max_ms']}")

    print("\nPer-query summary:")
    for r in results:
        qcheck = simple_quality_check(r)
        print(f"\nQ: {r.query}")
        print(f"  time_ms: embed={r.embed_ms} vector={r.vector_ms} llm={r.llm_ms} total={r.total_ms}")
        print(f"  top: {[ (t['id'], t['score']) for t in r.top ]}")
        print(f"  quality: {qcheck}")
        # Keep answer concise in log
        a = r.answer.replace('\n', ' ')
        print(f"  answer: {a[:220]}{'...' if len(a)>220 else ''}")

    # Optionally write JSON for further inspection
    out = {
        'timing': timing,
        'results': [asdict(r) for r in results],
    }
    with open('rag_benchmark_results.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nSaved detailed results to rag_benchmark_results.json")


if __name__ == '__main__':
    main()
