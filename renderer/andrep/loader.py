"""
loader.py — TemplateLoader protocol and FilesystemLoader.
"""
import json
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class TemplateLoader(Protocol):
    def load(self, name: str) -> dict:
        """Load a template by logical name.

        Template names come from the caller and from the ``target`` of
        composition rules, which are part of the (untrusted) template content.
        A loader must never resolve a name outside its own storage, and must
        distinguish two outcomes:

        - FileNotFoundError: valid name, no such template.  For a composition
          target the rule is skipped silently (optional overrides).
        - ValueError: invalid name or outside the loader's perimeter.  Never
          skipped — it reaches the caller.
        """
        ...


class FilesystemLoader:
    """Load AndRep template JSON files from the filesystem.

    Search order:
    1. custom_dir/<name>.json
    2. base_dir/<name>.json

    A name must resolve (symlinks included) inside the directory it is looked
    up in: ``..``, absolute names and symlinks leading outside raise ValueError.

    Args:
        base_dir:   directory containing standard templates.
        custom_dir: directory for local overrides (default: base_dir/custom).
    """

    def __init__(self, base_dir: Path, custom_dir: Path = None, lang: str = None):
        self.base_dir = Path(base_dir)
        self.custom_dir = Path(custom_dir) if custom_dir is not None else self.base_dir / "custom"
        self.lang = lang

    @staticmethod
    def _candidate(directory: Path, name: str) -> Path:
        root = directory.resolve()
        path = (root / f"{name}.json").resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"Template name {name!r} resolves outside {directory}")
        return path

    def load(self, name: str) -> dict:
        for directory in (self.custom_dir, self.base_dir):
            candidate = self._candidate(directory, name)
            if candidate.exists():
                template = json.loads(candidate.read_text(encoding="utf-8"))
                if self.lang:
                    from .expr_tools import apply_translations
                    template = apply_translations(template, self.lang)
                return template
        raise FileNotFoundError(
            f"Template '{name}' not found in {self.custom_dir} or {self.base_dir}"
        )
