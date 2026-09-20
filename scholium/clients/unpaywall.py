"""Unpaywall: the best open-access PDF link for a DOI. No key; email
required. By-DOI lookup only, per plan section 15.1; there is no search.
"""

from __future__ import annotations

from typing import Any

from scholium.clients.base import ClientSession
from scholium.store.ids import canonical_id
from scholium.store.records import PaperRecord

SOURCE = "unpaywall"


def _best_oa_url(data: dict[str, Any]) -> str | None:
    best = data.get("best_oa_location")
    if not best:
        return None
    return best.get("url_for_pdf") or best.get("url")


def _map_result(data: dict[str, Any]) -> PaperRecord:
    doi = data.get("doi")
    return PaperRecord(
        id=canonical_id(doi=doi, title=data.get("title"), year=data.get("year")),
        doi=doi,
        title=data.get("title"),
        year=data.get("year"),
        oa_url=_best_oa_url(data),
    )


class UnpaywallClient:
    name = SOURCE

    def __init__(self, session: ClientSession, *, email: str) -> None:
        if not email:
            raise ValueError("Unpaywall requires a contact email; set contact.email in config")
        self._session = session
        self._email = email

    def get_by_id(self, doi: str) -> PaperRecord | None:
        try:
            data = self._session.get_json(f"/{doi}", {"email": self._email})
        except Exception:
            return None
        return _map_result(data)

    def best_oa_url(self, doi: str) -> str | None:
        record = self.get_by_id(doi)
        return record.oa_url if record else None
