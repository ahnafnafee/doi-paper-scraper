"""Base scraper — uses pydoll for Cloudflare bypass + Scrapling for HTML parsing."""

from __future__ import annotations

import hashlib
import json
import re
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from pathlib import Path

from scrapling import Selector

from academic_paper_api.models import Paper


class BaseScraper(ABC):
    """Abstract base for publisher-specific scrapers.

    Subclasses implement ``scrape()`` to extract structured data from
    the HTML of a publisher page.  The shared helpers use **pydoll** to
    fetch pages (bypasses Cloudflare) and **Scrapling Selector** to parse
    the resulting HTML.
    """

    publisher_name: str = "unknown"

    def __init__(self) -> None:
        pass

    @abstractmethod
    def scrape(self, url: str, doi: str, output_dir: Path) -> Paper:
        """Scrape a paper from the publisher URL."""
        ...

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def _browser_tab(self, cookies_file: str | None = None):
        """Context manager for a Cloudflare-safe browser tab.
        
        Yields the active ``tab`` so we can navigate, extract HTML, and
        evaluate JavaScript (e.g., to download images with exact cookies).
        """
        from pydoll.browser.chromium import Chrome
        from pydoll.browser.options import ChromiumOptions

        options = ChromiumOptions()
        # Headless mode is often blocked by Cloudflare (ACM), so we run headed
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # Detect Chrome binary (handles WSL → Windows Chrome)
        chrome_path = self._find_chrome_binary()
        if chrome_path:
            options.binary_location = chrome_path

        async with Chrome(options=options) as browser:
            tab = await browser.start()

            # Load cookies if provided
            if cookies_file:
                cookie_path = Path(cookies_file)
                if cookie_path.exists():
                    with open(cookie_path) as f:
                        cookies = json.load(f)
                    await tab.set_cookies(cookies)

            # Enable automatic Cloudflare bypass
            await tab.enable_auto_solve_cloudflare_captcha()

            yield tab

    @staticmethod
    def _parse_html(html: str) -> Selector:
        """Parse HTML string with Scrapling Selector for rich querying."""
        return Selector(html, auto_match=False)

    @staticmethod
    def _first(results):
        """Return the first element from a css()/xpath() result, or None."""
        if results and len(results) > 0:
            return results[0]
        return None

    async def _download_image(
        self,
        tab,
        url: str,
        output_dir: Path,
        *,
        referer: str = "",
    ) -> str:
        """Download an image using the active browser tab.

        Evaluates JS in the browser to fetch the image as a base64 string,
        guaranteeing a 100% match of cookies, Cloudflare clearances, and
        headers.

        Returns:
            Relative path like ``images/fig_abc123.png``, or ``""`` on failure.
        """
        if not url or url.startswith("data:"):
            return ""

        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Build stable filename from URL hash
        ext = Path(url.split("?")[0]).suffix or ".png"
        name_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        filename = f"fig_{name_hash}{ext}"
        dest = images_dir / filename

        if dest.exists():
            return f"images/{filename}"

        if not tab:
            print(f"  ⚠ Browser tab not available to download {url}")
            return ""

        script = f"""
        async () => {{
            const resp = await window.fetch('{url}', {{
                headers: {{ 'Referer': '{referer}' || window.location.href }}
            }});
            if (!resp.ok) throw new Error(`HTTP ${{resp.status}}`);
            const blob = await resp.blob();
            return new Promise((resolve, reject) => {{
                const reader = new FileReader();
                reader.onloadend = () => {{
                    // data:image/jpeg;base64,/9j/4AAQSkZJRg...
                    const result = reader.result;
                    resolve(result.split(',')[1]);
                }};
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            }});
        }}
        """
        try:
            import base64
            # Wrap the async function in an IIFE and await its promise using execute_script options
            wrapped_script = f"return ({script})();"
            response = await tab.execute_script(wrapped_script, await_promise=True)
            result = response.get("result", {}).get("result", {})
            b64_data = result.get("value")
            if b64_data:
                dest.write_bytes(base64.b64decode(b64_data))
            else:
                print(f"  ⚠ Failed to download image {url} via browser: No base64 data returned.")
                return ""
        except Exception as exc:
            print(f"  ⚠ Failed to download image {url} via browser: {exc}")
            return ""

        return f"images/{filename}"

    @staticmethod
    def _clean_text(text: str | None) -> str:
        """Normalize whitespace in extracted text."""
        if not text:
            return ""
        return re.sub(r"\s+", " ", str(text)).strip()

    @staticmethod
    def _make_absolute_url(base: str, relative: str) -> str:
        """Convert a potentially relative URL to absolute."""
        if not relative:
            return ""
        if relative.startswith(("http://", "https://", "//")):
            if relative.startswith("//"):
                return "https:" + relative
            return relative
        from urllib.parse import urljoin
        return urljoin(base, relative)

    @staticmethod
    def _find_chrome_binary() -> str | None:
        """Find a Chrome/Chromium binary, with WSL support."""
        import shutil

        # Quick check: is a native Linux Chrome available?
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            if shutil.which(name):
                return None  # Let pydoll find it normally

        # Detect WSL
        is_wsl = False
        try:
            with open("/proc/version", "r") as f:
                is_wsl = "microsoft" in f.read().lower()
        except FileNotFoundError:
            pass

        if not is_wsl:
            return None

        candidates = [
            "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
            "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
            "/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe",
            "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        ]
        for path in candidates:
            if Path(path).exists():
                print(f"  ▸ Using browser: {path}")
                return path

        return None
