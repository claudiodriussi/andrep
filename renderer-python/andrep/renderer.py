"""
renderer.py — AndRepRenderer: emit / compile / to_html / to_pdf / to_json
"""
import json
import os
import sys
import types
from datetime import datetime
from html import escape
from pathlib import Path

from .loader import TemplateLoader
from .variables import _apply_formatter, _parse_tokens, _to_ns, eval_expr


# ---------------------------------------------------------------------------
# Template loading and composition
# ---------------------------------------------------------------------------

def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_template(template, template_dir=None, loader: TemplateLoader = None):
    """Load a template (name, path or dict) and apply composition rules.

    When a loader is provided it is used for all file lookups (main template
    and every composition target).  When no loader is given the function falls
    back to direct filesystem access using template_dir.

    Returns the final template dict with rows already merged.
    """
    if loader is not None:
        tmpl = loader.load(template) if isinstance(template, str) else dict(template)
    elif isinstance(template, str):
        path = template
        if template_dir is None:
            template_dir = os.path.dirname(os.path.abspath(path))
        tmpl = _load_json(path)
    else:
        tmpl = dict(template)
        if template_dir is None:
            template_dir = "."

    composition = tmpl.get("composition", [])
    if not composition:
        return tmpl

    for comp in composition:
        rule = comp.get("rule", "").lower().replace("_", "").replace("-", "")
        target = comp.get("target", "")
        if not target:
            continue

        if loader is not None:
            try:
                ref_tmpl = loader.load(target)
            except FileNotFoundError:
                continue
        else:
            ref_path = os.path.join(template_dir, f"{target}.json")
            if not os.path.exists(ref_path):
                continue
            ref_tmpl = _load_json(ref_path)

        ref_rows = ref_tmpl.get("rows", [])
        main_rows = tmpl.get("rows", [])

        if rule in ("insbefore", "insertbefore"):
            ref_bands: dict[str, list] = {}
            for row in ref_rows:
                ref_bands.setdefault(row["name"], []).append(row)

            new_rows = []
            inserted: set[str] = set()
            for row in main_rows:
                name = row["name"]
                if name in ref_bands and name not in inserted:
                    new_rows.extend(ref_bands[name])
                    inserted.add(name)
                new_rows.append(row)

            for name, rows in ref_bands.items():
                if name not in inserted:
                    new_rows = rows + new_rows

            tmpl["rows"] = new_rows

        elif rule in ("insafter", "insertafter"):
            ref_bands = {}
            for row in ref_rows:
                ref_bands.setdefault(row["name"], []).append(row)

            new_rows = []
            inserted = set()
            for row in main_rows:
                new_rows.append(row)
                name = row["name"]
                if name in ref_bands and name not in inserted:
                    new_rows.extend(ref_bands[name])
                    inserted.add(name)

            for name, rows in ref_bands.items():
                if name not in inserted:
                    new_rows.extend(rows)

            tmpl["rows"] = new_rows

        elif rule == "replace":
            ref_bands = {}
            for row in ref_rows:
                ref_bands.setdefault(row["name"], []).append(row)

            seen: set[str] = set()
            new_rows = []
            for row in main_rows:
                name = row["name"]
                if name in ref_bands:
                    if name not in seen:
                        new_rows.extend(ref_bands[name])
                        seen.add(name)
                else:
                    new_rows.append(row)
            tmpl["rows"] = new_rows

        elif rule == "ifnot":
            existing_names = {row["name"] for row in main_rows}
            for row in ref_rows:
                if row["name"] not in existing_names:
                    main_rows.append(row)
            tmpl["rows"] = main_rows

    return tmpl


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

_PAGE_ROLES = {"first_header", "page_header", "page_footer", "last_footer", "page_filler"}


