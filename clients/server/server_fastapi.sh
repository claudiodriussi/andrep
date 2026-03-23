#!/usr/bin/env bash
# server_fastapi.sh — start the AndRep FastAPI renderer server.
#
# Usage (from any directory):
#   ./clients/server/server_fastapi.sh [--template-dir DIR] [--port PORT] [--host HOST]
#
# Defaults: port 5000, host 127.0.0.1, template-dir = this script's directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENDERER_DIR="$(cd "$SCRIPT_DIR/../../renderer" && pwd)"

export PYTHONPATH="$RENDERER_DIR${PYTHONPATH:+:$PYTHONPATH}"

exec python3 "$SCRIPT_DIR/server_fastapi.py" "$@"
