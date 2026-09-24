"""
The expression namespace holds data only (internal notes §4.2, §4.3, §4.4).

Legitimate uses must keep working; a programmer passing a non-data object
explicitly (r["x"] = ...) gets an exception on that line.
"""
import json
import os
import sqlite3
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from andrep import AndRepRenderer, register_adapter
from andrep.expr_check import DATA_TYPES, EXCLUDED_METHODS
from andrep.variables import _adapters
from conftest import emitted_values, make_template

GOLDEN = Path(__file__).parent / "golden_methods.json"


def values(template_cells: list, **scope):
    """Emit a one-band template with *scope* as the caller's locals."""
    r = AndRepRenderer(make_template({"band": template_cells}))
    _emit(r, scope)
    return emitted_values(r)


def _emit(r, scope):
    """r.emit('band') from a frame whose locals are *scope* (plus r)."""
    exec("r.emit('band')", {}, {"r": r, **scope})


# ---------------------------------------------------------------------------
# Data in, data out
# ---------------------------------------------------------------------------

def test_mapping_rows_are_readable():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT 'ART001' AS code, 2.5 AS price").fetchone()
    assert values(["[row.code]", "[row.price * 2]"], row=row) == ["ART001", 5.0]


def test_non_data_locals_do_not_break_the_loop():
    """A loop always has non-data locals (connection, renderer…): they are left out."""
    con = sqlite3.connect(":memory:")
    row = {"code": "ART001"}
    assert values(["[row.code]"], row=row, con=con) == ["ART001"]


def test_str_subclass_is_normalized():
    class Markup(str):
        pass

    [value] = values(["[note]"], note=Markup("hello"))
    assert value == "hello" and type(value) is str


def test_dict_with_non_str_keys_stays_a_dict():
    assert values(["[d[1]]"], d={1: "one"}) == ["one"]


def test_workspace_accepts_data_and_sees_later_changes():
    tot = {"amount": 1}
    r = AndRepRenderer(make_template({"band": ["[tot.amount]"]}))
    r["tot"] = tot
    _emit(r, {})
    tot["amount"] = 2
    _emit(r, {})
    assert emitted_values(r) == [1, 2]


def test_r_exposes_data_attributes():
    class Report(AndRepRenderer):
        def on_init(self):
            self.total = 10
            self.doc = {"num": "2025-001"}

    r = Report(make_template({"band": ["[_r.total]", "[_r.doc.num]", "[_r.title]"]}))
    r.title = "Invoice"
    _emit(r, {})
    assert emitted_values(r) == [10, "2025-001", "Invoice"]


def test_registered_adapter():
    try:
        register_adapter(uuid.UUID, str)
        uid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        assert values(["[row.id]"], row={"id": uid}) == [str(uid)]
    finally:
        _adapters.pop(uuid.UUID, None)


def test_trusted_exposes_everything_as_before():
    r = AndRepRenderer(make_template({"band": ["[_r.has_band('band')]"]}), trusted=True)
    _emit(r, {})
    assert emitted_values(r) == [True]


# ---------------------------------------------------------------------------
# Programmer errors are explicit
# ---------------------------------------------------------------------------

def test_workspace_rejects_non_data_on_assignment():
    r = AndRepRenderer(make_template({"band": ["[x]"]}))
    with pytest.raises(TypeError, match=r"r\['con'\]: sqlite3.Connection is not data"):
        r["con"] = sqlite3.connect(":memory:")


def test_workspace_accepts_anything_when_trusted():
    r = AndRepRenderer(make_template({"band": ["[x]"]}), trusted=True)
    r["con"] = sqlite3.connect(":memory:")


# ---------------------------------------------------------------------------
# Golden list of the methods templates can call on data (§4.4)
# ---------------------------------------------------------------------------

def public_methods() -> dict:
    result = {}
    for kind in sorted(DATA_TYPES, key=lambda t: t.__name__):
        excluded = EXCLUDED_METHODS.get(kind, frozenset())
        result[kind.__name__] = sorted(
            n for n in dir(kind) if not n.startswith("_") and n not in excluded
        )
    return result


def test_golden_methods():
    """A new Python version adding a method fails here: review it, then accept
    it (ANDREP_UPDATE_SNAPSHOTS=1) or add it to EXCLUDED_METHODS."""
    current = public_methods()
    if os.environ.get("ANDREP_UPDATE_SNAPSHOTS") == "1" or not GOLDEN.exists():
        GOLDEN.write_text(json.dumps(current, indent=1) + "\n", encoding="utf-8")
    assert current == json.loads(GOLDEN.read_text(encoding="utf-8"))
