# AndRep

Visual WYSIWYG editor for band-based report templates.

Produces a JSON template that describes layout and content, independent from data.
The same template can be rendered to HTML or PDF by a separate renderer.

> **Work in progress** — not yet usable.

## Components

| Component | Description | Status |
|---|---|---|
| [`editor/`](editor/) | Svelte 5 visual designer | In progress |
| [`renderer-python/`](renderer-python/) | Python renderer → HTML + PDF (WeasyPrint) | Planned |
| [`renderer-js/`](renderer-js/) | JS/TS renderer → HTML (browser + Node) | Planned |

## Quick start (editor)

```bash
cd editor
pnpm install
pnpm dev
```

