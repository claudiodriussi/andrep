"""
andrep-expr — extract and merge expression translations for AndRep templates.

Usage:
    andrep-expr extract template.json --lang js [-o translations.json]
    andrep-expr merge   template.json translations.json --lang js [-o out.json]

extract:
    Scans all [expr|fmt] tokens in the template and produces a JSON file with
    one entry per expression. Entries already translated for the target language
    keep their value; new expressions get "" as placeholder.
    Run repeatedly: existing translations are never overwritten.

merge:
    Reads a translations file (output of extract, edited by the user) and merges
    non-empty values into template.expressions[lang]. Writes the result in-place
    unless -o is specified.
"""
import argparse
import json
import sys
from pathlib import Path


def cmd_extract(args):
    template = json.loads(Path(args.template).read_text(encoding="utf-8"))
    from andrep.expr_tools import extract_expressions
    result = extract_expressions(template, args.lang)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Extracted {len(result)} expressions → {args.output}", file=sys.stderr)
    else:
        print(output)


def cmd_merge(args):
    template = json.loads(Path(args.template).read_text(encoding="utf-8"))
    translations = json.loads(Path(args.translations).read_text(encoding="utf-8"))
    from andrep.expr_tools import merge_expressions
    updated = merge_expressions(template, translations, args.lang)
    out_path = args.output or args.template
    Path(out_path).write_text(
        json.dumps(updated, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    non_empty = sum(1 for v in translations.values() if v)
    print(f"Merged {non_empty} translation(s) → {out_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        prog="andrep-expr",
        description="Extract and merge expression translations for AndRep templates.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ext = sub.add_parser("extract", help="Extract expressions from a template")
    p_ext.add_argument("template", help="Template JSON file")
    p_ext.add_argument("--lang", required=True, help="Target language key (e.g. js, csharp)")
    p_ext.add_argument("-o", "--output", help="Output file (default: stdout)")

    p_mrg = sub.add_parser("merge", help="Merge translations into a template")
    p_mrg.add_argument("template", help="Template JSON file")
    p_mrg.add_argument("translations", help="Translations JSON file (produced by extract)")
    p_mrg.add_argument("--lang", required=True, help="Target language key")
    p_mrg.add_argument("-o", "--output", help="Output file (default: in-place)")

    args = parser.parse_args()
    if args.command == "extract":
        cmd_extract(args)
    elif args.command == "merge":
        cmd_merge(args)


if __name__ == "__main__":
    main()
