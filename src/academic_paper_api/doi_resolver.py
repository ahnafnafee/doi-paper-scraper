"""DOI resolver — accepts any DOI format and resolves to publisher URL.

Supported input formats:
  - Plain DOI:        10.1145/3746059.3747603
  - doi.org URL:      https://doi.org/10.1145/3746059.3747603
  - dx.doi.org URL:   https://dx.doi.org/10.1145/3746059.3747603
  - Publisher URL:    https://dl.acm.org/doi/10.1145/3746059.3747603
  - Any URL containing a DOI pattern
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

# Regex to extract a DOI from any string.
# DOI format: 10.XXXX/... where XXXX is 4-5 digit registrant code
DOI_PATTERN = re.compile(r"(10\.\d{4,9}/[^\s]+)")

# Known DOI prefixes → publisher names
PREFIX_TO_PUBLISHER: dict[str, str] = {
    "10.1145": "acm",       # ACM
    "10.1109": "ieee",      # IEEE
    "10.1007": "springer",  # Springer
    "10.1016": "elsevier",  # Elsevier
    "10.1038": "nature",    # Nature
    "10.1126": "science",   # Science (AAAS)
}

# Domain → publisher fallback mapping
DOMAIN_TO_PUBLISHER: dict[str, str] = {
    "dl.acm.org": "acm",
    "ieeexplore.ieee.org": "ieee",
    "link.springer.com": "springer",
    "sciencedirect.com": "elsevier",
    "nature.com": "nature",
    "science.org": "science",
    "arxiv.org": "arxiv",
}


@dataclass
class ResolvedDOI:
    """Result of DOI resolution."""

    doi: str
    publisher: str
    url: str


def extract_doi(input_str: str) -> str:
    """Extract a DOI from any input string (plain DOI, URL, etc.).

    Args:
        input_str: A DOI string, DOI URL, or publisher URL containing a DOI.

    Returns:
        The extracted DOI (e.g. '10.1145/3746059.3747603').

    Raises:
        ValueError: If no valid DOI is found in the input.
    """
    input_str = input_str.strip()

    match = DOI_PATTERN.search(input_str)
    if match:
        # Clean trailing punctuation that might have been captured
        doi = match.group(1).rstrip(".,;:)")
        return doi

    raise ValueError(
        f"Could not extract a DOI from input: '{input_str}'. "
        "Expected formats: '10.XXXX/...', 'https://doi.org/10.XXXX/...', "
        "or a publisher URL containing a DOI."
    )


def _detect_publisher_from_prefix(doi: str) -> str | None:
    """Detect publisher from the DOI prefix."""
    for prefix, publisher in PREFIX_TO_PUBLISHER.items():
        if doi.startswith(prefix):
            return publisher
    return None


def _detect_publisher_from_url(url: str) -> str | None:
    """Detect publisher from the resolved URL domain."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower().removeprefix("www.")
    for known_domain, publisher in DOMAIN_TO_PUBLISHER.items():
        if known_domain in domain:
            return publisher
    return None


def resolve_doi(input_str: str) -> ResolvedDOI:
    """Resolve any DOI input to a publisher name and URL.

    Accepts plain DOIs, doi.org URLs, dx.doi.org URLs, or publisher URLs.

    Args:
        input_str: Any string containing a DOI.

    Returns:
        ResolvedDOI with doi, publisher name, and resolved URL.

    Raises:
        ValueError: If no DOI found or publisher is unsupported.
        httpx.HTTPError: If DOI resolution fails.
    """
    doi = extract_doi(input_str)

    # Try detecting publisher from prefix first
    publisher = _detect_publisher_from_prefix(doi)

    # Resolve DOI to get the actual URL
    api_url = f"https://doi.org/api/handles/{doi}"
    try:
        resp = httpx.get(api_url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        resolved_url = ""
        for value in data.get("values", []):
            if value.get("type") == "URL":
                resolved_url = value["data"]["value"]
                break

        if not resolved_url:
            # Fallback: follow the redirect
            redirect_resp = httpx.get(
                f"https://doi.org/{doi}",
                follow_redirects=True,
                timeout=15,
            )
            resolved_url = str(redirect_resp.url)

    except httpx.HTTPError:
        # Fallback: try redirect approach
        redirect_resp = httpx.get(
            f"https://doi.org/{doi}",
            follow_redirects=True,
            timeout=15,
        )
        resolved_url = str(redirect_resp.url)

    # If we couldn't determine publisher from prefix, try from URL
    if not publisher:
        publisher = _detect_publisher_from_url(resolved_url)

    if not publisher:
        raise ValueError(
            f"Could not determine publisher for DOI '{doi}' "
            f"(resolved URL: {resolved_url}). "
            "This publisher may not be supported yet."
        )

    return ResolvedDOI(doi=doi, publisher=publisher, url=resolved_url)
