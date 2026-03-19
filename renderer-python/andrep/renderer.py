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

        # Batch all phantom-pass rows into a single WeasyPrint render (faster).
        # Set to False to revert to one render per row (easier to debug).
        self.phantom_batch: bool = True

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
        self._pdf_mode: bool = False   # True while generating PDF HTML (disables writing-mode)

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
        embeds: dict = {}
        for row in rows:
            for cell in row.get("cells", []):
                if cell.get("type") == "embed":
                    target = cell.get("embedTarget", "")
                    if target and target in self.bands:
                        embeds[id(cell)] = self._compile_band(target, ns, "", {})
                    # embed cells carry no token values; cssExtra still applies
                else:
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
        if embeds:
            record["embeds"] = embeds
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

    def _border_parts(self, borders: dict) -> "list[str]":
        return [f"border-{s}:{self._border_css(borders, s)}" for s in ("top", "bottom", "left", "right")]

    def _cell_style(self, cell: dict, css_extra: str = "", band_css: str = "", actual_h: int = 0) -> str:
        s = cell.get("style", {})
        borders = s.get("borders", {})
        wrap = cell.get("wrap", True)
        auto_stretch = cell.get("autoStretch", False)
        h = cell.get("height", 24)

        # Rotation — applied to the cell container div.
        # For 90° / 270°: writing-mode changes the inline axis to vertical, so
        # flex-direction:row aligns items along the vertical (inline) direction.
        # justify-content then controls vertical positioning as expected, and
        # text-align handles horizontal centering within each item.
        # For 180°: simple transform; flex-direction stays column.
        rotation = cell.get("rotation", 0)

        # verticalAlignment → justify-content.
        # rotation=90 uses writing-mode:vertical-rl + rotate(180deg): the 180°
        # transform visually inverts the flex main axis, so top/bottom must be swapped.
        if rotation == 90:
            va_map = {"top": "flex-end", "middle": "center", "bottom": "flex-start"}
        else:
            va_map = {"top": "flex-start", "middle": "center", "bottom": "flex-end"}
        va = va_map.get(s.get("verticalAlignment", "top"), va_map["top"])

        # actual_h > 0: phantom pass measured the real height; fix all cells to it
        # so vertical borders align across every cell in the row (Step 5b).
        # Otherwise: autoStretch+wrap cells use min-height (can grow), fixed cells
        # use an explicit height (borders may mis-align in HTML — acceptable).
        if actual_h > 0:
            size_css = f"height:{actual_h}px"
            overflow = "overflow:hidden"
        elif wrap and auto_stretch:
            size_css = f"min-height:{h}px"
            overflow = ""
        elif rotation in (90, 270):
            size_css = f"min-height:{h}px"
            overflow = "overflow:hidden"
        else:
            size_css = f"height:{h}px"
            overflow = "overflow:hidden"
        if rotation == 90:
            flex_dir = "row"
            rotation_parts = ["writing-mode:vertical-rl", "transform:rotate(180deg)"]
        elif rotation == 270:
            flex_dir = "row"
            rotation_parts = ["writing-mode:vertical-lr"]
        elif rotation == 180:
            flex_dir = "column"
            rotation_parts = ["transform:rotate(180deg)"]
        else:
            flex_dir = "column"
            rotation_parts = []

        parts = [
            f"width:{cell.get('width', 100)}px",
            size_css,
            "flex-shrink:0",
            overflow,
            f"white-space:{'nowrap' if not wrap else 'normal'}",
            "display:flex",
            f"flex-direction:{flex_dir}",
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
            *self._border_parts(borders),
            "box-sizing:border-box",
        ]
        parts.extend(rotation_parts)
        if css_extra:
            parts.append(css_extra)
        if band_css:
            parts.append(band_css)
        return ";".join(p for p in parts if p)

    # ------------------------------------------------------------------
    # HTML rendering — uses compiled values + template for layout/formatters
    # ------------------------------------------------------------------

    def _row_height(self, row: dict) -> int:
        heights = []
        for c in row.get("cells", []):
            if c.get("type") == "embed":
                target = c.get("embedTarget", "")
                sub_rows = self.bands.get(target, [])
                h = sum(self._row_height(r) for r in sub_rows) if sub_rows else c.get("height", 24)
            else:
                h = c.get("height", 24)
            heights.append(h)
        return max(heights, default=24)

    def _needs_phantom(self, row: dict) -> bool:
        """Return True if the row requires phantom height measurement.

        Rows with embed cells or autoStretch+wrap cells can grow beyond the
        template height; WeasyPrint must render them to measure the actual height.
        """
        for cell in row.get("cells", []):
            if cell.get("type") == "embed":
                return True
            if cell.get("autoStretch", False) and cell.get("wrap", False):
                return True
        return False

    def _count_row_values(self, row: dict) -> int:
        """Return the number of values the values_iter will consume for one row.

        Embed cells consume no main values (they have their own sub-record).
        All other cells consume one value per expression token (expr is not None).
        Used to slice the values list for double-call phantom rows.
        """
        count = 0
        for cell in row.get("cells", []):
            if cell.get("type") == "embed":
                continue
            for _, expr, _ in self._cell_tokens.get(id(cell), []):
                if expr is not None:
                    count += 1
        return count

    def _phantom_doc(self, body_html: str, content_w: int) -> str:
        return (
            "<!DOCTYPE html><html><head>"
            '<meta charset="utf-8">'
            "<style>"
            "* { box-sizing: border-box; margin: 0; padding: 0; }"
            f"@page {{ size: {content_w}px 99999px; margin: 0; }}"
            f"body {{ width: {content_w}px; }}"
            "ul, ol { padding-left: 1.4em; }"
            "li { margin-bottom: 0.15em; }"
            "</style></head><body>"
            + body_html
            + "</body></html>"
        )

    def _measure_html_height(self, html: str, content_w: int) -> int:
        """Render one HTML row via WeasyPrint and return its actual pixel height.

        Used by the phantom pass to get real heights for rows that can grow
        beyond their template height (autoStretch+wrap or embed cells).
        """
        from weasyprint import HTML  # type: ignore
        fetcher = getattr(self, "_url_fetcher", None)
        doc = self._phantom_doc(html, content_w)
        document = HTML(string=doc, url_fetcher=fetcher).render()
        try:
            # Walk page_box → <html> box → <body> box; read shrink-wrapped height.
            body = document.pages[0]._page_box.children[0].children[0]
            return max(1, round(body.height))
        except (IndexError, AttributeError):
            return 24

    def _measure_html_heights_batch(self, html_list: "list[str]", content_w: int) -> "list[int]":
        """Render phantom rows and return their actual pixel heights.

        With phantom_batch=True (default): one WeasyPrint render for all rows.
        With phantom_batch=False: one render per row (slower, easier to debug).
        """
        if not html_list:
            return []
        if not self.phantom_batch:
            return [self._measure_html_height(h, content_w) for h in html_list]
        from weasyprint import HTML  # type: ignore
        fetcher = getattr(self, "_url_fetcher", None)
        wrapped = "".join(f"<div>{h}</div>" for h in html_list)
        doc = self._phantom_doc(wrapped, content_w)
        document = HTML(string=doc, url_fetcher=fetcher).render()
        try:
            body = document.pages[0]._page_box.children[0].children[0]
            return [max(1, round(child.height)) for child in body.children]
        except (IndexError, AttributeError):
            return [24] * len(html_list)

    # CSS flex alignment maps
    _ALIGN_ITEMS  = {"left": "flex-start", "center": "center", "right": "flex-end"}
    _JUSTIFY_CONT = {"top": "flex-start",  "middle": "center", "bottom": "flex-end"}

    def _cell_html(self, cell: dict, values_iter, css_extra: str = "", band_css: str = "",
                   embed_map: dict = None, row_height: int = 0, actual_h: int = 0) -> str:
        """Render one cell to HTML, consuming its token values from values_iter."""
        cell_type = cell.get("type", "text")

        if cell_type == "embed":
            sub_record = (embed_map or {}).get(id(cell), {})
            return self._embed_cell_html(cell, sub_record, css_extra, band_css)

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
            return self._graphic_cell_html(cell, svg, css_extra, band_css, actual_h)

        if cell_type == "image":
            tokens = self._cell_tokens[id(cell)]
            v = next(values_iter, None)
            # Apply formatters (img formatter returns a full <img> tag)
            for _, expr, fmts in tokens:
                if expr is not None and fmts:
                    for fmt in fmts:
                        v = _apply_formatter(v, fmt, r=self)
                break
            if isinstance(v, str) and (v.startswith("<img") or v.startswith("<svg")):
                return self._graphic_cell_html(cell, v, css_extra, band_css, actual_h)
            # No formatter or formatter returned a plain URL — legacy behaviour
            src  = str(v) if v is not None else ""
            auto = cell.get("autoStretch", False)
            if auto:
                img = f'<img src="{escape(src)}" style="width:100%;height:auto;display:block">'
            else:
                img = f'<img src="{escape(src)}" style="max-width:100%;max-height:100%;object-fit:contain;display:block">'
            return self._graphic_cell_html(cell, img, css_extra, band_css, actual_h)

        # ---- markdown -------------------------------------------------------
        if cell_type == "markdown":
            tokens = self._cell_tokens[id(cell)]
            parts = []
            for text, expr, fmts in tokens:
                if text:
                    parts.append(text)          # literal markdown — do NOT escape
                if expr is not None:
                    v = next(values_iter, None)
                    if fmts:
                        for fmt in fmts:
                            v = _apply_formatter(v, fmt, r=self)
                    parts.append(str(v) if v is not None else "")
            raw_md = "".join(parts)
            try:
                import markdown as _md
                html_content = _md.markdown(raw_md)
            except ImportError:
                html_content = escape(raw_md).replace("\n", "<br>")
            return f'<div style="{self._cell_style(cell, css_extra, band_css, actual_h)}">{html_content}</div>'

        # ---- text / embed ---------------------------------------------------
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
                elif isinstance(v, str) and v.startswith("<img"):
                    parts.append(v)
                else:
                    parts.append(escape(str(v) if v is not None else ""))
        content = "".join(
            p if (p.startswith("<svg") or p.startswith("<img")) else p.replace("\n", "<br>")
            for p in parts
        )
        if self._pdf_mode and cell.get("rotation", 0) in (90, 270):
            return self._rotated_pdf_cell_html(cell, content, css_extra, band_css, row_height, actual_h)
        return f'<div style="{self._cell_style(cell, css_extra, band_css, actual_h)}">{content}</div>'

    def _rotated_pdf_cell_html(self, cell: dict, content: str, css_extra: str, band_css: str,
                               row_height: int = 0, actual_h: int = 0) -> str:
        """Two-div structure for rotated text cells in PDF (WeasyPrint has no writing-mode).

        Outer div: min-height so flex align-items:stretch can grow it to match the row.
        Inner div: swapped dimensions (inner_h × cell_w), absolutely positioned and rotated
                   via transform:rotate so the text fills the outer box.
        inner_h priority: actual_h (phantom-measured) > row_height (estimated) > cell.height.
        """
        s = cell.get("style", {})
        borders = s.get("borders", {})
        rotation = cell.get("rotation", 0)
        cell_w = cell.get("width", 100)
        cell_h = cell.get("height", 24)
        if actual_h > 0:
            inner_h = actual_h
        else:
            inner_h = row_height if row_height > cell_h else cell_h

        if rotation == 90:
            va_map = {"top": "flex-end", "middle": "center", "bottom": "flex-start"}
            pos_css = f"top:{inner_h}px;left:0"
            rot_css = "transform:rotate(-90deg);transform-origin:0 0"
        else:  # 270
            va_map = {"top": "flex-start", "middle": "center", "bottom": "flex-end"}
            pos_css = f"top:0;left:{cell_w}px"
            rot_css = "transform:rotate(90deg);transform-origin:0 0"
        va = va_map.get(s.get("verticalAlignment", "top"), va_map["top"])

        outer_css = ";".join([
            f"width:{cell_w}px",
            f"min-height:{cell_h}px",
            "align-self:stretch",
            "flex-shrink:0",
            "overflow:hidden",
            "position:relative",
            f"background-color:{s.get('backgroundColor', '#ffffff')}",
            *self._border_parts(borders),
            "box-sizing:border-box",
        ])

        padding = (
            f"padding:{s.get('paddingTop', 2)}px "
            f"{s.get('paddingRight', 4)}px "
            f"{s.get('paddingBottom', 2)}px "
            f"{s.get('paddingLeft', 4)}px"
        )
        inner_parts = [
            "position:absolute",
            f"width:{inner_h}px",
            f"height:{cell_w}px",
            pos_css,
            rot_css,
            "display:flex",
            "flex-direction:column",
            f"justify-content:{va}",
            f"font-family:{s.get('fontFamily', 'Arial')},sans-serif",
            f"font-size:{s.get('fontSize', 11)}pt",
            f"font-weight:{s.get('fontWeight', 'normal')}",
            f"font-style:{s.get('fontStyle', 'normal')}",
            f"text-decoration:{s.get('textDecoration', 'none')}",
            f"color:{s.get('color', '#000000')}",
            f"text-align:{s.get('alignment', 'left')}",
            padding,
            "box-sizing:border-box",
        ]
        if css_extra:
            inner_parts.append(css_extra)
        if band_css:
            inner_parts.append(band_css)
        inner_css = ";".join(p for p in inner_parts if p)
        return f'<div style="{outer_css}"><div style="{inner_css}">{content}</div></div>'

    def _graphic_svg(self, cell: dict, value: str) -> str:
        """Generate a barcode/qrcode SVG for a dedicated graphic cell."""
        from .barcode import barcode_svg, qr_svg, _PYBARCODE_TYPES
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

    _OBJ_POS = {"top": "center top", "middle": "center center", "bottom": "center bottom"}

    def _graphic_cell_html(self, cell: dict, content_html: str, css_extra: str, band_css: str, actual_h: int = 0) -> str:
        """Wrap a graphic element (SVG, img) in a correctly aligned cell div.

        For graphic cells we override text-align with align-items on the flex
        container so the SVG/img is positioned horizontally per the cell's
        alignment setting.

        For contain/cover images the img fills height:100%, so flexbox
        justify-content has no effect on vertical positioning — we inject
        object-position instead.
        """
        s     = cell.get("style", {})
        align = s.get("alignment", "left")
        va    = s.get("verticalAlignment", "top")
        extra = f"align-items:{self._ALIGN_ITEMS.get(align, 'flex-start')}"
        if css_extra:
            extra = f"{css_extra};{extra}"
        # object-fit images fill height:100% — inject object-position for VA
        if "object-fit" in content_html:
            obj_pos = self._OBJ_POS.get(va, "center top")
            content_html = content_html.replace(
                "display:block", f"object-position:{obj_pos};display:block", 1
            )
        # SVG barcodes/QR: constrain to the cell bounds so they don't overflow.
        # In browsers, SVG flex items shrink automatically; WeasyPrint renders at
        # intrinsic size and clips — max-width/max-height prevent the clipping.
        if content_html.startswith("<svg"):
            content_html = content_html.replace(
                "<svg ", '<svg style="max-width:100%;max-height:100%;display:block" ', 1
            )
        return f'<div style="{self._cell_style(cell, extra, band_css, actual_h)}">{content_html}</div>'

    def _embed_cell_html(self, cell: dict, sub_record: dict, css_extra: str = "", band_css: str = "") -> str:
        """Render an embed cell by expanding its target band inside a container div.

        The container inherits borders and background from the embed cell's style
        but has no fixed height — it grows with the embedded content.
        In HTML the parent row's flex align-items:stretch ensures both embed
        containers reach the same height. Vertical borders on the containers
        therefore span the full row height without any pre-measurement.
        (In PDF, borders that must match variable-height rows require the phantom
        pass; that is deferred to the PDF renderer implementation.)
        """
        target = cell.get("embedTarget", "")
        rows = self.bands.get(target, [])
        s = cell.get("style", {})
        borders = s.get("borders", {})
        parts = [
            f"width:{cell.get('width', 100)}px",
            "flex-shrink:0",
            *self._border_parts(borders),
            f"background-color:{s.get('backgroundColor', 'transparent')}",
            "box-sizing:border-box",
            "overflow:hidden",
        ]
        if css_extra:
            parts.append(css_extra)
        if band_css:
            parts.append(band_css)
        style = ";".join(p for p in parts if p)

        if not rows:
            return f'<div style="{style}"></div>'

        sub_values_iter = iter(sub_record.get("values", []))
        sub_css_iter = iter(sub_record.get("css_extras", []))
        sub_band_css = sub_record.get("band_css", "")
        sub_embed_map = sub_record.get("embeds", {})

        inner = "".join(
            self._row_html(row, sub_values_iter, sub_css_iter, sub_band_css, sub_embed_map)
            for row in rows
        )
        return f'<div style="{style}">{inner}</div>'

    def _row_html(self, row: dict, values_iter, css_extras_iter, band_css: str = "", embed_map: dict = None, actual_h: int = 0) -> str:
        height = self._row_height(row)
        # Cells sorted by x — insert spacer divs for gaps between cells.
        # The editor guarantees no overlap, so gaps are always >= 0.
        sorted_cells = sorted(row.get("cells", []), key=lambda c: c.get("x", 0))
        parts: list[str] = []
        prev_end = 0
        for cell in sorted_cells:
            x = cell.get("x", 0)
            gap = x - prev_end
            if gap > 0:
                parts.append(f'<div style="width:{gap}px;flex-shrink:0"></div>')
            parts.append(
                self._cell_html(cell, values_iter, next(css_extras_iter, ""), band_css, embed_map,
                                row_height=height, actual_h=actual_h)
            )
            prev_end = x + cell.get("width", 100)
        h_css = f"height:{actual_h}px" if actual_h > 0 else f"min-height:{height}px"
        return (
            f'<div style="display:flex;{h_css};align-items:stretch">'
            + "".join(parts)
            + "</div>\n"
        )

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
                f'column-gap:{gap}px;align-items:flex-start" '
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
            embed_map = record.get("embeds", {})

            if col_w is not None:
                # wrap all rows of this emission in a single flex item
                inner = "".join(
                    self._row_html(row, values_iter, css_extras_iter, band_css, embed_map)
                    for row in rows
                )
                body_parts.append(
                    f'<div style="width:{col_w}px;overflow:hidden">{inner}</div>\n'
                )
            else:
                for row in rows:
                    body_parts.append(self._row_html(row, values_iter, css_extras_iter, band_css, embed_map))

        if in_flex:
            body_parts.append(_close_flex())

        return (
            "<!DOCTYPE html>\n<html><head>\n"
            '<meta charset="utf-8">\n'
            "<style>\n"
            "* { box-sizing: border-box; margin: 0; padding: 0; }\n"
            f"body {{ width: {width}px; padding: {mt}px {mr}px {mb}px {ml}px; }}\n"
            "ul, ol { padding-left: 1.4em; }\n"
            "li { margin-bottom: 0.15em; }\n"
            "</style>\n</head><body>\n"
            + "".join(body_parts)
            + "</body></html>\n"
        )

    def _records_to_items(
        self,
        records: "list[dict]",
        content_w: int,
        bands_cfg: dict,
    ) -> "list[tuple[str, int, int | None]]":
        """Convert compiled records to a flat list of (html, height, flex_gap|None).

        Single-column bands → one item per row.
        Multi-column bands  → one item per packed row-of-C-columns (height = max in group).
        Page-break markers  → ("__break__", 0, None).

        flex_gap = None  → normal row; no flex wrapper needed.
        flex_gap = int   → row is a horizontal group of multi-column items;
                           caller wraps consecutive same-gap items in a flex container.

        3-phase approach:
          Phase 1: collect phantom HTML for rows that need measurement.
          Phase 2: measure all phantom rows in one call (batch or per-row per phantom_batch).
          Phase 3: generate items using measured heights.
        """
        items: list[tuple[str, int, "int | None"]] = []
        multi_buf: list[tuple[str, int]] = []
        multi_columns = 0
        multi_gap     = 0
        multi_col_w   = 0

        def _flush() -> None:
            if not multi_buf:
                return
            for i in range(0, len(multi_buf), multi_columns):
                group = multi_buf[i: i + multi_columns]
                items.append(("".join(h for h, _ in group), max(h for _, h in group), multi_gap))
            multi_buf.clear()

        # ── Phase 1: pre-process records, collect phantom HTML ────────────────
        # rec_plan entries:
        #   ("break",)
        #   ("multi",  col_w, gap, columns, inner_html, h)
        #   ("single", band_css, embed_map, row_plans, keep_together)
        #     row_plan: (row, val_s, css_s, ph_idx)  ph_idx=None → no phantom needed
        rec_plan: list = []
        ph_html_list: list[str] = []

        for record in records:
            band_name = record["band"]

            if band_name == "__page_break__":
                rec_plan.append(("break",))
                continue

            rows = self.bands.get(band_name, [])
            if not rows:
                continue

            cfg      = bands_cfg.get(band_name, {})
            columns  = cfg.get("columns", 1)
            gap      = cfg.get("columnGap", 0)
            col_w    = int((content_w - (columns - 1) * gap) / columns) if columns > 1 else 0
            band_css  = record.get("band_css", "")
            embed_map = record.get("embeds", {})

            if columns > 1:
                values_iter     = iter(record.get("values",     []))
                css_extras_iter = iter(record.get("css_extras", []))
                inner = "".join(
                    self._row_html(row, values_iter, css_extras_iter, band_css, embed_map)
                    for row in rows
                )
                rec_plan.append(("multi", col_w, gap, columns, inner,
                                  sum(self._row_height(r) for r in rows)))
            else:
                values_list = record.get("values",     [])
                css_list    = record.get("css_extras", [])
                val_idx = css_idx = 0
                row_plans = []
                for row in rows:
                    n_vals = self._count_row_values(row)
                    n_css  = len(row.get("cells", []))
                    val_s  = values_list[val_idx: val_idx + n_vals]
                    css_s  = css_list   [css_idx: css_idx  + n_css]
                    ph_idx = None
                    if self._needs_phantom(row):
                        ph_html = self._row_html(
                            row, iter(val_s), iter(css_s), band_css, embed_map,
                        )
                        ph_idx = len(ph_html_list)
                        ph_html_list.append(ph_html)
                    row_plans.append((row, val_s, css_s, ph_idx))
                    val_idx += n_vals
                    css_idx += n_css
                keep_together = cfg.get("keepTogether", False)
                rec_plan.append(("single", band_css, embed_map, row_plans, keep_together))

        # ── Phase 2: measure all phantom rows (batch or per-row) ─────────────
        ph_heights = self._measure_html_heights_batch(ph_html_list, content_w)

        # ── Phase 3: generate items using measured heights ────────────────────
        for entry in rec_plan:
            kind = entry[0]

            if kind == "break":
                _flush()
                items.append(("__break__", 0, None))

            elif kind == "multi":
                _, col_w, gap, columns, inner, h = entry
                if columns != multi_columns or gap != multi_gap:
                    _flush()
                    multi_columns, multi_gap, multi_col_w = columns, gap, col_w
                multi_buf.append((
                    f'<div style="width:{multi_col_w}px;overflow:hidden">{inner}</div>\n', h,
                ))

            else:  # single
                _, band_css, embed_map, row_plans, keep_together = entry
                _flush()
                multi_columns = 0
                group_html = ""
                group_h    = 0
                for row, val_s, css_s, ph_idx in row_plans:
                    if ph_idx is not None:
                        actual_h = ph_heights[ph_idx]
                        html = self._row_html(
                            row, iter(val_s), iter(css_s), band_css, embed_map, actual_h,
                        )
                    else:
                        html     = self._row_html(
                            row, iter(val_s), iter(css_s), band_css, embed_map,
                        )
                        actual_h = self._row_height(row)
                    if keep_together:
                        group_html += html
                        group_h    += actual_h
                    else:
                        items.append((html, actual_h, None))
                if keep_together:
                    items.append((group_html, group_h, None))

        _flush()
        return items

    def _items_to_html(self, items: "list[tuple[str, int, int | None]]") -> str:
        """Assemble a flat items list to HTML, managing flex containers for multi-column."""
        parts: list[str] = []
        in_flex_gap: "int | None" = None

        for html, _h, tag in items:
            if tag is not None:
                if in_flex_gap != tag:
                    if in_flex_gap is not None:
                        parts.append("</div>\n")
                    parts.append(
                        f'<div style="display:flex;flex-wrap:wrap;'
                        f'column-gap:{tag}px;align-items:flex-start">\n'
                    )
                    in_flex_gap = tag
            else:
                if in_flex_gap is not None:
                    parts.append("</div>\n")
                    in_flex_gap = None
            parts.append(html)

        if in_flex_gap is not None:
            parts.append("</div>\n")
        return "".join(parts)

    def _render_page_hdr(self, is_first: bool, ns: dict, content_w: int) -> str:
        """Return the header HTML for one PDF page (first_header or page_header)."""
        if is_first and "first_header" in self.bands:
            name = "first_header"
        elif "page_header" in self.bands:
            name = "page_header"
        else:
            return ""
        return self._render_band_html(self._compile_band(name, ns, "", {}), content_w)

    def _render_page_ftr(self, is_last: bool, ns: dict, content_w: int) -> str:
        """Return the footer HTML for one PDF page (last_footer or page_footer)."""
        if is_last and "last_footer" in self.bands:
            name = "last_footer"
        elif "page_footer" in self.bands:
            name = "page_footer"
        else:
            return ""
        return self._render_band_html(self._compile_band(name, ns, "", {}), content_w)

    def _render_band_html(self, record: dict, content_w: int, actual_h: int = 0) -> str:
        """Render a compiled band record to HTML rows (for page headers/footers/filler).

        actual_h > 0: override cell heights (used for page_filler so borders
        extend the full fill height instead of just the template cell height).
        """
        band_name = record["band"]
        rows = self.bands.get(band_name, [])
        if not rows:
            return ""
        values_iter     = iter(record.get("values",     []))
        css_extras_iter = iter(record.get("css_extras", []))
        band_css        = record.get("band_css", "")
        embed_map       = record.get("embeds", {})
        return "".join(
            self._row_html(row, values_iter, css_extras_iter, band_css, embed_map, actual_h)
            for row in rows
        )

    def _to_pdf_html(self) -> str:
        """Generate paginated HTML for WeasyPrint.

        Strategy (no phantom pass):
          1. Pre-render all emission rows to (html, height, flex_gap|None).
             Single-column bands → one item per row.
             Multi-column bands  → one item per row-of-columns (packed group).
          2. Paginate items using template heights as estimates.
          3. Re-compile page_header / page_footer per page with correct _page.
          4. Assemble one fixed-size <div> per page; @page CSS sets size/margin=0.
        """
        self.compile()   # triggers on_after(); populates self._emissions

        page      = self.page
        pw        = page.get("width") or 794
        ph        = page.get("height") or 1123   # A4 portrait at 96 dpi; fallback for null/custom
        mt        = page.get("marginTop",     40)
        mb        = page.get("marginBottom",  40)
        ml        = page.get("marginLeft",    30)
        mr        = page.get("marginRight",   30)
        content_h = ph - mt - mb
        content_w = pw - ml - mr
        bands_cfg: dict = self.template.get("bands", {})

        # ── special-band heights ────────────────────────────────────────────
        def _band_h(name: str) -> int:
            return sum(self._row_height(r) for r in self.bands.get(name, []))

        has_filler = "page_filler" in self.bands

        first_hdr_h = _band_h("first_header")
        page_hdr_h  = _band_h("page_header")
        page_ftr_h  = _band_h("page_footer")
        last_ftr_h  = _band_h("last_footer")

        def _hdr_h(is_first: bool) -> int:
            if is_first and "first_header" in self.bands:
                return first_hdr_h
            return page_hdr_h if "page_header" in self.bands else 0

        # Reserve the larger footer height on every page so page_footer and
        # last_footer always start at the same y-position.
        max_ftr_h = max(page_ftr_h, last_ftr_h)

        def _avail(is_first: bool) -> int:
            return content_h - _hdr_h(is_first) - max_ftr_h

        # ── pre-render emissions → items ────────────────────────────────────
        items = self._records_to_items(self._emissions, content_w, bands_cfg)

        # ── paginate items into pages ────────────────────────────────────────
        pages: "list[list[tuple[str, int, int | None]]]" = []
        cur: "list[tuple[str, int, int | None]]" = []
        cur_h    = 0
        is_first = True
        avail    = _avail(is_first=True)

        for html, h, tag in items:
            if html == "__break__":
                pages.append(cur)
                cur, cur_h, is_first = [], 0, False
                avail = _avail(is_first=False)
                continue
            if cur_h + h > avail and cur:
                pages.append(cur)
                cur, cur_h, is_first = [], 0, False
                avail = _avail(is_first=False)
            cur.append((html, h, tag))
            cur_h += h

        pages.append(cur)
        total_pages = len(pages)

        # ── render each page ────────────────────────────────────────────────
        page_divs: list[str] = []

        for page_idx, page_items in enumerate(pages):
            page_num   = page_idx + 1
            is_first_p = page_idx == 0
            is_last_p  = page_idx == total_pages - 1

            # Build eval ns with the correct _page value for this page
            saved_page, self.cur_page = self.cur_page, page_num
            ns = self._sys_eval_ns()
            self.cur_page = saved_page

            hdr_html = self._render_page_hdr(is_first_p, ns, content_w)
            ftr_html = self._render_page_ftr(is_last_p,  ns, content_w)

            # Content
            content_html = self._items_to_html(page_items)

            # Page filler — spacer between content and footer.
            # Always reserve max_ftr_h at the bottom so page_footer and
            # last_footer start at the same y-position on every page.
            filler_html = ""
            if has_filler:
                used_h = sum(h for _, h, _ in page_items)
                space  = content_h - _hdr_h(is_first_p) - max_ftr_h - used_h
                if space > 0:
                    # Pass actual_h=space so filler cells extend the full height,
                    # keeping vertical border lines continuous.
                    filler_html = self._render_band_html(
                        self._compile_band("page_filler", ns, "", {}), content_w,
                        actual_h=space,
                    )

            pb = "" if is_last_p else "page-break-after:always;"
            page_divs.append(
                f'<div style="width:{pw}px;height:{ph}px;{pb}'
                f'padding:{mt}px {mr}px {mb}px {ml}px;box-sizing:border-box;overflow:hidden">\n'
                + hdr_html
                + content_html
                + filler_html
                + ftr_html
                + "</div>\n"
            )

        return (
            "<!DOCTYPE html>\n<html><head>\n"
            '<meta charset="utf-8">\n'
            "<style>\n"
            "* { box-sizing: border-box; margin: 0; padding: 0; }\n"
            f"@page {{ size: {pw}px {ph}px; margin: 0; }}\n"
            "body { margin: 0; padding: 0; }\n"
            "ul, ol { padding-left: 1.4em; }\n"
            "li { margin-bottom: 0.15em; }\n"
            "</style>\n</head><body>\n"
            + "".join(page_divs)
            + "</body></html>\n"
        )

    def _make_url_cache(self):
        """Return a url_fetcher that caches responses, shared across phantom and PDF renders.

        Avoids re-downloading the same HTTP image URLs during both the phantom
        pass and the final PDF render.  Compatible with WeasyPrint 68+ (URLFetcher API).
        """
        from weasyprint.urls import URLFetcher, URLFetcherResponse  # type: ignore
        _fetcher = URLFetcher()
        _cache: dict = {}  # url → (bytes, EmailMessage headers)

        def fetcher(url: str) -> "URLFetcherResponse":
            if url not in _cache:
                resp = _fetcher.fetch(url)
                _cache[url] = (resp.read(), resp.headers)
            data, headers = _cache[url]
            return URLFetcherResponse(url, body=data, headers=headers)

        return fetcher

    def to_pdf(self) -> bytes:
        """Render to PDF via WeasyPrint. Requires: pip install weasyprint"""
        try:
            from weasyprint import HTML  # type: ignore
        except ImportError as e:
            raise ImportError("weasyprint is not installed: pip install weasyprint") from e
        self._pdf_mode = True
        fetcher = self._make_url_cache()
        self._url_fetcher = fetcher
        try:
            html = self._to_pdf_html()
        finally:
            self._pdf_mode = False
            self._url_fetcher = None
        return HTML(string=html, url_fetcher=fetcher).write_pdf()

    # ------------------------------------------------------------------
    # Composed template export
    # ------------------------------------------------------------------renderer-python/sample/templates/test_img_md.json

    def save_composed(self, path: str | Path) -> None:
        """Save the resolved template to a JSON file (rows merged, no composition key)."""
        out = {k: v for k, v in self.template.items() if k != "composition"}
        Path(path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
