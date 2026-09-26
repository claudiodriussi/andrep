"""
Carry forward: _page_start / _page_end in page bands.

The accumulator is kept by the code (on_after_band); the template says which
fields to show and the renderer snapshots them after every band. Pages are
300 px high with 20 px header and footer: two 100 px rows per page.
"""
import json
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
        row("first_header", "OPEN [_page_start.total]", 20),
        row("page_header", "BF [_page_start.total]", 20),
        row("band", "[amount]", 100),
        row("page_footer", "CF [_page_end.total] PAGE [_page_end.total - _page_start.total]", 20),
        row("last_footer", "TOTAL [_page_end.total]", 20),
    ],
}


class Ledger(AndRepRenderer):
    opening = 0

    def on_before(self):
        self.total = self.opening

    def on_after_band(self, band_name):
        if band_name == "band":
            self.total += self.data.amount


def marks(html: str) -> list:
    return re.findall(r"(?:OPEN|BF|CF|TOTAL) -?\d+(?: PAGE -?\d+)?", html)


def run(amounts, renderer_cls=Ledger, reset_after=None) -> AndRepRenderer:
    r = renderer_cls(TEMPLATE)
    for i, amount in enumerate(amounts):  # noqa: B007 — amount is read by emit()
        if reset_after is not None and i == reset_after:
            r.page_break(reset=True)
        r.emit("band")
    return r


def test_brought_and_carried_forward():
    r = run([10, 20, 30, 40, 50])
    assert marks(r._to_pdf_html()) == [
        "OPEN 0", "CF 30 PAGE 30",
        "BF 30", "CF 100 PAGE 70",
        "BF 100", "TOTAL 150",
    ]


def test_opening_balance():
    class WithOpening(Ledger):
        opening = 1000

    r = run([10, 20, 30], WithOpening)
    assert marks(r._to_pdf_html()) == ["OPEN 1000", "CF 1030 PAGE 30", "BF 1030", "TOTAL 1060"]


def test_only_fields_read_by_page_bands_are_snapshot():
    r = run([10, 20])
    assert r._carry_fields == {"total"}
    assert [rec["carry"] for rec in r._emissions] == [{"total": 10}, {"total": 30}]


def test_sections_carry_on():
    """The code resets the accumulator if each section needs it; the engine does not."""
    r = run([10, 20, 30], reset_after=2)
    assert marks(r._to_pdf_html()) == ["OPEN 0", "TOTAL 30", "OPEN 30", "TOTAL 60"]


def test_html_is_one_page():
    r = run([10, 20, 30, 40, 50])
    html = r.to_html()
    assert "OPEN 0" in html and "TOTAL 150" in html


def test_carry_survives_compiled_records():
    r = run([10, 20, 30, 40, 50])
    records = json.loads(r.to_json())
    body = [rec for rec in records if rec["band"] == "band"]
    assert [rec["carry"]["total"] for rec in body] == [10, 30, 60, 100, 150]
    html = AndRepRenderer.from_compiled(TEMPLATE, body)._to_pdf_html()
    # no on_before() ran: the opening value is unknown — the first page shows a
    # marker where it is needed (opening line, page total); later pages are right
    assert marks(html) == ["CF 30", "BF 30", "CF 100 PAGE 70", "BF 100", "TOTAL 150"]
    assert "OPEN [#_page_start.total: AttributeError" in html


def test_templates_without_carry_store_nothing():
    template = {**TEMPLATE, "rows": [row("band", "[amount]", 100)]}
    r = Ledger(template)
    amount = 5  # noqa: F841
    r.emit("band")
    assert r._carry_fields == set() and "carry" not in r._emissions[0]
