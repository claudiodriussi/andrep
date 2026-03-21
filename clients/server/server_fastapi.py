"""
server_fastapi.py — AndRep renderer REST server (FastAPI).

Usage:
    pip install fastapi uvicorn
    python server_fastapi.py --template-dir /path/to/templates
    python server_fastapi.py --template-dir /path/to/templates --port 8000 --host 0.0.0.0

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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
import uvicorn
from core import make_loader, render, list_templates

# ---------------------------------------------------------------------------
# Args / config
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--template-dir", default=os.environ.get("ANDREP_TEMPLATE_DIR", "."))
parser.add_argument("--port",         default=int(os.environ.get("ANDREP_PORT", 8000)), type=int)
parser.add_argument("--host",         default=os.environ.get("ANDREP_HOST", "127.0.0.1"))
args = parser.parse_args()

loader = make_loader(args.template_dir)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="AndRep Renderer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RenderRequest(BaseModel):
    template: str
    records: list[dict]
    format: str = "html"
    metadata: dict | None = None


@app.post("/render")
def render_endpoint(body: RenderRequest):
    output = render(body.template, body.records, body.format, body.metadata, loader)
    if body.format == "pdf":
        return Response(content=output, media_type="application/pdf")
    return HTMLResponse(content=output)


@app.get("/health")
def health():
    return {"status": "ok", "template_dir": str(args.template_dir)}


@app.get("/templates")
def templates():
    return list_templates(loader)


if __name__ == "__main__":
    print(f"AndRep FastAPI server → http://{args.host}:{args.port}")
    print(f"  template-dir: {args.template_dir}")
    print(f"  docs         → http://{args.host}:{args.port}/docs")
    uvicorn.run(app, host=args.host, port=args.port)
