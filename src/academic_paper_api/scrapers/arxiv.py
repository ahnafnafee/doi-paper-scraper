"""arXiv scraper.

Handles pages at arxiv.org.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from academic_paper_api.models import Figure, Paper, Section
from academic_paper_api.scrapers.base import BaseScraper


class ArxivScraper(BaseScraper):
    """Scraper for arXiv (arxiv.org)."""

    publisher_name = "arxiv"
    BASE = "https://arxiv.org"

    def scrape(
        self,
        url: str,
        doi: str,
        output_dir: Path,
        cookies_file: str | None = None,
        proxy_url: str | None = None,
    ) -> Paper:
        """Scrape an arXiv paper."""
        return asyncio.run(
            self._scrape_async(url, doi, output_dir, cookies_file, proxy_url)
        )

    async def _scrape_async(
        self,
        url: str,
        doi: str,
        output_dir: Path,
        cookies_file: str | None = None,
        proxy_url: str | None = None,
    ) -> Paper:
        paper = Paper(doi=doi, publisher=self.publisher_name, url=url)

        async with self._browser_tab(cookies_file) as tab:
            landing_url = url
            nav_url = self._build_proxied_url(proxy_url, landing_url)
            print(f"  ▸ Fetching arXiv page: {nav_url}")
            await tab.go_to(nav_url)

            import asyncio
            await asyncio.sleep(5)

            await self._wait_for_login(tab, cookies_file=cookies_file)
            nav_url = await tab.current_url

            html = await tab.page_source
            page = self._parse_html(html)

            # Title
            title_el = self._first(page.css('h1.title, .title'))
            paper.title = self._clean_text(self._get_text(title_el)).replace("Title:", "").strip() if title_el else ""

            # Authors
            author_els = page.css('.authors a')
            paper.authors = [self._clean_text(self._get_text(a)) for a in author_els if a.text]
            paper.authors = list(dict.fromkeys(paper.authors))

            # Abstract
            abstract_section = self._first(page.css('blockquote.abstract, .abstract'))
            if abstract_section:
                paper.abstract = self._clean_text(self._get_text(abstract_section)).replace("Abstract:", "").strip()

            # For arxiv, full HTML might be available via arxiv.org/html/arxiv_id
            # Wait to check if there is an HTML link
            html_link = self._first(page.css('a.abs-button[href*="/html/"]'))
            if html_link:
                html_url = self._make_absolute_url(nav_url, html_link.attrib.get('href'))
                nav_html_url = self._build_proxied_url(proxy_url, html_url)
                print(f"  ▸ HTML version available, fetching: {nav_html_url}")
                await tab.go_to(nav_html_url)
                await asyncio.sleep(5)

                html = await tab.page_source
                page = self._parse_html(html)

                body = self._first(page.css('.ltx_document, .ltx_page_main'))
                if body:
                    paper.sections = await self._extract_sections(body, output_dir, nav_html_url, tab)

            if not paper.sections and paper.abstract:
                paper.sections = [
                    Section(heading="Abstract", level=2, content=[paper.abstract])
                ]

        return paper

    async def _extract_sections(
        self,
        body_el,
        output_dir: Path,
        base_url: str,
        tab,
    ) -> list[Section]:
        sections: list[Section] = []
        top_sections = body_el.css(".ltx_section")

        if top_sections:
            for sec_el in top_sections:
                extracted = await self._extract_single_section(sec_el, output_dir, base_url, tab)
                if extracted:
                    sections.append(extracted)
        else:
            sections = await self._extract_flat(body_el, output_dir, base_url, tab)

        return sections

    async def _extract_single_section(
        self,
        sec_el,
        output_dir: Path,
        base_url: str,
        tab,
    ) -> Section | None:
        heading_el = self._first(sec_el.css("h2, h3, h4, .ltx_title_section"))
        if not heading_el:
            return None

        heading_text = self._clean_text(heading_el.text)
        tag = heading_el.tag if hasattr(heading_el, "tag") else "h2"
        level = int(tag[1]) if tag and tag[0] == "h" else 2

        section = Section(heading=heading_text, level=level, content=[])

        for child in sec_el.children:
            tag_name = child.tag if hasattr(child, "tag") else ""
            classes = child.attrib.get("class", "")

            if tag_name in ("h2", "h3", "h4") or "ltx_title" in classes:
                continue
            elif tag_name == "p" or "ltx_para" in classes:
                text = self._clean_text(child.text)
                if text:
                    section.content.append(text)
            elif tag_name == "figure" or "ltx_figure" in classes:
                fig = await self._extract_figure(child, output_dir, base_url, tab)
                if fig:
                    section.content.append(fig)

        if section.content or heading_text:
            return section
        return None

    async def _extract_flat(
        self,
        body_el,
        output_dir: Path,
        base_url: str,
        tab,
    ) -> list[Section]:
        sections: list[Section] = []
        current: Section | None = None

        for child in body_el.children:
            tag = child.tag if hasattr(child, "tag") else ""
            classes = child.attrib.get("class", "")

            if tag in ("h2", "h3", "h4") or "ltx_title" in classes:
                level = int(tag[1]) if tag.startswith('h') else 2
                heading = self._clean_text(child.text)
                current = Section(heading=heading, level=level, content=[])
                sections.append(current)

            elif (tag == "p" or "ltx_para" in classes) and current:
                text = self._clean_text(child.text)
                if text:
                    current.content.append(text)

            elif (tag == "figure" or "ltx_figure" in classes) and current:
                fig = await self._extract_figure(child, output_dir, base_url, tab)
                if fig:
                    current.content.append(fig)

        return sections

    async def _extract_figure(
        self,
        element,
        output_dir: Path,
        base_url: str,
        tab,
    ) -> Figure | None:
        img = self._first(element.css("img"))
        if not img:
            return None

        src = img.attrib.get("src", "")
        if not src:
            return None

        abs_url = self._make_absolute_url(base_url, src)

        caption_el = self._first(element.css("figcaption, .ltx_caption"))
        caption = self._clean_text(caption_el.text) if caption_el else ""

        fig_id = element.attrib.get("id", "")

        local_path = await self._download_image(tab, abs_url, output_dir, referer=base_url)

        return Figure(
            url=abs_url,
            local_path=local_path,
            caption=caption,
            figure_id=fig_id,
        )
