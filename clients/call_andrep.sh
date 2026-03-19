#!/usr/bin/env bash
# call_andrep.sh — invoke the AndRep renderer from any directory.
#
# Usage:
#   ./call_andrep.sh render --template tmpl.json --records records.json \
#                           --format pdf --output report.pdf
#
# The script adds the renderer/ directory to PYTHONPATH so that
# "python3 -m andrep" works without installing the package.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENDERER_DIR="$SCRIPT_DIR/../renderer"

PYTHONPATH="$RENDERER_DIR${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m andrep "$@"
