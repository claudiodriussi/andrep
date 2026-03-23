"""
rest.py — Call the AndRep renderer via REST server.

Usage:
    from rest import call_andrep_rest

    html = call_andrep_rest(
        server_url="http://localhost:5000",
        template="products",
        records=r._emissions,
        metadata={"title": r.title, "name": r.name},
        format="html",
    )

Requires:
    pip install requests
"""

from typing import Any

try:
    import requests
except ImportError as exc:
    raise ImportError("Install requests: pip install requests") from exc


def call_andrep_rest(
    server_url: str,
    template: str,
    records: list[dict],
    format: str = "html",
    metadata: dict[str, Any] | None = None,
) -> bytes:
    """
    POST compiled records to the AndRep REST server and return the output.

    Compatible with both server_flask.py and server_fastapi.py.
    The server must have the template available in its template-dir.

    Args:
        server_url: Base URL of the server, e.g. "http://localhost:5000".
        template:   Template name (resolved by the server's template-dir).
        records:    Compiled records from AndRepRenderer._emissions.
        format:     "html" or "pdf". Default: "html".
        metadata:   Renderer attributes for page_role band expressions
                    (e.g. {"title": "...", "name": [...]}).

    Returns:
        Response body as bytes (HTML text or PDF binary).
    """
    url = server_url.rstrip("/") + "/render"
    body: dict[str, Any] = {"template": template, "records": records, "format": format}
    if metadata:
        body["metadata"] = metadata

    resp = requests.post(url, json=body, timeout=60)
    resp.raise_for_status()
    return resp.content
