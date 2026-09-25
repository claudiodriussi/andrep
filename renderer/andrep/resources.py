"""
resources.py — ResourceResolver protocol and DefaultResolver.

Every resource a template refers to (``load`` / ``img`` formatters, image
cells) is read through a resolver, and embedded in the document as a
``data:`` URL: the PDF backend and the browser never fetch anything.

DefaultResolver reads:
  - files inside ``base_dir`` (relative paths only; ``..``, absolute paths and
    symlinks leading outside are refused);
  - files inside named roots: ``media:2026/09/x.jpg`` → ``roots["media"]``;
  - http(s) URLs of public hosts.  The check is made on the address the
    connection is actually made to, for every request (redirects included),
    so neither DNS nor redirects can lead to a private address.

Public API:
    ResourceResolver  — protocol: open(ref) -> (bytes, mime)
    DefaultResolver   — base_dir, named roots, public network
    ResourceError     — a resource that cannot be read (the message says why)
    is_public_address(host) -> bool
"""
import http.client
import ipaddress
import mimetypes
import urllib.error
import urllib.request
from pathlib import Path
from typing import Protocol, runtime_checkable


class ResourceError(Exception):
    """A resource that cannot be read: missing, refused or unreachable."""


@runtime_checkable
class ResourceResolver(Protocol):
    def open(self, ref: str) -> "tuple[bytes, str]":
        """Return (content, MIME type) for *ref*, or raise ResourceError."""
        ...


# ---------------------------------------------------------------------------
# Network: public addresses only
# ---------------------------------------------------------------------------

def is_public_address(host: str) -> bool:
    """True if *host* is an IP address on the public internet."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


class _PeerCheck(http.client.HTTPConnection):
    """After the TCP connection is made, refuse it unless the peer is public."""

    def connect(self):
        super().connect()
        address = self.sock.getpeername()[0]
        if not is_public_address(address):
            self.sock.close()
            raise ResourceError(f"{self.host} is not a public address ({address})")


class _PublicHTTPConnection(_PeerCheck):
    pass


class _PublicHTTPSConnection(http.client.HTTPSConnection, _PeerCheck):
    # MRO: HTTPSConnection.connect → _PeerCheck.connect (TCP + check) → TLS
    pass


class _HTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_PublicHTTPConnection, req)


class _HTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_PublicHTTPSConnection, req, context=self._context)


def _build_opener() -> urllib.request.OpenerDirector:
    # Built by hand: only http/https (no file, ftp, data), no proxies — with a
    # proxy the checked address would be the proxy's.
    opener = urllib.request.OpenerDirector()
    for handler in (
        urllib.request.ProxyHandler({}),
        urllib.request.UnknownHandler(),
        _HTTPHandler(),
        _HTTPSHandler(),
        urllib.request.HTTPDefaultErrorHandler(),
        urllib.request.HTTPRedirectHandler(),
        urllib.request.HTTPErrorProcessor(),
    ):
        opener.add_handler(handler)
    return opener


_OPENER = _build_opener()


# ---------------------------------------------------------------------------
# Default resolver
# ---------------------------------------------------------------------------

class DefaultResolver:
    """Files inside base_dir and named roots; http(s) to public hosts.

    Args:
        base_dir: directory for relative paths (default: current directory).
        roots:    named directories, {"media": "/srv/app/media"} → "media:x.jpg".
        network:  False disables http(s).
        timeout:  seconds for a network request.
    """

    def __init__(self, base_dir=None, roots: dict = None, network: bool = True,
                 timeout: float = 10):
        self.base_dir = Path(base_dir) if base_dir is not None else None
        self.roots = {name: Path(path) for name, path in (roots or {}).items()}
        self.network = network
        self.timeout = timeout

    def open(self, ref: str) -> "tuple[bytes, str]":
        if ref.startswith(("http://", "https://")):
            return self._fetch(ref)
        if "://" in ref:
            raise ResourceError("only http and https URLs are allowed")
        name, sep, rest = ref.partition(":")
        if sep and name in self.roots:
            return self._read(self.roots[name], rest)
        return self._read(self.base_dir or Path.cwd(), ref)

    def _read(self, root: Path, relative: str) -> "tuple[bytes, str]":
        if Path(relative).is_absolute():
            raise ResourceError("absolute paths are not allowed")
        root = root.resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ResourceError("outside the allowed directory")
        try:
            data = path.read_bytes()
        except OSError as e:
            raise ResourceError(e.strerror or "cannot read") from None
        return data, mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    def _fetch(self, url: str) -> "tuple[bytes, str]":
        if not self.network:
            raise ResourceError("network access is disabled")
        try:
            with _OPENER.open(url, timeout=self.timeout) as resp:
                return resp.read(), resp.headers.get_content_type()
        except urllib.error.URLError as e:
            raise ResourceError(str(e.reason)) from None
        except (OSError, ValueError, http.client.HTTPException) as e:
            raise ResourceError(str(e) or type(e).__name__) from None
