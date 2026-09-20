from __future__ import annotations

import httpx
import respx

from scholium.clients.base import ClientSession
from scholium.clients.europepmc import EuropePmcClient

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"

RESULT = {
    "doi": "10.1/xyz",
    "pmid": "12345678",
    "title": "Conditional Diffusion for MR to CT Synthesis",
    "abstractText": "We propose a method.",
    "journalTitle": "Medical Image Analysis",
    "pubYear": "2023",
    "authorList": {"author": [{"fullName": "Smith J"}]},
    "fullTextUrlList": {
        "fullTextUrl": [{"availability": "Open access", "url": "https://example.org/paper.pdf"}]
    },
}


@respx.mock
def test_search_maps_results(tmp_path):
    respx.get(f"{BASE_URL}/search").mock(
        return_value=httpx.Response(200, json={"resultList": {"result": [RESULT]}})
    )
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = EuropePmcClient(session)
    results = client.search("diffusion models")
    assert len(results) == 1
    paper = results[0]
    assert paper.doi == "10.1/xyz"
    assert paper.pmid == "12345678"
    assert paper.oa_url == "https://example.org/paper.pdf"
    assert paper.id == "doi:10.1/xyz"


@respx.mock
def test_get_by_id_none_when_no_results(tmp_path):
    respx.get(f"{BASE_URL}/search").mock(
        return_value=httpx.Response(200, json={"resultList": {"result": []}})
    )
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = EuropePmcClient(session)
    assert client.get_by_id("999") is None


@respx.mock
def test_fetch_fulltext_xml_returns_none_on_failure(tmp_path):
    respx.get(f"{BASE_URL}/PMC1/fullTextXML").mock(return_value=httpx.Response(404))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = EuropePmcClient(session)
    assert client.fetch_fulltext_xml("PMC1") is None


@respx.mock
def test_fetch_fulltext_xml_returns_text_on_success(tmp_path):
    respx.get(f"{BASE_URL}/PMC1/fullTextXML").mock(
        return_value=httpx.Response(200, text="<article/>")
    )
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = EuropePmcClient(session)
    assert client.fetch_fulltext_xml("PMC1") == "<article/>"
