"""
expr_tools.py — expression extraction and translation tools for AndRep templates.

Public API:
    extract_expressions(template, lang) -> dict
        Return {expr: translation_or_empty} for all expressions in the template.
        Existing translations for lang are preserved; new expressions get "".
        Safe to run repeatedly without losing work.

    merge_expressions(template, translations, lang) -> dict
        Return updated template with translations merged into expressions[lang].
        Only non-empty translation values are stored.
"""
import copy

from .variables import _parse_tokens

# System variables injected by the renderer — language-neutral, skip in extract
_SYSTEM_VARS = {"_page", "_name", "_date", "_time", "_user", "_r"}


def _is_literal(expr: str) -> bool:
    """True if expr is a string/numeric/boolean literal (always language-neutral)."""
    s = expr.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return True
    try:
        float(s)
        return True
    except ValueError:
        pass
    return s in ("True", "False", "None", "true", "false", "null")


def _collect_expressions(template: dict) -> list:
    """Walk all cells in template rows; return ordered list of unique expressions."""
    seen = set()
    result = []
    for row in template.get("rows", []):
        for cell in row.get("cells", []):
            content = cell.get("content", "")
            if not content or "[" not in content:
                continue
            for _, expr, _ in _parse_tokens(content):
                if not expr:
                    continue
                if expr in _SYSTEM_VARS:
                    continue
                if _is_literal(expr):
                    continue
                if expr not in seen:
                    seen.add(expr)
                    result.append(expr)
    return result


def extract_expressions(template: dict, lang: str) -> dict:
    """Return translation dict for lang.

    All expressions found in the template are included:
    - expressions already translated for lang keep their value
    - new expressions get "" (portable / not yet translated)

    The returned dict is meant to be edited by the user then passed to
    merge_expressions().
    """
    existing = template.get("expressions", {}).get(lang, {})
    return {expr: existing.get(expr, "") for expr in _collect_expressions(template)}


def merge_expressions(template: dict, translations: dict, lang: str) -> dict:
    """Return updated template with translations merged into expressions[lang].

    Only non-empty translation values are written into the template —
    empty strings mean "portable, evaluate as-is" and are not stored.
    """
    t = copy.deepcopy(template)
    expressions = t.setdefault("expressions", {})
    lang_map = expressions.setdefault(lang, {})
    for expr, translation in translations.items():
        if translation:
            lang_map[expr] = translation
    # Clean up empty entries
    if not lang_map:
        del expressions[lang]
    if not expressions:
        del t["expressions"]
    return t
