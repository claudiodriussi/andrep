"""
test_compose.py — Load sells.json, apply composition, save the resolved template.

Run from the renderer-python/ directory:
    python sample/test_compose.py
"""
import sys
from pathlib import Path

# Allow importing andrep without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from andrep import AndRepRenderer, FilesystemLoader

TEMPLATES = Path(__file__).parent.parent / "templates"
OUTPUT = Path(__file__).parent / "output" / "sells_composed.json"

loader = FilesystemLoader(base_dir=TEMPLATES)
renderer = AndRepRenderer("sells", loader=loader)

renderer.save_composed(OUTPUT)
print(f"Composed template saved to: {OUTPUT}")

# Quick summary: band names and row counts
bands = renderer.bands
print(f"\nBands after composition ({len(bands)} total):")
for name, rows in bands.items():
    print(f"  {name}: {len(rows)} row(s)")
