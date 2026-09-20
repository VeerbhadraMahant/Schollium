"""Canonical paper ID normalization.

Precedence, per CLAUDE.md and plan section 2.2: lowercase DOI, else arXiv ID
without version, else PubMed ID, else OpenAlex work ID, else a hash of
normalized title plus first author surname plus year.

Each form is prefixed (doi:, arxiv:, pmid:, openalex:, titlehash:) so the
canonical ID's provenance is visible in logs and so the four namespaces can
never collide with each other by coincidence of characters.

One subtlety the plan calls out explicitly: arXiv's own DOI prefix is
10.48550, and a DOI of the form 10.48550/arxiv.2301.12345v1 refers to the same
paper as arXiv ID 2301.12345. Left alone, a record carrying only that DOI and
a record carrying only the bare arXiv ID would get two different canonical
IDs and never merge. So DOI normalization detects this pattern and folds it
into the arxiv: namespace instead of the doi: namespace.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

_DOI_URL_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi.org/",
    "dx.doi.org/",
)
_ARXIV_DOI_RE = re.compile(r"^10\.48550/arxiv\.(?P<arxiv_id>.+)$", re.IGNORECASE)
_ARXIV_VERSION_RE = re.compile(r"v\d+$", re.IGNORECASE)
_ARXIV_PREFIX_RE = re.compile(r"^arxiv:\s*", re.IGNORECASE)
_LATEX_COMMAND_RE = re.compile(r"\\[a-zA-Z]+\{([^{}]*)\}")
_LATEX_MATH_RE = re.compile(r"[$]([^$]*)[$]")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean(raw: str | None) -> str | None:
    """Empty and whitespace-only strings are treated as absent, not as values."""
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped or None


def normalize_doi(raw: str | None) -> str | None:
    """Lowercase, strip resolver URL prefixes and a leading 'doi:' label."""
    value = _clean(raw)
    if value is None:
        return None
    lowered = value.strip().lower()
    for prefix in _DOI_URL_PREFIXES:
        if lowered.startswith(prefix):
            lowered = lowered[len(prefix) :]
            break
    if lowered.startswith("doi:"):
        lowered = lowered[len("doi:") :].strip()
    lowered = lowered.strip().strip(".")
    return lowered or None


def normalize_arxiv_id(raw: str | None) -> str | None:
    """Strip an 'arXiv:' label and a trailing version suffix, then lowercase.

    Handles both new-style IDs (2301.12345) and old-style IDs with an archive
    prefix (hep-th/9901001).
    """
    value = _clean(raw)
    if value is None:
        return None
    stripped = _ARXIV_PREFIX_RE.sub("", value.strip())
    stripped = _ARXIV_VERSION_RE.sub("", stripped)
    stripped = stripped.strip("/ ").lower()
    return stripped or None


def normalize_pmid(raw: str | int | None) -> str | None:
    """PMIDs are digits only. Anything else in the field is stripped away."""
    if raw is None:
        return None
    digits = re.sub(r"\D", "", str(raw))
    return digits or None


def normalize_openalex_id(raw: str | None) -> str | None:
    """Accept the short form (W123) or the full URL and return the short form."""
    value = _clean(raw)
    if value is None:
        return None
    short = value.strip()
    if short.lower().startswith("https://openalex.org/"):
        short = short[len("https://openalex.org/") :]
    short = short.strip("/ ")
    if not short:
        return None
    return short[0].upper() + short[1:]


def normalize_title(raw: str | None) -> str | None:
    """Lowercase, drop LaTeX commands and math delimiters, fold unicode, strip
    punctuation, collapse whitespace. Used only for the title-hash fallback."""
    value = _clean(raw)
    if value is None:
        return None
    text = _LATEX_COMMAND_RE.sub(r"\1", value)
    text = _LATEX_MATH_RE.sub(r"\1", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = _NON_ALNUM_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text or None


def title_hash(title: str | None, first_author_surname: str | None, year: int | None) -> str:
    """The fallback ID when no external identifier is available.

    Deterministic: the same three inputs always produce the same hash, which
    is what lets the fallback act as a real key rather than a random one.
    """
    norm_title = normalize_title(title) or ""
    norm_author = normalize_title(first_author_surname) or ""
    norm_year = str(year) if year else ""
    basis = f"{norm_title}|{norm_author}|{norm_year}"
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()
    return digest[:16]


def canonical_id(
    *,
    doi: str | None = None,
    arxiv_id: str | None = None,
    pmid: str | int | None = None,
    openalex_id: str | None = None,
    title: str | None = None,
    first_author_surname: str | None = None,
    year: int | None = None,
) -> str:
    """The single ID every store table references. See module docstring."""
    doi_norm = normalize_doi(doi)
    if doi_norm is not None:
        match = _ARXIV_DOI_RE.match(doi_norm)
        if match:
            folded = normalize_arxiv_id(match.group("arxiv_id"))
            if folded:
                return f"arxiv:{folded}"
        return f"doi:{doi_norm}"

    arxiv_norm = normalize_arxiv_id(arxiv_id)
    if arxiv_norm is not None:
        return f"arxiv:{arxiv_norm}"

    pmid_norm = normalize_pmid(pmid)
    if pmid_norm is not None:
        return f"pmid:{pmid_norm}"

    openalex_norm = normalize_openalex_id(openalex_id)
    if openalex_norm is not None:
        return f"openalex:{openalex_norm}"

    return f"titlehash:{title_hash(title, first_author_surname, year)}"
