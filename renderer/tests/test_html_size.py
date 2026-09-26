"""
Inline styles become classes in the generated documents: cells repeat a few
styles thousands of times, so the HTML shrinks by about ten times.
"""
import re

from andrep import AndRepRenderer
from andrep.renderer import _styles_to_classes
from conftest import make_template


def test_repeated_styles_share_a_class():
    r = AndRepRenderer(make_template({"band": ["[i]", "x"]}))
    for i in range(50):  # noqa: B007 — read by emit()
        r.emit("band")
    html = r.to_html()
    body = html.split("</head>")[1]
    assert 'style="' not in body
    classes = set(re.findall(r'class="(s\d+)"', body))
    assert 0 < len(classes) < 10
    for name in classes:
        assert f".{name}{{" in html.split("</head>")[0]


def test_svg_keeps_inline_styles():
    html = ('<html><head><style>x{}</style></head><body><div style="color:red">a</div>'
            '<svg style="display:block"><rect style="fill:black"/></svg></body></html>')
    out = _styles_to_classes(html)
    assert '<div class="s0">' in out and ".s0{color:red}" in out
    assert '<svg style="display:block"><rect style="fill:black"/></svg>' in out


def test_styles_that_are_not_plain_css_stay_inline():
    html = ('<html><head><style></style></head><body>'
            '<p style="color:red}p{color:blue">a</p><p style="a:b/*">b</p></body></html>')
    out = _styles_to_classes(html)
    assert 'style="color:red}p{color:blue"' in out and 'style="a:b/*"' in out
    assert "</style>" in out and out.count("{") == html.count("{")
