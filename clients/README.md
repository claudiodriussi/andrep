# AndRep — Clients

This directory contains loop engine clients and renderer servers for AndRep.

## Architecture

```
Your data + Template JSON
        │
        ▼
  Loop engine client        ← evaluates expressions, iterates data
  (JS/TS, Python, ...)      → produces compiled records (JSON)
        │
        ▼
  Python renderer           ← applies formatters, paginates, renders
  (CLI or REST server)      → HTML / PDF
```

The Python renderer knows nothing about your data or business logic.
It only consumes compiled records and produces output.

---

## Compiled records format

Every client must produce a JSON array of records:

```json
[
  {
    "band":       "band_name",
    "values":     [val1, val2, ...],
    "css_extras": ["", "color:red", ""],
    "band_css":   "",
    "embeds":     { "cell_id": { "band": "...", "values": [...] } }
  }
]
```

- `values` — one raw value per expression token in declaration order
- `css_extras` — per-cell inline CSS override (empty string = no override)
- `band_css` — whole-band CSS override (e.g. background for zebra striping)
- `embeds` — sub-records for embed cells, keyed by `cell.id`

**Never include bands with `page_role`** (`first_header`, `page_header`,
`page_footer`, `last_footer`, `page_filler`) — the renderer inserts them automatically.

---

## JS/TS client (`js/`)

Zero runtime dependencies. Works in Node.js (≥ 18) and modern browsers (loader excluded).

### Install

```bash
cd clients/js
npm install       # or: pnpm install
```

### API

```typescript
import { AndRepEngine, FilesystemLoader } from "./src/index.js";

// 1 — Load template (Node.js only)
const loader   = new FilesystemLoader("/path/to/templates");
const template = loader.load("my_report");

// 2 — Subclass to add business logic
class MyEngine extends AndRepEngine {
  override onBeforeBand(band, ctx) {
    if (band === "row" && this.state.bandCount["row"] % 2 === 1)
      this.patchBand("background:#f5f5f5");   // zebra striping
  }
  override onAfterBand(band, ctx) { /* accumulate totals, etc. */ }
}

// 3 — Run the loop
const engine = new MyEngine(template);
engine.emit("header");
for (const row of myData)  engine.emit("row", { row });
engine.emit("totals", { total: engine.total });

// 4 — Get compiled records
const records  = engine.getRecords();
const metadata = { title: "My Report", name: ["ACME Corp", "..."] };
```

#### Engine hooks

| Hook | When |
|------|------|
| `onInit(ctx)` | once, before first emit |
| `onBefore(band, ctx)` | before every emit |
| `onBeforeBand(band, ctx)` | before emit of a specific band |
| `onAfterBand(band, ctx)` | after emit of a specific band |
| `onAfter(band, ctx)` | after every emit |

#### Engine methods

| Method | Description |
|--------|-------------|
| `emit(band, ctx?, silent?)` | emit a band record |
| `patchBand(css)` | set `band_css` for the current emit |
| `patch(match, css)` | set `css_extras` for the cell matching `match` |
| `pageBreak()` | force a page break before the next emit |
| `getRecords()` | return the compiled records array |

#### State variables exposed in template expressions

| Variable | Value |
|----------|-------|
| `_r` | engine state object (`_r.title`, `_r.name[0]`, ...) |
| `_name` | current user name |
| `_date` | today as `dd/mm/yyyy` |
| `_time` | current time as `hh:mm` |
| `_user` | current username |
| `_page` | page counter placeholder (resolved by renderer) |

#### Formatters

JS-side formatters run before compiled records are produced.
All standard formatters (`img`, `ean13`, `qr`, `.2`, `currency`, ...) are
**delegated to the Python renderer** — pass them through as-is.

Only register formatters in JS that are not available in the Python renderer:

```typescript
import { applyFormatter, type FormatterFn } from "./src/index.js";

const customs: Record<string, FormatterFn> = {
  capitalize: (v) => String(v).replace(/\b\w/g, c => c.toUpperCase()),
};
```

#### Template composition

`FilesystemLoader` resolves `composition[]` rules at load time:

```json
{ "composition": [{ "rule": "InsBefore", "target": "stdhdr" }] }
```

