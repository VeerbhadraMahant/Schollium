"""initial schema: the 13 tables in plan section 2.2

Revision ID: 97dcfeb6e8be
Revises:
Create Date: 2026-09-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR

from alembic import op

revision: str = "97dcfeb6e8be"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PAPER_EMBEDDING_DIM = 768


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "paper",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("doi", sa.Text, unique=True),
        sa.Column("arxiv_id", sa.Text, unique=True),
        sa.Column("pmid", sa.Text, unique=True),
        sa.Column("openalex_id", sa.Text, unique=True),
        sa.Column("s2_id", sa.Text),
        sa.Column("title", sa.Text),
        sa.Column("abstract", sa.Text),
        sa.Column("year", sa.Integer),
        sa.Column("venue", sa.Text),
        sa.Column("authors", JSONB),
        sa.Column("oa_url", sa.Text),
        sa.Column("pdf_path", sa.Text),
        sa.Column("bibtex", sa.Text),
        sa.Column(
            "search_vector",
            TSVECTOR,
            sa.Computed(
                "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
                "setweight(to_tsvector('english', coalesce(abstract, '')), 'B')",
                persisted=True,
            ),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_paper_search_vector_gin", "paper", ["search_vector"], postgresql_using="gin"
    )

    op.create_table(
        "project",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("problem_statement", sa.Text),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "run",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", sa.Uuid, sa.ForeignKey("project.id", ondelete="SET NULL")),
        sa.Column("tool", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="running"),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("git_hash", sa.Text),
        sa.Column("config_snapshot", JSONB),
        sa.Column("stats", JSONB),
        sa.CheckConstraint("status in ('running', 'finished', 'failed')", name="ck_run_status"),
    )
    op.create_index("ix_run_project_tool", "run", ["project_id", "tool"])

    op.create_table(
        "paper_embedding",
        sa.Column(
            "paper_id", sa.Text, sa.ForeignKey("paper.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("model_name", sa.Text, nullable=False),
        sa.Column("vector", Vector(PAPER_EMBEDDING_DIM), nullable=False),
        sa.Column("dim", sa.Integer, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("paper_id", "model_name", name="pk_paper_embedding"),
    )
    op.create_index(
        "ix_paper_embedding_vector_hnsw",
        "paper_embedding",
        ["vector"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"vector": "vector_cosine_ops"},
    )

    op.create_table(
        "candidate",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "project_id", sa.Uuid, sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "paper_id", sa.Text, sa.ForeignKey("paper.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("run_id", sa.Uuid, sa.ForeignKey("run.id", ondelete="SET NULL")),
        sa.Column("channels", JSONB),
        sa.Column("fusion_score", sa.Float),
        sa.Column("rerank_score", sa.Float),
        sa.Column("rerank_reason", sa.Text),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("project_id", "paper_id", name="uq_candidate_project_paper"),
    )
    op.create_index("ix_candidate_project_id", "candidate", ["project_id"])

    op.create_table(
        "label",
        sa.Column(
            "project_id", sa.Uuid, sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "paper_id", sa.Text, sa.ForeignKey("paper.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("note", sa.Text),
        sa.Column(
            "labeled_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("project_id", "paper_id", name="pk_label"),
        sa.CheckConstraint("label in ('relevant', 'irrelevant', 'maybe')", name="ck_label_value"),
    )
    op.create_index("ix_label_project_id", "label", ["project_id"])

    op.create_table(
        "citation_edge",
        sa.Column(
            "citing_id", sa.Text, sa.ForeignKey("paper.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "cited_id", sa.Text, sa.ForeignKey("paper.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("source", sa.Text, nullable=False),
        sa.PrimaryKeyConstraint("citing_id", "cited_id", "source", name="pk_citation_edge"),
    )
    op.create_index("ix_citation_edge_cited_id", "citation_edge", ["cited_id"])

    op.create_table(
        "extraction",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "paper_id", sa.Text, sa.ForeignKey("paper.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "project_id", sa.Uuid, sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("field", sa.Text, nullable=False),
        sa.Column("value", JSONB),
        sa.Column("evidence_span", sa.Text),
        sa.Column("page", sa.Integer),
        sa.Column("confidence", sa.Float),
        sa.Column("model_name", sa.Text),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_extraction_paper_id", "extraction", ["paper_id"])
    op.create_index("ix_extraction_project_field", "extraction", ["project_id", "field"])

    op.create_table(
        "plan",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "project_id", sa.Uuid, sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("section", sa.Text, nullable=False),
        sa.Column("content", sa.Text),
        sa.Column("status", sa.Text, nullable=False, server_default="proposed"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("status in ('proposed', 'edited', 'approved')", name="ck_plan_status"),
    )

    op.create_table(
        "draft",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "project_id", sa.Uuid, sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("section", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("latex", sa.Text),
        sa.Column("cite_keys", JSONB),
        sa.Column("status", sa.Text, nullable=False, server_default="draft"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "cite_check",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "draft_id", sa.Uuid, sa.ForeignKey("draft.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("cite_key", sa.Text, nullable=False),
        sa.Column("resolves", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("supports_score", sa.Float),
        sa.Column("retracted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("issue", sa.Text),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "figure",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "project_id", sa.Uuid, sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("script_path", sa.Text),
        sa.Column("source_result", sa.Text),
        sa.Column("status", sa.Text, nullable=False, server_default="draft"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("project_id", "name", name="uq_figure_project_name"),
    )

    op.create_table(
        "review",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "draft_id", sa.Uuid, sa.ForeignKey("draft.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("criterion", sa.Text),
        sa.Column("severity", sa.Text),
        sa.Column("comment", sa.Text),
        sa.Column("evidence_ref", sa.Text),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("review")
    op.drop_table("figure")
    op.drop_table("cite_check")
    op.drop_table("draft")
    op.drop_table("plan")
    op.drop_table("extraction")
    op.drop_table("citation_edge")
    op.drop_table("label")
    op.drop_table("candidate")
    op.drop_table("paper_embedding")
    op.drop_table("run")
    op.drop_table("project")
    op.drop_table("paper")
