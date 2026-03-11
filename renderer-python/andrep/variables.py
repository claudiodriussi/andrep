"""
variables.py — parser [expr|formatter] e valutazione espressioni per AndRep.
"""
import re
import types
from datetime import date, datetime


def _to_ns(data):
    """Converte ricorsivamente dict/list in SimpleNamespace per accesso con attributi."""
    if isinstance(data, dict):
        ns = types.SimpleNamespace()
        for k, v in data.items():
            setattr(ns, k, _to_ns(v))
        return ns
    elif isinstance(data, list):
        return [_to_ns(i) for i in data]
    return data


def eval_expr(expr, ctx):
    """Valuta un'espressione nel contesto ctx (dict).
    Ritorna il valore o '[#expr#]' in caso di errore.
    """
    try:
        ns_locals = {k: _to_ns(v) for k, v in ctx.items()}
        return eval(expr, {"__builtins__": {}}, ns_locals)  # noqa: S307
    except ZeroDivisionError:
        return 0
    except Exception:
        return f"[#{expr}#]"


def _apply_formatter(value, fmt):
    """Applica un singolo formatter a un valore."""
    fmt = fmt.strip()
    if not fmt:
        return value

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
            # € 1.234,56  (formato italiano)
            formatted = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"€ {formatted}"
        except (TypeError, ValueError):
            return str(value)

    # Formato data esplicito: contiene d/m/y (es. dd/mm/yyyy)
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

    # Formato numerico con sign opzionale: +.2  .2  10.2  10
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
            # Separatori italiani
            formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
            if width:
                formatted = formatted.rjust(width)
            return formatted
        except (TypeError, ValueError):
            return str(value)

    # Solo cifre: N decimali fissi senza separatore migliaia
    if re.match(r"^\d+$", fmt):
        decimals = int(fmt)
        try:
            v = float(value)
            return f"{v:{sign}.{decimals}f}"
        except (TypeError, ValueError):
            return str(value)

    return str(value) if value is not None else ""


def _split_token(token):
    """Divide il contenuto di un token [token] in (expr, [formatter, ...]).

    Regola:
    1. Se contiene \\| → separatore esplicito (tutto prima = expr)
    2. Altrimenti: primo | singolo (non parte di ||) è il separatore
    """
    # Passo 1: cerca separatore esplicito \|
    if "\\" + "|" in token:
        idx = token.index("\\" + "|")
        expr = token[:idx]
        rest = token[idx + 2:]
        formatters = [f.strip() for f in rest.split("|") if f.strip()]
        return expr.strip(), formatters

    # Passo 2: primo | singolo (non parte di ||)
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
    """Parsa una stringa content in lista di (testo_letterale, expr, formatters).

    - (text, None, None) → testo letterale
    - ('', expr, [fmt, ...]) → token variabile
    """
    result = []
    i = 0
    current_text = []

    while i < len(content):
        if content[i] == "[":
            # Trova il ] corrispondente (gestisce annidate)
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
                token = content[i + 1 : j - 1]
                expr, formatters = _split_token(token)
                result.append(("", expr, formatters))
                i = j
            else:
                # Parentesi aperta senza chiusura → letterale
                current_text.append(content[i])
                i += 1
        else:
            current_text.append(content[i])
            i += 1

    if current_text:
        result.append(("".join(current_text), None, None))

    return result


def resolve_content(content, ctx):
    """Risolve tutti i token [var|formatter] in content usando il dizionario ctx.
    Ritorna la stringa con tutti i token sostituiti.
    """
    if not content or "[" not in content:
        return content

    tokens = _parse_tokens(content)
    parts = []

    for text, expr, formatters in tokens:
        if expr is None:
            parts.append(text)
        else:
            value = eval_expr(expr, ctx)
            if formatters:
                for fmt in formatters:
                    value = _apply_formatter(value, fmt)
                parts.append(str(value) if value is not None else "")
            else:
                parts.append("" if value is None else str(value))

    return "".join(parts)
