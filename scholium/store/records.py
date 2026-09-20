"""Pydantic records, one per store table. Every client and tool that returns a
row from the store, or a row destined for it, returns one of these rather than
a raw dict, per CLAUDE.md: "Pydantic models for every store record."

These are read/write shapes for the accessors in scholium/store/accessors.py,
not an ORM. Fields the database fills in (created_at, computed columns, server
defaults) are optional here and absent until a row is read back.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class PaperRecord(Record):
    id: str
    doi: str | None = None
    arxiv_id: str | None = None
    pmid: str | None = None
    openalex_id: str | None = None
    s2_id: str | None = None
    title: str | None = None
    abstract: str | None = None
    year: int | None = None
    venue: str | None = None
    authors: list[dict[str, Any]] | None = None
    oa_url: str | None = None
    pdf_path: str | None = None
    bibtex: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PaperEmbeddingRecord(Record):
    paper_id: str
    model_name: str
    vector: list[float]
    dim: int
    created_at: datetime | None = None


class ProjectRecord(Record):
    id: UUID | None = None
    name: str
    problem_statement: str | None = None
    created_at: datetime | None = None


class RunRecord(Record):
    id: UUID | None = None
    project_id: UUID | None = None
    tool: str
    status: Literal["running", "finished", "failed"] = "running"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    git_hash: str | None = None
    config_snapshot: dict[str, Any] | None = None
    stats: dict[str, Any] | None = None


class CandidateRecord(Record):
    id: UUID | None = None
    project_id: UUID
    paper_id: str
    run_id: UUID | None = None
    channels: dict[str, Any] | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None
    rerank_reason: str | None = None
    created_at: datetime | None = None


class LabelRecord(Record):
    project_id: UUID
    paper_id: str
    label: Literal["relevant", "irrelevant", "maybe"]
    note: str | None = None
    labeled_at: datetime | None = None


class CitationEdgeRecord(Record):
    citing_id: str
    cited_id: str
    source: str


class ExtractionRecord(Record):
    id: UUID | None = None
    paper_id: str
    project_id: UUID
    field: str
    value: Any = None
    evidence_span: str | None = None
    page: int | None = None
    confidence: float | None = None
    model_name: str | None = None
    version: int = 1
    created_at: datetime | None = None


class PlanRecord(Record):
    id: UUID | None = None
    project_id: UUID
    version: int
    section: str
    content: str | None = None
    status: Literal["proposed", "edited", "approved"] = "proposed"
    created_at: datetime | None = None


class DraftRecord(Record):
    id: UUID | None = None
    project_id: UUID
    section: str
    version: int
    latex: str | None = None
    cite_keys: list[str] | None = None
    status: str = "draft"
    created_at: datetime | None = None


class CiteCheckRecord(Record):
    id: UUID | None = None
    draft_id: UUID
    cite_key: str
    resolves: bool = False
    supports_score: float | None = None
    retracted: bool = False
    issue: str | None = None
    created_at: datetime | None = None


class FigureRecord(Record):
    id: UUID | None = None
    project_id: UUID
    name: str
    script_path: str | None = None
    source_result: str | None = None
    status: str = "draft"
    created_at: datetime | None = None


class ReviewRecord(Record):
    id: UUID | None = None
    draft_id: UUID
    version: int
    criterion: str | None = None
    severity: str | None = None
    comment: str | None = None
    evidence_ref: str | None = None
    created_at: datetime | None = None


__all__ = [
    "CandidateRecord",
    "CitationEdgeRecord",
    "CiteCheckRecord",
    "DraftRecord",
    "ExtractionRecord",
    "FigureRecord",
    "LabelRecord",
    "PaperEmbeddingRecord",
    "PaperRecord",
    "PlanRecord",
    "ProjectRecord",
    "ReviewRecord",
    "RunRecord",
]
