"""
gen_invoice_template.py — generates sample/templates/test_invoice.json

Run from renderer-python/:
    python3 sample/gen_invoice_template.py
"""

import json
from pathlib import Path

TEMPLATES = Path(__file__).parent / "templates"

# ── Column layout (content_w = 794 - 30 - 30 = 734 px) ───────────────────────
#
#  x     w     field
#  0    55     Code
#  55  340     Description   (band_article / band_direct / band_desc)
#  55   40     Thumbnail     (band_article_img only)
#  95  300     Description   (band_article_img)
# 395   30     UM
# 425   65     Qty
# 490   65     Unit price
# 555   45     Discount %
# 600   70     Amount
# 670   64     VAT %
# ─────────────────────────────────────────────────────────────────────────────
# total: 55+340+30+65+65+45+70+64 = 734 ✓

C_CODE   = (0,   55)
C_DESC   = (55,  340)
C_THUMB  = (55,  40)
C_DESC_I = (95,  300)   # description when thumbnail is present
C_UM     = (395, 30)
C_QTY    = (425, 65)
C_PRICE  = (490, 65)
C_DISC   = (555, 45)
C_AMOUNT = (600, 70)
C_VAT    = (670, 64)

HDR_BG  = "#e8ecf0"
B_NONE  = {"width": 0, "style": "none",  "color": "#000000"}
B_COL   = {"width": 1, "style": "solid", "color": "#bbbbbb"}   # column separator
B_SEP   = {"width": 1, "style": "solid", "color": "#555555"}   # section separator
B_LIGHT = {"width": 1, "style": "solid", "color": "#aaaaaa"}   # light separator

_cid = 0
_rid = 0


def _cid_next():
    global _cid
    _cid += 1
    return f"c{_cid:03d}"


def _rid_next():
    global _rid
    _rid += 1
    return f"r{_rid:02d}"


def mk_cell(content, x, w, h, *,
            ctype="text",
            wrap=False, stretch=False,
            size=9, bold=False, italic=False,
            color="#000000", bg="#ffffff",
            align="left", va="top",
            pt=2, pb=2, pl=4, pr=4,
            bt=None, bb=None, bl=None, br=None,
            embed_target=None):
    c = {
        "id": _cid_next(),
        "content": content,
        "type": ctype,
        "x": x, "width": w, "height": h,
        "wrap": wrap, "autoStretch": stretch,
        "style": {
            "fontFamily": "Arial",
            "fontSize": size,
            "fontWeight": "bold" if bold else "normal",
            "fontStyle": "italic" if italic else "normal",
            "textDecoration": "none",
            "color": color, "backgroundColor": bg,
            "alignment": align, "verticalAlignment": va,
            "paddingTop": pt, "paddingBottom": pb,
            "paddingLeft": pl, "paddingRight": pr,
            "borders": {
                "top":    bt or B_NONE,
                "bottom": bb or B_NONE,
                "left":   bl or B_NONE,
                "right":  br or B_NONE,
            },
        },
    }
    if embed_target:
        c["embedTarget"] = embed_target
    return c


def mk_row(name, cells):
    return {"id": _rid_next(), "name": name, "cells": cells}


def col_hdrs(band_name):
    """Column header row (shared by first_header and page_header)."""
    kw = dict(bold=True, bg=HDR_BG, bb=B_SEP, size=8)
    return mk_row(band_name, [
        mk_cell("Code",        *C_CODE,   18, align="left",   bl=B_COL, br=B_COL, **kw),
        mk_cell("Description", *C_DESC,   18, align="left",   br=B_COL, **kw),
        mk_cell("UM",          *C_UM,     18, align="center", br=B_COL, **kw),
        mk_cell("Qty",         *C_QTY,    18, align="right",  br=B_COL, **kw),
        mk_cell("Unit price",  *C_PRICE,  18, align="right",  br=B_COL, **kw),
        mk_cell("Disc%",       *C_DISC,   18, align="right",  br=B_COL, **kw),
        mk_cell("Amount",      *C_AMOUNT, 18, align="right",  br=B_COL, **kw),
        mk_cell("VAT%",        *C_VAT,    18, align="right",  br=B_COL, **kw),
    ])


def body_row(name, code_expr, desc_expr, desc_col=C_DESC, h=18):
    """Standard body row: code + description (autoStretch) + amounts."""
    return mk_row(name, [
        mk_cell(code_expr,          *C_CODE,   h,                          bl=B_COL, br=B_COL),
        mk_cell(desc_expr,          *desc_col, h, wrap=True, stretch=True, br=B_COL),
        mk_cell("[row.um]",         *C_UM,     h, align="center",          br=B_COL),
        mk_cell("[row.qty|.2]",     *C_QTY,    h, align="right",           br=B_COL),
        mk_cell("[row.price|.4]",   *C_PRICE,  h, align="right",           br=B_COL),
        mk_cell("[row.disc|.1]",    *C_DISC,   h, align="right",           br=B_COL),
        mk_cell("[row.amount|.2]",  *C_AMOUNT, h, align="right", bold=True, br=B_COL),
        mk_cell("[row.vat]",        *C_VAT,    h, align="right",           br=B_COL),
    ])


