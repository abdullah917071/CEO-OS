# Memory

Memory is an external subsystem, not accumulated prompt text. It distinguishes working state, episodes, semantic facts, procedures, relationships, business records, documents, and preferences.

Every durable memory carries source/provenance, confidence, importance, observation time, validity interval, and access metadata. Corrections supersede or close facts rather than appending permanent contradictions. Sensitive memories are classified and access-controlled.

Retrieval starts from current intent and entities, combines semantic, relationship, recent episodic, and procedural signals, then compiles a bounded context pack. Raw retrieval results remain distinguishable from verified facts and model inference.

PostgreSQL is authoritative and pgvector is the initial replaceable semantic index. Milestone 3 implements extraction, retrieval, correction, consolidation, deletion, and restart-persistence tests. Task checkpoints are runtime state, not long-term memory.

## Memory V1 implementation

Memory V1 implements semantic facts and episodic task outcomes. The provider-neutral embedding
boundary currently uses a deterministic offline 384-dimensional feature-hash provider. PostgreSQL
stores these as `vector(384)` and indexes cosine distance with HNSW; SQLite stores JSON vectors and
performs exact cosine scoring for portable tests and local fallback.

Retrieval considers only active records inside their validity interval, then combines semantic
similarity, importance, and recency. Every result includes its independently stored provenance.
Access count and last-access time are updated after retrieval.

Corrections never overwrite history. They close the previous validity interval, mark that record
`superseded`, and create an active replacement linked through `supersedes_id`. Deletion is a soft
delete and immediately removes the record from retrieval.

The runtime exposes `memory.remember` as R1 and `memory.search` as R0. Explicit owner instructions
to remember become semantic memories; successful tasks produce one idempotent episodic memory.
Raw conversation transcripts are not silently retained. The HTTP API supports create, get, search,
correct, and delete operations under `/api/v1/memories`.
