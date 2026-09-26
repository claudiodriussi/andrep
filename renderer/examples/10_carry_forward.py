"""
10_carry_forward.py — running balance carried from page to page.

The code keeps the balance (on_before / on_after_band); the template shows it:

  first_header  — opening balance (hidden when zero)
  page_header   — "Brought forward"  [_page_start.balance]
  band          — one entry, with the running balance
  page_footer   — page total and "Carried forward"  [_page_end.balance]
  last_footer   — page total and closing balance

_page_start / _page_end are the values at the start and at the end of each
PDF page; the renderer snapshots the fields the page bands read after every
emit(), so nothing has to be declared.

Run from the renderer/ directory:
    python3 examples/10_carry_forward.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from andrep import AndRepRenderer, FilesystemLoader  # noqa: E402

SAMPLE_DIR = Path(__file__).parent
TEMPLATES  = SAMPLE_DIR / "templates"
DB         = SAMPLE_DIR / "sample.db"
OUTPUT     = SAMPLE_DIR / "output"

OPENING_BALANCE = 1000.00


class LedgerReport(AndRepRenderer):
    def on_before(self):
        self.balance = OPENING_BALANCE

    def on_after_band(self, band_name):
        if band_name == "band":
            self.balance += self.data.row.price


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    articles = con.execute("SELECT code, description, price FROM articles ORDER BY code").fetchall()
    con.close()
    entries = articles * 3          # enough entries for three pages

    r = LedgerReport("carry_forward", loader=FilesystemLoader(base_dir=TEMPLATES))
    r.title = "Article ledger"
    for row in entries:  # noqa: B007 — read by emit()
        r.emit("band")

    OUTPUT.mkdir(exist_ok=True)
    r.save_output(OUTPUT / "10_carry_forward.json")
    (OUTPUT / "10_carry_forward.html").write_text(r.to_html(), encoding="utf-8")
    pdf_file = OUTPUT / "10_carry_forward.pdf"
    pdf_file.write_bytes(r.to_pdf())
    print(f"Written: {pdf_file}  ({len(entries)} entries, closing balance {r.balance:,.2f})")


if __name__ == "__main__":
    main()
