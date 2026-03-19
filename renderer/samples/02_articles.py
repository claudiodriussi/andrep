"""
02_articles.py — Article list report, portrait or landscape.

Usage:
    python3 samples/02_articles.py              # portrait
    python3 samples/02_articles.py --landscape  # landscape (adds Category column)

Run from the renderer/ directory.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from andrep import AndRepRenderer, FilesystemLoader

name = [
    "ACME Fireworks & Electronic Components Corp.",
    "1 Canyon Road, Desert Flats, AZ",
    "orders@acme-kaboom.example",
    "VAT: US000001"
]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SAMPLE_DIR = Path(__file__).parent
TEMPLATES = SAMPLE_DIR / "templates"
DB = SAMPLE_DIR / "sample.db"
OUTPUT = SAMPLE_DIR / "output"


# ---------------------------------------------------------------------------
# Renderer subclass — accumulators
# ---------------------------------------------------------------------------
class ArticlesReport(AndRepRenderer):
    def on_init(self):
        self.count = 0
        self.total = 0.0

    def on_before_band(self, band_name):
        if band_name == "band":
            # zebra striping — odd rows get a light background
            if self.count % 2 == 1:
                self.patch_band(cssExtra="background:#f0f4f8")
            # SRV articles: italic description
            if self.data and self.data.row.type == "SRV":
                self.patch("[row.description", cssExtra="font-style:italic;color:#555555")

    def on_after_band(self, band_name):
        if band_name == "band":
            self.count += 1
            self.total += self.data.row.price


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(landscape: bool | None = None):
    if landscape is None:
        parser = argparse.ArgumentParser(description="AndRep — article list report")
        parser.add_argument("--landscape", action="store_true", help="landscape layout with Category column")
        args = parser.parse_args()
        landscape = args.landscape

    template_name = "articles_landscape" if landscape else "articles"
    stem = "02_articles_landscape" if landscape else "02_articles"
    title = "Article List (Landscape)" if landscape else "Article List"

    loader = FilesystemLoader(base_dir=TEMPLATES)
    r = ArticlesReport(template_name, loader=loader)
    r.title = title
    r.name = name

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    articles = con.execute("""
        SELECT a.code, a.description, a.type, a.uom, a.price, a.ean, a.url,
               c.description AS category
          FROM articles a
          JOIN categories c ON c.id = a.category_id
         ORDER BY a.type, c.code, a.code
    """).fetchall()

    for row in articles:
        r.emit("band")

    r.emit("totals")
    con.close()

    OUTPUT.mkdir(exist_ok=True)
    r.save_output(OUTPUT / f"{stem}.json")
    out_file = OUTPUT / f"{stem}.html"
    out_file.write_text(r.to_html(), encoding="utf-8")
    pdf_file = OUTPUT / f"{stem}.pdf"
    pdf_file.write_bytes(r.to_pdf())
    print(f"Written: {out_file}  ({r.count} articles, total price {r.total:,.2f})")
    print(f"         {pdf_file}")


if __name__ == "__main__":
    main()
