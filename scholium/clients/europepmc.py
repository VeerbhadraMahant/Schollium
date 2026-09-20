"""Europe PMC: search, get by ID, and full-text XML when open access. No key.
Superset of PubMed (ADR 0002); `resultType=core` is requested so abstracts
and author lists come back on the search call itself, not a second request.
"""

from __future__ import annotations

from typing import Any

from scholium.clients.base import ClientSession
from scholium.store.ids import canonical_id, normalize_pmid
from scholium.store.records import PaperRecord

SOURCE = "europepmc"


def _map_result(result: dict[str, Any]) -> PaperRecord:
    doi = result.get("doi")
    pmid = normalize_pmid(result.get("pmid"))
    authors = None
    author_list = (result.get("authorList") or {}).get("author")
    if author_list:
        authors = [{"name": a.get("fullName")} for a in author_list if a.get("fullName")] or None
    year_text = result.get("pubYear")
    year = int(year_text) if year_text and str(year_text).isdigit() else None

    oa_url = None
    for link in (result.get("fullTextUrlList") or {}).get("fullTextUrl", []):
        if link.get("availability", "").lower().startswith("open access"):
            oa_url = link.get("url")
            break

    return PaperRecord(
        id=canonical_id(doi=doi, pmid=pmid, title=result.get("title"), year=year),
        doi=doi,
        pmid=pmid,
        title=result.get("title"),
        abstract=result.get("abstractText"),
        year=year,
        venue=result.get("journalTitle"),
        authors=authors,
        oa_url=oa_url,
    )


class EuropePmcClient:
    name = SOURCE

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    def search(self, query: str, *, page_size: int = 50) -> list[PaperRecord]:
        params = {"query": query, "format": "json", "resultType": "core", "pageSize": page_size}
        data = self._session.get_json("/search", params)
        return [_map_result(r) for r in data.get("resultList", {}).get("result", [])]

    def get_by_id(self, pmid: str) -> PaperRecord | None:
        normalized = normalize_pmid(pmid)
        if normalized is None:
            return None
        params = {
            "query": f"EXT_ID:{normalized} AND SRC:MED",
            "format": "json",
            "resultType": "core",
        }
        data = self._session.get_json("/search", params)
        results = data.get("resultList", {}).get("result", [])
        return _map_result(results[0]) if results else None

    def fetch_fulltext_xml(self, pmcid: str) -> str | None:
        """Open-access full text as XML. `pmcid` is the PMC id (e.g. PMC1234567),
        present on europepmc results with an open-access full-text link. Used by
        Read (Phase 1); Phase 0 only needs the plumbing to exist.
        """
        try:
            return self._session.get_text(f"/{pmcid}/fullTextXML")
        except Exception:
            return None
