# ADR 0001: Postgres with pgvector as the shared store

Date: 2026-09-18
Status: accepted

## Context

Every Scholium tool reads and writes one shared store. The original draft of the plan chose SQLite for zero setup and single-file backups, with vector search kept outside the database in a numpy or FAISS index. The owner wants to invest in a stack that is worth learning and that removes side components rather than adding them.

## Decision

Use PostgreSQL 16 or newer with the pgvector extension, run locally through Docker Compose with a named volume. Access through psycopg 3 and SQLAlchemy Core (not the ORM). All schema changes through Alembic migrations. Paper and chunk embeddings live in pgvector columns with HNSW cosine indexes. Title and abstract carry a tsvector column with a GIN index. Run snapshots, channel metadata and stats are JSONB.

## Consequences

Easier: one similarity query instead of a separate index to keep in sync; a fourth keyword channel for Find via full-text search over stored abstracts and chunks; queryable run metadata; real concurrency for a later web review view.
Harder: one Docker service must be running; backups are pg_dump plus a JSONL export rather than copying a file; store tests need a throwaway Postgres (testcontainers) instead of an in-memory database.
Plan sections changed: 2.1, 2.2, 3.3, 4.2 week 1, 5.2 to 5.4, 13.4, 15.3.

## Alternatives considered

- SQLite plus numpy: simplest, but two stores to keep consistent and no full-text search worth using.
- SQLite plus a vector database (Chroma, Qdrant): three components for a single-user tool; rejected.
- Postgres plus a separate search engine (Elasticsearch, Meilisearch): full-text search in Postgres is sufficient at this scale; rejected.
