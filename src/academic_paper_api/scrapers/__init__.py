"""Scraper registry — maps publisher names to scraper implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseScraper


def get_scraper(publisher: str) -> BaseScraper:
    """Return the appropriate scraper for the given publisher name."""
    from .acm import ACMScraper
    from .ieee import IEEEScraper
    from .springer import SpringerScraper
    from .elsevier import ElsevierScraper
    from .wiley import WileyScraper
    from .arxiv import ArxivScraper

    scrapers: dict[str, type[BaseScraper]] = {
        "acm": ACMScraper,
        "ieee": IEEEScraper,
        "springer": SpringerScraper,
        "elsevier": ElsevierScraper,
        "wiley": WileyScraper,
        "arxiv": ArxivScraper,
    }

    key = publisher.lower()
    if key not in scrapers:
        supported = ", ".join(sorted(scrapers.keys()))
        raise ValueError(
            f"No scraper available for publisher '{publisher}'. "
            f"Supported publishers: {supported}"
        )

    return scrapers[key]()
