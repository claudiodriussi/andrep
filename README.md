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

## Documentation

- [`_docs/ARCHITECTURE_ANDREP.md`](_docs/ARCHITECTURE_ANDREP.md) — full architecture, JSON format, renderer contract
- [`_docs/IMPLEMENTATION_NOTES.md`](_docs/IMPLEMENTATION_NOTES.md) — implementation decisions and notes

## Quick start (editor)

```bash
cd editor
pnpm install
pnpm dev
```

## Install renderers

```bash
# Python
pip install git+https://github.com/USER/andrep.git#subdirectory=renderer-python

# JS/TS
npm install github:USER/andrep#path=renderer-js
```
