"""Typed access functions for every store table. Rule 1: all SQL lives here.

Every function takes an open `Connection` so callers control transactions and
tests can wrap a call in a rollback. Nothing here opens its own connection.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import Connection
from sqlalchemy.dialects.postgresql import insert as pg_insert

from scholium.store import schema
from scholium.store.records import (
    CandidateRecord,
    CitationEdgeRecord,
    CiteCheckRecord,
    DraftRecord,
    ExtractionRecord,
    FigureRecord,
    LabelRecord,
    PaperEmbeddingRecord,
    PaperRecord,
    PlanRecord,
    ProjectRecord,
    Record,
    ReviewRecord,
    RunRecord,
)

# Columns on `paper` that participate in "never overwrite a filled value with
# an empty one" upsert merging. Excludes the primary key and computed/managed
# columns (search_vector, created_at, updated_at).
_PAPER_MERGE_COLUMNS = (
    "doi",
    "arxiv_id",
    "pmid",
    "openalex_id",
    "s2_id",
    "title",
    "abstract",
    "venue",
    "oa_url",
    "pdf_path",
    "bibtex",
)
_PAPER_COALESCE_COLUMNS = ("year", "authors")


def _merge_text(column: str) -> sa.ColumnElement:
    """SET col = CASE WHEN excluded.col is non-null and non-empty THEN it,
    ELSE keep the existing value. This is the upsert rule from CLAUDE.md."""
    excluded = sa.literal_column(f"excluded.{column}")
    existing = schema.paper.c[column]
    return sa.case(
        (sa.and_(excluded.is_not(None), excluded != ""), excluded),
        else_=existing,
    )


def _insert_returning(conn: Connection, table: sa.Table, values: dict[str, Any]) -> sa.Row:
    stmt = sa.insert(table).values(**values).returning(*table.c)
    return conn.execute(stmt).one()


def _row_to(record_type: type[Record], row: sa.Row) -> Record:
    return record_type.model_validate(row, from_attributes=True)


# -- paper ---------------------------------------------------------------


def upsert_paper(conn: Connection, record: PaperRecord) -> str:
    """Insert a paper, or merge onto an existing row without ever overwriting
    a filled field with an empty one. Returns the canonical id."""
    values = record.model_dump(exclude={"created_at", "updated_at"})
    stmt = pg_insert(schema.paper).values(**values)
    update_set = {col: _merge_text(col) for col in _PAPER_MERGE_COLUMNS}
    update_set.update(
        {
            col: sa.func.coalesce(sa.literal_column(f"excluded.{col}"), schema.paper.c[col])
            for col in _PAPER_COALESCE_COLUMNS
        }
    )
    update_set["updated_at"] = sa.func.now()
    stmt = stmt.on_conflict_do_update(index_elements=[schema.paper.c.id], set_=update_set)
    conn.execute(stmt)
    return record.id


def get_paper(conn: Connection, paper_id: str) -> PaperRecord | None:
    row = conn.execute(sa.select(schema.paper).where(schema.paper.c.id == paper_id)).one_or_none()
    return _row_to(PaperRecord, row) if row is not None else None


# -- paper_embedding -------------------------------------------------------


def upsert_paper_embedding(conn: Connection, record: PaperEmbeddingRecord) -> None:
    values = record.model_dump(exclude={"created_at"})
    stmt = pg_insert(schema.paper_embedding).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[schema.paper_embedding.c.paper_id, schema.paper_embedding.c.model_name],
        set_={"vector": stmt.excluded.vector, "dim": stmt.excluded.dim},
    )
    conn.execute(stmt)


def nearest_papers(
    conn: Connection, vector: list[float], *, model_name: str, limit: int = 20
) -> list[tuple[str, float]]:
    """Nearest papers to `vector` by cosine distance, restricted to one
    embedding model so different embedding spaces are never mixed.

    This is one of the two similarity helpers plan section 5.2 asks for, so
    no tool has to write its own vector query.
    """
    distance = schema.paper_embedding.c.vector.cosine_distance(vector).label("distance")
    stmt = (
        sa.select(schema.paper_embedding.c.paper_id, distance)
        .where(schema.paper_embedding.c.model_name == model_name)
        .order_by(distance)
        .limit(limit)
    )
    return [(row.paper_id, float(row.distance)) for row in conn.execute(stmt)]


def nearest_chunks(
    conn: Connection, vector: list[float], *, paper_id: str, model_name: str, limit: int = 6
) -> list[tuple[str, float]]:
    """Nearest chunks within one paper. Deferred: the chunk table is created
    by Read in Phase 1 (plan section 7.4), which is outside Phase 0's schema
    in section 2.2. This stub exists so the call site the plan describes has
    somewhere to point to; it raises rather than silently returning nothing.
    """
    raise NotImplementedError(
        "nearest_chunks needs the chunk table, added by the Read tool (Phase 1, "
        "plan section 7.4). Not part of the Phase 0 schema in plan section 2.2."
    )


# -- project ---------------------------------------------------------------


def create_project(conn: Connection, record: ProjectRecord) -> ProjectRecord:
    values = record.model_dump(exclude={"created_at"}, exclude_none=True)
    row = _insert_returning(conn, schema.project, values)
    return _row_to(ProjectRecord, row)


def get_project_by_name(conn: Connection, name: str) -> ProjectRecord | None:
    row = conn.execute(sa.select(schema.project).where(schema.project.c.name == name)).one_or_none()
    return _row_to(ProjectRecord, row) if row is not None else None


# -- run ---------------------------------------------------------------


def insert_run(conn: Connection, record: RunRecord) -> RunRecord:
    values = record.model_dump(exclude={"started_at", "finished_at"}, exclude_none=True)
    row = _insert_returning(conn, schema.run, values)
    return _row_to(RunRecord, row)


def finish_run(
    conn: Connection, run_id: UUID, *, status: str, stats: dict[str, Any] | None
) -> None:
    stmt = (
        sa.update(schema.run)
        .where(schema.run.c.id == run_id)
        .values(status=status, stats=stats, finished_at=sa.func.now())
    )
    conn.execute(stmt)


# -- candidate ---------------------------------------------------------------


def upsert_candidate(conn: Connection, record: CandidateRecord) -> CandidateRecord:
    values = record.model_dump(exclude={"id", "created_at"}, exclude_none=True)
    stmt = pg_insert(schema.candidate).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[schema.candidate.c.project_id, schema.candidate.c.paper_id],
        set_={
            "channels": stmt.excluded.channels,
            "fusion_score": stmt.excluded.fusion_score,
            "rerank_score": stmt.excluded.rerank_score,
            "rerank_reason": stmt.excluded.rerank_reason,
            "run_id": stmt.excluded.run_id,
        },
    ).returning(*schema.candidate.c)
    row = conn.execute(stmt).one()
    return _row_to(CandidateRecord, row)


# -- label ---------------------------------------------------------------


def upsert_label(conn: Connection, record: LabelRecord) -> LabelRecord:
    values = record.model_dump(exclude={"labeled_at"})
    stmt = pg_insert(schema.label).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[schema.label.c.project_id, schema.label.c.paper_id],
        set_={
            "label": stmt.excluded.label,
            "note": stmt.excluded.note,
            "labeled_at": sa.func.now(),
        },
    ).returning(*schema.label.c)
    row = conn.execute(stmt).one()
    return _row_to(LabelRecord, row)


# -- citation_edge -------------------------------------------------------


def insert_citation_edge(conn: Connection, record: CitationEdgeRecord) -> None:
    stmt = pg_insert(schema.citation_edge).values(**record.model_dump())
    stmt = stmt.on_conflict_do_nothing(
        index_elements=[
            schema.citation_edge.c.citing_id,
            schema.citation_edge.c.cited_id,
            schema.citation_edge.c.source,
        ]
    )
    conn.execute(stmt)


# -- extraction, plan, draft, cite_check, figure, review ---------------------
# One insert-and-return function each. Re-runs create a new version row rather
# than overwriting (extraction.version, plan.version, draft.version), so old
# versions are kept, per plan section 7.6.


def insert_extraction(conn: Connection, record: ExtractionRecord) -> ExtractionRecord:
    values = record.model_dump(exclude={"id", "created_at"}, exclude_none=True)
    row = _insert_returning(conn, schema.extraction, values)
    return _row_to(ExtractionRecord, row)


def insert_plan(conn: Connection, record: PlanRecord) -> PlanRecord:
    values = record.model_dump(exclude={"id", "created_at"}, exclude_none=True)
    row = _insert_returning(conn, schema.plan, values)
    return _row_to(PlanRecord, row)


def insert_draft(conn: Connection, record: DraftRecord) -> DraftRecord:
    values = record.model_dump(exclude={"id", "created_at"}, exclude_none=True)
    row = _insert_returning(conn, schema.draft, values)
    return _row_to(DraftRecord, row)


def insert_cite_check(conn: Connection, record: CiteCheckRecord) -> CiteCheckRecord:
    values = record.model_dump(exclude={"id", "created_at"}, exclude_none=True)
    row = _insert_returning(conn, schema.cite_check, values)
    return _row_to(CiteCheckRecord, row)


def insert_figure(conn: Connection, record: FigureRecord) -> FigureRecord:
    values = record.model_dump(exclude={"id", "created_at"}, exclude_none=True)
    row = _insert_returning(conn, schema.figure, values)
    return _row_to(FigureRecord, row)


def insert_review(conn: Connection, record: ReviewRecord) -> ReviewRecord:
    values = record.model_dump(exclude={"id", "created_at"}, exclude_none=True)
    row = _insert_returning(conn, schema.review, values)
    return _row_to(ReviewRecord, row)
