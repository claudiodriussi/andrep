"""
expr_check.py — validation and compilation of template expressions.

Template expressions are a subset of Python: they read data, they never
define functions, assign, or reach Python internals.  Each expression is
parsed with ``ast`` (nothing is executed), checked against the allowed
subset, and compiled once — when the template is loaded.

Public API:
    compile_expr(source, trusted=False) -> CompiledExpr
    SYSTEM_NAMES                         — names starting with "_" that are allowed
"""
import ast

# System variables injected by the renderer — the only names starting with "_"
SYSTEM_NAMES = frozenset({"_r", "_page", "_date", "_time", "_user", "_name"})

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
    """

    __slots__ = ("source", "code", "error")

    def __init__(self, source: str, code=None, error: str = ""):
        self.source = source
        self.code = code
        self.error = error

    def marker(self, reason: str) -> str:
        """What the report shows in place of a failed expression."""
        return f"[#{self.source}: {reason}#]"


def _check(tree: ast.AST) -> str:
    """Return the reason *tree* is outside the allowed subset, or ""."""
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            return f"{type(node).__name__} is not allowed"
        if isinstance(node, ast.Name) and node.id.startswith("_") and node.id not in SYSTEM_NAMES:
            return f"name {node.id!r} is not allowed"
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            return f"attribute {node.attr!r} is not allowed"
        if isinstance(node, ast.keyword) and node.arg is None:
            return "**-unpacking is not allowed"
        if isinstance(node, ast.comprehension) and node.is_async:
            return "async comprehension is not allowed"
    return ""


def compile_expr(source: str, trusted: bool = False) -> CompiledExpr:
    """Parse, validate and compile *source*.

    trusted=True skips the subset check (the caller trusts its templates);
    syntax errors are reported either way.
    """
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except SyntaxError as e:
        return CompiledExpr(source, error=f"syntax error: {e.msg}")
    if not trusted:
        reason = _check(tree)
        if reason:
            return CompiledExpr(source, error=reason)
    return CompiledExpr(source, code=compile(tree, "<template>", "eval"))
