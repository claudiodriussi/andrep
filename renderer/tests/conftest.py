"""
Shared fixtures for the AndRep renderer tests.

The examples in examples/ were the original (visual) test suite; these tests
add rigorous checks for the security perimeter described in the internal
design notes, plus a regression snapshot of the examples' compiled records.
"""
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

from andrep import AndRepRenderer

RENDERER_DIR = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = RENDERER_DIR / "examples"
REPO_DIR = RENDERER_DIR.parent

# Fixed system variables, so compiled records do not depend on when/who runs the tests
FIXED_SYS_VARS = {
    "report_date": "01/01/2026",
    "report_time": "12:00:00",
    "report_user": "tester",
}


def make_template(bands: dict, **extra) -> dict:
    """Build an in-memory template from {band_name: [cell_content, ...]}.

    Each band gets one row; each content string becomes one text cell.
    """
    rows = []
    for name, contents in bands.items():
        cells = [
            {"id": f"{name}_{i}", "type": "text", "content": c, "width": 100}
            for i, c in enumerate(contents)
        ]
        rows.append({"name": name, "height": 20, "cells": cells})
    return {"rows": rows, **extra}


def emitted_values(r: AndRepRenderer) -> list:
    """Values of all compiled records, in emission order."""
    r.compile()
    return [v for rec in r._compiled for v in rec.get("values", [])]


def write_templates(directory: Path, templates: dict) -> Path:
    """Write {name: template_dict} as <name>.json files in *directory*."""
    directory.mkdir(parents=True, exist_ok=True)
    for name, tmpl in templates.items():
        (directory / f"{name}.json").write_text(json.dumps(tmpl), encoding="utf-8")
    return directory


def load_example(name: str):
    """Import examples/<name>.py as a module (file names start with a digit)."""
    path = EXAMPLES_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"andrep_example_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(EXAMPLES_DIR))   # 07_embed_orientation / 09 import siblings
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(EXAMPLES_DIR))
    return module


@pytest.fixture(scope="session")
def sample_db(tmp_path_factory) -> Path:
    """sample.db built from examples/create_db.sql (the real one is git-ignored)."""
    db = tmp_path_factory.mktemp("db") / "sample.db"
    con = sqlite3.connect(db)
    con.executescript((EXAMPLES_DIR / "create_db.sql").read_text(encoding="utf-8"))
    con.close()
    return db


@pytest.fixture
def fixed_renderer(monkeypatch):
    """Freeze system variables and skip PDF generation for every renderer."""
    original_init = AndRepRenderer.__init__

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        for key, value in FIXED_SYS_VARS.items():
            setattr(self, key, value)

    monkeypatch.setattr(AndRepRenderer, "__init__", init)
    monkeypatch.setattr(AndRepRenderer, "to_pdf", lambda self, backend=None: b"")
