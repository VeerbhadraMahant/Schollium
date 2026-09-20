"""Semantic Scholar Graph API: search, get by ID, references, citations.
Free key required for a usable rate; the field list is requested explicitly
on every call since the API returns nothing by default.
"""

from __future__ import annotations

from typing import Any

from scholium.clients.base import ClientSession
from scholium.store.ids import canonical_id
from scholium.store.records import CitationEdgeRecord, PaperRecord

SOURCE = "semanticscholar"

FIELDS = "title,abstract,year,venue,authors,externalIds,openAccessPdf"


def _map_paper(paper: dict[str, Any]) -> PaperRecord:
    external = paper.get("externalIds") or {}
    authors = [{"name": a.get("name")} for a in paper.get("authors", []) or []]
    oa = paper.get("openAccessPdf") or {}
    return PaperRecord(
        id=canonical_id(
            doi=external.get("DOI"),
            arxiv_id=external.get("ArXiv"),
            pmid=external.get("PubMed"),
            title=paper.get("title"),
            year=paper.get("year"),
        ),
        doi=external.get("DOI"),
        arxiv_id=external.get("ArXiv"),
        pmid=external.get("PubMed"),
        s2_id=paper.get("paperId"),
        title=paper.get("title"),
        abstract=paper.get("abstract"),
        year=paper.get("year"),
        venue=paper.get("venue"),
        authors=authors or None,
        oa_url=oa.get("url"),
    )


class SemanticScholarClient:
    name = SOURCE

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    def search(self, query: str, *, limit: int = 50) -> list[PaperRecord]:
        params = {"query": query, "limit": limit, "fields": FIELDS}
        data = self._session.get_json("/paper/search", params)
        return [_map_paper(p) for p in data.get("data", [])]

    def get_by_id(self, s2_paper_id: str) -> PaperRecord | None:
        """`s2_paper_id` accepts S2's own id, or a prefixed external id such
        as DOI:10.x/y or ARXIV:2301.12345, per the Graph API's own convention.
        """
        try:
            data = self._session.get_json(f"/paper/{s2_paper_id}", {"fields": FIELDS})
        except Exception:
            return None
        return _map_paper(data)

    def references(self, s2_paper_id: str, *, limit: int = 100) -> list[CitationEdgeRecord]:
        data = self._session.get_json(
            f"/paper/{s2_paper_id}/references", {"fields": FIELDS, "limit": limit}
        )
        citing = _resolve_edge_id(s2_paper_id)
        edges = []
        for item in data.get("data", []):
            cited_paper = item.get("citedPaper") or {}
            cited = _resolve_edge_id(cited_paper.get("paperId"), fallback=cited_paper)
            edges.append(CitationEdgeRecord(citing_id=citing, cited_id=cited, source=SOURCE))
        return edges

    def citations(self, s2_paper_id: str, *, limit: int = 100) -> list[CitationEdgeRecord]:
        data = self._session.get_json(
            f"/paper/{s2_paper_id}/citations", {"fields": FIELDS, "limit": limit}
        )
        cited = _resolve_edge_id(s2_paper_id)
        edges = []
        for item in data.get("data", []):
            citing_paper = item.get("citingPaper") or {}
            citing = _resolve_edge_id(citing_paper.get("paperId"), fallback=citing_paper)
            edges.append(CitationEdgeRecord(citing_id=citing, cited_id=cited, source=SOURCE))
        return edges


def _resolve_edge_id(s2_paper_id: str | None, fallback: dict[str, Any] | None = None) -> str:
    """Citation edges reference the canonical id, not the raw S2 paper id, so
    they line up with rows written by any other client. When only the bare S2
    id is available (no DOI/arXiv/PMID in the edge payload), fall back to it
    directly; it is still stable and joinable against `paper.s2_id`.
    """
    if fallback:
        external = fallback.get("externalIds") or {}
        if external.get("DOI") or external.get("ArXiv") or external.get("PubMed"):
            return canonical_id(
                doi=external.get("DOI"), arxiv_id=external.get("ArXiv"), pmid=external.get("PubMed")
            )
    return f"s2:{s2_paper_id}"
