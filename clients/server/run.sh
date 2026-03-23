#!/usr/bin/env bash
# run.sh — unified entry point for the AndRep renderer servers.
#
# Usage:
#   ./clients/server/run.sh flask   [--template-dir DIR] [--port PORT] [--host HOST]
#   ./clients/server/run.sh fastapi [--template-dir DIR] [--port PORT] [--host HOST]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SERVER="${1:-}"
if [[ -z "$SERVER" ]]; then
    echo "Usage: $0 flask|fastapi [options]" >&2
    exit 1
fi
shift

case "$SERVER" in
    flask)   exec "$SCRIPT_DIR/server_flask.sh"   "$@" ;;
    fastapi) exec "$SCRIPT_DIR/server_fastapi.sh" "$@" ;;
    *)
        echo "Unknown server '$SERVER'. Choose flask or fastapi." >&2
        exit 1
        ;;
esac
