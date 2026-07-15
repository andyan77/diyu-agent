#!/usr/bin/env python3
"""Standard-library HTTP adapter for the light-expression service."""

from __future__ import annotations

import argparse
import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from light_expression_service import LightExpressionService, TrustedUpstreamContext


LOGGER = logging.getLogger("diyu.light_expression")
MAX_REQUEST_BYTES = 1_048_576


class LightExpressionHttpServer(ThreadingHTTPServer):
    service: LightExpressionService
    trusted_context: TrustedUpstreamContext | None


class LightExpressionHandler(BaseHTTPRequestHandler):
    server: LightExpressionHttpServer

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._write_json(HTTPStatus.OK, {"status": "ok", "scope": "PROCESS_ONLY"})
            return
        if self.path == "/readyz":
            payload = self.server.service.readiness()
            status = HTTPStatus.OK if payload["ready"] else HTTPStatus.SERVICE_UNAVAILABLE
            self._write_json(status, payload)
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})

    def do_POST(self) -> None:
        if self.path not in {"/v1/content/prepare", "/v1/content/validate"}:
            self._write_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return
        payload = self._read_json()
        if payload is None:
            return
        if self.path == "/v1/content/prepare":
            response = self.server.service.prepare(payload, self.server.trusted_context)
            status = HTTPStatus.OK if self.server.trusted_context is not None else HTTPStatus.FORBIDDEN
        else:
            response = self.server.service.validate(payload, self.server.trusted_context)
            status = HTTPStatus.OK if self.server.trusted_context is not None else HTTPStatus.FORBIDDEN
        self._write_json(status, response)

    def _read_json(self) -> dict[str, Any] | None:
        if self.headers.get_content_type() != "application/json":
            self._write_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"status": "application_json_required"})
            return None
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length < 1 or length > MAX_REQUEST_BYTES:
            self._write_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_content_length"})
            return None
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._write_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_json"})
            return None
        if not isinstance(value, dict):
            self._write_json(HTTPStatus.BAD_REQUEST, {"status": "json_object_required"})
            return None
        return value

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string: str, *args: Any) -> None:
        LOGGER.info("http_request " + format_string, *args)


def build_server(
    host: str,
    port: int,
    service: LightExpressionService,
    trusted_context: TrustedUpstreamContext | None,
) -> LightExpressionHttpServer:
    if trusted_context is not None and trusted_context.simulation_only:
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("The local simulation context may bind only to a loopback host")
    server = LightExpressionHttpServer((host, port), LightExpressionHandler)
    server.service = service
    server.trusted_context = trusted_context
    return server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("serve", nargs="?")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument(
        "--simulation-context",
        action="store_true",
        help="Inject the repository's non-publishable simulation identity for local acceptance only.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 0 <= args.port <= 65535:
        raise SystemExit("--port must be between 0 and 65535")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    service = LightExpressionService()
    context = TrustedUpstreamContext.from_simulation_identity() if args.simulation_context else None
    server = build_server(args.host, args.port, service, context)
    LOGGER.info("light-expression service listening on %s:%s", *server.server_address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
