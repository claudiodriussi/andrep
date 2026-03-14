"""
04_labels.py — Article labels with EAN-13 barcode, 3 columns per page.

Structure:
  page_header   — calibration spacer (5 px)
  For each article:
    band        — barcode row + code/price row + description row

Run from the renderer-python/ directory:
    python3 sample/04_labels.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from andrep import AndRepRenderer, FilesystemLoader

SAMPLE_DIR = Path(__file__).parent
TEMPLATES   = SAMPLE_DIR.parent / "templates"
DB          = SAMPLE_DIR / "sample.db"
OUTPUT      = SAMPLE_DIR / "output"


def main():
    loader = FilesystemLoader(base_dir=TEMPLATES)
    r = AndRepRenderer("labels", loader=loader)
    r.title = "Article Labels"

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    articles = con.execute(
        "SELECT code, description, uom, price, ean FROM articles ORDER BY code"
    ).fetchall()
    con.close()

    for art in articles:
        r.emit("band")

    OUTPUT.mkdir(exist_ok=True)
    out_file = OUTPUT / "04_labels.html"
    out_file.write_text(r.to_html(), encoding="utf-8")
    print(f"Written: {out_file}  ({len(articles)} labels)")


if __name__ == "__main__":
    main()
