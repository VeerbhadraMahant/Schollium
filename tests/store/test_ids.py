"""Canonical ID tests. Phase 0 checklist requires at least 25 cases, ugly ones
included: uppercase DOIs, arXiv IDs embedded inside a 10.48550 DOI, old-style
arXiv IDs, titles with LaTeX and unicode.
"""

from __future__ import annotations

import pytest

from scholium.store.ids import (
    canonical_id,
    normalize_arxiv_id,
    normalize_doi,
    normalize_openalex_id,
    normalize_pmid,
    normalize_title,
    title_hash,
)

# -- DOI normalization -------------------------------------------------------

DOI_CASES = [
    ("10.1000/xyz123", "10.1000/xyz123"),
    ("10.1000/XYZ123", "10.1000/xyz123"),  # uppercase folds
    ("https://doi.org/10.1000/xyz123", "10.1000/xyz123"),
    ("http://doi.org/10.1000/xyz123", "10.1000/xyz123"),
    ("https://dx.doi.org/10.1000/xyz123", "10.1000/xyz123"),
    ("doi:10.1000/xyz123", "10.1000/xyz123"),
    ("DOI:10.1000/xyz123", "10.1000/xyz123"),
    ("  10.1000/xyz123  ", "10.1000/xyz123"),
    ("10.1000/xyz123.", "10.1000/xyz123"),  # trailing punctuation
    (None, None),
    ("", None),
    ("   ", None),
]


@pytest.mark.parametrize("raw, expected", DOI_CASES)
def test_normalize_doi(raw, expected):
    assert normalize_doi(raw) == expected


# -- arXiv ID normalization ---------------------------------------------------

ARXIV_CASES = [
    ("2301.12345", "2301.12345"),
    ("2301.12345v1", "2301.12345"),
    ("2301.12345v23", "2301.12345"),
    ("arXiv:2301.12345", "2301.12345"),
    ("arxiv:2301.12345v2", "2301.12345"),
    ("hep-th/9901001", "hep-th/9901001"),  # old-style, archive prefix
    ("hep-th/9901001v2", "hep-th/9901001"),
    ("astro-ph/0501001", "astro-ph/0501001"),
    ("  2301.12345  ", "2301.12345"),
    (None, None),
    ("", None),
]


@pytest.mark.parametrize("raw, expected", ARXIV_CASES)
def test_normalize_arxiv_id(raw, expected):
    assert normalize_arxiv_id(raw) == expected


# -- PMID normalization -------------------------------------------------------

PMID_CASES = [
    ("12345678", "12345678"),
    ("PMID: 12345678", "12345678"),
    (12345678, "12345678"),
    ("  12345678  ", "12345678"),
    (None, None),
    ("", None),
    ("no digits here", None),
]


@pytest.mark.parametrize("raw, expected", PMID_CASES)
def test_normalize_pmid(raw, expected):
    assert normalize_pmid(raw) == expected


# -- OpenAlex ID normalization -------------------------------------------------

OPENALEX_CASES = [
    ("W2741809807", "W2741809807"),
    ("w2741809807", "W2741809807"),
    ("https://openalex.org/W2741809807", "W2741809807"),
    ("  W2741809807  ", "W2741809807"),
    (None, None),
    ("", None),
]


@pytest.mark.parametrize("raw, expected", OPENALEX_CASES)
def test_normalize_openalex_id(raw, expected):
    assert normalize_openalex_id(raw) == expected


# -- Title normalization (fallback hash input) ---------------------------------


def test_normalize_title_strips_latex():
    assert normalize_title(r"A \emph{Novel} Approach") == "a novel approach"


def test_normalize_title_strips_math():
    assert normalize_title(r"Bounds on $O(n)$ complexity") == "bounds on o n complexity"


def test_normalize_title_folds_unicode():
    assert normalize_title("Über Diffusion Modelle") == "uber diffusion modelle"


def test_normalize_title_collapses_whitespace_and_punctuation():
    assert (
        normalize_title("Multi-Modal,   MR-to-CT!! Synthesis") == "multi modal mr to ct synthesis"
    )


def test_normalize_title_none_and_empty():
    assert normalize_title(None) is None
    assert normalize_title("   ") is None


def test_title_hash_is_deterministic():
    a = title_hash("Some Paper", "Smith", 2023)
    b = title_hash("Some Paper", "Smith", 2023)
    assert a == b


def test_title_hash_changes_with_any_input():
    base = title_hash("Some Paper", "Smith", 2023)
    assert title_hash("Some Other Paper", "Smith", 2023) != base
    assert title_hash("Some Paper", "Jones", 2023) != base
    assert title_hash("Some Paper", "Smith", 2024) != base


# -- canonical_id precedence and the ugly real cases ---------------------------


def test_canonical_id_doi_wins_over_everything():
    cid = canonical_id(
        doi="10.1000/xyz123",
        arxiv_id="2301.12345",
        pmid="999",
        openalex_id="W1",
        title="Ignored",
    )
    assert cid == "doi:10.1000/xyz123"


def test_canonical_id_uppercase_doi_normalizes():
    assert canonical_id(doi="10.1000/XYZ123") == "doi:10.1000/xyz123"


def test_canonical_id_arxiv_wins_over_pmid_and_openalex():
    cid = canonical_id(arxiv_id="2301.12345", pmid="999", openalex_id="W1")
    assert cid == "arxiv:2301.12345"


def test_canonical_id_pmid_wins_over_openalex():
    cid = canonical_id(pmid="12345678", openalex_id="W1")
    assert cid == "pmid:12345678"


def test_canonical_id_openalex_is_last_real_identifier():
    cid = canonical_id(openalex_id="W2741809807", title="Something")
    assert cid == "openalex:W2741809807"


def test_canonical_id_falls_back_to_title_hash():
    cid = canonical_id(title="Some Paper", first_author_surname="Smith", year=2023)
    assert cid.startswith("titlehash:")
    assert cid == canonical_id(title="Some Paper", first_author_surname="Smith", year=2023)


def test_canonical_id_arxiv_doi_folds_into_arxiv_namespace():
    """The ugly real case the plan calls out by name: 10.48550 is arXiv's own
    DOI prefix, so a 10.48550 DOI and the bare arXiv ID must merge to one ID.
    """
    from_doi = canonical_id(doi="10.48550/arXiv.2301.12345")
    from_arxiv = canonical_id(arxiv_id="2301.12345")
    assert from_doi == from_arxiv == "arxiv:2301.12345"


def test_canonical_id_arxiv_doi_with_version_and_case_variants():
    assert canonical_id(doi="10.48550/ARXIV.2301.12345v2") == "arxiv:2301.12345"
    assert (
        canonical_id(doi="https://doi.org/10.48550/arxiv.hep-th/9901001") == "arxiv:hep-th/9901001"
    )


def test_canonical_id_empty_strings_are_treated_as_absent():
    cid = canonical_id(doi="", arxiv_id="", pmid="", openalex_id="", title="X", year=2020)
    assert cid.startswith("titlehash:")


def test_canonical_id_whitespace_only_is_treated_as_absent():
    cid = canonical_id(doi="   ", title="X", year=2020)
    assert cid.startswith("titlehash:")


def test_canonical_id_nothing_at_all_still_produces_a_stable_id():
    assert canonical_id() == canonical_id()
