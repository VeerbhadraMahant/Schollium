"""SQLAlchemy Core table definitions for every table in plan section 2.2.

Core, not the ORM, per CLAUDE.md. This module is the only place table shapes
are defined; Alembic migrations and the typed accessors both import from here
so the schema has one source of truth.
"""

from __future__ import annotations

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR

metadata = sa.MetaData()

# SPECTER2 base, the fixed default for paper-level embeddings (plan section
# 2.3), produces 768-dimensional vectors. pgvector needs a fixed dimension per
# column for its HNSW index, so this is the schema's dimension. If a Phase 1
# model choice needs a different dimension, that is a new Alembic migration
# (widen or add a column), never an in-place edit, per rule on schema changes.
PAPER_EMBEDDING_DIM = 768

_now = sa.func.now()
_uuid = sa.text("gen_random_uuid()")

paper = sa.Table(
    "paper",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("doi", sa.Text, nullable=True, unique=True),
    sa.Column("arxiv_id", sa.Text, nullable=True, unique=True),
    sa.Column("pmid", sa.Text, nullable=True, unique=True),
    sa.Column("openalex_id", sa.Text, nullable=True, unique=True),
    sa.Column("s2_id", sa.Text, nullable=True),
    sa.Column("title", sa.Text, nullable=True),
    sa.Column("abstract", sa.Text, nullable=True),
    sa.Column("year", sa.Integer, nullable=True),
    sa.Column("venue", sa.Text, nullable=True),
    sa.Column("authors", JSONB, nullable=True),
    sa.Column("oa_url", sa.Text, nullable=True),
    sa.Column("pdf_path", sa.Text, nullable=True),
    sa.Column("bibtex", sa.Text, nullable=True),
    sa.Column(
        "search_vector",
        TSVECTOR,
        sa.Computed(
            "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('english', coalesce(abstract, '')), 'B')",
            persisted=True,
        ),
    ),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
    sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=_now,
        onupdate=_now,
        nullable=False,
    ),
)

paper_embedding = sa.Table(
    "paper_embedding",
    metadata,
    sa.Column("paper_id", sa.Text, sa.ForeignKey("paper.id", ondelete="CASCADE"), nullable=False),
    sa.Column("model_name", sa.Text, nullable=False),
    sa.Column("vector", Vector(PAPER_EMBEDDING_DIM), nullable=False),
    sa.Column("dim", sa.Integer, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
    sa.PrimaryKeyConstraint("paper_id", "model_name", name="pk_paper_embedding"),
)

project = sa.Table(
    "project",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True, server_default=_uuid),
    sa.Column("name", sa.Text, nullable=False, unique=True),
    sa.Column("problem_statement", sa.Text, nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
)

run = sa.Table(
    "run",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True, server_default=_uuid),
    sa.Column(
        "project_id", sa.Uuid, sa.ForeignKey("project.id", ondelete="SET NULL"), nullable=True
    ),
    sa.Column("tool", sa.Text, nullable=False),
    sa.Column("status", sa.Text, nullable=False, server_default="running"),
    sa.Column("started_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
    sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("git_hash", sa.Text, nullable=True),
    sa.Column("config_snapshot", JSONB, nullable=True),
    sa.Column("stats", JSONB, nullable=True),
    sa.CheckConstraint("status in ('running', 'finished', 'failed')", name="ck_run_status"),
)

candidate = sa.Table(
    "candidate",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True, server_default=_uuid),
    sa.Column(
        "project_id", sa.Uuid, sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    ),
    sa.Column("paper_id", sa.Text, sa.ForeignKey("paper.id", ondelete="CASCADE"), nullable=False),
    sa.Column("run_id", sa.Uuid, sa.ForeignKey("run.id", ondelete="SET NULL"), nullable=True),
    sa.Column("channels", JSONB, nullable=True),
    sa.Column("fusion_score", sa.Float, nullable=True),
    sa.Column("rerank_score", sa.Float, nullable=True),
    sa.Column("rerank_reason", sa.Text, nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
    sa.UniqueConstraint("project_id", "paper_id", name="uq_candidate_project_paper"),
)

label = sa.Table(
    "label",
    metadata,
    sa.Column(
        "project_id", sa.Uuid, sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    ),
    sa.Column("paper_id", sa.Text, sa.ForeignKey("paper.id", ondelete="CASCADE"), nullable=False),
    sa.Column("label", sa.Text, nullable=False),
    sa.Column("note", sa.Text, nullable=True),
    sa.Column("labeled_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
    sa.PrimaryKeyConstraint("project_id", "paper_id", name="pk_label"),
    sa.CheckConstraint("label in ('relevant', 'irrelevant', 'maybe')", name="ck_label_value"),
)

citation_edge = sa.Table(
    "citation_edge",
    metadata,
    sa.Column("citing_id", sa.Text, sa.ForeignKey("paper.id", ondelete="CASCADE"), nullable=False),
    sa.Column("cited_id", sa.Text, sa.ForeignKey("paper.id", ondelete="CASCADE"), nullable=False),
    sa.Column("source", sa.Text, nullable=False),
    sa.PrimaryKeyConstraint("citing_id", "cited_id", "source", name="pk_citation_edge"),
)

extraction = sa.Table(
    "extraction",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True, server_default=_uuid),
    sa.Column("paper_id", sa.Text, sa.ForeignKey("paper.id", ondelete="CASCADE"), nullable=False),
    sa.Column(
        "project_id", sa.Uuid, sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    ),
    sa.Column("field", sa.Text, nullable=False),
    sa.Column("value", JSONB, nullable=True),
    sa.Column("evidence_span", sa.Text, nullable=True),
    sa.Column("page", sa.Integer, nullable=True),
    sa.Column("confidence", sa.Float, nullable=True),
    sa.Column("model_name", sa.Text, nullable=True),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
)

plan = sa.Table(
    "plan",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True, server_default=_uuid),
    sa.Column(
        "project_id", sa.Uuid, sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    ),
    sa.Column("version", sa.Integer, nullable=False),
    sa.Column("section", sa.Text, nullable=False),
    sa.Column("content", sa.Text, nullable=True),
    sa.Column("status", sa.Text, nullable=False, server_default="proposed"),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
    sa.CheckConstraint("status in ('proposed', 'edited', 'approved')", name="ck_plan_status"),
)

