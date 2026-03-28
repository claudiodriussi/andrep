"""
CLI entry point:  python -m andrep render [options]

Usage
-----
python -m andrep render \\
    --template   path/to/template.json \\
    --records    path/to/records.json  \\  # or - for stdin
    --format     html | pdf            \\  # default: html
    --output     path/to/output        \\  # or - for stdout (default: -)
    --template-dir  path/to/templates/    # base dir for template lookup
"""

import argparse
import json
import sys
from pathlib import Path

from .loader import FilesystemLoader
from .renderer import AndRepRenderer


def cmd_render(args):
    if args.records == "-":
        records = json.load(sys.stdin)
    else:
        records = json.loads(Path(args.records).read_text(encoding="utf-8"))

    template_path = Path(args.template)
    if template_path.exists():
        base_dir = Path(args.template_dir) if args.template_dir else template_path.parent
        loader = FilesystemLoader(base_dir=base_dir)
        template = template_path.stem
    else:
        if not args.template_dir:
            print(f"Error: --template-dir required when template is a name, not a path", file=sys.stderr)
            sys.exit(1)
        loader = FilesystemLoader(base_dir=Path(args.template_dir))
        template = args.template

    metadata = json.loads(args.meta) if args.meta else None
    r = AndRepRenderer.from_compiled(template, records, loader=loader, metadata=metadata)

    fmt = args.format.lower()
    if fmt == "pdf":
        data = r.to_pdf()
        if args.output == "-":
            sys.stdout.buffer.write(data)
        else:
            Path(args.output).write_bytes(data)
    else:
        html = r.to_html()
        if args.output == "-":
            sys.stdout.write(html)
        else:
            Path(args.output).write_text(html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        prog="andrep",
        description="AndRep renderer — converts compiled records to HTML or PDF.",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    p = sub.add_parser("render", help="Render compiled records to HTML or PDF")
    p.add_argument("--template", required=True,
                   help="Template JSON file path or name (resolved by --template-dir)")
    p.add_argument("--records", required=True,
                   help="Compiled records JSON file, or - to read from stdin")
    p.add_argument("--format", default="html", choices=["html", "pdf"],
                   help="Output format (default: html)")
    p.add_argument("--output", default="-",
                   help="Output file path, or - to write to stdout (default: -)")
    p.add_argument("--template-dir", default=None,
                   help="Base directory for template file resolution")
    p.add_argument("--meta", default=None,
                   help="JSON object of renderer attributes (e.g. '{\"title\":\"Report\",\"name\":[\"Acme\"]}')")

    args = parser.parse_args()

    if args.command == "render":
        cmd_render(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
