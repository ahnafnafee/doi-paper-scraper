"""Scraper registry — maps publisher names to scraper implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseScraper


def get_scraper(publisher: str) -> BaseScraper:
    """Return the appropriate scraper for the given publisher name."""
    from .acm import ACMScraper
    from .ieee import IEEEScraper

    scrapers: dict[str, type[BaseScraper]] = {
        "acm": ACMScraper,
        "ieee": IEEEScraper,
    }

    key = publisher.lower()
    if key not in scrapers:
        supported = ", ".join(sorted(scrapers.keys()))
        raise ValueError(
            f"No scraper available for publisher '{publisher}'. "
            f"Supported publishers: {supported}"
        )

    return scrapers[key]()
