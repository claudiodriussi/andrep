"""
05_barcode_test.py — Standalone barcode / QR rendering test.

Tests barcode_svg() and qr_svg() directly — no database, no template, no renderer.
Generates an HTML page with all combinations.

Run from renderer-python/:
    python3 sample/05_barcode_test.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from andrep.barcode import barcode_svg, qr_svg

OUTPUT = Path(__file__).parent / "output"


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

BARCODE_TESTS = [
    # (bc_type, data, w_px, h_px, show_text, font_size, label)
    # font_size note: due to viewBox scaling, font_size is NOT screen pt.
    # At 200 px wide, font=4 renders like TrueType 9-10 pt (scale ≈ 3.1×).
    # Rule of thumb: font_size ≈ w_px / 50.
    ("ean13",   "5901234123457",  200, 68, True,  4, "EAN-13  200×68  ref (font=4 ≈ TT 9-10pt)"),
    ("ean13",   "5901234123457",  200, 68, False, 4, "EAN-13  200×68  bars only"),
    ("ean13",   "5901234123457",  150, 52, True,  3, "EAN-13  150×52  small  (font=3)"),
    ("ean13",   "5901234123457",  300, 80, True,  4, "EAN-13  300×80  large  (font=4)"),
    ("ean13",   "5901234123457",  200,  0, True,  4, "EAN-13  200×auto"),
    ("code128", "HELLO WORLD",    200, 68, True,  4, "Code128 200×68"),
    ("code128", "12345678",       200, 68, True,  4, "Code128 numeric 200×68"),
    ("code128", "ABC-123/XYZ",    150, 52, True,  3, "Code128 150×52"),
    ("code39",  "HELLO",          200, 68, True,  4, "Code39  200×68"),
    ("ean8",    "5901234",        120, 52, True,  3, "EAN-8   120×52"),
    ("itf",     "12345678901234", 200, 68, True,  4, "ITF     200×68"),
]

ALIGN_TESTS = [
    # 240×80 cell with a 160×50 barcode: alignment within the cell
    ("ean13", "5901234123457", 160, 50, "left",   "top",    "align: left/top"),
    ("ean13", "5901234123457", 160, 50, "center", "middle", "align: center/middle"),
    ("ean13", "5901234123457", 160, 50, "right",  "bottom", "align: right/bottom"),
]

QR_TESTS = [
    # (data, w_px, h_px, label)
    ("https://example.com/test",  80,  80, "QR  80×80"),
    ("https://example.com/test", 120, 120, "QR 120×120"),
    ("https://example.com/test", 150,  80, "QR 150×80 (takes min=80)"),
    ("HELLO WORLD",               80,  80, "QR text"),
    ("1234567890",                 80,  80, "QR digits"),
]


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Arial, sans-serif; font-size: 12px; padding: 24px; background: #f5f5f5; }
h2 { margin: 24px 0 8px; font-size: 14px; color: #333; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
.row  { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; align-items: flex-start; }
.cell { background: #fff; border: 1px solid #ccc; padding: 6px; }
.lbl  { font-size: 9px; color: #888; margin-bottom: 4px; white-space: nowrap; }
.ok   { color: green; font-size: 9px; }
.err  { color: red;   font-size: 9px; }
/* Alignment demo cells */
.align-wrap { position: relative; width: 240px; height: 80px;
              border: 1px dashed #aaa; background: #fafafa;
              display: flex; flex-direction: column; overflow: hidden; }
.align-left   { align-items: flex-start; }
.align-center { align-items: center; }
.align-right  { align-items: flex-end; }
.va-top    { justify-content: flex-start; }
.va-middle { justify-content: center; }
.va-bottom { justify-content: flex-end; }
"""


def _svg_status(svg: str) -> str:
    """Return a short diagnostic line about the generated SVG."""
    import re
    if "fill=\"red\"" in svg[:200]:
        return '<span class="err">ERROR</span>'
    m_w = re.search(r'width="(\d+)"', svg[:400])
    m_h = re.search(r'height="(\d+)"', svg[:400])
    has_vb = "viewBox" in svg[:400]
    w = m_w.group(1) if m_w else "?"
    h = m_h.group(1) if m_h else "?"
    vb = "viewBox ✓" if has_vb else "viewBox ✗"
    return f'<span class="ok">{w}×{h}px  {vb}</span>'


def build_html() -> str:
    parts = [
        "<!DOCTYPE html><html><head>",
        '<meta charset="utf-8">',
        f"<style>{CSS}</style>",
        "</head><body>",
    ]

    # ---- 1D barcodes --------------------------------------------------------
    parts.append("<h2>1D Barcodes</h2><div class='row'>")
    for bc_type, data, w, h, show_text, font_size, label in BARCODE_TESTS:
        svg = barcode_svg(bc_type, data, w, h, show_text, font_size)
        parts.append(
            f"<div class='cell'>"
            f"<div class='lbl'>{label}<br>{_svg_status(svg)}</div>"
            f"{svg}"
            f"</div>"
        )
    parts.append("</div>")

    # ---- QR codes -----------------------------------------------------------
    parts.append("<h2>QR Codes</h2><div class='row'>")
    for data, w, h, label in QR_TESTS:
        svg = qr_svg(data, w, h)
        parts.append(
            f"<div class='cell'>"
            f"<div class='lbl'>{label}<br>{_svg_status(svg)}</div>"
            f"{svg}"
            f"</div>"
        )
    parts.append("</div>")

    # ---- Alignment demo -----------------------------------------------------
    parts.append("<h2>Alignment (cell 240×80, barcode 160×50)</h2><div class='row'>")
    ha_map = {"left": "align-left", "center": "align-center", "right": "align-right"}
    va_map = {"top": "va-top", "middle": "va-middle", "bottom": "va-bottom"}
    for bc_type, data, w, h, ha, va, label in ALIGN_TESTS:
        svg = barcode_svg(bc_type, data, w, h, True, 5)
        ha_cls = ha_map[ha]
        va_cls = va_map[va]
        parts.append(
            f"<div class='cell'>"
            f"<div class='lbl'>{label}</div>"
            f"<div class='align-wrap {ha_cls} {va_cls}'>{svg}</div>"
            f"</div>"
        )
    parts.append("</div>")

    parts.append("</body></html>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT.mkdir(exist_ok=True)
    html = build_html()
    out_file = OUTPUT / "05_barcode_test.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"Written: {out_file}")

    # Quick sanity check: count errors
    errors = html.count('class="err"')
    oks    = html.count('class="ok"')
    print(f"  OK: {oks}   Errors: {errors}")

    from weasyprint import HTML
    pdf_file = OUTPUT / "05_barcode_test.pdf"
    pdf_file.write_bytes(HTML(string=html).write_pdf())
    print(f"         {pdf_file}")


if __name__ == "__main__":
    main()
