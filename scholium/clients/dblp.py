"""DBLP: publication search and lookup by dblp key. No key required. Its
value to Scholium is canonical computer science venue metadata (ADR 0002):
DBLP's `venue` string is a controlled name, so "MICCAI", "CVPR" and "NeurIPS"
become filterable rather than free-text matched.
"""

from __future__ import annotations

from typing import Any

from scholium.clients.base import ClientSession
from scholium.store.ids import canonical_id
from scholium.store.records import PaperRecord

SOURCE = "dblp"


def _authors(info: dict[str, Any]) -> list[dict[str, str]] | None:
    raw = (info.get("authors") or {}).get("author")
    if raw is None:
        return None
    if isinstance(raw, dict):
        raw = [raw]
    names = []
    for a in raw:
        name = a.get("text") if isinstance(a, dict) else a
        if name:
            names.append({"name": name})
    return names or None


def _map_hit(hit: dict[str, Any]) -> PaperRecord:
    info = hit.get("info", {})
    doi = info.get("doi")
    title = info.get("title")
    year_text = info.get("year")
    year = int(year_text) if year_text and str(year_text).isdigit() else None
    return PaperRecord(
        id=canonical_id(doi=doi, title=title, year=year),
        doi=doi,
        title=title,
        year=year,
        venue=info.get("venue"),
        authors=_authors(info),
    )


class DblpClient:
    name = SOURCE

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    def search(self, query: str, *, hits: int = 50) -> list[PaperRecord]:
        params = {"q": query, "format": "json", "h": hits}
        data = self._session.get_json("/search/publ/api", params)
        raw_hits = (data.get("result", {}).get("hits", {}) or {}).get("hit", [])
        return [_map_hit(h) for h in raw_hits]

    def get_by_id(self, dblp_key: str) -> PaperRecord | None:
        """`dblp_key` is DBLP's own record key, e.g. `conf/miccai/Smith23`."""
        try:
            data = self._session.get_json(f"/rec/{dblp_key}.json")
        except Exception:
            return None
        info = (data.get("result", {}).get("hit", [{}]) or [{}])[0].get("info", {})
        return _map_hit({"info": info}) if info else None