def filler_row():
    """page_filler: column-border cells, h=24 (will be adapted by phantom pass)."""
    h = 24
    return mk_row("page_filler", [
        mk_cell("", *C_CODE,   h, bl=B_COL, br=B_COL),
        mk_cell("", *C_DESC,   h, br=B_COL),
        mk_cell("", *C_UM,     h, br=B_COL),
        mk_cell("", *C_QTY,    h, br=B_COL),
        mk_cell("", *C_PRICE,  h, br=B_COL),
        mk_cell("", *C_DISC,   h, br=B_COL),
        mk_cell("", *C_AMOUNT, h, br=B_COL),
        mk_cell("", *C_VAT,    h, br=B_COL),
    ])


# ── Band construction ─────────────────────────────────────────────────────────

rows = []

# ── company_block (full — used in first_header) ───────────────────────────────
# Left embed: x=0, w=372 — contains logo placeholder + company name + address
rows += [
    mk_row("company_block", [
        mk_cell("[_r.company_name]", 0, 372, 30, bold=True, size=12),
    ]),
    mk_row("company_block", [
        mk_cell("[_r.company_addr]", 0, 372, 16, size=8, color="#555555"),
    ]),
    mk_row("company_block", [
        mk_cell("[_r.company_vat]", 0, 372, 14, size=7, color="#777777"),
    ]),
]

# ── customer_block (full — used in first_header) ──────────────────────────────
# Right embed: x=374, w=360 — contains customer address block
rows += [
    mk_row("customer_block", [
        mk_cell("Spett.le:", 0, 360, 14, bold=True, size=8, color="#777777"),
    ]),
    mk_row("customer_block", [
        mk_cell("[_r.customer_name]", 0, 360, 26, bold=True, size=12),
    ]),
    mk_row("customer_block", [
        mk_cell("[_r.customer_addr]", 0, 360, 16, size=9),
    ]),
    mk_row("customer_block", [
        mk_cell("", 0, 360, 6),
    ]),
]

# ── company_block_compact (used in page_header) ───────────────────────────────
rows += [
    mk_row("company_block_compact", [
        mk_cell("[_r.company_name]", 0, 372, 16, bold=True, size=8),
    ]),
    mk_row("company_block_compact", [
        mk_cell("[_r.company_addr]", 0, 372, 14, size=7, color="#777777"),
    ]),
]

# ── customer_block_compact (used in page_header) ──────────────────────────────
rows += [
    mk_row("customer_block_compact", [
        mk_cell("[_r.customer_name]", 0, 360, 16, bold=True, size=8),
    ]),
    mk_row("customer_block_compact", [
        mk_cell("[_r.customer_addr]", 0, 360, 14, size=7, color="#777777"),
    ]),
]

# ── first_header (4 rows, ≈ 118 px) ──────────────────────────────────────────
rows += [
    # Row 1: company embed (left) + customer embed (right)
    mk_row("first_header", [
        mk_cell("", 0, 372, 62, ctype="embed", embed_target="company_block"),
        mk_cell("", 374, 360, 62, ctype="embed", embed_target="customer_block"),
    ]),
    # Row 2: document info
    mk_row("first_header", [
        mk_cell("[_r.doc_type]", 0, 260, 18, bold=True),
        mk_cell("No. [_r.doc_num]", 260, 120, 18, bold=True, align="right"),
        mk_cell("[_r.doc_date]", 380, 200, 18, align="right"),
        mk_cell("Page [_page]", 580, 154, 18, align="right"),
    ]),
    # Row 3: payment info
    mk_row("first_header", [
        mk_cell("Payment terms: [_r.payment]", 0, 734, 16,
                italic=True, size=8, color="#666666", bb=B_LIGHT),
    ]),
    # Row 4: column headers
    col_hdrs("first_header"),
]

# ── page_header (3 rows, ≈ 66 px) ────────────────────────────────────────────
rows += [
    # Row 1: compact company embed (left) + compact customer embed (right)
    mk_row("page_header", [
        mk_cell("", 0, 372, 30, ctype="embed", embed_target="company_block_compact"),
        mk_cell("", 374, 360, 30, ctype="embed", embed_target="customer_block_compact"),
    ]),
    # Row 2: document info + continued marker
    mk_row("page_header", [
        mk_cell("[_r.doc_type]  No.[_r.doc_num]  —  [_r.doc_date]", 0, 540, 18, size=8),
        mk_cell("*** CONTINUED ***   Page [_page]", 540, 194, 18,
                size=8, italic=True, color="#888888", align="right"),
    ]),
    # Row 3: column headers
    col_hdrs("page_header"),
]

