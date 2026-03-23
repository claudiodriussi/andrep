"""
run_rest.py — Batch runner: loop engine → REST server → HTML + PDF.

The Python renderer (andrep) is used only for the loop engine and template
loading. HTML/PDF rendering is delegated to a remote Python REST server —
useful when WeasyPrint is not installed locally.

Start the REST server first:
    ./clients/server/run.sh flask   --template-dir clients/python/examples/templates
    ./clients/server/run.sh fastapi --template-dir clients/python/examples/templates

Usage (from clients/python/examples/):
    python run_rest.py
    python run_rest.py --html-only
    python run_rest.py --server http://localhost:5000
"""

import argparse
import json
import sys
from pathlib import Path

# Rest helper is in clients/python/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rest import call_andrep_rest  # noqa: E402

from loop import build_report  # noqa: E402

OUTPUT = Path(__file__).parent / "output"
OUTPUT.mkdir(exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server",    default="http://localhost:5000")
    parser.add_argument("--html-only", action="store_true")
    args = parser.parse_args()

    print(f"Server: {args.server}")

    r = build_report()
    records  = r._emissions
    metadata = {"title": r.title, "name": r.name}

    print(f"Compiled {len(records)} records for {r.article_count} products")
    print(f"Grand total: € {r.grand_total:.2f}")

    # Save records JSON for inspection
    records_path = OUTPUT / "products-records.json"
    records_path.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")
    print(f"Records saved → {records_path}")

    # HTML
    print("Rendering HTML...")
    html_bytes = call_andrep_rest(
        server_url=args.server,
        template="products",
        records=records,
        metadata=metadata,
        format="html",
    )
    html_path = OUTPUT / "products-rest.html"
    html_path.write_bytes(html_bytes)
    print(f"HTML saved → {html_path}")

    # PDF
    if not args.html_only:
        print("Rendering PDF...")
        pdf_bytes = call_andrep_rest(
            server_url=args.server,
            template="products",
            records=records,
            metadata=metadata,
            format="pdf",
        )
        pdf_path = OUTPUT / "products-rest.pdf"
        pdf_path.write_bytes(pdf_bytes)
        print(f"PDF saved → {pdf_path}")


if __name__ == "__main__":
    main()
