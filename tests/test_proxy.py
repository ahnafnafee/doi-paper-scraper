import pytest
from academic_paper_api.scrapers.base import BaseScraper
import urllib.parse

class DummyScraper(BaseScraper):
    def scrape(self, *args, **kwargs):
        pass

def test_base_scraper_proxy_templates():
    scraper = DummyScraper()

    target = "https://dl.acm.org/doi/10.1145/3746059.3747603"

    # Template: %u (full URL)
    template1 = "https://mutex.gmu.edu/login?qurl=%u"
    proxy_url1 = scraper._build_proxied_url(template1, target)
    expected_qurl = urllib.parse.quote(target, safe="")
    assert proxy_url1 == f"https://mutex.gmu.edu/login?qurl={expected_qurl}"

    # Template: %h (hostname) %p (path)
    template2 = "https://%h.proxy.edu/%p"
    proxy_url2 = scraper._build_proxied_url(template2, target)
    assert proxy_url2 == "https://dl.acm.org.proxy.edu/doi/10.1145/3746059.3747603"

    # Template: Without scheme
    template3 = "%h.proxy.edu/%p"
    proxy_url3 = scraper._build_proxied_url(template3, target)
    assert proxy_url3 == "https://dl.acm.org.proxy.edu/doi/10.1145/3746059.3747603"
