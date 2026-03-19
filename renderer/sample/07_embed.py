"""
07_embed.py — embed cell type test.

Renders all articles using two embed cells per band:
  art_left  — code (bold) + description (wrap+autoStretch) / image (autoStretch)
  art_right — tipo, u.m., prezzo, ean (label+value rows) + notes (markdown, autoStretch)

Tests:
  - embed cells compile the target band with the same eval namespace
  - autoStretch inside an embed grows the container naturally in HTML
  - two embed cells in a flex row both stretch to the same height (the taller one)
  - outer card borders span the full row height via flex align-items:stretch
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from andrep import AndRepRenderer, FilesystemLoader


class ArticleEmbedReport(AndRepRenderer):
    def on_init(self):
        self.count = 0
        self.total = 0.0

    def on_after_band(self, band_name):
        if band_name == "band":
            self.count += 1
            self.total += float(self.data.row.price or 0)


SAMPLE_DIR = Path(__file__).parent
TEMPLATES  = SAMPLE_DIR / "templates"
DB         = SAMPLE_DIR / "sample.db"
OUTPUT     = SAMPLE_DIR / "output" / "07_embed.html"


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        SELECT a.code, a.description, a.type, a.price,
               a.uom, a.image, a.notes, a.ean
          FROM articles a
         ORDER BY a.id
    """).fetchall()
    con.close()

    loader = FilesystemLoader(base_dir=TEMPLATES)
    r = ArticleEmbedReport("test_embed", loader=loader)
    r.base_dir = SAMPLE_DIR   # resolves @data/... paths in load formatter

    for row in rows:
        r.emit("band")

    r.emit("totals")

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(r.to_html(), encoding="utf-8")
    pdf_path = OUTPUT.with_suffix(".pdf")
    pdf_path.write_bytes(r.to_pdf())
    print(f"Written: {OUTPUT}  ({len(rows)} articles)")
    print(f"         {pdf_path}")


if __name__ == "__main__":
    main()
