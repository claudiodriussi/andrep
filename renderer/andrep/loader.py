"""
loader.py — TemplateLoader protocol and FilesystemLoader.
"""
import json
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class TemplateLoader(Protocol):
    def load(self, name: str) -> dict:
        """Load a template by name. Raises FileNotFoundError if not found."""
        ...


class FilesystemLoader:
    """Load AndRep template JSON files from the filesystem.

    Search order:
    1. custom_dir/<name>.json
    2. base_dir/<name>.json

    Args:
        base_dir:   directory containing standard templates.
        custom_dir: directory for local overrides (default: base_dir/custom).
    """

    def __init__(self, base_dir: Path, custom_dir: Path = None, lang: str = None):
        self.base_dir = Path(base_dir)
        self.custom_dir = Path(custom_dir) if custom_dir is not None else self.base_dir / "custom"
        self.lang = lang

    def load(self, name: str) -> dict:
        for candidate in (self.custom_dir / f"{name}.json", self.base_dir / f"{name}.json"):
            if candidate.exists():
                template = json.loads(candidate.read_text(encoding="utf-8"))
                if self.lang:
                    from .expr_tools import apply_translations
                    template = apply_translations(template, self.lang)
                return template
        raise FileNotFoundError(
            f"Template '{name}' not found in {self.custom_dir} or {self.base_dir}"
        )
