"""IEEE Xplore scraper.

Handles pages at ieeexplore.ieee.org.  IEEE serves paper content
through a combination of server-rendered HTML and client-side JS,
so we use pydoll to get the fully-rendered page.

IEEE full-text HTML (when available) is at URLs like:
    https://ieeexplore.ieee.org/document/<ARNUMBER>

The DOI-based URL typically redirects to the abstract page.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from urllib.parse import urljoin

from academic_paper_api.models import Figure, Paper, Section
from academic_paper_api.scrapers.base import BaseScraper


class IEEEScraper(BaseScraper):
    """Scraper for IEEE Xplore (ieeexplore.ieee.org)."""

    publisher_name = "ieee"
    BASE = "https://ieeexplore.ieee.org"

    def scrape(
        self,
        url: str,
        doi: str,
        output_dir: Path,
        cookies_file: str | None = None,
    ) -> Paper:
        """Scrape an IEEE paper — sync wrapper."""
        return asyncio.run(
            self._scrape_async(url, doi, output_dir, cookies_file)
        )

    async def _scrape_async(
        self,
        url: str,
        doi: str,
        output_dir: Path,
        cookies_file: str | None = None,
    ) -> Paper:
        paper = Paper(doi=doi, publisher=self.publisher_name, url=url)

        # ----------------------------------------------------------
        # 1. Fetch the paper page
        # ----------------------------------------------------------
        async with self._browser_tab(cookies_file) as tab:
            print(f"  ▸ Fetching IEEE page: {url}")
            await tab.go_to(url)
            
            import asyncio
            await asyncio.sleep(5)
            try:
                await tab.query(".document-title, h1.document-title", timeout=15)
            except Exception:
                pass

            html = await tab.page_source
            page = self._parse_html(html)

            # Title
            title_el = self._first(page.css(
                "h1.document-title span, .document-title, .title-wrapper h1"
            ))
            paper.title = self._clean_text(title_el.text) if title_el else ""

            # Authors
            author_els = page.css(
                '.authors-info span.author-name, '
                '[class*="author"] a span, '
                '.authors-container .author-card span'
            )
            paper.authors = [
                self._clean_text(a.text) for a in author_els if a.text
            ]
            # Deduplicate while preserving order
            seen = set()
            unique_authors = []
            for a in paper.authors:
                if a and a not in seen:
                    seen.add(a)
                    unique_authors.append(a)
            paper.authors = unique_authors

            # Abstract
            abstract_el = self._first(page.css(
                ".abstract-text div, .abstract-text, #abstractSection p"
            ))
            paper.abstract = self._clean_text(abstract_el.text) if abstract_el else ""

            # Keywords
            keyword_els = page.css(
                '.stats-keywords-container .keyword a, '
                '[class*="keyword"] a, '
                '.doc-keywords-list li'
            )
            paper.keywords = list(dict.fromkeys(
                self._clean_text(k.text) for k in keyword_els if k.text
            ))

            # ----------------------------------------------------------
            # 2. Try to get full-text HTML content
            # ----------------------------------------------------------
            paper.sections = await self._extract_sections(page, output_dir, url, tab)

            if not paper.sections and paper.abstract:
                paper.sections = [
                    Section(heading="Abstract", level=2, content=[paper.abstract])
                ]

        return paper

    async def _extract_sections(
        self,
        page,
        output_dir: Path,
        base_url: str,
        tab,
    ) -> list[Section]:
        """Extract sections from IEEE paper page."""
        sections: list[Section] = []

        body = self._first(page.css(
            ".article-body, .document-text, #article, .section-body"
        ))
        if not body:
            section_els = page.css(
                "div.section, .document-section, section[id]"
            )
            if section_els:
                for sec_el in section_els:
                    sub = await self._extract_from_section(sec_el, output_dir, base_url, tab)
                    sections.extend(sub)
                return sections
            return []

        current_section: Section | None = None

        for child in body.children:
            tag = child.tag if hasattr(child, "tag") else ""

            if tag in ("h2", "h3", "h4"):
                level = int(tag[1])
                heading = self._clean_text(child.text)
                if heading:
                    current_section = Section(
                        heading=heading, level=level, content=[]
                    )
                    sections.append(current_section)

            elif tag == "p":
                text = self._clean_text(child.text)
                if text:
                    if current_section:
                        current_section.content.append(text)
                    else:
                        current_section = Section(heading="", level=2, content=[text])
                        sections.append(current_section)

            elif tag in ("figure", "div"):
                fig = await self._extract_figure(child, output_dir, base_url, tab)
                if fig:
                    if current_section:
                        current_section.content.append(fig)
                    elif sections:
                        sections[-1].content.append(fig)

            elif tag == "section":
                sub = await self._extract_from_section(child, output_dir, base_url, tab)
                sections.extend(sub)

        return sections

    async def _extract_from_section(
        self,
        section_el,
        output_dir: Path,
        base_url: str,
        tab,
    ) -> list[Section]:
        """Extract content from a <section> or section-like div."""
        sections: list[Section] = []

        heading_el = self._first(section_el.css("h2, h3, h4, .section-title"))
        heading = self._clean_text(heading_el.text) if heading_el else ""
        level = 2
        if heading_el and hasattr(heading_el, "tag") and heading_el.tag.startswith("h"):
            level = int(heading_el.tag[1])

        current = Section(heading=heading, level=level, content=[])
        sections.append(current)

        for child in section_el.children:
            tag = child.tag if hasattr(child, "tag") else ""

            if tag in ("h2", "h3", "h4"):
                continue

            elif tag == "p":
                text = self._clean_text(child.text)
                if text:
                    current.content.append(text)

            elif tag in ("figure", "div"):
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
        """Extract a Figure from an element."""
        img = self._first(element.css("img"))
        if not img:
            return None

        src = img.attrib.get("src", "") or img.attrib.get("data-src", "")
        if not src:
            return None

        abs_url = self._make_absolute_url(base_url, src)

        caption_el = self._first(element.css(
            "figcaption, .figcaption, .fig-caption, .caption"
        ))
        caption = self._clean_text(caption_el.text) if caption_el else ""
        fig_id = element.attrib.get("id", "")

        local_path = await self._download_image(tab, abs_url, output_dir, referer=base_url)

        return Figure(
            url=abs_url,
            local_path=local_path,
            caption=caption,
            figure_id=fig_id,
        )
