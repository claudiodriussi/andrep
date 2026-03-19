"""
barcode.py — Barcode / QR SVG generators for AndRep.

Strategy (no-distortion):
  Generate the barcode at a module_width computed so that the SVG's natural mm
  dimensions ≈ target pixel dimensions at 96 DPI.  The resulting viewBox scales
  uniformly (same px/mm ratio on both axes) → bars AND text glyphs render at
  their correct proportions without any matrix tricks.

Usage — type="barcode" cell (clean, recommended):
    Cell JSON:
        "type":        "barcode"
        "content":     "[row.ean]"          ← data expression only
        "barcodeType": "ean13"              ← barcode symbology
        "showText":    true                 ← human-readable digits
        "fontSize":    5                    ← pt
        "autoStretch": false                ← false = natural, true = fill cell

Usage — inline formatter inside type="text" cell:
    [expr | ean13]              EAN-13 at cell dimensions
    [expr | ean13,200]          EAN-13 200 px wide, height proportional
    [expr | ean13,200,52]       EAN-13 200×52 px
    [expr | ean13,200,52,0]     EAN-13, no text
    [expr | ean13,200,52,0,4]   EAN-13, no text, font 4 pt
    [expr | code128]            Code-128
    [expr | qr]                 QR code at cell dimensions
    [expr | qr,100]             QR code 100×100 px

Supported python-barcode type names (passed verbatim to barcode.get()):
    codabar  code128  code39  ean  ean13  ean14  ean8
    gs1  gs1_128  gtin  isbn  isbn10  isbn13  issn
    itf  jan  nw-7  pzn  upc  upca
"""
import io
import re

# 96 DPI screen: 1 px = 25.4/96 mm
MM_PER_PX = 25.4 / 96.0
PX_PER_MM = 96.0 / 25.4

