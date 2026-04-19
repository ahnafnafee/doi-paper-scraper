import pytest
from academic_paper_api.scrapers.base import BaseScraper
from academic_paper_api.scrapers import get_scraper

class DummyScraper(BaseScraper):
    def scrape(self, *args, **kwargs):
        pass

def test_get_scraper():
    assert get_scraper("acm").publisher_name == "acm"
    assert get_scraper("ieee").publisher_name == "ieee"
    assert get_scraper("springer").publisher_name == "springer"
    assert get_scraper("elsevier").publisher_name == "elsevier"
    assert get_scraper("wiley").publisher_name == "wiley"
    assert get_scraper("arxiv").publisher_name == "arxiv"

def test_build_proxied_url():
    scraper = DummyScraper()

    target = "https://dl.acm.org/doi/10.1145/123"

    # No proxy
    assert scraper._build_proxied_url(None, target) == target

    # %u
    proxy1 = "https://mutex.gmu.edu/login?qurl=%u"
    assert scraper._build_proxied_url(proxy1, target) == "https://mutex.gmu.edu/login?qurl=https%3A%2F%2Fdl.acm.org%2Fdoi%2F10.1145%2F123"

    # %h and %p
    proxy2 = "https://%h.proxy.edu/%p"
    assert scraper._build_proxied_url(proxy2, target) == "https://dl.acm.org.proxy.edu/doi/10.1145/123"