Supported rules: `IfNot`, `Replace`, `InsBefore`, `InsAfter`.

---

## Renderer transports

Two ways to send compiled records to the Python renderer:

### A — CLI subprocess (`callAndrep`)

Spawns `python -m andrep render` as a child process.
The renderer must be on `PYTHONPATH` (use `call_andrep.sh`).

```typescript
import { callAndrep } from "./src/cli.js";

const html = await callAndrep({
  template:    "my_report",
  templateDir: "/path/to/templates",
  records,
  metadata,
  format:      "html",   // or "pdf"
  python:      "python3",
});
```

### B — REST server (`callAndrepRest`)

Posts compiled records to a running Python REST server.
No local Python or WeasyPrint required on the Node.js machine.

```typescript
import { callAndrepRest } from "./src/cli.js";

const pdf = await callAndrepRest({
  serverUrl: "http://localhost:5000",
  template:  "my_report",
  records,
  metadata,
  format:    "pdf",
});
```

---

## REST renderer servers (`server/`)

Generic Python servers that expose the renderer over HTTP.
Both servers accept the same request format and use the same default port.

### Routes

| Method | Path | Body / params | Response |
|--------|------|---------------|----------|
| `POST` | `/render` | `{ template, records, format?, metadata? }` | HTML or PDF |
| `GET` | `/health` | — | `{ status, template_dir }` |
| `GET` | `/templates` | — | `["name", ...]` |

### Flask

```bash
pip install flask

# from repo root:
./clients/server/server_flask.sh --template-dir /path/to/templates
./clients/server/server_flask.sh --template-dir /path/to/templates --port 5000 --host 0.0.0.0
```

### FastAPI

```bash
pip install fastapi uvicorn pydantic

./clients/server/server_fastapi.sh --template-dir /path/to/templates
```

### Unified entry point

```bash
./clients/server/run.sh flask   --template-dir /path/to/templates
./clients/server/run.sh fastapi --template-dir /path/to/templates
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANDREP_TEMPLATE_DIR` | `.` | template directory |
| `ANDREP_PORT` | `5000` | listening port |
| `ANDREP_HOST` | `127.0.0.1` | listening host |

---

## CLI wrapper (`call_andrep.sh`)

Direct CLI wrapper that sets `PYTHONPATH` automatically:

```bash
./clients/call_andrep.sh render \
  --template  my_report.json \
  --records   records.json   \
  --format    pdf            \
  --output    report.pdf
```

Pass `-` for `--records` / `--output` to use stdin/stdout.

---

## Examples (`js/examples/`)

The `products` demo shows a complete products catalog with images, barcodes,
company header (via `stdhdr` composition), zebra striping and totals.

| File | Description |
|------|-------------|
| `data.ts` | Product data and company info |
| `loop.ts` | `ProductsEngine` — zebra striping, totals accumulation |
| `run-cli.ts` | Batch runner via CLI subprocess → `output/products.html/.pdf` |
| `call-server.ts` | Batch runner via REST server → `output/products-rest.html/.pdf` |
| `server.ts` | Node HTTP server — browser UI, uses CLI subprocess |
| `server-rest.ts` | Node HTTP server — browser UI, uses REST server |
| `public/index.html` | Browser UI with HTML preview, PDF preview, records viewer |

### Quick start — CLI subprocess

```bash
# Batch: generate HTML + PDF in examples/output/
cd clients/js
PYTHONPATH=../../renderer npx tsx examples/run-cli.ts

# Node server with browser UI (CLI subprocess for each request)
PYTHONPATH=../../renderer npx tsx examples/server.ts
# open http://localhost:3000
```

### Quick start — REST

```bash
# Terminal 1 — Python renderer server
./clients/server/run.sh flask --template-dir clients/js/examples/templates

# Terminal 2 — batch run via REST
cd clients/js
npx tsx examples/call-server.ts

# Terminal 2 — or: Node server with browser UI
npx tsx examples/server-rest.ts
# open http://localhost:3000
```

---

## Python client (`python/`)

Uses `AndRepRenderer` from the `andrep` package as the loop engine — no separate
engine implementation needed. The interesting use case is offloading rendering to
a remote REST server: `andrep` handles template loading, expression evaluation and
the emit loop; WeasyPrint only needs to be installed on the rendering server.

