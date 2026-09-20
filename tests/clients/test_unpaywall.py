from __future__ import annotations

import httpx
import pytest
import respx

from scholium.clients.base import ClientSession
from scholium.clients.unpaywall import UnpaywallClient

BASE_URL = "https://api.unpaywall.org/v2"

RESPONSE = {
    "doi": "10.1/xyz",
    "title": "Conditional Diffusion for MR to CT Synthesis",
    "year": 2023,
    "best_oa_location": {
        "url_for_pdf": "https://example.org/paper.pdf",
        "url": "https://example.org/x",
    },
}


def test_requires_email(tmp_path):
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    with pytest.raises(ValueError):
        UnpaywallClient(session, email="")


@respx.mock
def test_get_by_id_prefers_pdf_url(tmp_path):
    respx.get(f"{BASE_URL}/10.1/xyz").mock(return_value=httpx.Response(200, json=RESPONSE))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = UnpaywallClient(session, email="me@example.com")
    paper = client.get_by_id("10.1/xyz")
    assert paper.oa_url == "https://example.org/paper.pdf"


@respx.mock
def test_get_by_id_falls_back_to_url_when_no_pdf(tmp_path):
    data = dict(RESPONSE, best_oa_location={"url": "https://example.org/x"})
    respx.get(f"{BASE_URL}/10.1/xyz").mock(return_value=httpx.Response(200, json=data))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = UnpaywallClient(session, email="me@example.com")
    paper = client.get_by_id("10.1/xyz")
    assert paper.oa_url == "https://example.org/x"


@respx.mock
def test_get_by_id_none_when_no_oa_location(tmp_path):
    data = dict(RESPONSE, best_oa_location=None)
    respx.get(f"{BASE_URL}/10.1/xyz").mock(return_value=httpx.Response(200, json=data))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = UnpaywallClient(session, email="me@example.com")
    assert client.best_oa_url("10.1/xyz") is None


@respx.mock
def test_get_by_id_returns_none_on_404(tmp_path):
    respx.get(f"{BASE_URL}/10.1/missing").mock(return_value=httpx.Response(404))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = UnpaywallClient(session, email="me@example.com")
    assert client.get_by_id("10.1/missing") is None