# All types handled by python-barcode via barcode.get()
_PYBARCODE_TYPES = {
    "codabar", "code128", "code39", "ean", "ean13", "ean13-guard",
    "ean14", "ean8", "ean8-guard", "gs1", "gs1_128", "gtin",
    "isbn", "isbn10", "isbn13", "issn", "itf", "jan", "nw-7",
    "pzn", "upc", "upca",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def barcode_svg(
    bc_type: str,
    data: str,
    w_px: int,
    h_px: int = 0,
    show_text: bool = True,
    font_size: int = 4,
    text_distance: float | None = None,
) -> str:
    """Generate a 1D barcode as inline SVG.

    Args:
        bc_type:       python-barcode type name (ean13, code128, itf, …).
        data:          data string to encode.
        w_px:          target pixel width; bars fill this width exactly.
        h_px:          target pixel height (0 = natural proportional height).
        show_text:     draw human-readable digits below the bars.
        font_size:     digit font size as SVG user units (≈ mm at standard scale).
                       Due to viewBox scaling this is NOT screen pt — at 200 px
                       wide font_size=4 renders like TrueType 9-10 pt (scale ≈ 3.1×).
                       Rule of thumb: font_size ≈ w_px / 50  (4 @ 200 px, 3 @ 150 px).
        text_distance: gap between bars and digit baseline in mm.
                       None (default) → font_size mm, which prevents digit/bar
                       overlap at any font size (cap-height ≈ 0.7 × font_size).
                       python-barcode default is 5.0 mm.

    Returns:
        Inline SVG with pixel width/height, no XML declaration.
        The SVG's natural mm dimensions match the target px size at 96 DPI so
        the viewBox scales uniformly — no text distortion.
    """
    import barcode as bc
    from barcode.writer import SVGWriter

    data = str(data).strip()
    if not data:
        return f'<svg width="{w_px or 200}" height="{h_px or 50}"></svg>'
    w_px = w_px or 200
    # Default text_distance = font_size (same user-unit space): cap-height ≈ 0.7×
    # font_size, so font_size mm of gap prevents digit/bar overlap for any font size.
    if text_distance is None:
        text_distance = float(font_size) + 1.0  # cap-height ≈ 0.7×font + 1mm margin
    target_w_mm = w_px * MM_PER_PX

    # ---- Step 1: probe at module_width=1.0 ---------------------------------
    # Use the same text/font options as the final render so the measured
    # non-bar height (text + gap) is accurate for the height calculation.
    buf = io.BytesIO()
    try:
        bc.get(bc_type, data, writer=SVGWriter()).write(buf, options={
            "write_text": show_text,
            "module_width": 1.0,
            "module_height": 10.0,
            "font_size": font_size,
            "text_distance": text_distance,
            "quiet_zone": 6.5,
        })
    except Exception as e:
        return _error_svg(w_px, h_px or 50, f"{bc_type}: {e}")

    probe_svg   = buf.getvalue().decode()
    probe_w_mm  = _parse_svg_mm(probe_svg, "width")
    probe_h_mm  = _parse_svg_mm(probe_svg, "height")
    if not probe_w_mm:
        return _error_svg(w_px, h_px or 50, f"{bc_type}: probe failed")

    # ---- Step 2: compute module dimensions ---------------------------------
    mod_w = target_w_mm / probe_w_mm   # fills target_w_px exactly

    if h_px:
        target_h_mm = h_px * MM_PER_PX
        # non_bar_mm: text + gap + padding at the reference module_height=10
        non_bar_mm = max(0.0, probe_h_mm - 10.0)
        mod_h = max(mod_w * 3, target_h_mm - non_bar_mm)
    else:
        # Natural proportions: scale mod_h by the same factor as mod_w
        mod_h = 10.0 * mod_w

    # ---- Step 3: generate final SVG ----------------------------------------
    buf2 = io.BytesIO()
    try:
        bc.get(bc_type, data, writer=SVGWriter()).write(buf2, options={
            "write_text": show_text,
            "module_width": mod_w,
            "module_height": mod_h,
            "font_size": font_size,
            "text_distance": text_distance,
            "quiet_zone": 6.5,
        })
    except Exception as e:
        return _error_svg(w_px, h_px or 50, f"{bc_type}: {e}")

    return _finalize_svg(buf2.getvalue().decode(), w_px, h_px or None)


def qr_svg(data: str, w_px: int, h_px: int = 0) -> str:
    """Generate a QR code as inline SVG.

    Always square: side = min(w_px, h_px) or w_px when h_px=0.
    """
    import qrcode
    import qrcode.image.svg as qr_mod

    side = min(w_px, h_px) if h_px else w_px
    side = side or 100

    img = qrcode.make(str(data).strip(), image_factory=qr_mod.SvgPathImage)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode()

    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    svg = re.sub(r"<!DOCTYPE[^>]*>", "", svg).strip()

    # qrcode emits width/height in mm; strip to user units, add pixel dimensions
    nat_w = _parse_svg_mm(svg, "width") or side
    nat_h = _parse_svg_mm(svg, "height") or side

    svg = re.sub(r'width="[\d.]+mm"',  f'width="{side}"',  svg, count=1)
    svg = re.sub(r'height="[\d.]+mm"', f'height="{side}"', svg, count=1)

    if "viewBox" not in svg[:400]:
        svg = svg.replace("<svg ", f'<svg viewBox="0 0 {nat_w} {nat_h}" ', 1)

    # Strip mm suffixes → user units scaled by viewBox (uniform for square QR)
    svg = re.sub(r"([\d.]+)mm", r"\1", svg)
    return svg


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_svg_mm(svg: str, dim: str) -> float:
    """Extract mm value from SVG width/height attribute ('69.0855mm' → 69.0855)."""
    m = re.search(rf'{dim}="([\d.]+)mm"', svg[:600])
    return float(m.group(1)) if m else 0.0


def _finalize_svg(svg: str, w_px: int, h_px: int | None = None) -> str:
    """Convert a python-barcode SVG to an inline pixel SVG.

    - Removes XML declaration and DOCTYPE.
    - Sets SVG width to w_px.
    - Sets SVG height to h_px if given; otherwise computes from natural mm ratio.
    - Adds viewBox with natural mm values so content coords become user units.
    - Strips 'mm' suffixes from all content coordinates.

    When h_px matches target_h_px from barcode_svg() (computed via non_bar_mm),
    the viewBox scale factors for x and y are approximately equal → no distortion.
    """
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    svg = re.sub(r"<!DOCTYPE[^>]*>", "", svg).strip()

    w_mm = _parse_svg_mm(svg, "width")
    h_mm = _parse_svg_mm(svg, "height")

    if not w_mm:
        return svg

    out_h = h_px if h_px else (round(h_mm * PX_PER_MM) if h_mm else 50)

    svg = re.sub(r'width="[\d.]+mm"',  f'width="{w_px}"',   svg, count=1)
    svg = re.sub(r'height="[\d.]+mm"', f'height="{out_h}"', svg, count=1)

    svg = svg.replace("<svg ", f'<svg viewBox="0 0 {w_mm} {h_mm}" ', 1)

    # Strip mm suffix → user units (scaled uniformly by viewBox)
    svg = re.sub(r"([\d.]+)mm", r"\1", svg)

    return svg


def _error_svg(w: int, h: int, msg: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">'
        f'<rect width="{w}" height="{h}" fill="#fff" stroke="#ccc"/>'
        f'<text x="4" y="14" font-size="9" fill="red">{msg[:80]}</text>'
        f'</svg>'
    )
