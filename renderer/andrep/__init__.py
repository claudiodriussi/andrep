"""
andrep — Python renderer for AndRep templates.

Minimal usage::

    from andrep import AndRepRenderer, FilesystemLoader
    from pathlib import Path

    loader = FilesystemLoader(Path("templates/"))
    r = AndRepRenderer("sells", loader=loader)
    r.emit("band", {"row": {"it": "001", "description": "Widget", "amount": 5, "price": 10}})
    html = r.to_html()
"""
from .loader import FilesystemLoader, TemplateLoader
from .renderer import AndRepRenderer, load_template

__all__ = ["AndRepRenderer", "FilesystemLoader", "TemplateLoader", "load_template"]
