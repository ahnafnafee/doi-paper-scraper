import pytest
from pathlib import Path
from academic_paper_api.scrapers.springer import SpringerScraper
from academic_paper_api.scrapers.elsevier import ElsevierScraper
from academic_paper_api.scrapers.wiley import WileyScraper
from academic_paper_api.scrapers.arxiv import ArxivScraper

class MockTab:
    def __init__(self, html):
        self._html = html

    @property
    async def current_url(self):
        return "https://example.com/paper"

    async def go_to(self, url):
        pass

    async def query(self, selector, timeout=1):
        pass

    @property
    async def page_source(self):
        return self._html

    async def execute_script(self, script, await_promise=False):
        pass

class MockBrowserCtx:
    def __init__(self, html):
        self.tab = MockTab(html)

    async def __aenter__(self):
        return self.tab

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

async def mock_wait(*args, **kwargs):
    pass

@pytest.mark.asyncio
async def test_springer_mocked(tmp_path):
    html = """
    <h1 class="c-article-title">Springer Paper</h1>
    <li class="c-article-author-list__item"><a data-test="author-name">Alice</a></li>
    <div id="Abs1-content"><p>Springer abstract.</p></div>
    <div class="c-article-body">
        <section data-title="Intro"><p>Intro content.</p></section>
    </div>
    """
    scraper = SpringerScraper()
    scraper._browser_tab = lambda c=None: MockBrowserCtx(html)
    scraper._wait_for_login = mock_wait

    paper = await scraper._scrape_async("https://link.springer.com/article/10", "10", tmp_path)
    assert paper.title == "Springer Paper"
    assert paper.authors == ["Alice"]
    assert paper.abstract == "Springer abstract."
    assert len(paper.sections) == 1
    assert paper.sections[0].heading == "Intro"

@pytest.mark.asyncio
async def test_elsevier_mocked(tmp_path):
    html = """
    <h1 class="title-text">Elsevier Paper</h1>
    <div class="author-group"><a class="author"><span class="text">Bob</span></a></div>
    <div class="abstract author"><p>Elsevier abstract.</p></div>
    <div id="body"><section><h2>Method</h2><p>Content</p></section></div>
    """
    scraper = ElsevierScraper()
    scraper._browser_tab = lambda c=None: MockBrowserCtx(html)
    scraper._wait_for_login = mock_wait

    paper = await scraper._scrape_async("https://sciencedirect.com/10", "10", tmp_path)
    assert paper.title == "Elsevier Paper"
    assert paper.authors == ["Bob"]
    assert paper.abstract == "Elsevier abstract."
    assert len(paper.sections) == 1
    assert paper.sections[0].heading == "Method"

@pytest.mark.asyncio
async def test_wiley_mocked(tmp_path):
    html = """
    <h1 class="citation__title">Wiley Paper</h1>
    <div class="author-name"><span>Charlie</span></div>
    <div class="article-section__abstract"><p>Wiley abstract.</p></div>
    <div class="article-section__content"><section class="article-section"><h2 class="article-section__title">Result</h2><p>Value</p></section></div>
    """
    scraper = WileyScraper()
    scraper._browser_tab = lambda c=None: MockBrowserCtx(html)
    scraper._wait_for_login = mock_wait

    paper = await scraper._scrape_async("https://onlinelibrary.wiley.com/doi/10", "10", tmp_path)
    assert paper.title == "Wiley Paper"
    assert paper.authors == ["Charlie"]
    assert paper.abstract == "Wiley abstract."
    assert len(paper.sections) == 1
    assert paper.sections[0].heading == "Result"

@pytest.mark.asyncio
async def test_arxiv_mocked(tmp_path):
    html = """
    <html>
    <body>
    <h1 class="title mathjax"><span class="descriptor">Title:</span> My Test Paper</h1>
    <div class="authors"><a href="#">Author One</a>, <a href="#">Author Two</a></div>
    <blockquote class="abstract mathjax"><span class="descriptor">Abstract:</span> This is the abstract.</blockquote>
    </body>
    </html>
    """
    scraper = ArxivScraper()
    scraper._browser_tab = lambda c=None: MockBrowserCtx(html)
    scraper._wait_for_login = mock_wait

    paper = await scraper._scrape_async("https://arxiv.org/abs/1234.56789", "10.48550/arXiv.1234.56789", tmp_path)
    assert paper.title == "My Test Paper"
    assert paper.authors == ["Author One", "Author Two"]
    assert paper.abstract == "This is the abstract."
