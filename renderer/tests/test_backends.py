"""
PDF backends load data: URLs only; generated documents carry a CSP
(internal notes §4.6, second layer).

Each backend is tested on its own, without the CSP, so the check shows the
backend itself fetches nothing.  The local server only listens on 127.0.0.1.
"""
import base64
import http.server
import threading
from pathlib import Path

import pytest

from andrep import AndRepRenderer
from andrep.backends import PlaywrightBackend, WeasyPrintBackend
from conftest import make_template

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
DATA_PNG = "data:image/png;base64," + base64.b64encode(PNG).decode()


@pytest.fixture
def local_server():
    """An HTTP server on 127.0.0.1 that records the requests it receives."""
    requests = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.end_headers()
            self.wfile.write(PNG)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}", requests
    server.shutdown()


def document(base_url: str) -> str:
    """A page that refers to external resources in the usual ways."""
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<link rel='stylesheet' href='{base_url}/style.css'>"
        f"<style>.bg {{ background: url('{base_url}/bg.png'); }}</style></head><body>"
        f"<img src='{base_url}/img.png'>"
        "<div class='bg phantom-row'>text</div>"
        f"<img src='{DATA_PNG}'>"
        "</body></html>"
    )


def chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    with sync_playwright() as p:
        return Path(p.chromium.executable_path).exists()


def backends():
    result = []
    try:
        import weasyprint  # noqa: F401
        result.append(pytest.param(WeasyPrintBackend, id="weasyprint"))
    except ImportError:
        result.append(pytest.param(None, id="weasyprint", marks=pytest.mark.skip("not installed")))
    marks = [] if chromium_available() else [pytest.mark.skip("chromium not installed")]
    result.append(pytest.param(PlaywrightBackend, id="playwright", marks=marks))
    return result


@pytest.mark.parametrize("backend_cls", backends())
def test_backend_fetches_nothing(backend_cls, local_server):
    base_url, requests = local_server
    backend = backend_cls()
    try:
        heights = backend.measure_heights(document(base_url), 1)
        pdf = backend.render(document(base_url))
    finally:
        if hasattr(backend, "close"):
            backend.close()
    assert requests == []
    assert heights and pdf.startswith(b"%PDF")


def test_weasyprint_fetcher_accepts_data_urls_only():
    pytest.importorskip("weasyprint")
    fetcher = WeasyPrintBackend()._get_fetcher()
    fetcher(DATA_PNG)
    for url in ("file:///etc/hostname", "http://example.com/x.png"):
        with pytest.raises(ValueError, match="data: URLs only"):
            fetcher(url)


@pytest.mark.skipif(not chromium_available(), reason="chromium not installed")
def test_playwright_runs_no_scripts():
    backend = PlaywrightBackend()
    try:
        page = backend._ensure_page()
        page.set_content("<title>before</title><script>document.title = 'after'</script>")
        assert page.title() == "before"
    finally:
        backend.close()


def test_generated_documents_carry_the_csp():
    r = AndRepRenderer(make_template({"band": ["x"]}))
    r.emit("band")
    html = r.to_html()
    assert '<meta http-equiv="Content-Security-Policy"' in html
    assert "default-src 'none'" in html
    assert html.index("Content-Security-Policy") < html.index("<style>")
