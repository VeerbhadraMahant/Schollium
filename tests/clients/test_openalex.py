from __future__ import annotations

import httpx
import respx

from scholium.clients.base import ClientSession
from scholium.clients.openalex import OpenAlexClient, reconstruct_abstract

BASE_URL = "https://api.openalex.org"

WORK = {
    "id": "https://openalex.org/W2741809807",
    "doi": "https://doi.org/10.1/xyz",
    "title": "Conditional Diffusion for MR to CT Synthesis",
    "publication_year": 2023,
    "primary_location": {"source": {"display_name": "MICCAI"}},
    "authorships": [{"author": {"display_name": "Jane Smith"}}],
    "open_access": {"oa_url": "https://example.org/paper.pdf"},
    "abstract_inverted_index": {"We": [0], "propose": [1], "a": [2], "method": [3]},
    "referenced_works": ["https://openalex.org/W1"],
}


def test_reconstruct_abstract_orders_by_position():
    assert reconstruct_abstract({"We": [0], "propose": [1], "a": [2]}) == "We propose a"


def test_reconstruct_abstract_none_when_missing():
    assert reconstruct_abstract(None) is None
    assert reconstruct_abstract({}) is None


@respx.mock
def test_search_maps_results(tmp_path):
    respx.get(f"{BASE_URL}/works").mock(return_value=httpx.Response(200, json={"results": [WORK]}))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = OpenAlexClient(session, email="me@example.com")
    results = client.search("diffusion models", year_from=2015)

    assert len(results) == 1
    paper = results[0]
    assert paper.doi == "10.1/xyz"
    assert paper.title == "Conditional Diffusion for MR to CT Synthesis"
    assert paper.year == 2023
    assert paper.venue == "MICCAI"
    assert paper.abstract == "We propose a method"
    assert paper.authors == [{"name": "Jane Smith"}]
    assert paper.id == "doi:10.1/xyz"


@respx.mock
def test_search_sends_email_for_polite_pool(tmp_path):
    route = respx.get(f"{BASE_URL}/works").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = OpenAlexClient(session, email="me@example.com")
    client.search("x")
    assert route.calls.last.request.url.params["mailto"] == "me@example.com"


@respx.mock
def test_get_by_id_returns_none_on_404(tmp_path):
    respx.get(f"{BASE_URL}/works/W999").mock(return_value=httpx.Response(404))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = OpenAlexClient(session)
    assert client.get_by_id("W999") is None


@respx.mock
def test_references_maps_to_citation_edges(tmp_path):
    respx.get(f"{BASE_URL}/works/W2741809807").mock(return_value=httpx.Response(200, json=WORK))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = OpenAlexClient(session)
    edges = client.references("W2741809807")
    assert len(edges) == 1
    assert edges[0].citing_id == "openalex:W2741809807"
    assert edges[0].cited_id == "openalex:W1"
    assert edges[0].source == "openalex"
