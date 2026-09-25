"""
Page numbering in PDF output: _page / _pages, sections started by
page_break(reset=True), r.cur_page as the number of the first page.

Pages are 300 px high with 20 px header and footer: two 100 px rows per page.
No backend is needed — rows have fixed heights, nothing to measure.
"""
import re

from andrep import AndRepRenderer


def row(name: str, content: str, height: int) -> dict:
    return {"name": name, "cells": [
        {"id": f"{name}_{content}", "type": "text", "content": content,
         "width": 400, "height": height}]}


TEMPLATE = {
    "page": {"width": 400, "height": 300, "marginTop": 0, "marginBottom": 0,
             "marginLeft": 0, "marginRight": 0},
    "rows": [
        row("first_header", "FIRST [_page]/[_pages]", 20),
        row("page_header", "HEAD [_page]/[_pages]", 20),
        row("band", "row", 100),
        row("page_footer", "FOOT [_page]/[_pages]", 20),
        row("last_footer", "LAST [_page]/[_pages]", 20),
    ],
}


def marks(r: AndRepRenderer) -> list:
    """Header / footer texts of every page, in order."""
    return re.findall(r"(?:FIRST|HEAD|FOOT|LAST) \d+/\d+", r._to_pdf_html())


def test_page_x_of_y():
    r = AndRepRenderer(TEMPLATE)
    for _ in range(5):
        r.emit("band")
    assert marks(r) == [
        "FIRST 1/3", "FOOT 1/3",
        "HEAD 2/3", "FOOT 2/3",
        "HEAD 3/3", "LAST 3/3",
    ]


def test_reset_starts_a_section():
    r = AndRepRenderer(TEMPLATE)
    for _ in range(3):
        r.emit("band")
    r.page_break(reset=True)
    for _ in range(2):
        r.emit("band")
    assert marks(r) == [
        "FIRST 1/2", "FOOT 1/2",
        "HEAD 2/2", "LAST 2/2",
        "FIRST 1/1", "LAST 1/1",
    ]


def test_plain_page_break_keeps_numbering():
    r = AndRepRenderer(TEMPLATE)
    r.emit("band")
    r.page_break()
    r.emit("band")
    assert marks(r) == ["FIRST 1/2", "FOOT 1/2", "HEAD 2/2", "LAST 2/2"]


def test_cur_page_is_the_first_page_number():
    r = AndRepRenderer(TEMPLATE)
    r.cur_page = 5
    for _ in range(3):
        r.emit("band")
    assert marks(r) == ["FIRST 5/6", "FOOT 5/6", "HEAD 6/6", "LAST 6/6"]


def test_html_is_one_page():
    r = AndRepRenderer(TEMPLATE)
    for _ in range(5):
        r.emit("band")
    html = r.to_html()
    assert "FIRST 1/1" in html and "LAST 1/1" in html


def test_reset_is_kept_in_compiled_records():
    r = AndRepRenderer(TEMPLATE)
    r.emit("band")
    r.page_break(reset=True)
    r.emit("band")
    r2 = AndRepRenderer.from_compiled(TEMPLATE, r._emissions)
    assert marks(r2) == marks(r) == ["FIRST 1/1", "LAST 1/1", "FIRST 1/1", "LAST 1/1"]
