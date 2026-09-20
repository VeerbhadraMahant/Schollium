"""arXiv: query API and by-ID lookup. No key; results are Atom XML, so this
is the one client that parses XML with ElementTree rather than reading JSON.
"""

from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree

from scholium.clients.base import ClientSession
from scholium.store.ids import canonical_id, normalize_arxiv_id
from scholium.store.records import PaperRecord

SOURCE = "arxiv"

_ATOM = "{http://www.w3.org/2005/Atom}"
_ARXIV_ID_RE = re.compile(r"arxiv\.org/abs/(?P<id>[^v]+)")


def _extract_id(entry_id_url: str) -> str | None:
    match = _ARXIV_ID_RE.search(entry_id_url)
    return normalize_arxiv_id(match.group("id")) if match else None


def _map_entry(entry: ElementTree.Element) -> PaperRecord:
    entry_id = entry.findtext(f"{_ATOM}id") or ""
    arxiv_id = _extract_id(entry_id)
    title = (entry.findtext(f"{_ATOM}title") or "").strip().replace("\n", " ")
    summary = (entry.findtext(f"{_ATOM}summary") or "").strip().replace("\n", " ") or None
    published = entry.findtext(f"{_ATOM}published") or ""
    year = int(published[:4]) if published[:4].isdigit() else None
    authors = [
        {"name": a.findtext(f"{_ATOM}name")}
        for a in entry.findall(f"{_ATOM}author")
        if a.findtext(f"{_ATOM}name")
    ]
    pdf_url = None
    for link in entry.findall(f"{_ATOM}link"):
        if link.get("title") == "pdf" or link.get("type") == "application/pdf":
            pdf_url = link.get("href")
            break

    return PaperRecord(
        id=canonical_id(arxiv_id=arxiv_id, title=title, year=year),
        arxiv_id=arxiv_id,
        title=title or None,
        abstract=summary,
        year=year,
        authors=authors or None,
        oa_url=pdf_url,
    )


class ArxivClient:
    name = SOURCE

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    def _entries(self, params: dict[str, Any]) -> list[ElementTree.Element]:
        text = self._session.get_text("/query", params)
        root = ElementTree.fromstring(text)
        return root.findall(f"{_ATOM}entry")

    def search(self, query: str, *, max_results: int = 50, start: int = 0) -> list[PaperRecord]:
        params = {
            "search_query": f"all:{query}",
            "start": start,
            "max_results": max_results,
        }
        return [_map_entry(e) for e in self._entries(params)]

    def get_by_id(self, arxiv_id: str) -> PaperRecord | None:
        normalized = normalize_arxiv_id(arxiv_id)
        if normalized is None:
            return None
        entries = self._entries({"id_list": normalized})
        return _map_entry(entries[0]) if entries else None
