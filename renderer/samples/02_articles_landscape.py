"""
02_articles_landscape.py — Landscape variant of the Article List report.

Adds a Category column; uses the articles_landscape template with stdlds header.

Run from the renderer/ directory:
    python3 samples/02_articles_landscape.py
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

articles = importlib.import_module("02_articles")

if __name__ == "__main__":
    articles.main(landscape=True)