class AndRepRenderer:
    """Band-based renderer for AndRep templates.

    Subclass to add accumulators and business logic::

        class ArticlesReport(AndRepRenderer):
            def on_init(self):
                self.count = 0
                self.total = 0.0

            def on_after_band(self, band_name):
                if band_name == "band":
                    self.count += 1
                    self.total += self.data.row.price   # self.data = f_locals at emit time

        loader = FilesystemLoader(Path("templates/"))
        r = ArticlesReport("articles", loader=loader)
        r.title = "Article List"

        for row in data:        # loop variable name = template expression name
            r.emit("band")      # template: [row.code]  [row.price | .2]

        r.emit("totals")
        r.save_output("output.json")
        html = r.to_html()
        pdf  = r.to_pdf()

    Eval namespace (priority, highest last — later entries win):
        f_globals of caller    — app, imported functions (only when trusted=True)
        f_locals of caller     — loop variables, local helpers
        r._ctx                 — explicit workspace: r["key"] = value
        r.globals              — callables / objects registered explicitly
        system vars            — _r, _name, _date, _time, _user, _page

    trusted=False (default): f_globals are NOT exposed automatically.
    Set trusted=True or register globals explicitly via r.globals["name"] = obj.
    """

    def __init__(
        self,
        template,
        template_dir=None,
        loader: TemplateLoader = None,
        trusted: bool = False,
    ):
        self.template = load_template(template, template_dir, loader=loader)
        self.page = self.template.get("page", {})
        self._emissions: list[tuple[str, dict]] = []
        self._compiled: list[dict] | None = None   # set by compile()

        # Eval namespace mode
        self.trusted: bool = trusted

        # User-registered callables / objects for template expressions
        # r.globals["fn"] = my_func  →  [fn(row.x)]
        # r.globals["app"] = app     →  [app.setting]
        self.globals: dict = {}

        # Explicit workspace: r["key"] = value  →  [key.field] in template
        self._ctx: dict = {}

        # f_locals captured at the last emit() call — readable in event handlers
        # as self.data.varname  (same notation as template expressions)
        self.data: types.SimpleNamespace | None = None

        # State — readable in expressions via _r
        self.cur_band: str = ""
        self.last_band: str = ""
        self.started: bool = False

        # System variables — override before first emit() if needed
        now = datetime.now()
        self.report_date: str = now.strftime("%d/%m/%Y")
        self.report_time: str = now.strftime("%H:%M:%S")
        self.report_user: str = os.environ.get("USER", os.environ.get("USERNAME", ""))
        self.title: str = self.template.get("name", "")   # _r.title — overridable
        self.cur_page: int = 1   # increment manually to chain reports

        # Group rows by band name
        self.bands: dict[str, list] = {}
        for row in self.template.get("rows", []):
            self.bands.setdefault(row["name"], []).append(row)

        # Pre-parse cell content tokens once — eval only at compile time
        self._cell_tokens: dict[int, list] = {}
        for band_rows in self.bands.values():
            for row in band_rows:
                for cell in row.get("cells", []):
                    self._cell_tokens[id(cell)] = _parse_tokens(cell.get("content", ""))

        self.on_init()

    # ------------------------------------------------------------------
    # Workspace access
    # ------------------------------------------------------------------

    def __setitem__(self, key: str, value) -> None:
        """Set a named value in the explicit workspace: r["row"] = article."""
        self._ctx[key] = value

    def __getitem__(self, key: str):
        """Get a workspace value with SimpleNamespace conversion applied."""
        return _to_ns(self._ctx[key])

    # ------------------------------------------------------------------
    # Eval namespace construction
    # ------------------------------------------------------------------

    def _sys_vars(self) -> dict:
        return {
            "_date": self.report_date,
            "_time": self.report_time,
            "_user": self.report_user,
            "_name": self.template.get("name", ""),
            "_page": self.cur_page,
            "_r": self,
        }

    def _build_eval_ns(self, frame) -> dict:
        """Build eval namespace from caller frame + workspace + system vars.

        Called once per emit(); the result is stored and reused for every cell
        in that band emission.
        """
        ns: dict = {}
        if self.trusted:
            ns.update(frame.f_globals)
        # f_locals: apply _to_ns so sqlite3.Row / plain dicts get attribute access
        for k, v in frame.f_locals.items():
            ns[k] = _to_ns(v)
        # explicit workspace — overrides locals
        for k, v in self._ctx.items():
            ns[k] = _to_ns(v)
        # registered functions / objects — override locals
        ns.update(self.globals)
        # system vars — highest priority
        ns.update(self._sys_vars())
        ns["__builtins__"] = {}
        return ns

    def _sys_eval_ns(self) -> dict:
        """Eval namespace for auto-inserted bands (header/footer) — no caller frame."""
        ns: dict = {}
        for k, v in self._ctx.items():
            ns[k] = _to_ns(v)
        ns.update(self.globals)
        ns.update(self._sys_vars())
        ns["__builtins__"] = {}
        return ns

    # ------------------------------------------------------------------
    # Emit
    # ------------------------------------------------------------------

    def emit(self, band_name: str, silent: bool = False) -> None:
        """Record a band emission.

        The caller's local variables are captured automatically and made
        available in template expressions.  Name your loop variable to match
        the template: ``for row in data: r.emit("band")`` → ``[row.price]``.

        Args:
            band_name: name of the band to emit.
            silent:    fire hooks without recording the emission (dry-run).
        """
        frame = sys._getframe(1)

        if not self.started:
            self.started = True
            self.on_before()

        # Snapshot f_locals for event handlers (self.data.row.price)
        self.data = types.SimpleNamespace(
            **{k: _to_ns(v) for k, v in frame.f_locals.items()}
        )

        self.on_before_band(band_name)   # hook may modify self._ctx

        # Build eval namespace AFTER on_before_band so _ctx changes are included
        ns = self._build_eval_ns(frame)

        if not silent:
            self._emissions.append((band_name, ns))

        self.on_after_band(band_name)
        self.last_band = self.cur_band
        self.cur_band = band_name

    # ------------------------------------------------------------------
    # Hooks — override in subclass
    # ------------------------------------------------------------------

    def on_init(self) -> None:
        """Called at the end of __init__. Initialize accumulators here."""
        pass

    def on_before(self) -> None:
        """Called once before the first emit()."""
        pass

    def on_before_band(self, band_name: str) -> None:
        """Called before each emit(). Modify self._ctx here to inject extra variables."""
        pass

    def on_after_band(self, band_name: str) -> None:
        """Called after each emit(). Use self.data to read captured locals."""
        pass

    def on_after(self) -> None:
        """Called once at compile time, after all emits."""
        pass

    def on_abort(self) -> None:
        """Called when the renderer is discarded without producing output."""
        pass

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def has_band(self, name: str) -> bool:
        """Return True if the template contains a band with the given name."""
        return name in self.bands

    def page_break(self) -> None:
        """Insert an explicit page break marker into the emission list."""
        self._emissions.append(("__page_break__", {}))

    # ------------------------------------------------------------------
    # Auto header / footer
    # ------------------------------------------------------------------

    def _header_band_name(self) -> str | None:
        for name in ("first_header", "page_header"):
            if name in self.bands:
                return name
        return None

    def _footer_band_name(self) -> str | None:
        for name in ("last_footer", "page_footer"):
            if name in self.bands:
                return name
        return None

    def _full_emissions(self) -> list[tuple[str, dict]]:
        """Auto header + caller emissions + auto footer."""
        result = []
        sys_ns = self._sys_eval_ns()
        header = self._header_band_name()
        footer = self._footer_band_name()
        if header:
            result.append((header, sys_ns))
        result.extend(self._emissions)
        if footer:
            result.append((footer, sys_ns))
        return result

    # ------------------------------------------------------------------
    # Compile — resolve all expressions once, produce flat output structure
    # ------------------------------------------------------------------

    def compile(self) -> None:
        """Resolve all token expressions and cache the output structure.

        Called automatically by to_html(), to_pdf(), to_json(), save_output().
        Safe to call multiple times — compiles only once.

        Output structure (self._compiled): list of records, one per emission::

            {"band": "band",    "values": ["ART001", "10 ohm...", 0.45]}
            {"band": "__page_break__"}
            {"band": "totals",  "values": [41, 726.75]}
            {"band": "page_footer"}   # no variables → no values key

        Values are raw (no formatters applied) so they can be used directly
        for JSON / Excel export.  Formatters are applied only during HTML/PDF rendering.
        """
        if self._compiled is not None:
            return

        self.on_after()
        result = []

        for band_name, ns in self._full_emissions():
            if band_name == "__page_break__":
                result.append({"band": "__page_break__"})
                continue

            rows = self.bands.get(band_name, [])

            values = []
            for row in rows:
                for cell in row.get("cells", []):
                    for _, expr, _ in self._cell_tokens[id(cell)]:
                        if expr is not None:
                            values.append(eval_expr(expr, ns))

            record: dict = {"band": band_name}
            if values:
                record["values"] = values
            result.append(record)

        self._compiled = result

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def save_output(self, path: str | Path) -> None:
        """Save the compiled output to a JSON file (raw values, no formatters)."""
        self.compile()
        Path(path).write_text(
            json.dumps(self._compiled, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def to_json(self) -> str:
        """Return the compiled output as a JSON string."""
        self.compile()
        return json.dumps(self._compiled, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Cell CSS
    # ------------------------------------------------------------------

    def _border_css(self, borders: dict, side: str) -> str:
        b = borders.get(side, {})
        w = b.get("width", 0)
        st = b.get("style", "none")
        c = b.get("color", "#000000")
        if w == 0 or st == "none":
            return "none"
        return f"{w}px {st} {c}"

    def _cell_style(self, cell: dict) -> str:
        s = cell.get("style", {})
        borders = s.get("borders", {})
        va_map = {"top": "flex-start", "middle": "center", "bottom": "flex-end"}
        va = va_map.get(s.get("verticalAlignment", "top"), "flex-start")
        parts = [
            "position:absolute",
            f"left:{cell.get('x', 0)}px",
            f"width:{cell.get('width', 100)}px",
            f"height:{cell.get('height', 24)}px",
            "overflow:hidden",
            "display:flex",
            "flex-direction:column",
            f"justify-content:{va}",
            f"font-family:{s.get('fontFamily', 'Arial')},sans-serif",
            f"font-size:{s.get('fontSize', 11)}pt",
            f"font-weight:{s.get('fontWeight', 'normal')}",
            f"font-style:{s.get('fontStyle', 'normal')}",
            f"text-decoration:{s.get('textDecoration', 'none')}",
            f"color:{s.get('color', '#000000')}",
            f"background-color:{s.get('backgroundColor', '#ffffff')}",
            f"text-align:{s.get('alignment', 'left')}",
            (
                f"padding:{s.get('paddingTop', 2)}px "
                f"{s.get('paddingRight', 4)}px "
                f"{s.get('paddingBottom', 2)}px "
                f"{s.get('paddingLeft', 4)}px"
            ),
            f"border-top:{self._border_css(borders, 'top')}",
            f"border-bottom:{self._border_css(borders, 'bottom')}",
            f"border-left:{self._border_css(borders, 'left')}",
            f"border-right:{self._border_css(borders, 'right')}",
            "box-sizing:border-box",
        ]
        return ";".join(parts)

    # ------------------------------------------------------------------
    # HTML rendering — uses compiled values + template for layout/formatters
    # ------------------------------------------------------------------

    def _row_height(self, row: dict) -> int:
        return max((c.get("height", 24) for c in row.get("cells", [])), default=24)

    def _cell_html(self, cell: dict, values_iter) -> str:
        """Render one cell to HTML, consuming its token values from values_iter."""
        tokens = self._cell_tokens[id(cell)]
        parts = []
        for text, expr, fmts in tokens:
            if text:
                parts.append(escape(text))
            if expr is not None:
                v = next(values_iter, None)
                if fmts:
                    for fmt in fmts:
                        v = _apply_formatter(v, fmt)
                parts.append(escape(str(v) if v is not None else ""))
        content = "".join(parts).replace("\n", "<br>")
        return f'<div style="{self._cell_style(cell)}">{content}</div>'

    def _row_html(self, row: dict, values_iter) -> str:
        height = self._row_height(row)
        cells = "".join(self._cell_html(c, values_iter) for c in row.get("cells", []))
        return f'<div style="position:relative;height:{height}px">{cells}</div>\n'

    def to_html(self) -> str:
        """Render to a complete HTML document."""
        self.compile()
        page = self.page
        width = page.get("width", 794)
        mt = page.get("marginTop", 40)
        mb = page.get("marginBottom", 40)
        ml = page.get("marginLeft", 30)
        mr = page.get("marginRight", 30)

        body_parts: list[str] = []
        for record in self._compiled:
            band_name = record["band"]
            if band_name == "__page_break__":
                body_parts.append('<div style="page-break-after:always;height:0"></div>\n')
                continue
            rows = self.bands.get(band_name, [])
            if not rows:
                body_parts.append(f"<!-- band '{band_name}' not found -->\n")
                continue
            values_iter = iter(record.get("values", []))
            for row in rows:
                body_parts.append(self._row_html(row, values_iter))

        return (
            "<!DOCTYPE html>\n<html><head>\n"
            '<meta charset="utf-8">\n'
            "<style>\n"
            "* { box-sizing: border-box; margin: 0; padding: 0; }\n"
            f"body {{ width: {width}px; padding: {mt}px {mr}px {mb}px {ml}px; }}\n"
            "</style>\n</head><body>\n"
            + "".join(body_parts)
            + "</body></html>\n"
        )

    def to_pdf(self) -> bytes:
        """Render to PDF via WeasyPrint. Requires: pip install weasyprint"""
        try:
            from weasyprint import HTML  # type: ignore
        except ImportError as e:
            raise ImportError("weasyprint is not installed: pip install weasyprint") from e
        return HTML(string=self.to_html()).write_pdf()

    # ------------------------------------------------------------------
    # Composed template export
    # ------------------------------------------------------------------

    def save_composed(self, path: str | Path) -> None:
        """Save the resolved template to a JSON file (rows merged, no composition key)."""
        out = {k: v for k, v in self.template.items() if k != "composition"}
        Path(path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
