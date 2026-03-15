"""
02_articles.py — Article list report with optional movement detail.

Usage:
    python3 sample/02_articles.py             # article list only
    python3 sample/02_articles.py --detail    # + movement detail per article (TODO)

Run from the renderer-python/ directory.
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
def main():
    parser = argparse.ArgumentParser(description="AndRep — article list report")
    parser.add_argument("--detail", action="store_true", help="include movement detail per article")
    args = parser.parse_args()

    if args.detail:
        print("Note: --detail not yet implemented, running list only.")

    loader = FilesystemLoader(base_dir=TEMPLATES)
    r = ArticlesReport("articles", loader=loader)
    r.title = "Article List"
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
    r.save_output(OUTPUT / "02_articles.json")
    out_file = OUTPUT / "02_articles.html"
    out_file.write_text(r.to_html(), encoding="utf-8")
    print(f"Written: {out_file}  ({r.count} articles, total price {r.total:,.2f})")


if __name__ == "__main__":
    main()
