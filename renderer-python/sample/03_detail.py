"""
03_detail.py — Articles & Movements detail report, two-level grouping.

Structure:
  For each category:
    cat_header       — category title band
    For each article in category:
      art_header     — article summary (code, description, type, uom, list price)
      mov_header     — column titles for movements (emitted once per article)
      For each movement:
        movement     — date, notes, uom, qty, unit_price, purchased, sold
      art_footer     — article subtotals: purchased / sold
    cat_footer       — category subtotals
    page_break()     — separator (meaningful for PDF)
  totals             — grand totals

Column layout (718 px content width):
  x=0   w=72   date / code
  x=72  w=186  notes / description
  x=258 w=40   uom
  x=298 w=80   qty / list price
  x=378 w=80   unit price
  x=458 w=130  purchased (C movements)
  x=588 w=130  sold (S movements)

Accumulators on the renderer instance:
  art_in  / art_out  — C / S amounts for the current article (reset at art_footer)
  cat_in  / cat_out  — category totals             (reset at cat_footer)
  grand_in/ grand_out— overall totals              (never reset)
  art_count          — total articles processed
  mov_count          — total movements processed

Run from the renderer-python/ directory:
    python3 sample/03_detail.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from andrep import AndRepRenderer, FilesystemLoader

name = [
    "ACME Fireworks & Electronic Components Corp.",
    "1 Canyon Road, Desert Flats, AZ",
    "orders@acme-kaboom.example",
    "VAT: US000001",
]

SUMMARY = "-s" in sys.argv or "summary" in sys.argv  # omit movement rows, keep totals

SAMPLE_DIR = Path(__file__).parent
TEMPLATES = SAMPLE_DIR / "templates"
DB = SAMPLE_DIR / "sample.db"
OUTPUT = SAMPLE_DIR / "output"


# ---------------------------------------------------------------------------
# Renderer subclass — accumulators and per-band hooks
# ---------------------------------------------------------------------------
class DetailReport(AndRepRenderer):
    def on_init(self):
        self.art_in = 0.0
        self.art_out = 0.0
        self.cat_in = 0.0
        self.cat_out = 0.0
        self.grand_in = 0.0
        self.grand_out = 0.0
        self.art_count = 0
        self.mov_count = 0
        self._mov_row = 0  # zebra counter, reset per article

    def on_before_band(self, band_name):
        if band_name == "movement":
            # zebra striping on movement rows
            if self._mov_row % 2 == 1:
                self.patch_band(cssExtra="background:#f8fafc")

    def on_after_band(self, band_name):
        if band_name == "movement":
            mov = self.data.mov
            amount = mov.qty * mov.unit_price
            if mov.type == "C":
                self.art_in += amount
            else:
                self.art_out += amount
            self.mov_count += 1
            self._mov_row += 1

        elif band_name == "art_footer":
            self.cat_in += self.art_in
            self.cat_out += self.art_out
            self.art_in = 0.0
            self.art_out = 0.0
            self.art_count += 1
            self._mov_row = 0  # reset zebra for next article

        elif band_name == "cat_footer":
            self.grand_in += self.cat_in
            self.grand_out += self.cat_out
            self.cat_in = 0.0
            self.cat_out = 0.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    loader = FilesystemLoader(base_dir=TEMPLATES)
    r = DetailReport("detail", loader=loader)
    r.title = "Articles & Movements Detail"
    r.name = name

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    categories = con.execute(
        "SELECT * FROM categories ORDER BY code"
    ).fetchall()

    for cat in categories:
        articles = con.execute(
            """
            SELECT a.id, a.code, a.description, a.type, a.uom, a.price
              FROM articles a
             WHERE a.category_id = ?
             ORDER BY a.code
            """,
            (cat["id"],),
        ).fetchall()

        r.emit("cat_header")

        for art in articles:
            movements = con.execute(
                """
                SELECT date, type, qty, unit_price, notes
                  FROM movements
                 WHERE article_id = ?
                 ORDER BY date
                """,
                (art["id"],),
            ).fetchall()

            r.emit("art_header")

            if movements:
                r.emit("mov_header")
                for mov in movements:
                    r.emit("movement", silent=SUMMARY)

            r.emit("art_footer")

        r.emit("cat_footer")
        r.page_break()

    r.emit("totals")
    con.close()

    OUTPUT.mkdir(exist_ok=True)
    r.save_output(OUTPUT / "03_detail.json")
    out_file = OUTPUT / "03_detail.html"
    out_file.write_text(r.to_html(), encoding="utf-8")
    pdf_file = OUTPUT / "03_detail.pdf"
    pdf_file.write_bytes(r.to_pdf())
    print(
        f"Written: {out_file}\n"
        f"         {pdf_file}\n"
        f"  {r.art_count} articles, {r.mov_count} movements\n"
        f"  Purchased: {r.grand_in:,.2f}   Sold: {r.grand_out:,.2f}"
    )


if __name__ == "__main__":
    main()
