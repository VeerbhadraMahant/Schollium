from __future__ import annotations

import httpx
import respx

from scholium.clients.base import ClientSession
from scholium.clients.crossref import CrossrefClient, is_retracted

BASE_URL = "https://api.crossref.org"

WORK = {
    "DOI": "10.1/XYZ",
    "title": ["Conditional Diffusion for MR to CT Synthesis"],
    "author": [{"given": "Jane", "family": "Smith"}],
    "published-print": {"date-parts": [[2023, 6]]},
    "container-title": ["MICCAI"],
}


def test_is_retracted_true_when_update_to_has_retraction_type():
    work = {"update-to": [{"type": "retraction"}]}
    assert is_retracted(work) is True


def test_is_retracted_false_when_no_update_to():
    assert is_retracted({}) is False


@respx.mock
def test_get_by_id_maps_work(tmp_path):
    respx.get(f"{BASE_URL}/works/10.1/xyz").mock(
        return_value=httpx.Response(200, json={"message": WORK})
    )
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = CrossrefClient(session, email="me@example.com")
    paper = client.get_by_id("10.1/xyz")
    assert paper.doi == "10.1/xyz"  # lowercased
    assert paper.title == "Conditional Diffusion for MR to CT Synthesis"
    assert paper.year == 2023
    assert paper.venue == "MICCAI"
    assert paper.authors == [{"name": "Jane Smith"}]


@respx.mock
def test_get_by_id_returns_none_on_404(tmp_path):
    respx.get(f"{BASE_URL}/works/10.1/missing").mock(return_value=httpx.Response(404))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = CrossrefClient(session)
    assert client.get_by_id("10.1/missing") is None


@respx.mock
def test_check_retracted(tmp_path):
    retracted_work = dict(WORK, **{"update-to": [{"type": "retraction"}]})
    respx.get(f"{BASE_URL}/works/10.1/xyz").mock(
        return_value=httpx.Response(200, json={"message": retracted_work})
    )
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = CrossrefClient(session)
    assert client.check_retracted("10.1/xyz") is True


@respx.mock
def test_search_maps_items(tmp_path):
    respx.get(f"{BASE_URL}/works").mock(
        return_value=httpx.Response(200, json={"message": {"items": [WORK]}})
    )
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = CrossrefClient(session)
    results = client.search("diffusion")
    assert len(results) == 1
