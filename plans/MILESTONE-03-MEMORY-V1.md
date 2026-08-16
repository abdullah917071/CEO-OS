# Milestone 3 — Memory V1 Execution Plan

`PLANS.md` remains the immutable governing roadmap. This file makes its Memory V1 milestone implementation-complete.

Status: implemented and verified on 2026-08-15.

## Objective

Add external, restart-persistent episodic and semantic memory with explicit provenance, correction history, deletion, and bounded retrieval. PostgreSQL is authoritative and pgvector provides production similarity search; SQLite provides behaviorally equivalent exact cosine search for tests/local fallback.

## Decisions

- A provider-neutral `EmbeddingProvider` returns normalized 384-dimensional vectors. V1 defaults to a deterministic offline feature-hash embedder; future local or hosted adapters replace it without changing memory records or retrieval APIs.
- `memories` stores type, content, subject key, lifecycle status, confidence, importance, observation/validity times, embedding identity/vector, sensitivity, access metadata, and correction linkage.
- `memory_provenance` stores one or more sources independently from memory content. A source includes type, URI, task ID, quoted/evidentiary detail, and observation time.
- Corrections are immutable history: the prior record becomes `superseded` with `valid_until`; a new active record links through `supersedes_id`. Deletion is soft and excludes the record from retrieval.
- PostgreSQL enables `vector`, stores `vector(384)`, and uses an HNSW cosine index. SQLite stores JSON vectors and computes exact cosine similarity in-process.
- Retrieval filters active/current records, combines cosine similarity with importance and recency, updates access metadata, and returns provenance with every result.
- Successful tasks create episodic memories. Explicit “remember …” requests use `memory.remember`; recall questions use `memory.search`. No unrestricted conversation transcript is silently memorized.

## Interfaces

- `POST /api/v1/memories`: create episodic or semantic memory with provenance.
- `GET /api/v1/memories/{id}` and `GET /api/v1/memories/search`: inspect or retrieve.
- `POST /api/v1/memories/{id}/correct`: supersede while preserving history.
- `DELETE /api/v1/memories/{id}`: soft-delete.
- Capabilities: `memory.remember` (R1) and `memory.search` (R0).

## Acceptance tests

- Semantic and episodic memories persist across service/repository recreation.
- Relevant semantic memory ranks above unrelated memory and includes its provenance.
- PostgreSQL executes pgvector cosine retrieval and has the HNSW index.
- Correction excludes the obsolete fact, returns the replacement, and preserves the supersession chain.
- Deleted or expired records are never retrieved.
- Task completion produces one idempotent episode; task replay does not duplicate it.
- “Remember that …” followed by a later recall returns the stored fact after restart.
- Existing durable-runtime, safety, API, dashboard, static, dependency, and container checks remain green.

## Verification result

All acceptance criteria passed. The test suite covers stable embeddings, ranked retrieval with
provenance, restart persistence, correction chains, deletion/expiry filtering, idempotent task
episodes, runtime remember/recall, and the complete memory HTTP lifecycle. The containerized
PostgreSQL instance has the `vector` extension and cosine HNSW index, executed a live similarity
search, and retained the result across an API container restart.
