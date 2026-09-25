"""
Resources: every file or URL a template refers to goes through the resolver
and is embedded as a data: URL (internal notes §4.6).
"""
import base64
import http.server
import threading

import pytest

from andrep import AndRepRenderer, DefaultResolver, ResourceError
from andrep.resources import is_public_address
from conftest import make_template

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@pytest.fixture
def media(tmp_path):
    base = tmp_path / "base"
    (base / "img").mkdir(parents=True)
    (base / "img" / "logo.png").write_bytes(PNG)
    (base / "notes.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("outside", encoding="utf-8")
    return base


# ---------------------------------------------------------------------------
# DefaultResolver — files
# ---------------------------------------------------------------------------

def test_reads_files_inside_base_dir(media):
    resolver = DefaultResolver(base_dir=media)
    assert resolver.open("notes.txt") == (b"hello", "text/plain")
    assert resolver.open("img/logo.png") == (PNG, "image/png")


@pytest.mark.parametrize("ref, reason", [
    ("../outside.txt", "outside the allowed directory"),
    ("img/../../outside.txt", "outside the allowed directory"),
    ("/etc/hostname", "absolute paths are not allowed"),
    ("file:///etc/hostname", "only http and https"),
    ("missing.txt", "No such file"),
])
def test_refuses_files_outside_base_dir(media, ref, reason):
    with pytest.raises(ResourceError, match=reason):
        DefaultResolver(base_dir=media).open(ref)


def test_symlink_leading_outside_is_refused(media):
    (media / "link.txt").symlink_to(media.parent / "outside.txt")
    with pytest.raises(ResourceError, match="outside the allowed directory"):
        DefaultResolver(base_dir=media).open("link.txt")


def test_named_roots(media, tmp_path):
    uploads = tmp_path / "uploads"
    (uploads / "2026").mkdir(parents=True)
    (uploads / "2026" / "x.txt").write_text("upload", encoding="utf-8")
    resolver = DefaultResolver(base_dir=media, roots={"uploads": uploads})
    assert resolver.open("uploads:2026/x.txt")[0] == b"upload"
    with pytest.raises(ResourceError, match="outside the allowed directory"):
        resolver.open("uploads:../base/notes.txt")


def test_network_can_be_disabled():
    with pytest.raises(ResourceError, match="disabled"):
        DefaultResolver(network=False).open("https://example.com/logo.png")


# ---------------------------------------------------------------------------
# DefaultResolver — network: public addresses only
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("address, public", [
    ("93.184.215.14", True),
    ("2606:4700:4700::1111", True),
    ("127.0.0.1", False),
    ("10.1.2.3", False),
    ("172.16.0.1", False),
    ("192.168.1.1", False),
    ("169.254.169.254", False),
    ("100.64.0.1", False),
    ("0.0.0.0", False),
    ("::1", False),
    ("fc00::1", False),
    ("fe80::1", False),
    ("::ffff:127.0.0.1", False),
    ("224.0.0.1", False),
    ("localhost", False),
])
def test_is_public_address(address, public):
    assert is_public_address(address) is public


@pytest.fixture
def local_server():
    """An HTTP server on 127.0.0.1 that counts the requests it receives."""
    requests = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"local")

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}", requests
    server.shutdown()


@pytest.mark.real_fetch
def test_local_server_is_not_reached(local_server):
    url, requests = local_server
    with pytest.raises(ResourceError, match="not a public address"):
        DefaultResolver().open(url + "/logo.png")
    assert requests == []   # connection refused before any request was sent


# ---------------------------------------------------------------------------
# Renderer: load / img / image cells
# ---------------------------------------------------------------------------

def html_of(cells: list, media, **attrs) -> str:
    r = AndRepRenderer(make_template({"band": cells}))
    r.base_dir = media
    for key, value in attrs.items():
        setattr(r, key, value)
    r.emit("band")
    return r.to_html()


def test_img_embeds_files_as_data_urls(media):
    html = html_of(['["@img/logo.png" | img]'], media)
    assert 'src="data:image/png;base64,' in html


def test_load_reads_text(media):
    assert "hello" in html_of(['["@notes.txt" | load]'], media)


def test_errors_are_visible_or_silent(media):
    html = html_of(['["@../outside.txt" | load]', '["@missing.png" | img,silent]'], media)
    assert "[#../outside.txt: outside the allowed directory#]" in html
    assert "missing.png" not in html


def test_image_cell_embeds_plain_reference(media):
    template = make_template({})
    template["rows"] = [{"name": "band", "height": 40, "cells": [
        {"id": "i", "type": "image", "content": '["img/logo.png"]', "width": 40}]}]
    r = AndRepRenderer(template)
    r.base_dir = media
    r.emit("band")
    assert 'src="data:image/png;base64,' in r.to_html()


def test_resources_are_read_once_per_renderer(media):
    calls = []

    class CountingResolver(DefaultResolver):
        def open(self, ref):
            calls.append(ref)
            return super().open(ref)

    html_of(['["@img/logo.png" | img]'] * 3, media, resolver=CountingResolver(base_dir=media))
    assert calls == ["img/logo.png"]


def test_custom_resolver():
    class Memory:
        def open(self, ref):
            return b"from memory", "text/plain"

    r = AndRepRenderer(make_template({"band": ['["@anything" | load]']}), resolver=Memory())
    r.emit("band")
    assert "from memory" in r.to_html()


def markdown_html(markdown_text: str, media) -> str:
    """Render a markdown cell whose text is loaded from notes.md (inside base_dir)."""
    pytest.importorskip("markdown")
    (media / "notes.md").write_text(markdown_text, encoding="utf-8")
    template = make_template({})
    template["rows"] = [{"name": "band", "height": 40, "cells": [
        {"id": "m", "type": "markdown", "content": '["@notes.md" | load]', "width": 200}]}]
    r = AndRepRenderer(template)
    r.base_dir = media
    r.emit("band")
    return r.to_html()


def test_markdown_images_are_embedded(media):
    html = markdown_html("Logo: ![logo](img/logo.png) and <img src='img/logo.png'>", media)
    assert html.count("data:image/png;base64,") == 2
    assert "img/logo.png" not in html


def test_markdown_image_errors_are_visible(media):
    html = markdown_html("![missing](img/missing.png)", media)
    assert "[#img/missing.png: No such file or directory#]" in html
    assert "<img" not in html.split("<body>")[1]
