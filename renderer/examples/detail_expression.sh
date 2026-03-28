#!/bin/bash
# detail_expression.sh — extract/merge example for expression translation
#
# Demonstrates the andrep-expr workflow:
#   1. extract: scan all [expr] tokens in the template, produce a translation file
#              (existing translations preserved, new expressions get "")
#   2. edit   : fill in the translations you need (non-portable expressions only)
#   3. merge  : write non-empty translations back into template.expressions[lang]
#
# Run from the renderer/ directory:
#   cd renderer
#   bash examples/detail_expression.sh

TEMPLATE="examples/templates/detail.json"
LANG="js"
TRANS="/tmp/detail_expr_${LANG}.json"

echo "=== extract ==="
python3 -m andrep.expr_cli extract "$TEMPLATE" --lang "$LANG" -o "$TRANS"
echo "Translations file: $TRANS"
echo ""

echo "=== translations (edit non-empty entries to add/update) ==="
cat "$TRANS"
echo ""

echo "=== merge ==="
python3 -m andrep.expr_cli merge "$TEMPLATE" "$TRANS" --lang "$LANG"
echo ""

echo "=== resulting expressions in template ==="
python3 -c "
import json
t = json.load(open('$TEMPLATE'))
print(json.dumps(t.get('expressions', {}), indent=2, ensure_ascii=False))
"
