"""
Every expression used by the shipped templates must stay accepted.

Each one must be accepted by the expression validator (andrep.expr_check).
Expression translations (template["expressions"]) are skipped: they
target other languages (e.g. "js" for the JS client).
"""
import json

import pytest

from andrep.expr_check import compile_expr
from andrep.variables import _parse_tokens
from conftest import EXAMPLES_DIR, REPO_DIR

TEMPLATE_DIRS = [EXAMPLES_DIR / "templates", REPO_DIR / "clients" / "templates"]


def collect_expressions() -> list:
    """(template file, expression) for every [expr] token and @cssExtra."""
    found = []
    for directory in TEMPLATE_DIRS:
        for path in sorted(directory.glob("*.json")):
            tmpl = json.loads(path.read_text(encoding="utf-8"))
            for row in tmpl.get("rows", []):
                for cell in row.get("cells", []):
                    for _, expr, _ in _parse_tokens(cell.get("content", "")):
                        if expr:
                            found.append((path.name, expr))
                    css = cell.get("cssExtra", "")
                    if css.startswith("@"):
                        found.append((path.name, css[1:]))
    # de-duplicate, keep first file that uses each expression
    seen, unique = set(), []
    for name, expr in found:
        if expr not in seen:
            seen.add(expr)
            unique.append((name, expr))
    return unique


EXPRESSIONS = collect_expressions()


def test_expressions_found():
    assert len(EXPRESSIONS) > 20


@pytest.mark.parametrize("source, expr", EXPRESSIONS, ids=[f"{s}:{e}" for s, e in EXPRESSIONS])
def test_expression_accepted(source, expr):
    compiled = compile_expr(expr)
    assert compiled.code is not None, compiled.error
