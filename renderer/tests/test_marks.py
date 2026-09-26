"""
r.mark(): where each part of the document lands, for splitting and bookmarks.

Same small pages as test_pagination: 300 px, 20 px header and footer, two
100 px rows per page, no margins.
"""
from io import BytesIO

import pytest

from andrep import AndRepRenderer
from test_pagination import TEMPLATE


def pages_of(marks) -> list:
    return [(m["label"], m["level"], m["first"], m["last"]) for m in marks]


def test_parts_and_their_pages():
    r = AndRepRenderer(TEMPLATE)
    r.mark("INV-1")                     # before any content: no empty page
    for _ in range(3):
        r.emit("band")
    r.page_break(reset=True)
    r.mark("INV-2")
    r.emit("band")
    r._to_pdf_html()
    assert pages_of(r.marks) == [("INV-1", 1, 0, 1), ("INV-2", 1, 2, 2)]


def test_mark_goes_with_the_band_that_follows_it():
    r = AndRepRenderer(TEMPLATE)
    r.emit("band")
    r.emit("band")                      # page 1 is full
    r.mark("NEXT")
    r.emit("band")                      # starts page 2: the mark goes with it
    r._to_pdf_html()
    assert pages_of(r.marks) == [("NEXT", 1, 1, 1)]
    assert r.marks[0]["top"] == (300 - 20) * 0.75      # just below the page header


def test_mark_in_the_middle_of_a_page():
    r = AndRepRenderer(TEMPLATE)
    r.mark("A")
    r.emit("band")
    r.mark("B")
    r.emit("band")
    r._to_pdf_html()
    assert [m["top"] for m in r.marks] == [(300 - 20) * 0.75, (300 - 120) * 0.75]
    assert pages_of(r.marks) == [("A", 1, 0, 0), ("B", 1, 0, 0)]


def test_levels_nest():
    r = AndRepRenderer(TEMPLATE)
    r.mark("Category A")
    r.mark("Article A1", level=2)
    r.emit("band")
    r.mark("Article A2", level=2)
    for _ in range(3):
        r.emit("band")
    r.mark("Category B")
    r.emit("band")
    r._to_pdf_html()
    assert pages_of(r.marks) == [
        ("Category A", 1, 0, 1),        # until Category B, which opens page 3
        ("Article A1", 2, 0, 0),        # until Article A2, on the same page
        ("Article A2", 2, 0, 1),        # until the next mark of level ≤ 2
        ("Category B", 1, 2, 2),
    ]


def test_marks_travel_in_compiled_records():
    r = AndRepRenderer(TEMPLATE)
    r.mark("A")
    r.emit("band")
    r.page_break()
    r.mark("B")
    r.emit("band")
    r2 = AndRepRenderer.from_compiled(TEMPLATE, r._emissions)
    r2._to_pdf_html()
    assert pages_of(r2.marks) == [("A", 1, 0, 0), ("B", 1, 1, 1)]


def test_marks_print_nothing():
    r = AndRepRenderer(TEMPLATE)
    r.mark("hidden-label")
    r.emit("band")
    assert "hidden-label" not in r.to_html() and "hidden-label" not in r._to_pdf_html()


def test_invalid_level():
    with pytest.raises(ValueError):
        AndRepRenderer(TEMPLATE).mark("x", level=0)


def test_split_and_bookmarks_with_pypdf():
    """The manual's recipes, on a real PDF."""
    pypdf = pytest.importorskip("pypdf")
    from pypdf.generic import Fit

    r = AndRepRenderer(TEMPLATE, pdf_backend="weasyprint")
    pytest.importorskip("weasyprint")
    for n in range(3):
        if n:
            r.page_break(reset=True)
        r.mark(f"INV-{n + 1}")
        for _ in range(n + 1):
            r.emit("band")
    pdf = r.to_pdf()

    parts = []
    for m in r.marks:
        writer = pypdf.PdfWriter()
        writer.append(BytesIO(pdf), pages=(m["first"], m["last"] + 1))
        out = BytesIO()
        writer.write(out)
        parts.append(len(pypdf.PdfReader(out).pages))
    assert parts == [1, 1, 2]

    writer = pypdf.PdfWriter(clone_from=BytesIO(pdf))
    for m in r.marks:
        writer.add_outline_item(m["label"], m["first"], fit=Fit.xyz(top=m["top"]))
    out = BytesIO()
    writer.write(out)
    reader = pypdf.PdfReader(out)
    assert [(o.title, reader.get_destination_page_number(o)) for o in reader.outline] == [
        ("INV-1", 0), ("INV-2", 1), ("INV-3", 2)]
