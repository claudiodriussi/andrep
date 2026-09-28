"""
sqlalchemy.py — AndRep view of SQLAlchemy mapped objects.

    from andrep.adapters import register_view
    from andrep.adapters.sqlalchemy import SQLAlchemyView

    register_view(Base, SQLAlchemyView)     # once, in the integration module

SQLAlchemy is imported when a view is first read, so importing this module
costs nothing.  It is also the reference for writing a view for another ORM.
"""
from types import MappingProxyType

from . import MANY, ONE, VALUE, RecordView


class SQLAlchemyView(RecordView):
    """View of a SQLAlchemy mapped object: its column attributes and its
    relationships, from the mapper.  Nothing else — no ``query``, no
    ``metadata``, no ``registry``, no methods.

    Properties that are data (e.g. computed fields of the application) can be
    added by a subclass through ``extra_fields``.  SQLAlchemy is imported only
    when a view is first read, so the engine does not depend on it.

        register_view(Base, SQLAlchemyView)
    """

    __slots__ = ()

    #: Additional readable attributes: {name: VALUE | ONE | MANY}
    extra_fields: dict = {}

    _cache: dict = {}   # mapped class -> fields

    @classmethod
    def fields(cls, record):
        key = (cls, type(record))
        found = SQLAlchemyView._cache.get(key)
        if found is None:
            from sqlalchemy import inspect

            mapper = inspect(type(record))
            names = {attr.key: VALUE for attr in mapper.column_attrs}
            for rel in mapper.relationships:
                names[rel.key] = MANY if rel.uselist else ONE
            names.update(cls.extra_fields)
            found = SQLAlchemyView._cache[key] = MappingProxyType(names)
        return found

    def label(self) -> str:
        from sqlalchemy import inspect

        identity = inspect(self._record).identity
        key = ",".join(str(k) for k in identity) if identity else "new"
        return f"{type(self._record).__name__}({key})"
