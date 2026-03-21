"""
server_flask.py — AndRep renderer REST server (Flask).

Usage:
    pip install flask
    python server_flask.py --template-dir /path/to/templates
    python server_flask.py --template-dir /path/to/templates --port 5000 --host 0.0.0.0

Environment variables (override args):
    ANDREP_TEMPLATE_DIR
    ANDREP_PORT
    ANDREP_HOST

Routes:
    POST /render    { template, records, format?, metadata? } → HTML or PDF
    GET  /health    → { status, template_dir }
    GET  /templates → ["name", ...]
"""

import argparse
import os
from flask import Flask, request, Response, jsonify
from core import make_loader, render, list_templates

# ---------------------------------------------------------------------------
# Args / config
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--template-dir", default=os.environ.get("ANDREP_TEMPLATE_DIR", "."))
parser.add_argument("--port",         default=int(os.environ.get("ANDREP_PORT", 5000)), type=int)
parser.add_argument("--host",         default=os.environ.get("ANDREP_HOST", "127.0.0.1"))
args = parser.parse_args()

loader = make_loader(args.template_dir)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = Flask(__name__)


def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.after_request
def add_cors(response):
    return _cors(response)


@app.route("/render", methods=["POST", "OPTIONS"])
def render_endpoint():
    if request.method == "OPTIONS":
        return _cors(Response(status=204))
    body     = request.get_json(force=True)
    template = body["template"]
    records  = body["records"]
    fmt      = body.get("format", "html")
    metadata = body.get("metadata")

    output = render(template, records, fmt, metadata, loader)

    if fmt == "pdf":
        return Response(output, mimetype="application/pdf")
    return Response(output, mimetype="text/html; charset=utf-8")


@app.route("/health")
def health():
    return jsonify(status="ok", template_dir=str(args.template_dir))


@app.route("/templates")
def templates():
    return jsonify(list_templates(loader))


if __name__ == "__main__":
    print(f"AndRep Flask server → http://{args.host}:{args.port}")
    print(f"  template-dir: {args.template_dir}")
    app.run(host=args.host, port=args.port)
