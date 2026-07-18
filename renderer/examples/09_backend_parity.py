"""
09_backend_parity.py — sanity check that WeasyPrint and Playwright backends
agree on the same document.

Renders 08_invoice (3 pages, images, autoStretch descriptions that trigger
the phantom pass — the most demanding template in examples/) once per
backend and compares:
  - phantom-measured row heights (tolerance: a few px, engines differ
    slightly in font metrics/hinting)
  - page count (from page-break markers in the paginated HTML)

Run from renderer/examples/:
    python3 09_backend_parity.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
inv = importlib.import_module("08_invoice")

from andrep.backends import get_backend

OUTPUT = Path(__file__).parent / "output"
HEIGHT_TOLERANCE_PX = 3


def get_phantom_rows():
    """Capture the phantom-pass HTML rows built for 08_invoice. Building this
    list is backend-agnostic (pure renderer.py logic) — only measuring their
    heights depends on the engine, which is what this script compares."""
    r = inv.build_invoice()
    r._pdf_mode = True
    r._active_pdf_backend, _ = r._resolve_pdf_backend("weasyprint")  # any backend works here
    captured = {}
    original = r._measure_phantom_heights

    def spy(html_list, content_w):
        captured["html_list"], captured["content_w"] = list(html_list), content_w
        return original(html_list, content_w)

    r._measure_phantom_heights = spy
    try:
        html = r._to_pdf_html()
    finally:
        r._pdf_mode = False
    return r, captured["html_list"], captured["content_w"], html


def render_with_backend(backend_name: str):
    r = inv.build_invoice()
    r._pdf_mode = True
    r._active_pdf_backend, owns = r._resolve_pdf_backend(backend_name)
    try:
        html = r._to_pdf_html()
        pdf = r._active_pdf_backend.render(html)
    finally:
        if owns and hasattr(r._active_pdf_backend, "close"):
            r._active_pdf_backend.close()
        r._pdf_mode = False
    return html, pdf


def main():
    OUTPUT.mkdir(exist_ok=True)

    # ── 1. Phantom row heights ────────────────────────────────────────────
    r, html_list, content_w, _ = get_phantom_rows()
    print(f"{len(html_list)} phantom rows to measure\n")

    wrapped = "".join(f'<div class="phantom-row">{h}</div>' for h in html_list)
    doc = r._phantom_doc(wrapped, content_w)

    heights = {}
    for backend_name in ("weasyprint", "playwright"):
        backend = get_backend(backend_name)()
        try:
            heights[backend_name] = backend.measure_heights(doc, len(html_list))
        finally:
            close = getattr(backend, "close", None)
            if close is not None:
                close()

    diffs = [abs(a - b) for a, b in zip(heights["weasyprint"], heights["playwright"])]
    max_diff = max(diffs) if diffs else 0
    print(f"max phantom height diff: {max_diff}px (tolerance {HEIGHT_TOLERANCE_PX}px)")
    if max_diff > HEIGHT_TOLERANCE_PX:
        bad = [
            (i, w, p) for i, (w, p) in enumerate(zip(heights["weasyprint"], heights["playwright"]))
            if abs(w - p) > HEIGHT_TOLERANCE_PX
        ]
        print(f"MISMATCH on {len(bad)} row(s), first few: {bad[:5]}")
    else:
        print("OK: phantom heights match within tolerance")

    # ── 2. Full PDF + page count per backend ──────────────────────────────
    print()
    page_counts = {}
    for backend_name in ("weasyprint", "playwright"):
        html, pdf = render_with_backend(backend_name)
        page_counts[backend_name] = html.count("page-break-after:always;") + 1
        (OUTPUT / f"09_parity_{backend_name}.pdf").write_bytes(pdf)
        print(f"[{backend_name:10s}] pages={page_counts[backend_name]}  pdf_bytes={len(pdf)}")

    pages_w, pages_p = page_counts["weasyprint"], page_counts["playwright"]
    if pages_w != pages_p:
        print(f"\nMISMATCH: page count differs (weasyprint={pages_w}, playwright={pages_p})")
    else:
        print(f"\nOK: both backends paginate to {pages_w} pages")

    print(f"PDFs written to {OUTPUT}/09_parity_*.pdf for visual inspection")


if __name__ == "__main__":
    main()
