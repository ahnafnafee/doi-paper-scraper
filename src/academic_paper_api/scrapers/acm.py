"""ACM Digital Library scraper.

Handles pages at dl.acm.org. Uses pydoll to bypass Cloudflare and
Scrapling Selector to parse the resulting HTML.

ACM full-text is embedded on the landing page at:
    https://dl.acm.org/doi/<DOI>

The article body lives inside ``section#bodymatter``.

Key DOM patterns (verified from real ACM HTML):
  - Paragraphs: ``div[role="paragraph"]``  (NOT <p>)
  - Sections:   ``section[id^="sec-"]`` with ``h2``/``h3``/``h4``
  - Figures:    ``.figure-wrap figure.graphic`` with ``img``
  - Hi-res img: ``img[data-viewer-src]`` attribute
  - Authors:    ``span[property="givenName"]`` + ``span[property="familyName"]``
  - Abstract:   ``#summary-abstract div[role="paragraph"]``
  - Title:      ``h1[property="name"]``
  - Keywords:   section with id containing "terms" or CCS concepts
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import urljoin

from academic_paper_api.models import Figure, Paper, Section
from academic_paper_api.scrapers.base import BaseScraper


class ACMScraper(BaseScraper):
    """Scraper for ACM Digital Library (dl.acm.org)."""

    publisher_name = "acm"
    BASE = "https://dl.acm.org"

    def scrape(
        self,
        url: str,
        doi: str,
        output_dir: Path,
        cookies_file: str | None = None,
    ) -> Paper:
        """Scrape an ACM paper — sync wrapper around the async implementation."""
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
        # Fetch the landing page (contains full text on ACM)
        # ----------------------------------------------------------
        async with self._browser_tab(cookies_file) as tab:
            landing_url = f"{self.BASE}/doi/{doi}"
            print(f"  ▸ Fetching ACM page: {landing_url}")
            await tab.go_to(landing_url)
            
            # Wait for Cloudflare/Page load
            import asyncio
            await asyncio.sleep(5)
            try:
                await tab.query('h1[property="name"]', timeout=15)
            except Exception:
                pass  # Ignore timeout

            html = await tab.page_source
            page = self._parse_html(html)

            # ── Title ──────────────────────────────────────────────────
            title_el = self._first(page.css('h1[property="name"]'))
            paper.title = self._clean_text(title_el.text) if title_el else ""

            # ── Authors ────────────────────────────────────────────────
            author_spans = page.css('span[property="author"][typeof="Person"]')
            seen_authors: set[str] = set()
            for author_span in author_spans:
                given = self._first(author_span.css('span[property="givenName"]'))
                family = self._first(author_span.css('span[property="familyName"]'))
                if given and family:
                    name = f"{self._clean_text(given.text)} {self._clean_text(family.text)}"
                    if name and name not in seen_authors:
                        seen_authors.add(name)
                        paper.authors.append(name)

            # ── Abstract ───────────────────────────────────────────────
            abstract_section = self._first(page.css("#summary-abstract"))
            if abstract_section:
                abs_paras = abstract_section.css('div[role="paragraph"]')
                paper.abstract = " ".join(
                    self._clean_text(p.text) for p in abs_paras if p.text
                )

            # ── Keywords / Index Terms ─────────────────────────────────
            kw_section = self._first(page.css("#sec-terms"))
            if kw_section:
                kw_links = kw_section.css("a")
                paper.keywords = [
                    self._clean_text(k.text) for k in kw_links
                    if k.text and self._clean_text(k.text)
                ]

            # ── Full-text body ─────────────────────────────────────────
            body = self._first(page.css("section#bodymatter"))
            if body:
                paper.sections = await self._extract_sections(body, output_dir, landing_url, tab)
            else:
                # Fallback: try fullHtml URL
                print("  ▸ No bodymatter found on landing page, trying fullHtml endpoint…")
                fulltext_url = f"{self.BASE}/doi/fullHtml/{doi}"
                await tab.go_to(fulltext_url)
                await asyncio.sleep(5)
                try:
                    await tab.query("h2", timeout=15)
                except Exception:
                    pass

                ft_html = await tab.page_source
                ft_page = self._parse_html(ft_html)
                ft_body = self._first(ft_page.css(
                    ".article__body, .hlFld-Fulltext, section#bodymatter"
                ))
                if ft_body:
                    paper.sections = await self._extract_sections(
                        ft_body, output_dir, fulltext_url, tab
                    )
                else:
                    print("  ⚠ Could not find extractable body content.")

            # If we still have no sections, at least include the abstract
            if not paper.sections and paper.abstract:
                paper.sections = [
                    Section(heading="Abstract", level=2, content=[paper.abstract])
                ]

        return paper

    # ------------------------------------------------------------------
    # Section extraction
    # ------------------------------------------------------------------

    async def _extract_sections(
        self,
        body_el,
        output_dir: Path,
        base_url: str,
        tab,
    ) -> list[Section]:
        """Extract sections from the bodymatter element."""
        sections: list[Section] = []

        top_sections = body_el.css("section[id]")
        if top_sections:
            for sec_el in top_sections:
                extracted = await self._extract_single_section(
                    sec_el, output_dir, base_url, tab
                )
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
        """Extract a single <section> element into a Section dataclass."""
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

            elif tag_name == "div":
                role = child.attrib.get("role", "")
                classes = child.attrib.get("class", "")

                if role == "paragraph":
                    text = self._clean_text(child.text)
                    if text:
                        section.content.append(text)

                elif role == "list" or "bullet" in child.attrib.get("data-type", ""):
                    list_text = self._extract_list(child)
                    if list_text:
                        section.content.append(list_text)

                elif "figure-wrap" in classes:
                    fig = await self._extract_figure(child, output_dir, base_url, tab)
                    if fig:
                        section.content.append(fig)

            elif tag_name == "section":
                pass  # Picked up by top-level iteration

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
        """Fallback: extract content without nested <section> elements."""
        sections: list[Section] = []
        current: Section | None = None

        for child in body_el.children:
            tag = child.tag if hasattr(child, "tag") else ""

            if tag in ("h2", "h3", "h4"):
                level = int(tag[1])
                heading = self._clean_text(child.text)
                current = Section(heading=heading, level=level, content=[])
                sections.append(current)

            elif tag == "div":
                role = child.attrib.get("role", "")
                classes = child.attrib.get("class", "")

                if role == "paragraph" and current:
                    text = self._clean_text(child.text)
                    if text:
                        current.content.append(text)

                elif "figure-wrap" in classes and current:
                    fig = await self._extract_figure(child, output_dir, base_url, tab)
                    if fig:
                        current.content.append(fig)

        return sections

    # ------------------------------------------------------------------
    # Figure extraction
    # ------------------------------------------------------------------

    async def _extract_figure(
        self,
        element,
        output_dir: Path,
        base_url: str,
        tab,
    ) -> Figure | None:
        """Extract a Figure from a .figure-wrap or <figure> element."""
        img = self._first(element.css("figure.graphic img, figure img, img"))
        if not img:
            return None

        src = (
            img.attrib.get("data-viewer-src", "")
            or img.attrib.get("src", "")
        )
        if not src:
            return None

        abs_url = self._make_absolute_url(base_url, src)

        caption_el = self._first(element.css("figcaption div[role='paragraph'], figcaption"))
        caption = self._clean_text(caption_el.text) if caption_el else ""

        fig_el = self._first(element.css("figure[id]"))
        fig_id = fig_el.attrib.get("id", "") if fig_el else ""

        label_el = self._first(element.css(".core-label"))
        label = self._clean_text(label_el.text) if label_el else ""
        if label and caption:
            caption = f"{label} {caption}"
        elif label:
            caption = label

        # Download image using the browser tab directly
        local_path = await self._download_image(tab, abs_url, output_dir, referer=base_url)

        return Figure(
            url=abs_url,
            local_path=local_path,
            caption=caption,
            figure_id=fig_id,
        )

    # ------------------------------------------------------------------
    # List extraction
    # ------------------------------------------------------------------

    def _extract_list(self, list_el) -> str:
        """Convert a div[role='list'] into markdown bullet list."""
        items = list_el.css('div[role="listitem"]')
        lines: list[str] = []
        for item in items:
            content_el = self._first(item.css(".content div[role='paragraph']"))
            if content_el:
                text = self._clean_text(content_el.text)
                if text:
                    lines.append(f"- {text}")
        return "\n".join(lines)
