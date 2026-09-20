from __future__ import annotations

import httpx
import respx

from scholium.clients.base import ClientSession
from scholium.clients.semanticscholar import SemanticScholarClient

BASE_URL = "https://api.semanticscholar.org/graph/v1"

PAPER = {
    "paperId": "abc123",
    "title": "Conditional Diffusion for MR to CT Synthesis",
    "abstract": "We propose a method.",
    "year": 2023,
    "venue": "MICCAI",
    "authors": [{"name": "Jane Smith"}],
    "externalIds": {"DOI": "10.1/xyz", "ArXiv": "2301.12345"},
    "openAccessPdf": {"url": "https://example.org/paper.pdf"},
}


@respx.mock
def test_search_maps_results(tmp_path):
    respx.get(f"{BASE_URL}/paper/search").mock(
        return_value=httpx.Response(200, json={"data": [PAPER]})
    )
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = SemanticScholarClient(session)
    results = client.search("diffusion models")
    assert len(results) == 1
    paper = results[0]
    assert paper.doi == "10.1/xyz"
    assert paper.arxiv_id == "2301.12345"
    assert paper.s2_id == "abc123"
    assert paper.id == "doi:10.1/xyz"


@respx.mock
def test_get_by_id_returns_none_on_error(tmp_path):
    respx.get(f"{BASE_URL}/paper/abc999").mock(return_value=httpx.Response(404))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = SemanticScholarClient(session)
    assert client.get_by_id("abc999") is None


@respx.mock
def test_references_map_to_edges_with_external_ids(tmp_path):
    respx.get(f"{BASE_URL}/paper/abc123/references").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [{"citedPaper": {"paperId": "def456", "externalIds": {"DOI": "10.2/aaa"}}}]
            },
        )
    )
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = SemanticScholarClient(session)
    edges = client.references("abc123")
    assert edges[0].citing_id == "s2:abc123"
    assert edges[0].cited_id == "doi:10.2/aaa"
    assert edges[0].source == "semanticscholar"


@respx.mock
def test_citations_map_to_edges_falling_back_to_s2_id(tmp_path):
    respx.get(f"{BASE_URL}/paper/abc123/citations").mock(
        return_value=httpx.Response(
            200, json={"data": [{"citingPaper": {"paperId": "ghi789", "externalIds": {}}}]}
        )
    )
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = SemanticScholarClient(session)
    edges = client.citations("abc123")
    assert edges[0].citing_id == "s2:ghi789"
    assert edges[0].cited_id == "s2:abc123"
