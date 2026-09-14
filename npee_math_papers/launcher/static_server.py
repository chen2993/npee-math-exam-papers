r"""Serve the built frontend, injecting the API origin.

Why not ``python -m http.server``
---------------------------------
``dist/`` is a static SPA whose bundle calls ``/api/...``. In development Vite
proxies that to the backend, but a plain static server has no proxy: the request
would hit the static server itself and 404, so the console would show "题库服务
不可用" even though the API is running.

This server keeps the zero-dependency promise of ``http.server`` while:

* injecting ``window.NPEE_API_URL`` into ``index.html`` so the bundled app knows
  where the backend lives;
* answering unknown paths with ``index.html`` so a deep link (``/#/papers`` uses
  a hash and needs no fallback, but a stray path still lands on the app rather
  than a directory listing).

Usage::

    python -m npee_math_papers.launcher.static_server --directory dist --port 5173 --api-url http://127.0.0.1:8766
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socket
import socketserver
import sys
from pathlib import Path

#: Placeholder the built ``index.html`` does not contain; we insert the script
#: before ``</head>`` instead, which works for any build.
INJECTION_MARKER = "</head>"


def inject_api_url(document: str, api_url: str) -> str:
    """Return ``document`` with the API origin injected as a global."""

    if not api_url:
        return document
    # ``json.dumps`` gives a correctly quoted JS string literal.
    import json

    snippet = f'  <script>window.NPEE_API_URL = {json.dumps(api_url)};</script>\n'
    if "NPEE_API_URL" in document:
        return document
    if INJECTION_MARKER in document:
        return document.replace(INJECTION_MARKER, snippet + INJECTION_MARKER, 1)
    return snippet + document


class SpaRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Static handler that injects the API origin and falls back to ``index.html``."""

    api_url: str = ""

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        path = self.path.split("?", 1)[0]
        target = Path(self.translate_path(path))

        if target.is_dir():
            target = target / "index.html"

        if not target.is_file():
            # Unknown asset path: serve the app shell so the SPA can route.
            if path.startswith("/api"):
                # Never mask API traffic; this server is not the API.
                self.send_error(404, "API requests must go to the application API, not the static server")
                return
            target = Path(self.directory) / "index.html"  # type: ignore[attr-defined]

        try:
            payload = target.read_bytes()
        except OSError:
            self.send_error(404, "File not found")
            return

        if target.name == "index.html" and self.api_url:
            payload = inject_api_url(payload.decode("utf-8"), self.api_url).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", self.guess_type(str(target)))
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
        """Silence per-request logging; the launcher owns the console."""


class ReusableTcpServer(socketserver.ThreadingTCPServer):
    """Threaded server that can restart immediately after a shutdown."""

    allow_reuse_address = True
    daemon_threads = True

    def server_bind(self) -> None:
        # Also allow binding IPv6 and dual-stack hosts without a restart delay.
        if self.address_family == socket.AF_INET6:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NPEE 前端静态服务器（注入 API 地址）")
    parser.add_argument("--directory", required=True, type=Path, help="dist 目录")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--api-url", default="", help="注入到页面的 API 基地址")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    directory = Path(args.directory).resolve()
    if not (directory / "index.html").is_file():
        print(f"[NPEE] 前端产物缺失：{directory / 'index.html'}", file=sys.stderr, flush=True)
        return 1

    handler = functools.partial(SpaRequestHandler, directory=str(directory))
    SpaRequestHandler.api_url = args.api_url
    with ReusableTcpServer((args.bind, args.port), handler) as httpd:  # type: ignore[arg-type]
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
