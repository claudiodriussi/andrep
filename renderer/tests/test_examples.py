"""
Regression: the examples must keep producing the same compiled records.

Compiled records (band + raw values + css extras) are compared, not the HTML:
the HTML is expected to change on purpose (embedded resources, CSP), while the
data a report shows must not.

Snapshots live in tests/snapshots/. To (re)create them after an intended
change:

    ANDREP_UPDATE_SNAPSHOTS=1 pytest tests/test_examples.py
"""
import json
import os

import pytest

from conftest import EXAMPLES_DIR, load_example

SNAPSHOTS = EXAMPLES_DIR.parent / "tests" / "snapshots"
UPDATE = os.environ.get("ANDREP_UPDATE_SNAPSHOTS") == "1"

# (snapshot name, example module, main() kwargs)
CASES = [
    ("02_articles",           "02_articles", {"landscape": False}),
    ("02_articles_landscape", "02_articles", {"landscape": True}),
    ("03_detail",             "03_detail",   {"summary": False}),
    ("03_detail_summary",     "03_detail",   {"summary": True}),
    ("04_labels",             "04_labels",   {}),
    ("06_img_markdown",       "06_img_markdown", {}),
    ("07_embed",              "07_embed",    {"band": "band"}),
    ("07_embed_orientation",  "07_embed",    {"band": "band_rot"}),
    ("08_invoice",            "08_invoice",  {}),
]


def check_snapshot(name: str, data) -> None:
    path = SNAPSHOTS / f"{name}.json"
    text = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True, default=str)
    if UPDATE or not path.exists():
        if not UPDATE:
            pytest.fail(f"missing snapshot {path.name} — run with ANDREP_UPDATE_SNAPSHOTS=1")
        SNAPSHOTS.mkdir(exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        return
    assert json.loads(text) == json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("snapshot, example, kwargs", CASES, ids=[c[0] for c in CASES])
def test_example_records(snapshot, example, kwargs, sample_db, fixed_renderer, tmp_path, monkeypatch):
    module = load_example(example)
    monkeypatch.setattr(module, "DB", sample_db)
    # Redirect output (a directory, or a single .html path) into tmp_path
    if module.OUTPUT.suffix:
        monkeypatch.setattr(module, "OUTPUT", tmp_path / module.OUTPUT.name)
    else:
        monkeypatch.setattr(module, "OUTPUT", tmp_path)
    if example == "07_embed":
        kwargs = {**kwargs, "output": tmp_path / f"{snapshot}.html"}

    module.main(**kwargs)

    records_file = next(tmp_path.glob("*.json"))
    check_snapshot(snapshot, json.loads(records_file.read_text(encoding="utf-8")))


def test_composed_template():
    """01_test_compose: the merged template (composition rules applied)."""
    from andrep import AndRepRenderer, FilesystemLoader

    r = AndRepRenderer("sells", loader=FilesystemLoader(base_dir=EXAMPLES_DIR / "templates"))
    composed = {k: v for k, v in r.template.items() if k != "composition"}
    check_snapshot("01_sells_composed", composed)
