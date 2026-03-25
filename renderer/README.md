# andrep — Python Renderer

Renders AndRep JSON templates to HTML and PDF (via [WeasyPrint](https://weasyprint.org/)).

## Install

Clone the repository and install from the `renderer/` directory:

```bash
git clone https://github.com/USER/andrep.git
cd andrep/renderer

pip install .            # core only (HTML output, no PDF)
pip install ".[pdf]"     # + WeasyPrint for PDF
pip install ".[barcode]" # + python-barcode and qrcode
pip install ".[markdown]"# + markdown for Markdown cells
pip install ".[all]"     # everything
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

```bash
cd renderer/examples
python 08_invoice.py     # output in examples/output/
```

## Requirements

- Python 3.10+
- `weasyprint` — PDF output
- `python-barcode`, `qrcode` — barcode/QR SVG cells
- `markdown` — Markdown cells

All optional; install only what you need.
