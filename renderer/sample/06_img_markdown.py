"""
06_img_markdown.py — image and markdown visual test.

Shows the same articles (those with image or notes) in three sections:
  1. band_contain — fixed height 100px, img,contain, notes as text
  2. band_cover   — fixed height 100px, img,cover,  notes as markdown (autoStretch)
  3. band_auto    — proportional image (autoStretch), markdown (autoStretch)

Images @data/... are embedded as data URIs (load,base64,silent).
Images https://... are passed directly as src.
Notes @data/... are loaded as text/markdown.
NULL values produce an empty string (load,silent / img with empty value).
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from andrep import AndRepRenderer, FilesystemLoader

SAMPLE_DIR = Path(__file__).parent
TEMPLATES  = SAMPLE_DIR / "templates"
DB         = SAMPLE_DIR / "sample.db"
OUTPUT     = SAMPLE_DIR / "output" / "06_img_markdown.html"


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        SELECT a.code, a.description, a.type, a.price,
               a.image, a.notes
          FROM articles a
         WHERE a.image IS NOT NULL OR a.notes IS NOT NULL
         ORDER BY a.id
    """).fetchall()
    con.close()

    loader = FilesystemLoader(base_dir=TEMPLATES)
    r = AndRepRenderer("test_img_md", loader=loader)
    r.base_dir = SAMPLE_DIR   # resolves relative @data/... paths

    # --- section 1: img,contain + text ---
    r.section = "① Fixed height 100px — img,contain — text notes"
    r.emit("sep")
    r.emit("col_header")
    for row in rows:
        r.emit("band_contain")

    # --- section 2: img,cover + markdown autoStretch ---
    r.section = "② Fixed height 100px — img,cover — markdown notes (autoStretch)"
    r.emit("sep")
    r.emit("col_header")
    for row in rows:
        r.emit("band_cover")

    # --- section 3: proportional image + markdown autoStretch ---
    r.section = "③ AutoStretch — proportional image — markdown notes"
    r.emit("sep")
    r.emit("col_header")
    for row in rows:
        r.emit("band_auto")

    OUTPUT.parent.mkdir(exist_ok=True)
    r.save_output(OUTPUT.with_suffix(".json"))
    OUTPUT.write_text(r.to_html(), encoding="utf-8")
    pdf_path = OUTPUT.with_suffix(".pdf")
    pdf_path.write_bytes(r.to_pdf())
    print(f"Written: {OUTPUT}  ({len(rows)} articles × 3 sections)")
    print(f"         {pdf_path}")


if __name__ == "__main__":
    main()
