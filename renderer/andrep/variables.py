"""
variables.py — [expr|formatter] parser and expression evaluation for AndRep.

Public API:
    resolve_content(content, ns) -> str   — full resolve (parse + eval + format)
    _parse_tokens(content)        -> list  — parse once, reuse across many evals
    eval_expr(expr, ns)           -> any   — evaluate a single expression
    _apply_formatter(value, fmt, r=None) -> any  — apply one formatter to a value

The `ns` parameter is a pre-built eval namespace dict (already contains
``__builtins__: {}``).  Build it once per emit() call and reuse for all cells
in that band — never rebuild per cell.

The optional `r` parameter is the AndRepRenderer instance.  It is used by
context-aware built-in formatters (e.g. ``load``) and by the per-renderer
formatter registry ``r.formatters``.  Pass ``r=self`` from ``_cell_html``.
"""
import re
import types
from datetime import date, datetime


def _to_ns(data):
    """Recursively convert dict / dict-like / list to SimpleNamespace for
    attribute access in template expressions.

    - dict           → SimpleNamespace (recursive)
    - dict-like      → SimpleNamespace (objects with .keys() + [key], e.g. sqlite3.Row)
    - list           → list of converted items
    - anything else  → returned as-is (SQLAlchemy Row, Odoo record, int, str, …)
    """
    if isinstance(data, dict):
        ns = types.SimpleNamespace()
        for k, v in data.items():
            setattr(ns, k, _to_ns(v))
        return ns
    elif isinstance(data, list):
        return [_to_ns(i) for i in data]
    elif (
        not isinstance(data, (str, bytes, int, float, bool, type(None), type))
        and hasattr(data, "keys")
        and hasattr(data, "__getitem__")
    ):
        # dict-like: sqlite3.Row, collections.OrderedDict subclasses, etc.
        try:
            ns = types.SimpleNamespace()
            for k in data.keys():
                setattr(ns, k, _to_ns(data[k]))
            return ns
        except Exception:
            pass
    return data


def eval_expr(expr, ns):
    """Evaluate *expr* in the pre-built namespace *ns*.

    *ns* must already contain ``"__builtins__": {}`` to restrict access.
    Returns the computed value or the literal string ``'[#expr#]'`` on error.
    """
    try:
        return eval(expr, ns)  # noqa: S307
    except ZeroDivisionError:
        return 0
    except Exception:
        return f"[#{expr}#]"


def _fmt_load(value, params, r):
    """Built-in ``load`` formatter — resolves ``@ref`` references.

    If *value* starts with ``@`` it is treated as a reference:
      - ``@https://...`` / ``@http://...``  — HTTP fetch
      - ``@/abs/path``  or  ``@rel/path``   — local filesystem
        Relative paths are resolved against ``r.base_dir`` when set,
        otherwise against ``Path.cwd()``.

    If *value* does not start with ``@`` it is returned unchanged (inline).

    Parameters (comma-separated after ``load``):
      ``base64``   — return a ``data:mime;base64,...`` string instead of text
      ``silent``   — return ``""`` on any error (default: ``"[#ref#]"``)
      encoding     — text encoding for local files, default ``utf-8``
    """
    import base64 as _b64
    import mimetypes
    import urllib.request
    from pathlib import Path

    if value is None:
        return ""
    val = str(value)
    if not val.startswith("@"):
        return val                          # inline value — pass through unchanged

    ref     = val[1:]
    silent  = "silent"  in params
    binary  = "base64"  in params
    enc     = next(
        (p for p in params if p not in ("silent", "base64") and p),
        "utf-8",
    )

    try:
        if ref.startswith(("http://", "https://")):
            with urllib.request.urlopen(ref) as resp:
                data = resp.read()
                if binary:
                    mime = resp.headers.get_content_type() or "application/octet-stream"
                    return f"data:{mime};base64,{_b64.b64encode(data).decode()}"
                return data.decode(enc)
        else:
            base_dir = getattr(r, "base_dir", None) or Path.cwd()
            p = Path(ref)
            if not p.is_absolute():
                p = Path(base_dir) / p
            p = p.resolve()
            if binary:
                data = p.read_bytes()
                mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
                return f"data:{mime};base64,{_b64.b64encode(data).decode()}"
            return p.read_text(encoding=enc)
    except Exception:
        return "" if silent else f"[#{ref}#]"


