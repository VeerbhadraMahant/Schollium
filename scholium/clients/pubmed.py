"""PubMed E-utilities: esearch for IDs, efetch for records. esearch returns
JSON; efetch returns XML, so this client mixes both response shapes on
purpose rather than forcing one through a JSON-only helper.
"""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree

from scholium.clients.base import ClientSession
from scholium.store.ids import canonical_id, normalize_pmid
from scholium.store.records import PaperRecord

SOURCE = "pubmed"


def _text(el: ElementTree.Element | None) -> str | None:
    return el.text.strip() if el is not None and el.text else None


def _map_article(article: ElementTree.Element) -> PaperRecord:
    medline = article.find("MedlineCitation")
    pmid = _text(medline.find("PMID")) if medline is not None else None
    article_el = medline.find("Article") if medline is not None else None

    title = _text(article_el.find("ArticleTitle")) if article_el is not None else None

    abstract_parts = []
    if article_el is not None:
        for chunk in article_el.findall("Abstract/AbstractText"):
            if chunk.text:
                abstract_parts.append(chunk.text.strip())
    abstract = " ".join(abstract_parts) or None

    venue = _text(article_el.find("Journal/Title")) if article_el is not None else None

    year = None
    if article_el is not None:
        year_text = _text(article_el.find("Journal/JournalIssue/PubDate/Year"))
        if year_text and year_text.isdigit():
            year = int(year_text)

    authors = []
    if article_el is not None:
        for author in article_el.findall("AuthorList/Author"):
            last = _text(author.find("LastName"))
            fore = _text(author.find("ForeName"))
            if last:
                name = f"{fore} {last}" if fore else last
                authors.append({"name": name})

    doi = None
    for eloc in article.findall(".//ELocationID") if article is not None else []:
        if eloc.get("EIdType") == "doi" and eloc.text:
            doi = eloc.text.strip()
            break

    pmid_norm = normalize_pmid(pmid)
    return PaperRecord(
        id=canonical_id(doi=doi, pmid=pmid_norm, title=title, year=year),
        doi=doi,
        pmid=pmid_norm,
        title=title,
        abstract=abstract,
        year=year,
        venue=venue,
        authors=authors or None,
    )


class PubMedClient:
    name = SOURCE

    def __init__(self, session: ClientSession, *, api_key: str | None = None) -> None:
        self._session = session
        self._api_key = api_key

    def _params(self, extra: dict[str, Any]) -> dict[str, Any]:
        params = dict(extra)
        if self._api_key:
            params["api_key"] = self._api_key
        return params

    def search(self, query: str, *, retmax: int = 50) -> list[PaperRecord]:
        ids = self.search_ids(query, retmax=retmax)
        return self.get_many(ids) if ids else []

    def search_ids(self, query: str, *, retmax: int = 50) -> list[str]:
        params = self._params({"db": "pubmed", "term": query, "retmax": retmax, "retmode": "json"})
        data = self._session.get_json("/esearch.fcgi", params)
        return data.get("esearchresult", {}).get("idlist", [])

    def get_many(self, pmids: list[str]) -> list[PaperRecord]:
        if not pmids:
            return []
        params = self._params({"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"})
        text = self._session.get_text("/efetch.fcgi", params)
        root = ElementTree.fromstring(text)
        return [_map_article(a) for a in root.findall("PubmedArticle")]

    def get_by_id(self, pmid: str) -> PaperRecord | None:
        results = self.get_many([pmid])
        return results[0] if results else None
