"""
03_detail_summary.py — Summary variant of the Articles & Movements report.

Emits the same bands as 03_detail but skips movement rows (silent=True),
producing a compact summary with article and category subtotals only.

Run from the renderer/ directory:
    python3 examples/03_detail_summary.py
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

detail = importlib.import_module("03_detail")

if __name__ == "__main__":
    detail.main(summary=True)
