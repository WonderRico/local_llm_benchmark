#!/usr/bin/env python3
"""Serve the generated benchmark report HTML files over HTTP.

Usage:
    python server.py [--port 8000] [--host 127.0.0.1]

Serves `benchmark-main.html` at `/main` and `benchmark-detail.html` at `/detail`,
plus an index page listing both. Every generated trajectory page under `html_traj/`
is served too, which is what the per-instance table links to.
"""

from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import typer

SCRIPT_DIR = Path(__file__).resolve().parent
TRAJ_DIR = (SCRIPT_DIR / "html_traj").resolve()

REPORTS = {
    "/main": ("Benchmark Dashboard", "benchmark-main.html"),
    "/detail": ("Detailed Report", "benchmark-detail.html"),
}

INDEX = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Benchmark Reports</title></head>
<body>
<h1>Benchmark Reports</h1>
<ul>
{links}
</ul>
</body>
</html>
"""


@dataclass
class Config:
    host: str
    port: int


def _resolve(path: str) -> Path | None:
    """Map a request path onto a report or a trajectory page, never onto anything else."""
    if path in REPORTS:
        return SCRIPT_DIR / REPORTS[path][1]
    target = (SCRIPT_DIR / unquote(path).lstrip("/")).resolve()
    return target if target.suffix == ".html" and target.is_relative_to(TRAJ_DIR) else None


def _serve(handler: BaseHTTPRequestHandler, path: str) -> None:
    target = _resolve(path)
    if target is None or not target.is_file():
        handler.send_error(HTTPStatus.NOT_FOUND, f"No page at {path}")
        return
    body = target.read_bytes()
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
    print(f"[{handler.address_string()}] {path} -> {target.relative_to(SCRIPT_DIR)} ({len(body)} bytes)")


class ReportHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        path = urlparse(self.path).path
        if path == "/":
            links = "".join(f'<li><a href="{route}">{title}</a></li>' for route, (title, _) in REPORTS.items())
            body = INDEX.format(links=links).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        _serve(self, path)

    def log_message(self, format: str = "", *args: object) -> None:  # silence default logging
        pass


def serve(cfg: Config) -> None:
    server = ThreadingHTTPServer((cfg.host, cfg.port), ReportHandler)
    print(f"Serving on http://{cfg.host}:{cfg.port}/")
    print(f"  dashboard:    http://{cfg.host}:{cfg.port}/main")
    print(f"  detail:       http://{cfg.host}:{cfg.port}/detail")
    print(f"  trajectories: http://{cfg.host}:{cfg.port}/html_traj/...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


def main(
    host: str = typer.Option("127.0.0.1", help="Bind address"),
    port: int = typer.Option(8000, help="Bind port"),
) -> None:
    serve(Config(host=host, port=port))


if __name__ == "__main__":
    typer.run(main)
