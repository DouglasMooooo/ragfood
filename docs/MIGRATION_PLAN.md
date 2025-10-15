# Cloud RAG Migration Plan (Upstash Vector + Groq)

Date: 2025-10-15


Repository: ragfood

## 1. Context & Goals

- Objective: Migrate Week 2 local RAG (ChromaDB + Ollama) to cloud (Upstash Vector + Groq LLM), with environment-based configuration and reproducible testing.
- Success: Faster, portable, serverless stack with documented setup, tests, and troubleshooting.

## 2. Architecture Overview

### Before (Local)

User → Ollama Embedding → ChromaDB (local) → Context → Ollama LLM → Answer

### After (Cloud)

User → SentenceTransformer local embed (or Upstash embed) → Upstash Vector (serverless) → Context → Groq LLM → Answer

Notes:

- We initially planned Upstash built‑in embeddings (MXBAI_EMBED_LARGE_V1), but used local SentenceTransformer for portability and to avoid external embedding quotas; vectors are padded to match Upstash index dimension (1024).
- LLM migrated from local Ollama to Groq `llama-3.1-8b-instant`.

## 3. Cloud Services Setup

- Vercel + Upstash Vector DB via Vercel Storage
  - Name: rag-food-advanced-[yourname]
  - Region: closest
  - Embedding model: MXBAI_EMBED_LARGE_V1
  - Similarity: cosine
- Groq Cloud API Key created and stored in `.env`
- Environment (.env):
  - `UPSTASH_VECTOR_REST_URL`
  - `UPSTASH_VECTOR_REST_TOKEN`
  - `GROQ_API_KEY`

## 4. Code Migration Summary

- Replaced ChromaDB with Upstash Vector SDK (`Index`)
- Query results normalization: Upstash `query()` returns a list of `QueryResult`; added robust parsing
- Added metadata-rich upserts with `text`, `region`, `type`, `name`, allowing better prompts
- Switched LLM to Groq; updated model name from deprecated `llama3-8b-8192` to `llama-3.1-8b-instant`
- Error handling displays empty/low-similarity separately; added score logs

## 5. Embedding Strategy

- Local: `sentence-transformers/all-MiniLM-L6-v2` (384-d) → pad to 1024 to match Upstash index
- Rationale: Avoid third-party embedding quotas; deterministic and fast locally
- Future: consider Upstash auto-embeddings with `query(data=...)` to remove local embedding dependency

## 6. Data Model & Enrichment

- foods.json now has 110 items; added 20 advanced entries (IDs 91–110) with:
  - ≥75-word descriptions, ingredients, method, nutrition, cultural background, regional variations, dietary tags, allergens
- Upsert stores: id, vector (padded), metadata {text, region, type, name, source}

## 7. Testing & Benchmarking

- Script: `rag_benchmark.py` (19 queries)
- Measures per-query ms: embedding (local), vector (Upstash), LLM (Groq), total
- Outputs `rag_benchmark_results.json` and console report
- Heuristic quality check compares answer text against metadata regions/types

### Example Results (this run)

- embedding avg ~39 ms, vector avg ~254 ms, LLM avg ~370 ms, total avg ~670 ms
- Bottlenecks: network + LLM; local embedding is small share of latency
- Some queries initially “weak” because fresh data not re-uploaded; re-upload improves recall (ensure choosing `y` to upload in `rag_run.py`)

## 8. Troubleshooting Log (Selected)

- Upstash SDK result shape changed across versions → normalize list/dict/attr cases
- “No relevant context found” → set threshold=0.1 and print scores; ensure foods re-upload
- Old Groq model decommissioned → use `llama-3.1-8b-instant`
- JSON syntax error (comma) after appending items → fixed; added validator (`validate_foods_descriptions.py`)

## 9. Risks & Mitigations

- Embedding mismatch: ensure vector dimension = index dimension (we pad to 1024)
- Data not uploaded: prompt user to re-upload; add CLI flag for auto-upload
- Rate limits / quotas: use local embeddings or Upstash auto-embeddings as fallback

## 10. Next Steps

- Embed enrichment: include name + description + ingredients for better recall
- Metadata filters & reranker (dietary tags/allergens)
- CI job to run `rag_benchmark.py` and publish results to `/docs/benchmarks.md`
- Vercel deployment of a minimal API/Edge function for RAG queries

## 11. Appendix: Commands

```powershell
# Run local RAG
py rag_run.py

# Upload new data when prompted
# Upload foods.json to Upstash? (y/n): y

# Run benchmark
py rag_benchmark.py

# Validate long-form descriptions
py validate_foods_descriptions.py
```
