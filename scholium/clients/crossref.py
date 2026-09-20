"""Crossref: works by DOI, works search. The authoritative source for DOI
metadata; also exposes a retraction signal via its `update-to` relation,
which Cite (Phase 2) will use for its retraction check.
"""

from __future__ import annotations

from typing import Any

from scholium.clients.base import ClientSession
from scholium.store.ids import canonical_id
from scholium.store.records import PaperRecord

SOURCE = "crossref"


def _year_from_date_parts(container: dict[str, Any] | None) -> int | None:
    if not container:
        return None
    parts = container.get("date-parts")
    if parts and parts[0] and parts[0][0]:
        return int(parts[0][0])
    return None


def is_retracted(work: dict[str, Any]) -> bool:
    return any(u.get("type") == "retraction" for u in work.get("update-to", []) or [])


def _map_work(work: dict[str, Any]) -> PaperRecord:
    doi = work.get("DOI")
    titles = work.get("title") or []
    title = titles[0] if titles else None
    authors = [
        {"name": " ".join(p for p in (a.get("given"), a.get("family")) if p)}
        for a in work.get("author", []) or []
    ]
    year = (
        _year_from_date_parts(work.get("published-print"))
        or _year_from_date_parts(work.get("published-online"))
        or _year_from_date_parts(work.get("published"))
    )
    container = work.get("container-title") or []
    venue = container[0] if container else None

    return PaperRecord(
        id=canonical_id(doi=doi, title=title, year=year),
        doi=doi.lower() if doi else None,
        title=title,
        year=year,
        venue=venue,
        authors=authors or None,
        bibtex=None,
    )


class CrossrefClient:
    name = SOURCE

    def __init__(self, session: ClientSession, *, email: str | None = None) -> None:
        self._session = session
        self._email = email

    def _params(self, extra: dict[str, Any]) -> dict[str, Any]:
        params = dict(extra)
        if self._email:
            params["mailto"] = self._email
        return params

    def search(self, query: str, *, rows: int = 50) -> list[PaperRecord]:
        params = self._params({"query": query, "rows": rows})
        data = self._session.get_json("/works", params)
        return [_map_work(w) for w in data.get("message", {}).get("items", [])]

    def get_by_id(self, doi: str) -> PaperRecord | None:
        try:
            data = self._session.get_json(f"/works/{doi}", self._params({}))
        except Exception:
            return None
        return _map_work(data.get("message", data))

    def check_retracted(self, doi: str) -> bool:
        try:
            data = self._session.get_json(f"/works/{doi}", self._params({}))
        except Exception:
            return False
        return is_retracted(data.get("message", data))
