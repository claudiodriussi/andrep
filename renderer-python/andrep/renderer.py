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


# ---------------------------------------------------------------------------
# Built-in CSS helper functions — available in cssExtra @expressions
# ---------------------------------------------------------------------------

def _css_highlight(val, lo, hi, css="background:#fff3cd;font-weight:bold"):
    """Return css if lo <= val <= hi, else ''."""
    try:
        return css if float(lo) <= float(val) <= float(hi) else ""
    except (TypeError, ValueError):
        return ""


def _css_threshold(val, t, css_over="", css_under=""):
    """Return css_over if val > t, css_under if val < t, else ''."""
    try:
        v = float(val)
        if v > float(t):
            return css_over
        if v < float(t):
            return css_under
        return ""
    except (TypeError, ValueError):
        return ""


def _css_striped(n, css="background:#f0f4f8"):
    """Return css if n is odd — use with _r.count for zebra striping."""
    try:
        return css if int(n) % 2 == 1 else ""
    except (TypeError, ValueError):
        return ""


_BUILTIN_CSS = {
    "highlight": _css_highlight,
    "threshold": _css_threshold,
    "striped": _css_striped,
}


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

        # Per-renderer custom formatters — checked before built-ins
        # r.formatters["indent"] = lambda v, fmt, r: "\u00a0" * 4 * int(v)
        # template: [row.level | indent]
        self.formatters: dict = {}

        # Base directory for the load formatter — resolves @relative/path refs
        # r.base_dir = Path(__file__).parent / "data"
        self.base_dir = None

        # Explicit workspace: r["key"] = value  →  [key.field] in template
        self._ctx: dict = {}

        # f_locals captured at the last emit() call — readable in event handlers
        # as self.data.varname  (same notation as template expressions)
        self.data: types.SimpleNamespace | None = None

        # Per-emission style overrides — set via patch_band() / patch() in on_before_band()
        # Captured at emit() time and reset automatically after each emission.
        self._band_css: str = ""  # CSS applied to ALL cells in the band
        self._cell_patches: dict = {}  # {content_match: css_string}

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
            "_r": self,  # live reference — safe because eval is immediate (before on_after_band)
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
        # built-in CSS helpers + registered globals — override locals
        ns.update(_BUILTIN_CSS)
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
        ns.update(_BUILTIN_CSS)
        ns.update(self.globals)
        ns.update(self._sys_vars())
        ns["__builtins__"] = {}
        return ns

    def _compile_band(self, band_name: str, ns: dict, band_css: str, cell_patches: dict) -> dict:
        """Evaluate all cell expressions for one band. Returns a compiled record."""
        rows = self.bands.get(band_name, [])
        values = []
        css_extras = []
        for row in rows:
            for cell in row.get("cells", []):
                for _, expr, _ in self._cell_tokens[id(cell)]:
                    if expr is not None:
                        values.append(eval_expr(expr, ns))
                raw = cell.get("cssExtra", "")
                if raw.startswith("@"):
                    res = eval_expr(raw[1:], ns)
                    cell_css = str(res) if res else ""
                else:
                    cell_css = raw
                content = cell.get("content", "")
                for match, patch_css in cell_patches.items():
                    if match in content:
                        cell_css = f"{cell_css};{patch_css}".strip(";") if cell_css else patch_css
                css_extras.append(cell_css)
        record: dict = {"band": band_name}
        if values:
            record["values"] = values
        if band_css or any(css_extras):
            record["css_extras"] = css_extras
            record["band_css"] = band_css
        return record

    # ------------------------------------------------------------------
    # Emit
    # ------------------------------------------------------------------

    def emit(self, band_name: str, silent: bool = False) -> None:
        """Compile and record a band emission.

        The caller's local variables are captured automatically and made
        available in template expressions.  Name your loop variable to match
        the template: ``for row in data: r.emit("band")`` → ``[row.price]``.

        Args:
            band_name: name of the band to emit.
            silent:    fire hooks without recording the emission (summary mode).
        """
        frame = sys._getframe(1)

        if not self.started:
            self.started = True
            self.on_before()

        # Snapshot f_locals for event handlers (self.data.row.price)
        self.data = types.SimpleNamespace(
            **{k: _to_ns(v) for k, v in frame.f_locals.items()}
        )

        self.on_before_band(band_name)   # hook may modify self._ctx / call patch_band / patch

        # Build eval namespace AFTER on_before_band so _ctx changes are included.
        # _r is a live reference — safe because eval happens here, before on_after_band resets.
        if not silent:
            ns = self._build_eval_ns(frame)
            self._emissions.append(
                self._compile_band(band_name, ns, self._band_css, dict(self._cell_patches))
            )

        # Reset per-emission overrides
        self._band_css = ""
        self._cell_patches = {}

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
        self._emissions.append({"band": "__page_break__"})

    def patch_band(self, cssExtra: str = "") -> None:
        """Apply CSS to ALL cells of the current band emission.

        Call from on_before_band().  Reset automatically after each emit().
        Example: self.patch_band(cssExtra="background:#f0f4f8")
        """
        self._band_css = cssExtra

    def patch(self, content_match: str, cssExtra: str = "") -> None:
        """Apply CSS to cells whose content contains content_match.

        Call from on_before_band().  Reset automatically after each emit().
        Example: self.patch("[row.price", cssExtra="color:red;font-weight:bold")
        """
        self._cell_patches[content_match] = cssExtra

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

    # ------------------------------------------------------------------
    # Compile — assemble header + emissions + footer
    # ------------------------------------------------------------------

    def compile(self) -> None:
        """Assemble the final output: auto header + emissions + auto footer.

        Called automatically by to_html(), to_pdf(), to_json(), save_output().
        Safe to call multiple times — runs only once.
        Band expressions were already evaluated at emit() time.
        """
        if self._compiled is not None:
            return

        self.on_after()
        sys_ns = self._sys_eval_ns()
        result = []

        header = self._header_band_name()
        if header:
            result.append(self._compile_band(header, sys_ns, "", {}))

        result.extend(self._emissions)

        footer = self._footer_band_name()
        if footer:
            result.append(self._compile_band(footer, sys_ns, "", {}))

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

    def _cell_style(self, cell: dict, css_extra: str = "", band_css: str = "") -> str:
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
            f"white-space:{'nowrap' if not cell.get('wrap', True) else 'normal'}",
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
        # css_extra and band_css appended last — override base properties
        if css_extra:
            parts.append(css_extra)
        if band_css:
            parts.append(band_css)
        return ";".join(parts)

    # ------------------------------------------------------------------
    # HTML rendering — uses compiled values + template for layout/formatters
    # ------------------------------------------------------------------

    def _row_height(self, row: dict) -> int:
        return max((c.get("height", 24) for c in row.get("cells", [])), default=24)

    # CSS flex alignment maps
    _ALIGN_ITEMS  = {"left": "flex-start", "center": "center", "right": "flex-end"}
    _JUSTIFY_CONT = {"top": "flex-start",  "middle": "center", "bottom": "flex-end"}

    def _cell_html(self, cell: dict, values_iter, css_extra: str = "", band_css: str = "") -> str:
        """Render one cell to HTML, consuming its token values from values_iter."""
        cell_type = cell.get("type", "text")

        if cell_type in ("barcode", "qrcode"):
            tokens = self._cell_tokens[id(cell)]
            svg = None
            for _, expr, fmts in tokens:
                if expr is not None:
                    v = next(values_iter, None)
                    if fmts:
                        for fmt in fmts:
                            v = _apply_formatter(v, fmt, r=self)
                    if isinstance(v, str) and v.startswith("<svg"):
                        svg = v   # formatter produced an SVG — use it directly
                    else:
                        # No barcode formatter → use cell properties
                        svg = self._graphic_svg(cell, str(v) if v is not None else "")
                    break  # barcode cells have exactly one expression token
            if svg is None:
                svg = self._graphic_svg(cell, "")
            return self._graphic_cell_html(cell, svg, css_extra, band_css)

        if cell_type == "image":
            v = next(values_iter, None)
            src = str(v) if v is not None else ""
            auto = cell.get("autoStretch", False)
            if auto:
                img = f'<img src="{escape(src)}" style="width:100%;height:auto;display:block">'
            else:
                img = f'<img src="{escape(src)}" style="max-width:100%;max-height:100%;object-fit:contain;display:block">'
            return self._graphic_cell_html(cell, img, css_extra, band_css)

        # ---- text / markdown / embed ----------------------------------------
        tokens = self._cell_tokens[id(cell)]
        parts = []
        for text, expr, fmts in tokens:
            if text:
                parts.append(escape(text))
            if expr is not None:
                v = next(values_iter, None)
                if fmts:
                    for fmt in fmts:
                        v = _apply_formatter(v, fmt, r=self)
                # Inline barcode: formatter returned an SVG string
                if isinstance(v, str) and v.startswith("<svg"):
                    # SVGs from new barcode.py are already in pixels; if not (legacy),
                    # fall back to embedding with block display.
                    if 'mm"' not in v[:300]:
                        v = v.replace("<svg ", '<svg style="display:block" ', 1)
                    parts.append(v)
                else:
                    parts.append(escape(str(v) if v is not None else ""))
        content = "".join(
            p if p.startswith("<svg") else p.replace("\n", "<br>")
            for p in parts
        )
        return f'<div style="{self._cell_style(cell, css_extra, band_css)}">{content}</div>'

    def _graphic_svg(self, cell: dict, value: str) -> str:
        """Generate a barcode/qrcode SVG for a dedicated graphic cell."""
        from .barcode import barcode_svg, qr_svg, _PYBARCODE_TYPES, _error_svg
        w         = cell.get("width",     100)
        h         = cell.get("height",     50)
        bc_type   = cell.get("barcodeType", "ean13")
        show_text = cell.get("showText",   True)
        font_size = cell.get("fontSize",   4)
        cell_type = cell.get("type", "barcode")
        # Empty / None value → blank placeholder (not an error)
        if not value or value == "None":
            return f'<svg width="{w}" height="{h}"></svg>'

        if cell_type == "qrcode" or bc_type == "qr":
            return qr_svg(value, w, h)
        if bc_type in _PYBARCODE_TYPES:
            return barcode_svg(bc_type, value, w, h, show_text, font_size)
        return (
            f'<svg width="{w}" height="{h}">'
            f'<text x="2" y="14" font-size="9" fill="red">unknown: {bc_type}</text>'
            f'</svg>'
        )

    def _graphic_cell_html(self, cell: dict, content_html: str, css_extra: str, band_css: str) -> str:
        """Wrap a graphic element (SVG, img) in a correctly aligned cell div.

        For graphic cells we override text-align with align-items on the flex
        container so the SVG/img is positioned horizontally per the cell's
        alignment setting.
        """
        s     = cell.get("style", {})
        align = s.get("alignment", "left")
        extra = f"align-items:{self._ALIGN_ITEMS.get(align, 'flex-start')}"
        if css_extra:
            extra = f"{css_extra};{extra}"
        return f'<div style="{self._cell_style(cell, extra, band_css)}">{content_html}</div>'

    def _row_html(self, row: dict, values_iter, css_extras_iter, band_css: str = "") -> str:
        height = self._row_height(row)
        cells = "".join(
            self._cell_html(c, values_iter, next(css_extras_iter, ""), band_css)
            for c in row.get("cells", [])
        )
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
        content_width = width - ml - mr
        bands_cfg: dict = self.template.get("bands", {})

        body_parts: list[str] = []
        in_flex = False  # True while inside a multi-column flex container

        def _open_flex(columns: int, gap: int) -> str:
            col_w = int((content_width - (columns - 1) * gap) / columns)
            return (
                f'<div style="display:flex;flex-wrap:wrap;'
                f'gap:{gap}px;align-items:flex-start" '
                f'data-col-width="{col_w}">\n'
            )

        def _close_flex() -> str:
            return '</div>\n'

        for record in self._compiled:
            band_name = record["band"]

            if band_name == "__page_break__":
                if in_flex:
                    body_parts.append(_close_flex())
                    in_flex = False
                body_parts.append('<div style="page-break-after:always;height:0"></div>\n')
                continue

            rows = self.bands.get(band_name, [])
            if not rows:
                body_parts.append(f"<!-- band '{band_name}' not found -->\n")
                continue

            cfg = bands_cfg.get(band_name, {})
            columns = cfg.get("columns", 1)
            gap = cfg.get("columnGap", 0)
            col_w = int((content_width - (columns - 1) * gap) / columns) if columns > 1 else None

            if columns > 1 and not in_flex:
                body_parts.append(_open_flex(columns, gap))
                in_flex = True
            elif columns <= 1 and in_flex:
                body_parts.append(_close_flex())
                in_flex = False

            values_iter = iter(record.get("values", []))
            css_extras_iter = iter(record.get("css_extras", []))
            band_css = record.get("band_css", "")

            if col_w is not None:
                # wrap all rows of this emission in a single flex item
                inner = "".join(
                    self._row_html(row, values_iter, css_extras_iter, band_css)
                    for row in rows
                )
                body_parts.append(
                    f'<div style="position:relative;width:{col_w}px;overflow:hidden">{inner}</div>\n'
                )
            else:
                for row in rows:
                    body_parts.append(self._row_html(row, values_iter, css_extras_iter, band_css))

        if in_flex:
            body_parts.append(_close_flex())

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
