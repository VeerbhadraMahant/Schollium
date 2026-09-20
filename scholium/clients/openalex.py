"""OpenAlex: works search, get by ID, references, citations. No key; a
contact email raises the rate limit ("polite pool"). Abstracts come back as
an inverted index (word -> positions), so reconstruction happens once, here,
and is tested, per plan section 5.2.
"""

from __future__ import annotations

from typing import Any

from scholium.clients.base import ClientSession
from scholium.store.ids import canonical_id
from scholium.store.records import CitationEdgeRecord, PaperRecord

SOURCE = "openalex"


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    if not inverted_index:
        return None
    positions: dict[int, str] = {}
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions[i] = word
    if not positions:
        return None
    return " ".join(positions[i] for i in sorted(positions))


def _strip_doi_url(doi: str | None) -> str | None:
    if doi is None:
        return None
    return doi.removeprefix("https://doi.org/")


def _short_openalex_id(openalex_url: str | None) -> str | None:
    if openalex_url is None:
        return None
    return openalex_url.rsplit("/", 1)[-1]


def _map_work(work: dict[str, Any]) -> PaperRecord:
    doi = _strip_doi_url(work.get("doi"))
    openalex_short = _short_openalex_id(work.get("id"))
    authors = [
        {"name": a.get("author", {}).get("display_name")} for a in work.get("authorships", []) or []
    ]
    year = work.get("publication_year")
    venue = (work.get("primary_location") or {}).get("source", {})
    venue_name = venue.get("display_name") if venue else None
    oa = work.get("open_access") or {}

    return PaperRecord(
        id=canonical_id(doi=doi, openalex_id=openalex_short, title=work.get("title"), year=year),
        doi=doi,
        openalex_id=openalex_short,
        title=work.get("title"),
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        year=year,
        venue=venue_name,
        authors=authors or None,
        oa_url=oa.get("oa_url"),
    )


class OpenAlexClient:
    name = SOURCE

    def __init__(self, session: ClientSession, *, email: str | None = None) -> None:
        self._session = session
        self._email = email

    def _params(self, extra: dict[str, Any]) -> dict[str, Any]:
        params = dict(extra)
        if self._email:
            params["mailto"] = self._email
        return params

    def search(
        self, query: str, *, year_from: int | None = None, per_page: int = 50
    ) -> list[PaperRecord]:
        params: dict[str, Any] = {"search": query, "per-page": per_page}
        if year_from is not None:
            params["filter"] = f"from_publication_date:{year_from}-01-01"
        data = self._session.get_json("/works", self._params(params))
        return [_map_work(w) for w in data.get("results", [])]

    def get_by_id(self, doi_or_openalex_id: str) -> PaperRecord | None:
        ref = doi_or_openalex_id
        path = (
            f"/works/https://doi.org/{ref}"
            if "/" in ref and not ref.startswith("W")
            else f"/works/{ref}"
        )
        try:
            data = self._session.get_json(path, self._params({}))
        except Exception:
            return None
        return _map_work(data)

    def references(self, openalex_id: str) -> list[CitationEdgeRecord]:
        """Papers `openalex_id` cites, via its referenced_works list."""
        data = self._session.get_json(f"/works/{openalex_id}", self._params({}))
        citing = canonical_id(openalex_id=openalex_id)
        edges = []
        for ref_url in data.get("referenced_works", []) or []:
            cited = canonical_id(openalex_id=_short_openalex_id(ref_url))
            edges.append(CitationEdgeRecord(citing_id=citing, cited_id=cited, source=SOURCE))
        return edges

    def citations(self, openalex_id: str, *, per_page: int = 50) -> list[CitationEdgeRecord]:
        """Papers that cite `openalex_id`."""
        params = self._params({"filter": f"cites:{openalex_id}", "per-page": per_page})
        data = self._session.get_json("/works", params)
        cited = canonical_id(openalex_id=openalex_id)
        edges = []
        for work in data.get("results", []):
            citing = canonical_id(openalex_id=_short_openalex_id(work.get("id")))
            edges.append(CitationEdgeRecord(citing_id=citing, cited_id=cited, source=SOURCE))
        return edges
