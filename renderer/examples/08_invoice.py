"""
08_invoice.py — Sales invoice test: 3 pages, all pagination mechanisms.

Exercises:
  - first_header (tall) vs page_header (compact)  — different avail heights
  - band_desc / band_article / band_direct / band_article_img
  - page_footer ("CONTINUED") vs last_footer (totals + legal text)
  - page_filler (vertical rules)
  - autoStretch descriptions → phantom pass required for correct pagination

Articles are read from the sample DB. If an article has an image, band_article_img
is used; otherwise band_article.

Run from renderer-python/:
    python3 sample/08_invoice.py
"""

import sqlite3
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from andrep import AndRepRenderer, FilesystemLoader

SAMPLE_DIR = Path(__file__).parent
TEMPLATES  = SAMPLE_DIR / "templates"
DATA_DIR   = SAMPLE_DIR / "data"
DB         = SAMPLE_DIR / "sample.db"
OUTPUT     = SAMPLE_DIR / "output"

# ── Invoice metadata ──────────────────────────────────────────────────────────

COMPANY_NAME = "ACME Electronics & Components"
COMPANY_ADDR = "12 Industrial Park, London EC1A 1BB — orders@acme-electronics.com"
COMPANY_VAT  = "VAT GB123456789"
CUSTOMER_NAME = "ROSS SYSTEMS LTD"
CUSTOMER_ADDR = "45 Commerce Street, Manchester M1 2BX"
PAYMENT      = "Bank transfer 60 days end of month"
LEGAL_TEXT   = (
    "Your data is processed under EU Regulation 2016/679 (GDPR); for further "
    "information please visit our company website. This document is issued for "
    "accounting purposes only. The original is available at the electronic "
    "address you provided or in your reserved area on our customer portal."
)

# ── Shipment groups — static invoice structure ────────────────────────────────
# Each group: (ship_num, ship_date, order_num, order_date, [(code, qty, disc)], [ref_ships])
# Articles without image → band_article; with image → band_article_img
# All quantities are capped so that qty * price * (1 - disc/100) < 1500

SHIPMENT_GROUPS = [
    ("3342", "01/09/25", "51297", "04/07/25",
     [("ART001", 1620, 0.0), ("ART002",  216, 0.0)],
     ["32738-05.08.2025", "32369-04.08.2025"]),

    ("3381", "03/09/25", "51297", "04/07/25",
     [("ART003", 2866, 0.0)],
     ["32738-05.08.2025", "32807-06.08.2025"]),

    ("3465", "09/09/25", "51275", "01/07/25",
     [("ART005", 4800, 0.0), ("ART031",   75, 0.0)],
     ["32136-01.08.2025", "32938-07.08.2025"]),

    ("3520", "11/09/25", "51275", "01/07/25",
     [("ART032",  40, 0.0)],
     ["32938-07.08.2025"]),

    ("3547", "12/09/25", "51275", "01/07/25",
     [("ART004", 3000, 0.0), ("ART006", 1080, 5.0)],
     ["32938-07.08.2025", "33012-13.09.2025"]),

    ("3612", "15/09/25", "51276", "02/07/25",
     [("ART007", 1800, 0.0), ("ART033",  250, 3.0)],
     ["33215-15.09.2025"]),

    ("3684", "19/09/25", "51298", "04/07/25",
     [("ART008", 1188, 0.0)],
     ["36625-09.09.2025"]),

    ("3738", "23/09/25", "51298", "04/07/25",
     [("ART009",  864, 0.0), ("ART010", 1600, 0.0)],
     ["36625-09.09.2025", "37130-11.09.2025"]),

    ("3797", "25/09/25", "51298", "04/07/25",
     [("ART011", 1620, 0.0), ("ART012", 1923, 0.0)],
     ["36625-09.09.2025", "37130-11.09.2025", "37344-12.09.2025"]),

    ("3845", "27/09/25", "51299", "05/07/25",
     [("ART001", 3240, 0.0), ("ART031",   80, 2.0)],
     ["37344-12.09.2025", "37520-13.09.2025"]),

    ("3880", "30/09/25", "51299", "05/07/25",
     [("ART003", 3000, 0.0), ("ART005", 2700, 5.0), ("ART032",  40, 0.0)],
     ["37520-13.09.2025", "37891-16.09.2025"]),

    ("3921", "01/10/25", "51300", "07/07/25",
     [("ART007", 1620, 0.0), ("ART008",  810, 2.5)],
     ["37891-16.09.2025"]),

    ("3975", "03/10/25", "51300", "07/07/25",
     [("ART009", 1200, 0.0), ("ART033",  250, 3.0), ("ART010",  540, 0.0)],
     ["37891-16.09.2025", "38102-18.09.2025"]),

    ("4023", "06/10/25", "51301", "08/07/25",
     [("ART011", 4320, 0.0), ("ART012", 2160, 0.0), ("ART031",  80, 2.0)],
     ["38102-18.09.2025", "38330-20.09.2025"]),

    ("4087", "09/10/25", "51301", "08/07/25",
     [("ART001", 2700, 0.0), ("ART003", 1350, 5.0)],
     ["38330-20.09.2025"]),
]

