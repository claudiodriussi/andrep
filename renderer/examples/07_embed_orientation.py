"""
07_embed_orientation.py — rotation test via embed.

Same data as 07_embed.py but emits band_rot instead of band.
In band_rot the left embed (art_left_rot) replaces the plain code cell
with a 22px-wide cell rotated 90° (writing-mode:vertical-rl) centred
both horizontally (text-align:center) and vertically (justify-content:center).

The right embed (art_right) is unchanged.

Run from the renderer/ directory:
    python3 examples/07_embed_orientation.py
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

embed = importlib.import_module("07_embed")

SAMPLE_DIR = Path(__file__).parent
OUTPUT = SAMPLE_DIR / "output" / "07_embed_orientation.html"

if __name__ == "__main__":
    embed.main(band="band_rot", output=OUTPUT)
