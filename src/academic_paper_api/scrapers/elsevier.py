"""Elsevier scraper.

Handles pages at sciencedirect.com.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from academic_paper_api.models import Figure, Paper, Section
from academic_paper_api.scrapers.base import BaseScraper


class ElsevierScraper(BaseScraper):
    """Scraper for Elsevier (sciencedirect.com)."""

    publisher_name = "elsevier"
    BASE = "https://www.sciencedirect.com"

    def scrape(
        self,
        url: str,
        doi: str,
        output_dir: Path,
        cookies_file: str | None = None,
        proxy_url: str | None = None,
    ) -> Paper:
        """Scrape an Elsevier paper."""
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
            # Use science direct pi based url if it exists, otherwise standard
            landing_url = url
            nav_url = self._build_proxied_url(proxy_url, landing_url)
            print(f"  ▸ Fetching Elsevier page: {nav_url}")
            await tab.go_to(nav_url)

            import asyncio
            await asyncio.sleep(5)

            await self._wait_for_login(tab, cookies_file=cookies_file)
            nav_url = await tab.current_url

            try:
                await tab.query('.title-text', timeout=15)
            except Exception:
                pass

            # Scroll to trigger lazy-loaded elements
            print("  ▸ Scrolling down to trigger lazy loading…")
            scroll_script = """
            async () => {
                let totalHeight = 0;
                let distance = 600;
                let maxScrolls = 50;
                let scrollCount = 0;
                while(scrollCount < maxScrolls) {
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    scrollCount++;
                    await new Promise(r => setTimeout(r, 150));
                    if (totalHeight >= document.body.scrollHeight) {
                        break;
                    }
                }
            }
            """
            try:
                wrapped = f"return ({scroll_script})();"
                await asyncio.wait_for(tab.execute_script(wrapped, await_promise=True), timeout=15)
            except Exception as exc:
                print(f"  ⚠ Automatic scroll timed out, but proceeding: {exc}")

            await asyncio.sleep(2)

            html = await tab.page_source
            page = self._parse_html(html)

            # Title
            title_el = self._first(page.css('.title-text, h1'))
            paper.title = self._clean_text(self._get_text(title_el)) if title_el else ""

            # Authors
            author_els = page.css('.author-group .author .text, a.author .text')
            paper.authors = [self._clean_text(self._get_text(a)) for a in author_els if a.text]
            paper.authors = list(dict.fromkeys(paper.authors))

            # Abstract
            abstract_section = self._first(page.css('.abstract.author, #abstracts'))
            if abstract_section:
                abs_paras = abstract_section.css('p, .abstract-text')
                paper.abstract = " ".join(self._clean_text(self._get_text(p)) for p in abs_paras if p.text)

            # Keywords
            kw_els = page.css('.keyword, .keywords-section .keyword-text')
            paper.keywords = list(dict.fromkeys(self._clean_text(self._get_text(k)) for k in kw_els if k.text))

            # Full-text body
            body = self._first(page.css('#body, .article-wrapper, article'))
            if body:
                paper.sections = await self._extract_sections(body, output_dir, nav_url, tab)

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
        top_sections = body_el.css("section")

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
        heading_el = self._first(sec_el.css("h2, h3, h4"))
        if not heading_el:
            return None

        heading_text = self._clean_text(heading_el.text)
        tag = heading_el.tag if hasattr(heading_el, "tag") else "h2"
        level = int(tag[1]) if tag and tag[0] == "h" else 2

        section = Section(heading=heading_text, level=level, content=[])

        for child in sec_el.children:
            tag_name = child.tag if hasattr(child, "tag") else ""

            if tag_name in ("h2", "h3", "h4"):
                continue
            elif tag_name == "p":
                text = self._clean_text(child.text)
                if text:
                    section.content.append(text)
            elif tag_name == "figure":
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

            if tag in ("h2", "h3", "h4"):
                level = int(tag[1])
                heading = self._clean_text(child.text)
                current = Section(heading=heading, level=level, content=[])
                sections.append(current)

            elif tag == "p" and current:
                text = self._clean_text(child.text)
                if text:
                    current.content.append(text)

            elif tag == "figure" and current:
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
        img = self._first(element.css("img, picture img"))
        if not img:
            return None

        src = img.attrib.get("src", "")
        if not src:
            return None

        abs_url = self._make_absolute_url(base_url, src)

        caption_el = self._first(element.css("figcaption, .caption-text"))
        caption = self._clean_text(caption_el.text) if caption_el else ""

        fig_id = element.attrib.get("id", "")

        local_path = await self._download_image(tab, abs_url, output_dir, referer=base_url)

        return Figure(
            url=abs_url,
            local_path=local_path,
            caption=caption,
            figure_id=fig_id,
        )