# Direct service lines inserted between shipment groups (index → line)
DIRECT_LINES = {
    3: {
        "desc": (
            "Freight and packaging — urgent shipment surcharge per agreement "
            "ref. 2025-LOG-001 September 2025 delivery"
        ),
        "um": "FLT", "qty": 1, "price": 65.00, "disc": 0.0, "vat": "22",
    },
    10: {
        "desc": (
            "On-site technical assistance — quality inspection MICHIGAN batch "
            "September 2025 ref. AT-2025-042 internal laboratory"
        ),
        "um": "HRS", "qty": 4, "price": 85.00, "disc": 0.0, "vat": "22",
    },
}


# ── Renderer ──────────────────────────────────────────────────────────────────

class InvoiceRenderer(AndRepRenderer):
    def on_init(self):
        self.taxable    = 0.0
        self.line_count = 0

    def on_after_band(self, band_name):
        if band_name in ("band_article", "band_direct", "band_article_img"):
            if self.data and hasattr(self.data, "row"):
                self.taxable    += float(getattr(self.data.row, "amount", 0))
                self.line_count += 1


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Load articles from DB
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    db_articles = {
        row["code"]: row
        for row in con.execute(
            "SELECT code, description, uom, price, image FROM articles"
        ).fetchall()
    }
    con.close()

    loader = FilesystemLoader(base_dir=TEMPLATES)
    r = InvoiceRenderer("doc_invoice", loader=loader)
    r.base_dir = SAMPLE_DIR

    # Invoice metadata
    r.company_name  = COMPANY_NAME
    r.company_addr  = COMPANY_ADDR
    r.company_vat   = COMPANY_VAT
    r.customer_name = CUSTOMER_NAME
    r.customer_addr = CUSTOMER_ADDR
    r.doc_type      = "SALES INVOICE"
    r.doc_num       = "2025-INV-200"
    r.doc_date      = "30/10/2025"
    r.payment       = PAYMENT
    r.legal_text    = LEGAL_TEXT

    def emit_article(code, qty, disc):
        """Emit band_article or band_article_img depending on whether image exists."""
        a = db_articles.get(code)
        if a is None:
            return
        amount = round(qty * a["price"] * (1 - disc / 100), 2)
        data = {
            "code":   code,
            "desc":   a["description"],
            "um":     a["uom"],
            "qty":    qty,
            "price":  a["price"],
            "disc":   disc,
            "amount": amount,
            "vat":    "22",
        }
        if a["image"]:
            data["image"] = a["image"]   # e.g. "@data/img/ART031.svg"
            row = types.SimpleNamespace(**data)  # noqa: F841
            r.emit("band_article_img")
        else:
            row = types.SimpleNamespace(**data)  # noqa: F841
            r.emit("band_article")

    # Emit shipment groups + direct lines
    for i, (ship_num, ship_date, order_num, order_date, articles, ref_ships) in enumerate(SHIPMENT_GROUPS):

        # Insert direct service line before this group (if any)
        if i in DIRECT_LINES:
            d = DIRECT_LINES[i]
            d_amount = round(d["qty"] * d["price"] * (1 - d["disc"] / 100), 2)
            row = types.SimpleNamespace(  # noqa: F841
                desc=d["desc"], um=d["um"],
                qty=d["qty"], price=d["price"], disc=d["disc"],
                amount=d_amount, vat=d["vat"],
            )
            r.emit("band_direct")

        # Shipment header note
        row = types.SimpleNamespace(  # noqa: F841
            text=f"Shipment no. {ship_num} dated {ship_date}  —  ORDER no. {order_num} dated {order_date}",
        )
        r.emit("band_desc")

        # Article lines
        for code, qty, disc in articles:
            emit_article(code, qty, disc)

        # Reference shipments
        if ref_ships:
            refs = "  /  ".join(f"Ref. Shipment no. {s}" for s in ref_ships)
            row = types.SimpleNamespace(text=refs)  # noqa: F841
            r.emit("band_desc")

    # Totals (evaluated lazily at to_html/to_pdf compile time via [_r.xxx])
    r.vat_amount = round(r.taxable * 0.22, 2)
    r.total      = round(r.taxable + r.vat_amount, 2)

    OUTPUT.mkdir(exist_ok=True)
    r.save_output(OUTPUT / "08_invoice.json")

    html_file = OUTPUT / "08_invoice.html"
    html_file.write_text(r.to_html(), encoding="utf-8")
    print(f"Written: {html_file}")

    pdf_file = OUTPUT / "08_invoice.pdf"
    pdf_file.write_bytes(r.to_pdf())
    print(f"Written: {pdf_file}")

    print(
        f"  Lines: {r.line_count}  "
        f"Taxable: {r.taxable:,.2f}  "
        f"VAT: {r.vat_amount:,.2f}  "
        f"Total: {r.total:,.2f}"
    )


if __name__ == "__main__":
    main()
