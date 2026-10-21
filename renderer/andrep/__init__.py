"""
andrep — Python renderer for AndRep templates.

Minimal usage::

    from andrep import AndRepRenderer, FilesystemLoader
    from pathlib import Path

    loader = FilesystemLoader(Path("templates/"))
    r = AndRepRenderer("sells", loader=loader)
    for row in rows:
        r.emit("band")          # 'row' captured from the local scope → [row.price]
    html = r.to_html()
"""
from .adapters import RecordView, register_view
from .loader import FilesystemLoader, TemplateLoader
from .renderer import AndRepRenderer, load_template
from .resources import DefaultResolver, ResourceError, ResourceResolver
from .variables import register_adapter

__all__ = [
    "AndRepRenderer", "FilesystemLoader", "TemplateLoader", "load_template",
    "register_adapter", "register_view", "RecordView",
    "DefaultResolver", "ResourceResolver", "ResourceError",
]
