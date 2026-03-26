# AndRep — Tutorial

> Getting started: from zero to your first report.

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Get the code](#2-get-the-code)
3. [Try the editor online](#3-try-the-editor-online)
4. [Run the editor locally](#4-run-the-editor-locally) *(optional)*
5. [Explore a real template](#5-explore-a-real-template)
6. [Install the Python renderer](#6-install-the-python-renderer)
7. [Run the examples](#7-run-the-examples)
8. [Language-agnostic: the JS loop engine](#8-language-agnostic-the-js-loop-engine)
9. [Your first report from scratch](#9-your-first-report-from-scratch)

---

## 1. Prerequisites

You need three tools installed on your system: **Git**, **Python 3.10+**, and **Node.js**.

### Linux

The commands below are tested on **Ubuntu 24.04** and work as-is on Debian, Linux Mint, and
other Debian-based distributions. On Fedora/RHEL replace `apt` with `dnf`; on Arch use
`pacman`. Package names may differ slightly but the tools are the same everywhere.

```bash
sudo apt update
sudo apt install git python3 python3-pip python3-venv nodejs npm
```

> **Tip — Node version.** Ubuntu 24.04 ships Node 18, which works fine. If you want the latest
> Node, use [nvm](https://github.com/nvm-sh/nvm) or the NodeSource repository.


#### WeasyPrint dependencies (for PDF output)

WeasyPrint requires a few system libraries to render fonts and graphics:

```bash
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
                 libffi-dev libjpeg-dev libopenjp2-7
```

---

<details>
<summary><strong>macOS notes</strong></summary>

Install [Homebrew](https://brew.sh/) if you don't have it, then:

```bash
brew install git python node
brew install pango libffi jpeg openjpeg  # WeasyPrint dependencies
```

Everything else in this tutorial works identically on macOS.

</details>

---

<details>
<summary><strong>Windows notes</strong></summary>

- **Git** — download from [git-scm.com](https://git-scm.com/download/win)
- **Python** — download from [python.org](https://www.python.org/downloads/); tick "Add Python to PATH" during setup
- **Node.js** — download from [nodejs.org](https://nodejs.org/)
- **WeasyPrint on Windows** — follow the official guide at
  [doc.courtbouillon.org/weasyprint](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows);
  it requires GTK3 which is installed via a separate installer

All commands in this tutorial use a Unix shell. On Windows, use **Git Bash** (included with
Git for Windows) or **WSL2** — both work fine.

</details>

---

## 2. Get the code

Clone the repository and move into it:

```bash
git clone https://github.com/claudiodriussi/andrep.git
cd andrep
```

The repository is organized into three independent components:

```
andrep/
├── editor/      ← Svelte 5 WYSIWYG designer
├── renderer/    ← Python renderer → HTML + PDF
└── clients/     ← loop engine clients (JS, Python, shell)
```

You do not need to build or install all of them to get started. The sections below
walk through each one separately.

> **Paths** — all shell commands assume you are in the `andrep/` repository root unless
> stated otherwise. Adjust paths if your working directory differs.

---

## 3. Try the editor online

The easiest way to explore the designer is the **hosted version** — no installation needed:

**[https://claudiodriussi.github.io/andrep/](https://claudiodriussi.github.io/andrep/)**

It runs entirely in your browser. Templates are saved as JSON files on your local machine;
nothing is sent to any server.

### Configure preferences first

Before designing your first template, spend a minute setting up the editor defaults.
Open the **Preferences** dialog from the popup menu of the last toolbar icon and review:

- **Language** — `en` or `it` (the editor is i18n-ready; adding a new language requires
  only a translation file in `editor/src/lib/i18n/`)
- **Default page format** — A4, Letter, or any other preset
- **Default margins** — top, bottom, left, right in pixels (1 px ≈ 0.26 mm at 96 dpi)
- **Default font** and **font size** — applied to every new cell
- **Default locale / currency** — used by number and date formatters

These settings are saved in your browser's local storage and become the starting point for
every new template. Setting them correctly now saves time later.

> **Tip** — you can export your preferences as a JSON file (*Preferences → Save config*) and
> import them in another browser or share them with your team.

---

## 4. Run the editor locally

Running the editor locally is only needed if you want to modify the editor source code.
For designing templates, the hosted version above is simpler and equivalent.

Install the dependencies and start the dev server:

```bash
cd editor
npm install
npm run dev
```

> **pnpm users** — the editor is fully compatible with pnpm. Just replace `npm install` with
> `pnpm install` and `npm run dev` with `pnpm dev`.

Open [http://localhost:5173](http://localhost:5173) in your browser. The editor hot-reloads
on every file save — changes in `editor/src/` are reflected immediately.

To stop the server press `Ctrl+C`.

---

## 5. Explore a real template

Before installing anything, let's look at a real template to understand the structure.

Open the editor (online or local), click the **Open** button in the toolbar, and navigate to
`renderer/examples/templates/articles.json` inside the cloned repository.

You will see four bands:

| Band | Role |
|------|------|
| `page_header` | Column headers — printed on every page |
| `band` | One data row — emitted once per article |
| `totals` | Summary row — emitted once at the end |
| `page_footer` | Footer line — printed at the bottom of every page |

Click on any cell and look at its content in the toolbar. Data cells use the
`[expression]` syntax — for example `[row.code]` or `[row.price | .2]` (value
formatted with thousands separator and 2 decimal places).

Also click the **Page** button in the toolbar to see how page format, orientation, and
margins are configured for this template.

**Do not save changes** — this template is used by the renderer examples in the next steps.

---

## 6. Install the Python renderer

Create a single virtual environment at the repository root and install everything from there:

```bash
cd andrep                                      # repository root
python3 -m venv .venv
source .venv/bin/activate                      # Windows: .venv\Scripts\activate

pip install -e "renderer/[all]"                # renderer + WeasyPrint + barcode + QR + Markdown
pip install -r clients/python/requirements.txt # Python REST client (requests)
```

> **uv / conda / pipenv users** — any virtual environment tool works. Just create and
> activate your environment as usual, then run the same `pip install` commands above.

> **HTML only** — if you don't need PDF output and want to skip the WeasyPrint system
> libraries, replace `renderer/[all]` with `renderer/`.

> **REST server** — if you plan to run the built-in server, also install one of:
> `pip install -r clients/server/requirements_flask.txt` or
> `pip install -r clients/server/requirements_fastapi.txt`

Verify the installation:

```bash
python3 -c "import andrep; print('andrep OK')"
```

---

## 7. Run the examples

The examples live in `renderer/examples/` and use a small SQLite database with sample data.
First, create the sample SQLite database:

```bash
cd renderer/examples
sh create_db.sh
cd ../..                           # back to repository root
```

> **Windows** — `sqlite3` must be installed separately; download the precompiled binary
> from [sqlite.org/download](https://www.sqlite.org/download.html) and add it to your PATH.
> Then run the script in Git Bash: `sh renderer/examples/create_db.sh`

Now run the examples (from the repository root, with the virtual environment active):

```bash
source .venv/bin/activate          # if not already active

python3 renderer/examples/02_articles.py
```

Output files are written to `examples/output/`:

```
renderer/examples/output/
├── 02_articles.html
├── 02_articles.pdf
└── 02_articles.json   ← compiled records (intermediate format)
```

Open `renderer/examples/output/02_articles.html` in your browser or the `.pdf` in a PDF viewer.

Now run all the examples:

```bash
python3 renderer/examples/01_test_compose.py           # template composition
python3 renderer/examples/02_articles.py               # article list, portrait
python3 renderer/examples/02_articles_landscape.py     # same report, landscape with Category column
python3 renderer/examples/03_detail.py                 # order with detail rows
python3 renderer/examples/03_detail_summary.py         # same data, summary layout
python3 renderer/examples/04_labels.py                 # label sheet
python3 renderer/examples/05_barcode_test.py           # barcodes and QR codes
python3 renderer/examples/06_img_markdown.py           # images and Markdown cells
python3 renderer/examples/07_embed.py                  # side-by-side embedded bands
python3 renderer/examples/07_embed_orientation.py      # same with rotated band
python3 renderer/examples/08_invoice.py                # full invoice, 3 pages
```

`08_invoice.py` is the most complete example — it exercises all pagination mechanisms:
`first_header`, `page_header`, `page_footer`, `last_footer`, and `page_filler`.

---

## 8. Language-agnostic: the JS loop engine

One of AndRep's key ideas is that **the loop engine can be written in any language**.
The Python renderer only produces HTML/PDF; it knows nothing about your data or business
logic. The loop — iterating rows, evaluating expressions, emitting bands — lives entirely
in your own code.

The repository includes a fully working **TypeScript loop engine** in `clients/js/src/`:

```
clients/js/src/
├── engine.ts      ← AndRepEngine base class (emit, getRecords)
├── expression.ts  ← [expr|fmt] parser and evaluator
├── formatters.ts  ← built-in formatters (.2, date, upper, ...)
├── loader.ts      ← FilesystemLoader — reads template JSON from disk
└── cli.ts         ← calls python -m andrep render as a subprocess
```

### Run the demo server

The easiest way to see the JS engine in action is the built-in demo server, which runs
a products catalog report and serves it live in your browser.

Install the JS dependencies and start the server (the Python virtual environment must be
active so the JS engine can call the Python renderer):

```bash
source .venv/bin/activate          # Python renderer must be reachable
cd clients/js
npm install
npx tsx examples/server.ts
```

Open [http://localhost:3000](http://localhost:3000) in your browser. You will see a simple
page with links to:

- `/report?format=html` — HTML report rendered inline
- `/report?format=pdf` — PDF rendered and served directly
- `/records` — raw compiled records JSON (useful for inspection)

The JS engine (`clients/js/examples/loop.ts`) runs the loop and produces compiled records;
it then calls `python -m andrep render` to turn them into HTML or PDF. The two sides
communicate through JSON — the Python renderer never sees the JS code or the data source.

### Making any language compatible with AndRep

To drive AndRep from a new language you only need to implement three things:

1. **Read the template JSON** — parse `rows` (bands and cells), `page`, and `composition`
2. **Run the loop** — iterate your data, evaluate `[expr|fmt]` expressions in your language,
   and collect the results into a **compiled records** array (a plain JSON structure)
3. **Call the Python renderer** — pass the compiled records to `python -m andrep render`
   via subprocess, CLI pipe, or HTTP REST call; receive back HTML or PDF bytes

The compiled records format is a simple JSON array — no binary encoding, no schema
registration. If your language can read JSON and spawn a subprocess (or make an HTTP
call), it can produce reports with AndRep.

For the CLI variant and further details, see the [User Manual](manual.md).

---

## 9. Your first report from scratch

Time to build something from scratch. We'll create a minimal template in the editor,
then render it with a few lines of Python.

### Step 1 — Load the template

A ready-made starter template is provided at `docs/data/my_first.json` in the repository.

Open the editor, click the **Open** button, and load `docs/data/my_first.json`.
You will see two bands: `page_header` (column headers) and `band` (one data row with
`[item.name]` and `[item.score | .2]`).

Feel free to inspect and modify it — change fonts, colors, or cell widths — then save it
(click the **Save** button) as `my_first.json` into a new folder, e.g. `~/andrep-test/`.

### Step 2 — Write the Python script

Create `~/andrep-test/my_first.py`:

```python
from andrep import AndRepRenderer, FilesystemLoader
from pathlib import Path

BASE = Path(__file__).parent
loader = FilesystemLoader(BASE)
r = AndRepRenderer("my_first", loader=loader)

data = [
    {"name": "Alice",   "score": 98.5},
    {"name": "Bob",     "score": 74.0},
    {"name": "Charlie", "score": 85.25},
]

for item in data:
    r.emit("band")

(BASE / "my_first.html").write_text(r.to_html(), encoding="utf-8")
(BASE / "my_first.pdf").write_bytes(r.to_pdf())
print("Done — open my_first.html or my_first.pdf")
```

### Step 3 — Run it

```bash
cd ~/andrep-test
source ~/andrep/.venv/bin/activate
python3 my_first.py
```

Open `my_first.html` in your browser. You should see a two-column table with Alice,
Bob, and Charlie — scores formatted with two decimal places, page header repeated on
every page.

Congratulations — you have a working report built entirely with your own code and data.

---

## What's next?

- Read the [User Manual](manual.md) for the complete reference
- Explore the `renderer/examples/` folder for more patterns: groups, subtotals,
  images, barcodes, embedded bands, template composition
- Look at `clients/js/` if you want to drive the loop from Node.js or the browser

