from __future__ import annotations

import httpx
import respx

from scholium.clients.base import ClientSession
from scholium.clients.pubmed import PubMedClient

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

EFETCH_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>Conditional Diffusion for MR to CT Synthesis</ArticleTitle>
        <Abstract>
          <AbstractText>We propose a method.</AbstractText>
          <AbstractText>It works well.</AbstractText>
        </Abstract>
        <Journal>
          <Title>Medical Image Analysis</Title>
          <JournalIssue>
            <PubDate><Year>2023</Year></PubDate>
          </JournalIssue>
        </Journal>
        <AuthorList>
          <Author><LastName>Smith</LastName><ForeName>Jane</ForeName></Author>
        </AuthorList>
        <ELocationID EIdType="doi">10.1/xyz</ELocationID>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""


@respx.mock
def test_search_ids_then_get_many(tmp_path):
    respx.get(f"{BASE_URL}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"idlist": ["12345678"]}})
    )
    respx.get(f"{BASE_URL}/efetch.fcgi").mock(return_value=httpx.Response(200, text=EFETCH_XML))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = PubMedClient(session)

    results = client.search("diffusion models")
    assert len(results) == 1
    paper = results[0]
    assert paper.pmid == "12345678"
    assert paper.doi == "10.1/xyz"
    assert paper.title == "Conditional Diffusion for MR to CT Synthesis"
    assert paper.abstract == "We propose a method. It works well."
    assert paper.venue == "Medical Image Analysis"
    assert paper.year == 2023
    assert paper.authors == [{"name": "Jane Smith"}]
    assert paper.id == "doi:10.1/xyz"


@respx.mock
def test_search_with_no_hits_does_not_call_efetch(tmp_path):
    respx.get(f"{BASE_URL}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"idlist": []}})
    )
    efetch_route = respx.get(f"{BASE_URL}/efetch.fcgi").mock(
        return_value=httpx.Response(200, text="")
    )
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = PubMedClient(session)
    assert client.search("nothing") == []
    assert efetch_route.call_count == 0


@respx.mock
def test_get_by_id(tmp_path):
    respx.get(f"{BASE_URL}/efetch.fcgi").mock(return_value=httpx.Response(200, text=EFETCH_XML))
    session = ClientSession(BASE_URL, cache_dir=tmp_path)
    client = PubMedClient(session)
    paper = client.get_by_id("12345678")
    assert paper is not None
    assert paper.pmid == "12345678"
