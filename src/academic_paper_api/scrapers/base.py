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
    def scrape(
        self,
        url: str,
        doi: str,
        output_dir: Path,
        cookies_file: str | None = None,
        proxy_url: str | None = None,
    ) -> Paper:
        """Scrape a paper from the publisher URL."""
        ...

    @staticmethod
    def _build_proxied_url(proxy_template: str | None, target_url: str) -> str:
        """Build a proxied URL if a template is provided.

        The template can contain:
        - '%u': Full target URL (URL-encoded)
        - '%h': Target hostname
        - '%p': Target path, query, and fragment (lstrip '/')
        
        Example: 'https://%h.proxy.edu/%p' or 'https://proxy.edu/login?qurl=%u'
        """
        if not proxy_template:
            return target_url
        
        import urllib.parse
        parsed = urllib.parse.urlparse(target_url)
        
        res = proxy_template
        if "%u" in res:
            encoded_url = urllib.parse.quote(target_url, safe="")
            res = res.replace("%u", encoded_url)
        
        if "%h" in res:
            res = res.replace("%h", parsed.netloc)
            
        if "%p" in res:
            # Reconstruct the path part (path + query + fragment)
            path = parsed.path.lstrip("/")
            if parsed.query:
                path += "?" + parsed.query
            if parsed.fragment:
                path += "#" + parsed.fragment
            res = res.replace("%p", path)
            
        # Ensure we have a scheme if it looks like a relative/partial template
        if not res.startswith(("http://", "https://")):
            res = f"https://{res}"
            
        return res

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
        # EZProxy rewrites domains (e.g. ieeexplore.ieee.org.mutex.gmu.edu)
        # which often don't match the wildcard SSL cert — ignore cert errors
        options.add_argument("--ignore-certificate-errors")

        # Detect Chrome binary (handles WSL → Windows Chrome)
        chrome_path = self._find_chrome_binary()
        if chrome_path:
            options.binary_location = chrome_path

        async with Chrome(options=options) as browser:
            tab = await browser.start()

            # Load cookies if provided (convert browser-extension → CDP format)
            if cookies_file:
                cookie_path = Path(cookies_file)
                if cookie_path.exists():
                    with open(cookie_path) as f:
                        raw_cookies = json.load(f)
                    cdp_cookies = self._convert_cookies_for_cdp(raw_cookies)
                    if cdp_cookies:
                        await tab.set_cookies(cdp_cookies)

            # Enable automatic Cloudflare bypass
            # FIXME: Disabled temporarily because it may conflict with EZProxy's JS rewrites
            # and cause Angular applications (like IEEE Xplore) to get stuck in a loading state.
            # await tab.enable_auto_solve_cloudflare_captcha()

            try:
                yield tab
            finally:
                # After scraping, save fresh cookies back for next time
                if cookies_file:
                    await self._save_cookies(tab, cookies_file)

    @staticmethod
    def _convert_cookies_for_cdp(raw_cookies: list[dict]) -> list[dict]:
        """Convert browser-extension cookie format to CDP-compatible format.
        
        Browser extensions (like Cookie Quick Manager) export cookies with
        fields like 'expirationDate', 'hostOnly', 'storeId', etc. that CDP
        doesn't understand. CDP expects 'expires', and specific sameSite values.
        """
        cdp_cookies = []
        
        # Map browser extension sameSite values to CDP values
        same_site_map = {
            "no_restriction": "None",
            "lax": "Lax",
            "strict": "Strict",
        }
        
        for raw in raw_cookies:
            cookie: dict = {
                "name": raw["name"],
                "value": raw["value"],
            }
            
            if "domain" in raw and raw["domain"]:
                cookie["domain"] = raw["domain"]
            if "path" in raw:
                cookie["path"] = raw["path"]
            if "secure" in raw:
                cookie["secure"] = raw["secure"]
            if "httpOnly" in raw:
                cookie["httpOnly"] = raw["httpOnly"]
            
            # Convert expirationDate → expires (CDP uses epoch seconds)
            if "expirationDate" in raw and raw["expirationDate"]:
                cookie["expires"] = raw["expirationDate"]
            
            # Convert sameSite values
            if "sameSite" in raw and raw["sameSite"]:
                ss = str(raw["sameSite"]).lower()
                cookie["sameSite"] = same_site_map.get(ss, "Lax")
                
            cdp_cookies.append(cookie)
        
        return cdp_cookies

    async def _wait_for_login(
        self, tab, login_indicators: list[str] | None = None,
        cookies_file: str | None = None,
    ):
        """Detect if we're on a login page and wait for the user to log in.
        
        Args:
            tab: Browser tab.
            login_indicators: URL substrings that indicate a login page.
            cookies_file: If provided, save cookies immediately after login.
        """
        import asyncio
        
        if login_indicators is None:
            login_indicators = ["/login", "/idp/", "/cas/", "shibboleth", "auth"]
        
        current_url = await tab.current_url
        
        is_login = any(ind in current_url.lower() for ind in login_indicators)
        if not is_login:
            return  # Not on a login page, proceed normally
        
        print()
        print("  ╔══════════════════════════════════════════════════════════╗")
        print("  ║  🔐 Login Required                                      ║")
        print("  ║                                                          ║")
        print("  ║  Please log in using the browser window that opened.     ║")
        print("  ║  The scraper will continue automatically once you're     ║")
        print("  ║  logged in and redirected to the paper page.             ║")
        print("  ╚══════════════════════════════════════════════════════════╝")
        print()
        
        # Poll until the URL changes away from the login page
        max_wait = 120  # 2 minutes
        elapsed = 0
        poll_interval = 2
        
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            
            current_url = await tab.current_url
            is_still_login = any(ind in current_url.lower() for ind in login_indicators)
            
            if not is_still_login:
                print(f"  ✓ Login detected! Continuing with: {current_url[:80]}…")
                # Save cookies NOW while the connection is still alive
                if cookies_file:
                    await self._save_cookies(tab, cookies_file)
                # Reload the page to ensure the Angular app and all JS assets load cleanly 
                # with the newly minted proxy session cookies.
                await tab.go_to(current_url)
                # Give the page a moment to fully load after reload
                await asyncio.sleep(5)
                return
        
        print("  ⚠ Login wait timed out (2 min). Proceeding with current page state.")

    @staticmethod
    async def _save_cookies(tab, cookies_file: str):
        """Save current browser cookies back to the cookies file."""
        try:
            cookies = await tab.get_cookies()
            if cookies:
                cookie_path = Path(cookies_file)
                with open(cookie_path, "w") as f:
                    json.dump(cookies, f, indent=4, default=str)
                print(f"  ✓ Saved {len(cookies)} cookies to {cookies_file}")
        except Exception as exc:
            print(f"  ⚠ Could not save cookies: {exc}")


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
        """Find a Chrome/Chromium binary, prioritizing Windows Chrome in WSL."""
        import shutil

        # Detect WSL first
        is_wsl = False
        try:
            with open("/proc/version", "r") as f:
                is_wsl = "microsoft" in f.read().lower()
        except FileNotFoundError:
            pass

        if is_wsl:
            candidates = [
                "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
                "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
                "/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe",
                "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            ]
            for path in candidates:
                if Path(path).exists():
                    print(f"  ▸ Using Windows browser: {path}")
                    return path

        # Fallback to native Linux Chrome
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            if shutil.which(name):
                return None  # Let pydoll find it normally

        return None
