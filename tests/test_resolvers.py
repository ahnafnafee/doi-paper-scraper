import pytest
from academic_paper_api.doi_resolver import extract_doi, resolve_doi

def test_extract_doi():
    # Regular DOI
    assert extract_doi("10.1145/123.456") == "10.1145/123.456"
    assert extract_doi("https://doi.org/10.1145/123.456") == "10.1145/123.456"

    # arXiv
    assert extract_doi("2104.08653") == "10.48550/arXiv.2104.08653"
    assert extract_doi("arxiv:2104.08653") == "10.48550/arXiv.2104.08653"
    assert extract_doi("https://arxiv.org/abs/2104.08653") == "10.48550/arXiv.2104.08653"
    assert extract_doi("https://arxiv.org/html/2104.08653") == "10.48550/arXiv.2104.08653"

def test_resolve_doi():
    # ACM
    resolved = resolve_doi("10.1145/3746059.3747603")
    assert resolved.publisher == "acm"

    # arXiv
    resolved = resolve_doi("2104.08653")
    assert resolved.publisher == "arxiv"
