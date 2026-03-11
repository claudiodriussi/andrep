"""
renderer.py — AndRepRenderer class: emit / to_html / to_pdf / save_composed
"""
import json
import os
from datetime import datetime
from html import escape
from pathlib import Path

from .loader import FilesystemLoader, TemplateLoader
from .variables import resolve_content


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
        # loader-based path: template is a name string
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

        # Load the target template — loader takes priority over template_dir
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
            # Group ref rows by band name
            ref_bands: dict[str, list] = {}
            for row in ref_rows:
                ref_bands.setdefault(row["name"], []).append(row)

            # Insert ref rows before the first main row with the same band name
            new_rows = []
            inserted: set[str] = set()
            for row in main_rows:
                name = row["name"]
                if name in ref_bands and name not in inserted:
                    new_rows.extend(ref_bands[name])
                    inserted.add(name)
                new_rows.append(row)

            # Ref bands with no matching main band: prepend at the top
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
                    # skip original row
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

        class SellsReport(AndRepRenderer):
            def on_init(self):
                self.tot_amount = 0

            def on_after_band(self, band_name, data):
                if band_name == "band":
                    self.tot_amount += data["row"]["amount"]

        loader = FilesystemLoader(Path("templates/"))
        r = SellsReport("sells", loader=loader)
        for row in data:
            r.emit("band", {"row": row})
        r.emit("totals")
        html = r.to_html()
        pdf  = r.to_pdf()   # requires weasyprint
    """

    def __init__(self, template, template_dir=None, loader: TemplateLoader = None):
        self.template = load_template(template, template_dir, loader=loader)
        self.page = self.template.get("page", {})
        self._emissions: list[tuple[str, dict]] = []

        # State — readable in expressions via _r
        self.cur_band: str = ""    # band currently being emitted
        self.last_band: str = ""   # band emitted in the previous emit() call
        self.started: bool = False  # True after first emit()

        # System variables — override before first emit() if needed
        now = datetime.now()
        self.report_date: str = now.strftime("%d/%m/%Y")   # _date in expressions
        self.report_time: str = now.strftime("%H:%M:%S")   # _time in expressions
        self.report_user: str = os.environ.get("USER", os.environ.get("USERNAME", ""))  # _user
        self.report_name: str = self.template.get("name", "")  # _name (report title)
        self.cur_page: int = 1     # _page — incremented by PDF renderer; set manually to continue numbering across reports

        # Group rows by band name
        self.bands: dict[str, list] = {}
        for row in self.template.get("rows", []):
            self.bands.setdefault(row["name"], []).append(row)

        self.on_init()

    # ------------------------------------------------------------------
    # Emit
    # ------------------------------------------------------------------

    def emit(self, band_name: str, data: dict | None = None, silent: bool = False) -> None:
        """Record a band emission with the given data.

        Args:
            band_name: name of the band to emit.
            data:      context dict passed to cell expressions.
            silent:    if True, fire hooks without recording the emission
                       (useful for preparatory calculations / dry-runs).
        """
        data = dict(data) if data else {}
        if not self.started:
            self.started = True
            self.on_before()
        self.on_before_band(band_name, data)   # data is mutable — add variables here
        if not silent:
            self._emissions.append((band_name, data))
        self.on_after_band(band_name, data)    # accumulate totals here
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

    def on_before_band(self, band_name: str, data: dict) -> None:
        """Called before each emit(). data is mutable — inject extra variables here."""
        pass

    def on_after_band(self, band_name: str, data: dict) -> None:
        """Called after each emit(). Accumulate totals here."""
        pass

    def on_after(self) -> None:
        """Called at the start of to_html() / to_pdf(), after all emits."""
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
        """Insert an explicit page break. PDF only; no-op in HTML output."""
        self._emissions.append(("__page_break__", {}))

    # ------------------------------------------------------------------
    # System context
    # ------------------------------------------------------------------

    def _sys_ctx(self) -> dict:
        return {
            "_date": self.report_date,
            "_time": self.report_time,
            "_user": self.report_user,
            "_name": self.report_name,
            "_page": self.cur_page,
        }

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
    # HTML rendering
    # ------------------------------------------------------------------

    def _render_cell(self, cell: dict, ctx: dict) -> str:
        content = resolve_content(cell.get("content", ""), ctx)
        content = escape(content).replace("\n", "<br>")
        style = self._cell_style(cell)
        return f'<div style="{style}">{content}</div>'

    def _row_height(self, row: dict) -> int:
        return max((c.get("height", 24) for c in row.get("cells", [])), default=24)

    def _render_row(self, row: dict, ctx: dict) -> str:
        height = self._row_height(row)
        cells = "".join(self._render_cell(c, ctx) for c in row.get("cells", []))
        return f'<div style="position:relative;height:{height}px">{cells}</div>\n'

    def _render_band(self, band_name: str, ctx: dict) -> str:
        rows = self.bands.get(band_name, [])
        if not rows:
            return f"<!-- band '{band_name}' not found -->\n"
        return "".join(self._render_row(row, ctx) for row in rows)

    def to_html(self) -> str:
        """Render all recorded emissions to a complete HTML document."""
        page = self.page
        width = page.get("width", 794)
        mt = page.get("marginTop", 40)
        mb = page.get("marginBottom", 40)
        ml = page.get("marginLeft", 30)
        mr = page.get("marginRight", 30)

        self.on_after()
        sys_ctx = self._sys_ctx()
        body_parts: list[str] = []

        for band_name, data in self._emissions:
            ctx = {**sys_ctx, **data}
            body_parts.append(self._render_band(band_name, ctx))

        body = "".join(body_parts)

        return (
            "<!DOCTYPE html>\n"
            "<html><head>\n"
            '<meta charset="utf-8">\n'
            "<style>\n"
            "* { box-sizing: border-box; margin: 0; padding: 0; }\n"
            f"body {{ width: {width}px; padding: {mt}px {mr}px {mb}px {ml}px; }}\n"
            "</style>\n"
            "</head><body>\n"
            f"{body}"
            "</body></html>\n"
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
        """Save the resolved template to a JSON file.

        The output is a valid andrep-template with rows in their final order.
        The 'composition' key is omitted — it has already been applied.
        """
        out = {k: v for k, v in self.template.items() if k != "composition"}
        Path(path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Debug / serialization
    # ------------------------------------------------------------------

    def to_json(self) -> str:
        """Return rendered emissions as JSON. Useful for debugging and tests."""
        sys_ctx = self._sys_ctx()
        result = []
        for band_name, data in self._emissions:
            ctx = {**sys_ctx, **data}
            rows = self.bands.get(band_name, [])
            rendered_rows = []
            for row in rows:
                rendered_cells = []
                for cell in row.get("cells", []):
                    rendered_cells.append({
                        "id": cell.get("id"),
                        "content": resolve_content(cell.get("content", ""), ctx),
                    })
                rendered_rows.append(rendered_cells)
            result.append({"band": band_name, "rows": rendered_rows})
        return json.dumps(result, ensure_ascii=False, indent=2)