# ── page_footer (1 row, 24 px) ────────────────────────────────────────────────
# bt=B_SEP closes the vertical rules from the filler above.
# The renderer reserves max(page_ftr_h, last_ftr_h) at the bottom of every page
# so the footer always starts at the same y-position; any extra space is empty.
rows += [
    mk_row("page_footer", [
        mk_cell("", 0, 455, 24, bt=B_SEP),
        mk_cell("*** CONTINUED ON NEXT PAGE ***", 455, 279, 24,
                italic=True, size=8, color="#888888", align="right", bt=B_SEP),
    ]),
]

# ── last_footer (3 rows, 72 px fixed) ────────────────────────────────────────
rows += [
    mk_row("last_footer", [
        mk_cell("", 0, 395, 20, bt=B_SEP),
        mk_cell("Taxable amount:", 395, 115, 20, bold=True, align="right", bt=B_SEP),
        mk_cell("[_r.taxable|.2]",     510,  90, 20, align="right", bt=B_SEP),
        mk_cell("VAT 22%:",            600,  70, 20, bold=True, align="right", bt=B_SEP),
        mk_cell("[_r.vat_amount|.2]",  670,  64, 20, align="right", bt=B_SEP),
    ]),
    mk_row("last_footer", [
        mk_cell("", 0, 395, 24),
        mk_cell("TOTAL PAYABLE:", 395, 165, 24, bold=True, size=11, align="right"),
        mk_cell("[_r.total|.2]",   560, 174, 24, bold=True, size=11, align="right"),
    ]),
    mk_row("last_footer", [
        mk_cell("[_r.legal_text]", 0, 734, 28,
                wrap=True,
                size=7, italic=True, color="#777777", bt=B_LIGHT),
    ]),
]

# ── page_filler ───────────────────────────────────────────────────────────────
rows += [filler_row()]

# ── band_desc (descriptive note — same 8-column layout, text in Description) ──
rows += [
    mk_row("band_desc", [
        mk_cell("",          *C_CODE,   14,                          bl=B_COL, br=B_COL),
        mk_cell("[row.text]",*C_DESC,   14, wrap=True, stretch=True, br=B_COL,
                italic=True, size=8, color="#555555"),
        mk_cell("",          *C_UM,     14,                          br=B_COL),
        mk_cell("",          *C_QTY,    14,                          br=B_COL),
        mk_cell("",          *C_PRICE,  14,                          br=B_COL),
        mk_cell("",          *C_DISC,   14,                          br=B_COL),
        mk_cell("",          *C_AMOUNT, 14,                          br=B_COL),
        mk_cell("",          *C_VAT,    14,                          br=B_COL),
    ]),
]

# ── band_article ──────────────────────────────────────────────────────────────
rows += [body_row("band_article", "[row.code]", "[row.desc]")]

# ── band_direct (no article code) ────────────────────────────────────────────
rows += [body_row("band_direct", "", "[row.desc]")]

# ── band_article_img (code + thumbnail + description + amounts) ───────────────
# Thumbnail column has no right border (visually merges with description)
rows += [
    mk_row("band_article_img", [
        mk_cell("[row.code]",              *C_CODE,   40,                          bl=B_COL, br=B_COL),
        mk_cell("[row.image|img,contain]", *C_THUMB,  40, ctype="image"),              # no right border
        mk_cell("[row.desc]",              *C_DESC_I, 40, wrap=True, stretch=True, br=B_COL),
        mk_cell("[row.um]",                *C_UM,     40, align="center",          br=B_COL),
        mk_cell("[row.qty|.2]",            *C_QTY,    40, align="right",           br=B_COL),
        mk_cell("[row.price|.4]",          *C_PRICE,  40, align="right",           br=B_COL),
        mk_cell("[row.disc|.1]",           *C_DISC,   40, align="right",           br=B_COL),
        mk_cell("[row.amount|.2]",         *C_AMOUNT, 40, align="right", bold=True, br=B_COL),
        mk_cell("[row.vat]",               *C_VAT,    40, align="right",           br=B_COL),
    ]),
]

# ── Template assembly ─────────────────────────────────────────────────────────
template = {
    "_type": "andrep-template",
    "name": "test_invoice",
    "version": "1.0",
    "page": {
        "preset": "A4",
        "width": 794, "height": 1123,
        "orientation": "portrait",
        "marginTop": 30, "marginBottom": 35,
        "marginLeft": 30, "marginRight": 30,
        "locale": "", "currency": "",
    },
    "rows": rows,
}

TEMPLATES.mkdir(exist_ok=True)
out = TEMPLATES / "test_invoice.json"
out.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Written: {out}  ({len(rows)} rows, {_cid} cells)")
