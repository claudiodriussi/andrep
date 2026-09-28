"""
andrep.adapters — read-only views of ORM records for template expressions.

A loop can pass ORM records as they are (mapped objects, recordsets):
an adapter wraps each one in a view that exposes exactly the fields declared
by the model.  Templates navigate the data graph and nothing else — a chain of
harmless attributes that leads to a session, a connection or a password
(``row.query.session.bind.url``) stops at the first name that is not a field.

Public API:
    RecordView                       — base class: fields(), raw(), collection(),
                                       safe_methods, label()
    register_view(base_cls, view)    — wrap instances of base_cls in *view*
    VALUE, ONE, MANY                 — kinds of field returned by fields()

The views for specific ORMs are separate modules, imported by the integration
that needs them — the engine depends on none of them:

    andrep.adapters.sqlalchemy       — SQLAlchemyView (a generic library)

Views for a vertical platform live in that platform's integration module,
not here.  Writing one means implementing ``fields()`` from the ORM's
metadata, and ``raw()`` / ``collection()`` when its values need normalizing;
andrep/adapters/sqlalchemy.py is the reference.  Views are read lazily: a
relation is loaded when a template reads it, with the ORM's own permissions
and costs.
"""
from types import MappingProxyType

# Kinds of field returned by RecordView.fields()
VALUE = "value"   # a column: read and converted to data
ONE = "one"       # a relation to one record: wrapped again (or None)
MANY = "many"     # a relation to many records: a list of wrapped records


class RecordView:
    """Read-only view of one record.  Subclasses implement ``fields()``.

    The record is kept in a slot whose name starts with ``_``: templates can
    never name it (the expression check refuses such attributes), and
    ``checked_getattr`` only reaches a view through ``_read``.
    """

    __slots__ = ("_record",)

    #: Methods of the record a template may call — declared by the author of
    #: the view, never by the author of a report.  Arguments must be data, at
    #: any depth (a method taking a function would hand it the raw record);
    #: results are converted to data (records returned are wrapped again).
    safe_methods: frozenset = frozenset()

    def __init__(self, record):
        object.__setattr__(self, "_record", record)

    def __setattr__(self, name, value):
        raise AttributeError(f"{type(self).__name__} is read-only")

    # -- to implement ---------------------------------------------------

    @classmethod
    def fields(cls, record) -> "MappingProxyType[str, str]":
        """{field name: VALUE | ONE | MANY} for *record*, from the ORM's metadata."""
        raise NotImplementedError

    def raw(self, name: str, kind: str):
        """Value of field *name* as the ORM returns it, before conversion."""
        return getattr(self._record, name)

    def collection(self, value):
        """A MANY field as templates see it: by default a list of records."""
        from ..variables import _to_data
        return [_to_data(item) for item in value]

    def label(self) -> str:
        """What the record shows when a template prints it as a whole."""
        return type(self._record).__name__

    # -- reading --------------------------------------------------------

    def _read(self, name: str):
        """Value of field *name*, converted to data; AccessDenied otherwise."""
        from ..expr_check import AccessDenied
        from ..variables import _to_data

        if name.startswith("_"):
            raise AccessDenied(f"attribute {name!r} is not allowed")
        record = self._record
        if name in self.safe_methods:
            return self._safe_method(name)
        kind = self.fields(record).get(name)
        if kind is None:
            raise AccessDenied(f"{type(record).__name__}.{name} is not a field")
        value = self.raw(name, kind)
        if kind == MANY:
            return self.collection(value)
        if kind == ONE and not value:
            return None          # e.g. an empty recordset
        return _to_data(value)   # a related record is wrapped by its adapter

    def _safe_method(self, name: str):
        from ..expr_check import AccessDenied
        from ..variables import NotData, _to_data

        method = getattr(self._record, name)

        def call(*args, **kwargs):
            # The same check as the namespace, through containers too: a
            # callable inside a list or a dict is refused like a bare one.
            # The arguments are passed as they are, only checked.
            try:
                _to_data([args, kwargs])
            except NotData as e:
                raise AccessDenied(f"{name}(): arguments must be data ({e})") from None
            return _to_data(method(*args, **kwargs))
        return call

    def __str__(self) -> str:
        try:
            return self.label()
        except Exception:     # e.g. an access error: printing must not stop the report
            return type(self._record).__name__

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self}>"

    # Two views of the same record are the same record for a template
    # (row.author == prev.author), as the records are for the ORM.
    def __eq__(self, other):
        if type(other) is not type(self):
            return NotImplemented
        return self._record == other._record

    def __hash__(self):
        return hash(self._record)


def register_view(base_cls, view: type) -> None:
    """Wrap instances of *base_cls* (and subclasses) in *view* when a loop
    passes them to a template.  *view* must be a RecordView: an adapter that
    returns anything else goes through ``register_adapter``."""
    from ..variables import register_adapter
    if not (isinstance(view, type) and issubclass(view, RecordView)):
        raise TypeError(f"register_view: {view!r} is not a RecordView subclass")
    register_adapter(base_cls, view)
