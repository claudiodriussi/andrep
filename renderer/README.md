# andrep — Python Renderer

Renders AndRep JSON templates to HTML and PDF. PDF output has two interchangeable
backends — [Playwright](https://playwright.dev/python/)/Chromium (default: full
CSS/SVG support, fast once warm) and [WeasyPrint](https://weasyprint.org/)
(fallback: zero extra setup, lighter footprint) — see
[PDF backends](#pdf-backends-playwright-vs-weasyprint) below.

## Install

Clone the repository and install from the `renderer/` directory:

```bash
git clone https://github.com/claudiodriussi/andrep.git
cd andrep/renderer

pip install .                 # core only (HTML output, no PDF)
pip install ".[playwright]"   # + Playwright (default PDF backend)
playwright install chromium   # required once, downloads the browser (~150-300MB)
pip install ".[pdf]"          # + WeasyPrint (fallback PDF backend, no extra step)
pip install ".[barcode]"      # + python-barcode and qrcode
pip install ".[markdown]"     # + markdown for Markdown cells
pip install ".[all]"          # everything (both PDF backends included)
```

## Usage — emit loop (Python)

```python
from andrep import AndRepRenderer, FilesystemLoader
from pathlib import Path

loader = FilesystemLoader(Path("templates/"))
r = AndRepRenderer("my_report", loader=loader)

for row in db_rows:
    r.emit("band")          # captures local variables automatically

r.emit("totals")
html = r.to_html()
pdf  = r.to_pdf()
```

## Usage — compiled records (external loop engine)

Any language can drive the loop and pass compiled records to the renderer:

```python
import json
from andrep import AndRepRenderer, FilesystemLoader
from pathlib import Path

loader = FilesystemLoader(Path("templates/"))
records = json.loads(Path("records.json").read_text())
r = AndRepRenderer.from_compiled("my_report", records, loader=loader)
html = r.to_html()
pdf  = r.to_pdf()
```

Or via CLI:

```bash
python -m andrep render \
  --template  path/to/template.json \
  --records   path/to/records.json  \
  --format    pdf                   \
  --output    report.pdf
```

## JSON output — post-processing (Excel, etc.)

The renderer can output the compiled records as JSON instead of rendering them to HTML/PDF.
This is useful for post-processing: generate an Excel file, feed an audit log, diff two runs, or pass the data to any downstream tool.

```python
r = AndRepRenderer("my_report", loader=loader)

for row in db_rows:
    r.emit("band")

json_str = r.to_json()           # compiled records as JSON string
r.save_output("records.json")    # or save directly to file
```

The JSON output can later be rendered without re-running the loop:

```python
import json
records = json.loads(Path("records.json").read_text())
r = AndRepRenderer.from_compiled("my_report", records, loader=loader)
pdf = r.to_pdf()
```

This decoupling is also how **external loop engines** (JS, PHP, any language) communicate with the Python renderer — the loop engine writes `records.json`, the renderer reads it.

## Examples

See [`examples/`](examples/) for full working examples:

| File | Description |
|---|---|
| `01_test_compose.py` | Template composition |
| `02_articles.py` | Articles list (supports `--landscape`) |
| `03_detail.py` | Order detail with rows (supports `--summary`) |
| `04_labels.py` | Label sheet |
| `05_barcode_test.py` | Barcode and QR codes |
| `06_img_markdown.py` | Images + Markdown cells |
| `07_embed.py` | Embedded side-by-side bands |
| `08_invoice.py` | Invoice |
| `09_backend_parity.py` | Compares WeasyPrint vs Playwright output on the same document |

```bash
cd renderer/examples
python 08_invoice.py     # output in examples/output/
```

## Requirements

- Python 3.10+
- `playwright` — PDF output, default backend (needs `playwright install chromium` once)
- `weasyprint` — PDF output, fallback backend (no extra step beyond pip install)
- `python-barcode`, `qrcode` — barcode/QR SVG cells
- `markdown` — Markdown cells

All optional; install only what you need.

## PDF backends: Playwright vs WeasyPrint

`to_pdf()` renders through a pluggable `PdfBackend` (see `andrep/backends.py`).
Resolution order — first one set wins:

1. `to_pdf(backend=...)` — per-call override (`"weasyprint"`, `"playwright"`, or an
   already-built backend instance, e.g. a warm `PlaywrightBackend` shared across renders)
2. `AndRepRenderer(pdf_backend=...)` — set once at construction
3. `ANDREP_PDF_BACKEND` environment variable — override an unmodified script from
   the outside (`ANDREP_PDF_BACKEND=weasyprint python my_report.py`)
4. default: **Playwright**

```python
pdf = r.to_pdf()                          # default: Playwright
pdf = r.to_pdf(backend="weasyprint")      # explicit fallback

# reuse one warm browser across many renders (real perf win — see below)
from andrep.backends import PlaywrightBackend
with PlaywrightBackend() as shared:
    for r in many_renderers:
        pdf = r.to_pdf(backend=shared)
```

**Why Playwright is the default**: it renders through Chromium, so AndRep templates
get full CSS/SVG support with no workarounds. Measured on a 3-page invoice with images
and autoStretch cells (see `examples/09_backend_parity.py`): the raw render step is
~12× faster than WeasyPrint once Chromium is warm, and even paying the browser launch
cost on every single call (no reuse) it's still faster end-to-end than WeasyPrint's
pure-Python layout engine. The one cost is setup: `playwright install chromium`
downloads a browser (~150-300MB) — not needed for WeasyPrint.

**Why WeasyPrint is still available**: zero extra setup beyond `pip install`, and a
much smaller footprint — useful on memory/CPU-constrained hosts (small VPS) where
installing Chromium isn't practical, or where the extra step is undesirable.
It has real CSS limitations compared to a browser engine:

- **CSS support** — not all CSS properties are supported; flexbox and grid are partially or not supported. AndRep uses only table-based layout, which WeasyPrint handles correctly.
- **Fonts** — system fonts must be installed; web fonts require explicit configuration.
- **Complex backgrounds, shadows, SVG gradients on text** — may not render exactly as in a browser (see `_docs/RENDERER.md` for a known gradient-on-text limitation).
- **Performance** — large documents (hundreds of pages) may be slow to generate.

Playwright has one known cosmetic limitation of its own: Chromium's PDF export never sets
the `/Interpolate` flag on embedded raster images (unlike WeasyPrint, which always does), so
raster images displayed well above their native resolution can look blocky when zoomed in
some PDF viewers, where WeasyPrint would show them smoothed instead. Only affects raster
images stretched far beyond their native size — vector (SVG) images are unaffected in both
backends, and images at a reasonable resolution for their display size show no visible
difference either way. See `_docs/RENDERER.md` for details.

For the vast majority of business reports (lists, invoices, labels, forms) both
backends produce excellent, visually equivalent results. Line heights can differ by a
pixel between the two engines, so a long document may break pages at a slightly
different row: pick one engine and keep it when the layout must not change.

### Large documents

AndRep lays out the whole document before rendering it (that is what makes page numbers,
"Page X of Y" and sections possible), then hands it to the PDF engine in one piece.
Measured on a 40-rows-per-page list (22-core desktop; memory is the peak resident size —
for Chromium the sum over its processes, which counts shared memory more than once):

| Pages | Playwright: time · Chromium memory | WeasyPrint: time · memory |
| ----: | ---------------------------------- | ------------------------- |
|    25 | 0.6 s · 0.6 GB                     | 8 s · 0.3 GB              |
|    81 | 1.3 s · 1.0 GB                     | 27 s · 0.9 GB             |
|   242 | 4.2 s · 1.9 GB                     | 79 s · 2.7 GB             |
|   989 | 35 s · 5.4 GB                      | —                         |
|  2010 | 133 s · 9.0 GB                     | —                         |
|  3015 | 294 s · 11.6 GB                    | —                         |

The loop, the layout and the HTML take about a second per 300 pages; the rest is the PDF
engine. Python itself needs about 1 GB per 1000 pages. Past a thousand pages Chromium's
time grows faster than the page count.

**As a server**, with one warm browser shared across renders (`PlaywrightBackend`
passed to `to_pdf()`), a 3-page invoice renders in 0.08 s — 300 invoices in 27 s — and
Chromium's memory levels off at about 1.4 GB after the first hundred documents.

Guidelines:

- **Playwright is the engine for production.** WeasyPrint is an emergency fallback: fine
  for short documents, but its memory grows with the page count inside the Python process
  (about 11 MB per page).
- A few hundred pages render in seconds. Around a thousand pages a machine needs several
  GB free; three thousand pages still work, in about five minutes.
- For larger documents, split the work: separate PDFs chained with `r.cur_page` (the
  number of the first page), or sections with `page_break(reset=True)`. A document of
  thousands of pages is usually an archive, not something anyone reads.

**Backends fetch nothing.** The renderer embeds every resource as a `data:` URL (see
*Resources* in the manual), so both backends load `data:` URLs only: WeasyPrint through a
URL fetcher that refuses anything else, Playwright in its own browser context with
JavaScript disabled and every network request aborted — also when you pass a shared
browser.

**Adding a third backend**: implement `measure_heights(doc_html, count)` and
`render(doc_html)` (see the `PdfBackend` Protocol in `andrep/backends.py`) and call
`andrep.backends.register_backend("name", YourBackend)` — no core changes needed.
A third-party backend should follow the same rule: load `data:` URLs only, run no
scripts.
