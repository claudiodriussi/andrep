"""
Token syntax: [expr | formatters]; \\[ is a literal "[".

The JS client parses tokens the same way (clients/js/src/expression.ts): the
number of values per cell must match between a loop engine and the renderer.
"""
import base64

import pytest

from andrep import AndRepRenderer
from andrep.variables import _parse_tokens
from conftest import emitted_values, make_template


@pytest.mark.parametrize("content, tokens", [
    ("see note \\[1]", [("see note [1]", None, None)]),
    ("[a] and \\[b] [c]", [("", "a", []), (" and [b] ", None, None), ("", "c", [])]),
    ("\\[\\[x]]", [("[[x]]", None, None)]),
    ("a \\ b", [("a \\ b", None, None)]),          # a lone backslash stays
])
def test_escaped_bracket_is_text(content, tokens):
    assert _parse_tokens(content) == tokens


def test_escape_prints_the_bracket_and_keeps_values_aligned():
    r = AndRepRenderer(make_template({"band": ["\\[[qty]] pcs", "[qty * 2]"]}))
    qty = 3  # noqa: F841
    r.emit("band")
    assert emitted_values(r) == [3, 6]
    assert "[3] pcs" in r.to_html()


def test_unescaped_brackets_are_expressions():
    """No guessing: a bracket that is not an expression shows the error marker."""
    r = AndRepRenderer(make_template({"band": ["[] warning []"]}))
    r.emit("band")
    assert all(str(v).startswith("[#") for v in emitted_values(r))


def test_markdown_image_alt_in_template(tmp_path):
    pytest.importorskip("markdown")
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
    (tmp_path / "logo.png").write_bytes(png)
    template = make_template({})
    template["rows"] = [{"name": "band", "cells": [
        {"id": "m", "type": "markdown", "content": "!\\[ACME logo](logo.png)", "width": 200, "height": 40}]}]
    r = AndRepRenderer(template)
    r.base_dir = tmp_path
    r.emit("band")
    html = r.to_html()
    assert 'alt="ACME logo"' in html and "data:image/png;base64," in html
