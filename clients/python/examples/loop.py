"""
loop.py — Products loop engine for the AndRep Python client demo.

Uses AndRepRenderer from the andrep package as the loop engine:
  - emit() captures local variables from the caller's frame automatically
  - on_before_band / on_after_band hooks for zebra striping and accumulators
  - _emissions contains the compiled records, ready to send to the REST server

Instead of calling r.to_html() / r.to_pdf() locally, we extract r._emissions
and POST them to a remote rendering server — useful when WeasyPrint is not
installed on this machine.
"""

import sys
from pathlib import Path

# Add the renderer package to the path (clients/python/examples → ../../../renderer)
RENDERER_DIR = Path(__file__).resolve().parents[3] / "renderer"
sys.path.insert(0, str(RENDERER_DIR))

from andrep import AndRepRenderer, FilesystemLoader  # noqa: E402

from data import PRODUCTS, COMPANY_INFO  # noqa: E402

TEMPLATES = Path(__file__).parent / "templates"


class ProductsReport(AndRepRenderer):

    def on_init(self):
        self._total_value = 0.0
        self._count = 0
        self._band_count: dict[str, int] = {}

    def on_before_band(self, band_name: str) -> None:
        if band_name == "band":
            # Zebra striping: odd rows (0-indexed) get a light background.
            # _band_count is incremented in on_after_band, so at this point
            # it holds the count of already-emitted rows (same timing as JS).
            if self._band_count.get("band", 0) % 2 == 1:
                self.patch_band("background:#f9fafb")

    def on_after_band(self, band_name: str) -> None:
        self._band_count[band_name] = self._band_count.get(band_name, 0) + 1
        if band_name == "band":
            self._total_value += self.data.row.price * self.data.row.qty
            self._count += 1

    @property
    def grand_total(self) -> float:
        return self._total_value

    @property
    def article_count(self) -> int:
        return self._count


def build_report() -> ProductsReport:
    """Build and run the products loop. Call r._emissions for compiled records."""
    loader = FilesystemLoader(base_dir=TEMPLATES)
    r = ProductsReport("products", loader=loader)

    r.title = "Products Catalog"
    r.name  = COMPANY_INFO   # _r.name[0..3] used by stdhdr.json

    r.emit("col_header")

    for row in PRODUCTS:
        r.emit("band")      # 'row' captured from local scope → [row.code], [row.price | .2] ...

    totals = {"count": r.article_count, "value": r.grand_total}
    r.emit("totals")        # 'totals' captured → [totals.count], [totals.value | .2]

    return r