### Install

```bash
cd clients/python
pip install -r requirements.txt   # requests
```

`andrep` is not installed as a package — add the renderer to `PYTHONPATH`:

```bash
export PYTHONPATH=/path/to/andrep/renderer
```

### API

```python
import sys
sys.path.insert(0, "../../renderer")

from andrep import AndRepRenderer, FilesystemLoader
from rest import call_andrep_rest

# 1 — Subclass to add business logic
class MyReport(AndRepRenderer):
    def on_init(self):
        self.total = 0.0

    def on_before_band(self, band_name):
        if band_name == "row" and self._band_count.get("row", 0) % 2 == 1:
            self.patch_band("background:#f5f5f5")   # zebra striping

    def on_after_band(self, band_name):
        self._band_count[band_name] = self._band_count.get(band_name, 0) + 1
        if band_name == "row":
            self.total += self.data.row.price       # self.data = f_locals at emit time

# 2 — Run the loop
loader = FilesystemLoader(base_dir=Path("templates/"))
r = MyReport("my_report", loader=loader)
r.title = "My Report"
r.name  = ["ACME Corp", "Via Roma 1", "Milano", "P.IVA: 12345"]  # → _r.name[0..3]

r.emit("header")
for row in my_data:
    r.emit("row")           # 'row' captured from local scope → [row.price | .2]
totals = {"total": r.total}
r.emit("totals")            # 'totals' captured → [totals.total | .2]

# 3 — Send compiled records to the REST server (no WeasyPrint needed locally)
records  = r._emissions
metadata = {"title": r.title, "name": r.name}

pdf = call_andrep_rest(
    server_url="http://localhost:5000",
    template="my_report",
    records=records,
    metadata=metadata,
    format="pdf",
)
Path("report.pdf").write_bytes(pdf)
```

#### Hooks

| Hook | When |
|------|------|
| `on_init()` | once, at construction |
| `on_before()` | once, before the first emit |
| `on_before_band(band_name)` | before each emit — call `patch_band()` / `patch()` here |
| `on_after_band(band_name)` | after each emit — accumulate totals via `self.data.*` |
| `on_after()` | once, called by `get_records()` |

#### Methods

| Method | Description |
|--------|-------------|
| `emit(band_name, silent=False)` | compile and record a band; captures caller's `f_locals` |
| `patch_band(css)` | set `band_css` for the current emit |
| `patch(content_match, css)` | set `css_extras` for cells whose content matches |
| `page_break()` | insert a page break marker |
| `has_band(name)` | check if a band exists in the template |

#### State in template expressions

`_r` is the renderer instance — any attribute set on `r` is accessible as `_r.attr`:

| Expression | Source |
|------------|--------|
| `_r.title` | `r.title` |
| `_r.name[0]` | `r.name` (list) |
| `_date` | `r.report_date` |
| `_time` | `r.report_time` |
| `_user` | `r.report_user` |
| `_page` | `r.cur_page` (pagination by renderer) |

#### REST transport

```python
from rest import call_andrep_rest

output = call_andrep_rest(
    server_url="http://localhost:5000",
    template="my_report",
    records=r._emissions,
    metadata={"title": r.title, "name": r.name},
    format="html",   # or "pdf"
)
```

### Examples (`python/examples/`)

| File | Description |
|------|-------------|
| `data.py` | Product data and company info (port of `js/examples/data.ts`) |
| `loop.py` | `ProductsReport` — zebra striping, totals; returns renderer after emit loop |
| `run_rest.py` | Batch runner: loop → REST server → `output/products-rest.html/.pdf` |
| `templates/` | Copy of `js/examples/templates/` (`products.json` + `stdhdr.json`) |

### Quick start

```bash
# Terminal 1 — Python renderer server
./clients/server/run.sh flask --template-dir clients/python/examples/templates

# Terminal 2 — Python loop engine client
cd clients/python/examples
PYTHONPATH=../../../renderer python run_rest.py
PYTHONPATH=../../../renderer python run_rest.py --html-only
PYTHONPATH=../../../renderer python run_rest.py --server http://localhost:5000
```
