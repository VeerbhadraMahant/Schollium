from __future__ import annotations

import httpx
import respx

from scholium.clients.arxiv import ArxivClient, _extract_id
from scholium.clients.base import ClientSession

BASE_URL = "http://export.arxiv.org/api"

ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v2</id>
    <published>2023-01-15T00:00:00Z</published>
    <title>Conditional Diffusion for
MR to CT Synthesis</title>
    <summary>We propose a
method.</summary>
    <author><name>Jane Smith</name></author>
    <link href="http://arxiv.org/abs/2301.12345v2" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/2301.12345v2" rel="related"
          type="application/pdf"/>
  </entry>
</feed>
"""


def test_extract_id_strips_version():
    assert _extract_id("http://arxiv.org/abs/2301.12345v2") == "2301.12345"


def test_extract_id_none_when_no_match():
    assert _extract_id("http://arxiv.org/nothing") is None


@respx.mock
def test_search_maps_entry(tmp_path):
    respx.get(f"{BASE_URL}/query").mock(return_value=httpx.Response(200, text=ATOM_FEED))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = ArxivClient(session)
    results = client.search("diffusion models")

    assert len(results) == 1
    paper = results[0]
    assert paper.arxiv_id == "2301.12345"
    assert paper.title == "Conditional Diffusion for MR to CT Synthesis"
    assert paper.abstract == "We propose a method."
    assert paper.year == 2023
    assert paper.oa_url == "http://arxiv.org/pdf/2301.12345v2"
    assert paper.authors == [{"name": "Jane Smith"}]
    assert paper.id == "arxiv:2301.12345"


@respx.mock
def test_get_by_id_returns_none_when_feed_is_empty(tmp_path):
    empty_feed = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    respx.get(f"{BASE_URL}/query").mock(return_value=httpx.Response(200, text=empty_feed))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = ArxivClient(session)
    assert client.get_by_id("9999.99999") is None


def test_get_by_id_with_unparseable_id_returns_none_without_a_request(tmp_path):
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = ArxivClient(session)
    assert client.get_by_id("") is None
