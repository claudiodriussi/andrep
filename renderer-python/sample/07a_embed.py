"""
07a_embed.py — rotation test via embed.

Same structure as 07_embed.py but uses band_rot instead of band.
In band_rot the left embed (art_left_rot) replaces the plain code cell
with a 22px-wide cell rotated 90° (writing-mode:vertical-rl) centred
both horizontally (text-align:center) and vertically (justify-content:center).

The right embed (art_right) is unchanged.
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
        if band_name == "band_rot":
            self.count += 1
            self.total += float(self.data.row.price or 0)


SAMPLE_DIR = Path(__file__).parent
TEMPLATES  = SAMPLE_DIR / "templates"
DB         = SAMPLE_DIR / "sample.db"
OUTPUT     = SAMPLE_DIR / "output" / "07a_embed.html"


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
    r.base_dir = SAMPLE_DIR

    for row in rows:
        r.emit("band_rot")

    r.emit("totals")

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(r.to_html(), encoding="utf-8")
    print(f"Written: {OUTPUT}  ({len(rows)} articles)")


if __name__ == "__main__":
    main()
