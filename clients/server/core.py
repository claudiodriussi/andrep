"""
core.py — Shared rendering logic for the AndRep REST servers.

Both server_flask.py and server_fastapi.py import from here.
"""

import sys
from pathlib import Path

# Add renderer package to path (clients/server/ → ../../renderer)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "renderer"))

from andrep import AndRepRenderer, FilesystemLoader  # noqa: E402


def make_loader(template_dir: str | Path) -> FilesystemLoader:
    return FilesystemLoader(base_dir=Path(template_dir))


def render(
    template: str,
    records: list[dict],
    fmt: str = "html",
    metadata: dict | None = None,
    loader: FilesystemLoader | None = None,
) -> bytes | str:
    """Render compiled records to HTML (str) or PDF (bytes)."""
    r = AndRepRenderer.from_compiled(template, records, loader=loader or make_loader("."), metadata=metadata)
    if fmt == "pdf":
        return r.to_pdf()
    return r.to_html()


def list_templates(loader: FilesystemLoader) -> list[str]:
    """Return template names available in the loader's base_dir."""
    base = Path(loader.baseDir)
    return sorted(p.stem for p in base.glob("*.json"))