def _fmt_img(value, params, r=None):
    """Built-in ``img`` formatter — renders an HTML ``<img>`` element.

    Syntax: ``img[,contain|cover|natural]``

    Parameters:
      *(none)*   — ``width:100%; height:auto`` — proportional fill-width,
                   height adapts to aspect ratio. Best with ``autoStretch=true``.
      ``contain`` — ``object-fit:contain`` — full image visible, may leave
                   empty margins. Best with ``autoStretch=false``.
      ``cover``   — ``object-fit:cover`` — fills cell box, clips excess edges.
      ``natural`` — ``max-width/max-height:100%`` — no upscaling; image stays
                   at its natural size, clipped if larger than cell.

    ``@ref`` paths and absolute file paths are resolved automatically:
    local files become ``data:mime;base64,...`` URLs; internet URLs and
    existing data URLs are used as-is.  No need to chain ``load,base64``
    explicitly.  Use ``silent`` to suppress errors for missing files::

        [row.image | img,cover]
        ["@data/logo.png" | img,natural,silent]
        [row.image | img,contain,silent]

    PDF note: WeasyPrint does not support gradient fills on SVG text elements.
    Use solid colours in SVG files intended for PDF output.
    """
    from html import escape as _esc
    from pathlib import Path

    if not value:
        return ""
    src = str(value)

    # Resolve local file references to base64 data URLs
    _load_params = {"base64"}
    if "silent" in params:
        _load_params.add("silent")
    if src.startswith("@"):
        src = _fmt_load(src, _load_params, r)
    elif not src.startswith(("http://", "https://", "data:")):
        # Bare absolute path (e.g. /home/user/img/photo.png)
        p = Path(src)
        if p.is_absolute():
            src = _fmt_load(f"@{src}", _load_params, r)

    mode = next((p for p in params if p in ("contain", "cover", "natural")), None)

    if mode == "cover":
        style = "width:100%;height:100%;object-fit:cover;display:block"
    elif mode == "contain":
        style = "width:100%;height:100%;object-fit:contain;display:block"
    elif mode == "natural":
        style = "max-width:100%;max-height:100%;display:block"
    else:
        style = "width:100%;height:auto;display:block"

    return f'<img src="{_esc(src)}" style="{style}">'


def _apply_formatter(value, fmt, r=None):
    """Apply a single formatter to a value.

    Args:
        value: the value to transform.
        fmt:   formatter string, e.g. ``"upper"``, ``".2"``, ``"load,silent"``.
        r:     optional AndRepRenderer instance — required by context-aware
               formatters (``load``) and checked against ``r.formatters`` for
               per-renderer custom formatters.
    """
    fmt = fmt.strip()
    if not fmt:
        return value

    # ---- per-renderer custom formatters (r.formatters registry) --------
    name = fmt.split(",")[0].strip()
    if r is not None:
        custom = getattr(r, "formatters", {}).get(name)
        if custom is not None:
            return custom(value, fmt, r)

    if fmt == "upper":
        return str(value).upper() if value is not None else ""
    if fmt == "lower":
        return str(value).lower() if value is not None else ""
    if fmt == "trim":
        return str(value).strip() if value is not None else ""
    if fmt == "space":
        if value is None or value == "" or value == 0:
            return ""
        return str(value)
    if fmt == "zeros":
        if value is None or value == "":
            return "0"
        return str(value)
    if fmt == "date":
        if isinstance(value, (date, datetime)):
            return value.strftime("%d/%m/%Y")
        return str(value) if value is not None else ""
    if fmt == "currency":
        try:
            v = float(value)
            # € 1.234,56  (Italian format)
            formatted = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"€ {formatted}"
        except (TypeError, ValueError):
            return str(value)

    # Explicit date format: contains d/m/y (e.g. dd/mm/yyyy)
    if re.match(r"^[dDmMyY/\-\s]+$", fmt) and any(c in fmt.lower() for c in "dmy"):
        if isinstance(value, (date, datetime)):
            py_fmt = (
                fmt.replace("dd", "%d")
                .replace("mm", "%m")
                .replace("yyyy", "%Y")
                .replace("yy", "%y")
            )
            try:
                return value.strftime(py_fmt)
            except Exception:
                pass
        return str(value) if value is not None else ""

    # Numeric format with optional sign: +.2  .2  10.2  10
    sign = ""
    rest = fmt
    if rest.startswith("+"):
        sign = "+"
        rest = rest[1:]

    m = re.match(r"^(\d*)\.(\d+)$", rest)
    if m:
        width_str, dec_str = m.groups()
        decimals = int(dec_str)
        width = int(width_str) if width_str else 0
        try:
            v = float(value)
            formatted = f"{v:{sign},.{decimals}f}"
            # Italian separators
            formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
            if width:
                formatted = formatted.rjust(width)
            return formatted
        except (TypeError, ValueError):
            return str(value)

    # Digits only: N fixed decimals without thousands separator
    if re.match(r"^\d+$", fmt):
        decimals = int(fmt)
        try:
            v = float(value)
            return f"{v:{sign}.{decimals}f}"
        except (TypeError, ValueError):
            return str(value)

    # ---- load formatter ------------------------------------------------
    if name == "load":
        params = {p.strip() for p in fmt.split(",")[1:]}
        return _fmt_load(value, params, r)

    # ---- img formatter — returns <img ...> string; renderer embeds raw --
    if name == "img":
        params = [p.strip() for p in fmt.split(",")[1:]]
        return _fmt_img(value, params, r)

    # Barcode formatters — return an SVG string; renderer detects <svg and embeds raw.
    #
    # Syntax: name[,w[,h[,show[,font_size]]]]
    #   All numeric params are pixels.
    #
    #   ean13                → EAN-13, renderer uses cell dimensions
    #   ean13,200            → 200 px wide, height proportional
    #   ean13,200,52         → 200×52 px
    #   ean13,200,52,0       → 200×52 px, bars only (no text)
    #   ean13,200,52,0,4     → 200×52 px, no text, font 4 pt
    #   code128,200,52       → Code-128 200×52 px
    #   qr                   → QR code, renderer uses cell dimensions
    #   qr,100               → QR code 100×100 px
    m_bc = re.match(r"^([\w\-]+)(?:,(\d+)(?:,(\d+)(?:,(0|1)(?:,(\d+))?)?)?)?$", fmt)
    if m_bc:
        name, p1, p2, p3, p4 = m_bc.groups()
        from .barcode import _PYBARCODE_TYPES, barcode_svg, qr_svg  # lazy import
        w         = int(p1) if p1 else 0
        h         = int(p2) if p2 else 0
        show_text = (p3 != "0") if p3 is not None else True
        font_size = int(p4) if p4 else 4
        code      = str(value) if value is not None else ""
        if name == "qr":
            return qr_svg(code, w, h)
        if name in _PYBARCODE_TYPES:
            return barcode_svg(name, code, w, h, show_text, font_size)

    return str(value) if value is not None else ""


