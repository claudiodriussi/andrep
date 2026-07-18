"""
backends.py — PdfBackend Protocol + implementations (WeasyPrint, Playwright).

Each backend only needs to answer two engine-agnostic questions about a
standalone HTML document built by renderer.py:

  measure_heights(doc_html, count) -> list[int]   phantom pass
  render(doc_html)                 -> bytes       final PDF

renderer.py owns all layout/pagination/CSS generation; backends know nothing
about AndRep's template model (bands, cells, embed). Third-party engines can
be added without touching the core — implement the two methods and call
register_backend().
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class PdfBackend(Protocol):
    def measure_heights(self, doc_html: str, count: int) -> "list[int]":
        """doc_html is a standalone HTML document with `count` top-level
        elements in <body>, each carrying class="phantom-row". Return their
        rendered pixel heights, in document order."""
        ...

    def render(self, doc_html: str) -> bytes:
        """doc_html is the final, fully paginated standalone HTML document.
        Return PDF bytes."""
        ...


# ---------------------------------------------------------------------------
# WeasyPrint backend
# ---------------------------------------------------------------------------

class WeasyPrintBackend:
    """Requires: pip install weasyprint (or andrep[pdf])"""

    def __init__(self):
        self._fetcher = None  # created lazily, shared across measure/render calls

    def _get_fetcher(self):
        """URL fetcher cache, shared between phantom measurement and final
        render so each image URL is only downloaded once (per backend instance).
        """
        if self._fetcher is None:
            try:
                from weasyprint.urls import URLFetcher, URLFetcherResponse  # type: ignore
            except ImportError as e:
                raise ImportError(
                    "weasyprint is not installed: pip install weasyprint"
                ) from e
            base_fetcher = URLFetcher()
            cache: dict = {}  # url -> (bytes, EmailMessage headers)

            def fetcher(url: str) -> "URLFetcherResponse":
                if url not in cache:
                    resp = base_fetcher.fetch(url)
                    cache[url] = (resp.read(), resp.headers)
                data, headers = cache[url]
                return URLFetcherResponse(url, body=data, headers=headers)

            self._fetcher = fetcher
        return self._fetcher

    def measure_heights(self, doc_html: str, count: int) -> "list[int]":
        try:
            from weasyprint import HTML  # type: ignore
        except ImportError as e:
            raise ImportError(
                "weasyprint is not installed: pip install weasyprint"
            ) from e
        document = HTML(string=doc_html, url_fetcher=self._get_fetcher()).render()
        try:
            # Walk page_box -> <html> box -> <body> box; read each phantom-row child.
            body = document.pages[0]._page_box.children[0].children[0]
            return [max(1, round(child.height)) for child in body.children]
        except (IndexError, AttributeError):
            return [24] * count

    def render(self, doc_html: str) -> bytes:
        try:
            from weasyprint import HTML  # type: ignore
        except ImportError as e:
            raise ImportError(
                "weasyprint is not installed: pip install weasyprint"
            ) from e
        return HTML(string=doc_html, url_fetcher=self._get_fetcher()).write_pdf()


# ---------------------------------------------------------------------------
# Playwright backend
# ---------------------------------------------------------------------------

class PlaywrightBackend:
    """Requires: pip install playwright && playwright install chromium
    (or andrep[playwright])

    browser=None (default): lazily launches its own Chromium instance on
    first use, closed by close() / context-manager exit — correct for
    one-shot/CLI use.

    browser=<already-launched Browser>: the backend does NOT own its
    lifecycle (caller launched it and is responsible for closing it) — use
    this to share one warm Chromium process across many renders (e.g. a
    long-running server), which is where the real performance advantage
    over WeasyPrint materializes.
    """

    def __init__(self, browser=None):
        self._browser = browser
        self._owns_browser = browser is None
        self._playwright_cm = None
        self._page = None

    def _ensure_page(self):
        if self._browser is None:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError as e:
                raise ImportError(
                    "playwright is not installed: pip install playwright "
                    "&& playwright install chromium"
                ) from e
            self._playwright_cm = sync_playwright().start()
            chromium = self._playwright_cm.chromium
            exe = Path(chromium.executable_path)
            if not exe.exists():
                raise RuntimeError(
                    f"Playwright Chromium not found at {exe}. Run: "
                    "playwright install chromium "
                    "(or call andrep.backends.ensure_chromium_installed())"
                )
            self._browser = chromium.launch()
        if self._page is None:
            self._page = self._browser.new_page()
            self._page.emulate_media(media="print")
        return self._page

    def measure_heights(self, doc_html: str, count: int) -> "list[int]":
        page = self._ensure_page()
        page.set_content(doc_html, wait_until="load")
        page.evaluate("document.fonts.ready")
        heights = page.eval_on_selector_all(
            ".phantom-row", "els => els.map(e => e.offsetHeight)"
        )
        if len(heights) != count:
            raise RuntimeError(
                f"PlaywrightBackend.measure_heights: expected {count} "
                f".phantom-row elements, found {len(heights)}"
            )
        return [max(1, round(h)) for h in heights]

    def render(self, doc_html: str) -> bytes:
        page = self._ensure_page()
        page.set_content(doc_html, wait_until="load")
        page.evaluate("document.fonts.ready")
        return page.pdf(prefer_css_page_size=True)

    def close(self) -> None:
        if self._page is not None:
            self._page.close()
            self._page = None
        if self._owns_browser and self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright_cm is not None:
            self._playwright_cm.stop()
            self._playwright_cm = None

    def __enter__(self) -> "PlaywrightBackend":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def ensure_chromium_installed() -> None:
    """Run `playwright install chromium` if the browser binary is missing.

    Not called automatically by PlaywrightBackend — a silent multi-hundred-MB
    download on first render would be a bad surprise in a server context.
    Call this explicitly once (Dockerfile RUN step, setup script, ...).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise ImportError(
            "playwright is not installed: pip install playwright"
        ) from e
    with sync_playwright() as p:
        exe = Path(p.chromium.executable_path)
        if exe.exists():
            return
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"], check=True
    )


# ---------------------------------------------------------------------------
# Registry — "a new engine is just a new plugin"
# ---------------------------------------------------------------------------

_REGISTRY: dict = {
    "weasyprint": WeasyPrintBackend,
    "playwright": PlaywrightBackend,
}


def get_backend(name: str) -> type:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"Unknown pdf backend {name!r}; available: {', '.join(sorted(_REGISTRY))}"
        ) from None


def register_backend(name: str, cls: type) -> None:
    """Register a third-party PdfBackend implementation under `name`, so it
    can be selected the same way as the built-ins (pdf_backend="name",
    ANDREP_PDF_BACKEND=name)."""
    _REGISTRY[name] = cls
