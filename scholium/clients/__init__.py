"""One module per external API: openalex, semanticscholar, arxiv, pubmed,
europepmc, crossref, unpaywall, dblp (Phase 0, ADR 0002). Each client returns
Pydantic records already mapped to store fields; no tool talks to these APIs
directly.
"""