def _split_token(token):
    """Split token content into (expr, [formatter, ...]).

    Rules:
    1. If it contains \\| → explicit separator (everything before = expr)
    2. Otherwise: first single | (not part of ||) is the separator
    """
    # Step 1: look for explicit separator \|
    if "\\" + "|" in token:
        idx = token.index("\\" + "|")
        expr = token[:idx]
        rest = token[idx + 2:]
        formatters = [f.strip() for f in rest.split("|") if f.strip()]
        return expr.strip(), formatters

    # Step 2: first single | (not part of ||)
    i = 0
    while i < len(token):
        if token[i] == "|":
            prev_pipe = i > 0 and token[i - 1] == "|"
            next_pipe = i + 1 < len(token) and token[i + 1] == "|"
            if not prev_pipe and not next_pipe:
                expr = token[:i].strip()
                rest = token[i + 1:]
                formatters = [f.strip() for f in rest.split("|") if f.strip()]
                return expr, formatters
        i += 1

    return token.strip(), []


def _parse_tokens(content):
    """Parse a content string into a list of (literal_text, expr, formatters).

    - (text, None, None) → literal text token
    - ('', expr, [fmt, ...]) → variable token
    """
    result = []
    i = 0
    current_text = []

    while i < len(content):
        if content[i] == "[":
            # Find matching ] (handles nesting)
            depth = 1
            j = i + 1
            while j < len(content) and depth > 0:
                if content[j] == "[":
                    depth += 1
                elif content[j] == "]":
                    depth -= 1
                j += 1

            if depth == 0:
                if current_text:
                    result.append(("".join(current_text), None, None))
                    current_text = []
                token = content[i + 1: j - 1]
                expr, formatters = _split_token(token)
                result.append(("", expr, formatters))
                i = j
            else:
                # Unclosed bracket → treat as literal
                current_text.append(content[i])
                i += 1
        else:
            current_text.append(content[i])
            i += 1

    if current_text:
        result.append(("".join(current_text), None, None))

    return result


def resolve_content(content, ns, r=None):
    """Resolve all [var|formatter] tokens in *content* using namespace *ns*.
    Returns the string with all tokens substituted.

    Pass ``r`` (the renderer instance) to enable context-aware formatters
    such as ``load`` and per-renderer ``r.formatters``.
    """
    if not content or "[" not in content:
        return content

    tokens = _parse_tokens(content)
    parts = []

    for text, expr, formatters in tokens:
        if expr is None:
            parts.append(text)
        else:
            value = eval_expr(expr, ns)
            if formatters:
                for fmt in formatters:
                    value = _apply_formatter(value, fmt, r=r)
                parts.append(str(value) if value is not None else "")
            else:
                parts.append("" if value is None else str(value))

    return "".join(parts)
