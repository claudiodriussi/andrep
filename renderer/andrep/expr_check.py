"""
expr_check.py — validation and compilation of template expressions.

Template expressions are a subset of Python: they read data, they never
define functions, assign, or reach Python internals.  Each expression is
parsed with ``ast`` (nothing is executed), checked against the allowed
subset, and compiled once — when the template is loaded.

Attribute access is checked again at runtime: every ``a.b`` is compiled as a
call to ``checked_getattr(a, "b")``, which only reads attributes of data
(the types in DATA_TYPES, already normalized by ``_to_data``).

Public API:
    compile_expr(source, trusted=False) -> CompiledExpr
    checked_getattr(obj, name)           — runtime attribute access for templates
    SYSTEM_NAMES                         — names starting with "_" that are allowed
    DATA_TYPES                           — exact types a template can read attributes of
"""
import ast
import types
from datetime import date, datetime, time, timedelta
from decimal import Decimal

# System variables injected by the renderer — the only names starting with "_"
SYSTEM_NAMES = frozenset({"_r", "_page", "_pages", "_page_start", "_page_end",
                          "_date", "_time", "_user", "_name"})

# Namespace keys used by compiled expressions; templates cannot name them
# (names starting with "_" are rejected by the validator).
ATTR_FN = "__andrep_attr__"          # checked_getattr
EXCLUDED_KEY = "__andrep_excluded__"  # {local name: why it is not in the namespace}

# Data a template can read attributes of — exact types: _to_data normalizes
# subclasses (e.g. markupsafe.Markup -> str) so only these methods are exposed.
DATA_TYPES = frozenset({
    type(None), bool, int, float, str, bytes, Decimal,
    date, datetime, time, timedelta,
    list, tuple, set, frozenset, dict, types.SimpleNamespace,
})

# Public methods of data types that templates must not use.  The format string
# of str.format / format_map can read attributes inside a literal, out of reach
# of the AST check; AndRep formatters cover formatting.
EXCLUDED_METHODS = {str: frozenset({"format", "format_map"})}

_ALLOWED_NODES = (
    ast.Expression,
    # literals and containers
    ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.Set,
    ast.JoinedStr, ast.FormattedValue,
    # names, attributes, indexing
    ast.Name, ast.Attribute, ast.Subscript, ast.Slice, ast.Load, ast.Store,
    # operators
    ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp,
    ast.operator, ast.unaryop, ast.boolop, ast.cmpop,
    # calls (registered functions, methods of data)
    ast.Call, ast.keyword,
    # comprehensions and generator expressions — they read, they do not write
    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.comprehension,
)


class CompiledExpr:
    """A template expression, validated and compiled.

    ``code`` is None when the expression was rejected; ``error`` says why.
    ``names`` are the names the expression reads — the renderer converts only
    these from the caller's locals.
    """

    __slots__ = ("source", "code", "error", "names")

    def __init__(self, source: str, code=None, error: str = "", names=frozenset()):
        self.source = source
        self.code = code
        self.error = error
        self.names = names

    def marker(self, reason: str) -> str:
        """What the report shows in place of a failed expression."""
        return f"[#{self.source}: {reason}#]"


class AccessDenied(Exception):
    """Attribute access refused by checked_getattr."""


def checked_getattr(obj, name: str):
    """Attribute access for template expressions: data only."""
    kind = type(obj)
    if kind not in DATA_TYPES:
        raise AccessDenied(f"attribute access on {kind.__name__} is not allowed")
    if name in EXCLUDED_METHODS.get(kind, ()):
        raise AccessDenied(f"{kind.__name__}.{name} is not allowed")
    return getattr(obj, name)


class _AttributesToCalls(ast.NodeTransformer):
    """Rewrite every ``a.b`` as ``__andrep_attr__(a, "b")``."""

    def visit_Attribute(self, node):
        self.generic_visit(node)
        call = ast.Call(
            func=ast.Name(id=ATTR_FN, ctx=ast.Load()),
            args=[node.value, ast.Constant(value=node.attr)],
            keywords=[],
        )
        return ast.copy_location(call, node)


def _check(tree: ast.AST) -> str:
    """Return the reason *tree* is outside the allowed subset, or ""."""
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            return f"{type(node).__name__} is not allowed"
        if isinstance(node, ast.Name) and node.id.startswith("_") and node.id not in SYSTEM_NAMES:
            return f"name {node.id!r} is not allowed"
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            return f"attribute {node.attr!r} is not allowed"
        if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.ctx, ast.Store):
            return "assignment is not allowed"
        if isinstance(node, ast.keyword) and node.arg is None:
            return "**-unpacking is not allowed"
        if isinstance(node, ast.comprehension) and node.is_async:
            return "async comprehension is not allowed"
    return ""


CARRY_NAMES = ("_page_start", "_page_end")


def carry_fields(source: str) -> set:
    """Fields read from _page_start / _page_end, e.g. {"total"} for
    "_page_end.total - _page_start.total" — the values to snapshot per band."""
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except SyntaxError:
        return set()
    return {node.attr for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id in CARRY_NAMES}


def compile_expr(source: str, trusted: bool = False) -> CompiledExpr:
    """Parse, validate and compile *source*.

    trusted=True skips the subset check and the runtime attribute check (the
    caller trusts its templates); syntax errors are reported either way.
    """
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except SyntaxError as e:
        return CompiledExpr(source, error=f"syntax error: {e.msg}")
    names = frozenset(n.id for n in ast.walk(tree) if isinstance(n, ast.Name))
    if not trusted:
        reason = _check(tree)
        if reason:
            return CompiledExpr(source, error=reason)
        tree = ast.fix_missing_locations(_AttributesToCalls().visit(tree))
    return CompiledExpr(source, code=compile(tree, "<template>", "eval"), names=names)