draft = sa.Table(
    "draft",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True, server_default=_uuid),
    sa.Column(
        "project_id", sa.Uuid, sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    ),
    sa.Column("section", sa.Text, nullable=False),
    sa.Column("version", sa.Integer, nullable=False),
    sa.Column("latex", sa.Text, nullable=True),
    sa.Column("cite_keys", JSONB, nullable=True),
    sa.Column("status", sa.Text, nullable=False, server_default="draft"),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
)

cite_check = sa.Table(
    "cite_check",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True, server_default=_uuid),
    sa.Column("draft_id", sa.Uuid, sa.ForeignKey("draft.id", ondelete="CASCADE"), nullable=False),
    sa.Column("cite_key", sa.Text, nullable=False),
    sa.Column("resolves", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("supports_score", sa.Float, nullable=True),
    sa.Column("retracted", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("issue", sa.Text, nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
)

figure = sa.Table(
    "figure",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True, server_default=_uuid),
    sa.Column(
        "project_id", sa.Uuid, sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    ),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("script_path", sa.Text, nullable=True),
    sa.Column("source_result", sa.Text, nullable=True),
    sa.Column("status", sa.Text, nullable=False, server_default="draft"),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
    sa.UniqueConstraint("project_id", "name", name="uq_figure_project_name"),
)

review = sa.Table(
    "review",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True, server_default=_uuid),
    sa.Column("draft_id", sa.Uuid, sa.ForeignKey("draft.id", ondelete="CASCADE"), nullable=False),
    sa.Column("version", sa.Integer, nullable=False),
    sa.Column("criterion", sa.Text, nullable=True),
    sa.Column("severity", sa.Text, nullable=True),
    sa.Column("comment", sa.Text, nullable=True),
    sa.Column("evidence_ref", sa.Text, nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
)

# Indexes named explicitly so Alembic's autogenerate and this module never disagree.
sa.Index(
    "ix_paper_embedding_vector_hnsw",
    paper_embedding.c.vector,
    postgresql_using="hnsw",
    postgresql_with={"m": 16, "ef_construction": 64},
    postgresql_ops={"vector": "vector_cosine_ops"},
)
sa.Index("ix_paper_search_vector_gin", paper.c.search_vector, postgresql_using="gin")
sa.Index("ix_candidate_project_id", candidate.c.project_id)
sa.Index("ix_label_project_id", label.c.project_id)
sa.Index("ix_extraction_paper_id", extraction.c.paper_id)
sa.Index("ix_extraction_project_field", extraction.c.project_id, extraction.c.field)
sa.Index("ix_run_project_tool", run.c.project_id, run.c.tool)
sa.Index("ix_citation_edge_cited_id", citation_edge.c.cited_id)

ALL_TABLES = [
    paper,
    paper_embedding,
    project,
    run,
    candidate,
    label,
    citation_edge,
    extraction,
    plan,
    draft,
    cite_check,
    figure,
    review,
]
