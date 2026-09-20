from __future__ import annotations

import httpx
import respx

from scholium.clients.base import ClientSession
from scholium.clients.dblp import DblpClient

BASE_URL = "https://dblp.org"

HIT = {
    "info": {
        "title": "Conditional Diffusion for MR to CT Synthesis",
        "venue": "MICCAI",
        "year": "2023",
        "doi": "10.1/xyz",
        "authors": {"author": {"text": "Jane Smith"}},
    }
}


@respx.mock
def test_search_maps_single_author_dict(tmp_path):
    respx.get(f"{BASE_URL}/search/publ/api").mock(
        return_value=httpx.Response(200, json={"result": {"hits": {"hit": [HIT]}}})
    )
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = DblpClient(session)
    results = client.search("diffusion")
    assert len(results) == 1
    paper = results[0]
    assert paper.venue == "MICCAI"
    assert paper.year == 2023
    assert paper.authors == [{"name": "Jane Smith"}]


@respx.mock
def test_search_maps_multiple_authors_list(tmp_path):
    hit = dict(HIT)
    hit["info"] = dict(
        HIT["info"], authors={"author": [{"text": "Jane Smith"}, {"text": "John Doe"}]}
    )
    respx.get(f"{BASE_URL}/search/publ/api").mock(
        return_value=httpx.Response(200, json={"result": {"hits": {"hit": [hit]}}})
    )
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = DblpClient(session)
    results = client.search("diffusion")
    assert results[0].authors == [{"name": "Jane Smith"}, {"name": "John Doe"}]


@respx.mock
def test_search_with_no_hits_returns_empty_list(tmp_path):
    respx.get(f"{BASE_URL}/search/publ/api").mock(
        return_value=httpx.Response(200, json={"result": {"hits": {}}})
    )
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = DblpClient(session)
    assert client.search("nothing") == []


@respx.mock
def test_get_by_id_returns_none_on_error(tmp_path):
    respx.get(f"{BASE_URL}/rec/conf/miccai/Missing23.json").mock(return_value=httpx.Response(404))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = DblpClient(session)
    assert client.get_by_id("conf/miccai/Missing23") is None
