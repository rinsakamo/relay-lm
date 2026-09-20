"""Transparent raw-response capture for the non-citable synthetic Hindsight smoke.

This module is diagnostic-only.  It never participates in the scientific campaign
and never interprets or mutates Hindsight semantics.  The proxy forwards localhost
HTTP requests to the already-attested llama.cpp server and records raw
/chat/completions responses under the fresh synthetic artifact root before
Hindsight can map finish_reason=length to OutputTooLongError.
"""

from __future__ import annotations

import gzip
import hashlib
import http.client
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


_CAPTURE_FORMAT_VERSION = 1
_MAX_PREVIEW_CHARS = 512
_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}
_INTERESTING_FIELDS = (
    "facts",
    "what",
    "when",
    "where",
    "who",
    "why",
    "fact_kind",
    "occurred_start",
    "occurred_end",
    "fact_type",
    "entities",
    "causal_relations",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_bytes_fsync(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _write_json_fsync(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    _write_bytes_fsync(path, encoded)


def _decoded_json_body(body: bytes, headers: list[tuple[str, str]]) -> Any:
    encoding = next(
        (value for name, value in headers if name.lower() == "content-encoding"),
        "",
    ).lower()
    decoded = gzip.decompress(body) if encoding == "gzip" else body
    return json.loads(decoded.decode("utf-8"))


def _bounded_content_summary(
    response_body: bytes,
    response_headers: list[tuple[str, str]],
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "response_json_parseable": False,
        "finish_reason": None,
        "completion_tokens": None,
        "message_content_chars": None,
        "message_content_sha256": None,
        "message_content_json_parseable": None,
        "message_content_prefix": None,
        "message_content_suffix": None,
        "field_occurrences": {},
    }
    try:
        payload = _decoded_json_body(response_body, response_headers)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return summary
    if not isinstance(payload, dict):
        return summary

    summary["response_json_parseable"] = True
    usage = payload.get("usage")
    if isinstance(usage, dict):
        completion_tokens = usage.get("completion_tokens")
        if isinstance(completion_tokens, int) and not isinstance(completion_tokens, bool):
            summary["completion_tokens"] = completion_tokens

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return summary
    choice = choices[0]
    finish_reason = choice.get("finish_reason")
    if isinstance(finish_reason, str):
        summary["finish_reason"] = finish_reason

    message = choice.get("message")
    if not isinstance(message, dict):
        return summary
    content = message.get("content")
    if not isinstance(content, str):
        return summary

    encoded = content.encode("utf-8")
    summary["message_content_chars"] = len(content)
    summary["message_content_sha256"] = _sha256_bytes(encoded)
    summary["message_content_prefix"] = content[:_MAX_PREVIEW_CHARS]
    summary["message_content_suffix"] = content[-_MAX_PREVIEW_CHARS:]
    summary["field_occurrences"] = {
        field: content.count(f'"{field}"') for field in _INTERESTING_FIELDS
    }
    try:
        json.loads(content)
    except json.JSONDecodeError:
        summary["message_content_json_parseable"] = False
    else:
        summary["message_content_json_parseable"] = True
    return summary


class _CaptureHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        upstream_host: str,
        upstream_port: int,
        artifact_root: Path,
    ) -> None:
        self.upstream_host = upstream_host
        self.upstream_port = upstream_port
        self.artifact_root = artifact_root
        self.capture_lock = threading.Lock()
        self.request_count = 0
        self.captures: list[dict[str, Any]] = []
        super().__init__(server_address, _CaptureHandler)

    def record_chat_completion(
        self,
        *,
        method: str,
        path: str,
        request_body: bytes,
        status_code: int,
        response_headers: list[tuple[str, str]],
        response_body: bytes,
    ) -> None:
        with self.capture_lock:
            ordinal = len(self.captures) + 1
            prefix = f"llama-capture-{ordinal:04d}"
            response_path = self.artifact_root / f"{prefix}.response.bin"
            metadata_path = self.artifact_root / f"{prefix}.json"
            _write_bytes_fsync(response_path, response_body)
            metadata: dict[str, Any] = {
                "format_version": _CAPTURE_FORMAT_VERSION,
                "method": method,
                "path": path,
                "request_body_sha256": _sha256_bytes(request_body),
                "request_body_bytes": len(request_body),
                "status_code": status_code,
                "response_body_path": str(response_path),
                "response_body_sha256": _sha256_bytes(response_body),
                "response_body_bytes": len(response_body),
                "summary": _bounded_content_summary(response_body, response_headers),
            }
            _write_json_fsync(metadata_path, metadata)
            metadata["metadata_path"] = str(metadata_path)
            metadata["metadata_sha256"] = _sha256_bytes(metadata_path.read_bytes())
            self.captures.append(metadata)


class _CaptureHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    @property
    def capture_server(self) -> _CaptureHTTPServer:
        server = self.server
        if not isinstance(server, _CaptureHTTPServer):
            raise RuntimeError("capture handler attached to unexpected server")
        return server

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        self._forward()

    def do_POST(self) -> None:  # noqa: N802
        self._forward()

    def do_HEAD(self) -> None:  # noqa: N802
        self._forward()

    def _forward(self) -> None:
        server = self.capture_server
        length_raw = self.headers.get("Content-Length", "0")
        try:
            length = int(length_raw)
        except ValueError:
            self.send_error(400, "invalid Content-Length")
            return
        request_body = self.rfile.read(length) if length else b""
        headers = {
            name: value
            for name, value in self.headers.items()
            if name.lower() not in _HOP_BY_HOP_HEADERS
            and name.lower() not in {"host", "content-length"}
        }
        if request_body:
            headers["Content-Length"] = str(len(request_body))
        headers["Host"] = f"{server.upstream_host}:{server.upstream_port}"

        with server.capture_lock:
            server.request_count += 1

        connection: http.client.HTTPConnection | None = None
        try:
            connection = http.client.HTTPConnection(
                server.upstream_host,
                server.upstream_port,
                timeout=180.0,
            )
            connection.request(
                self.command,
                self.path,
                body=request_body if request_body else None,
                headers=headers,
            )
            upstream = connection.getresponse()
            response_body = upstream.read()
            response_headers = list(upstream.getheaders())
            status_code = upstream.status
            reason = upstream.reason
        except OSError as exc:
            error = json.dumps(
                {"error": {"message": f"synthetic capture proxy upstream error: {type(exc).__name__}"}},
                sort_keys=True,
            ).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(error)))
            self.end_headers()
            self.wfile.write(error)
            return
        finally:
            if connection is not None:
                try:
                    connection.close()
                except OSError:
                    pass

        if self.command == "POST" and self.path.split("?", 1)[0] == "/v1/chat/completions":
            server.record_chat_completion(
                method=self.command,
                path=self.path,
                request_body=request_body,
                status_code=status_code,
                response_headers=response_headers,
                response_body=response_body,
            )

        self.send_response(status_code, reason)
        for name, value in response_headers:
            lower = name.lower()
            if lower in _HOP_BY_HOP_HEADERS or lower == "content-length":
                continue
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(response_body)


class SyntheticLlamaCaptureProxy:
    """Owned localhost proxy for one fixed-input synthetic diagnostic."""

    def __init__(
        self,
        *,
        upstream_base_url: str,
        artifact_root: Path,
    ) -> None:
        parsed = urlsplit(upstream_base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError("synthetic capture upstream must be localhost HTTP")
        if parsed.port is None:
            raise ValueError("synthetic capture upstream must include a port")
        if not artifact_root.is_absolute():
            raise ValueError("synthetic capture artifact_root must be absolute")
        if artifact_root.exists():
            raise ValueError("synthetic capture artifact_root must be fresh")
        artifact_root.mkdir(parents=True, exist_ok=False)

        self.artifact_root = artifact_root
        self._server = _CaptureHTTPServer(
            ("127.0.0.1", 0),
            upstream_host="127.0.0.1",
            upstream_port=parsed.port,
            artifact_root=artifact_root,
        )
        port = int(self._server.server_address[1])
        self.base_url = f"http://127.0.0.1:{port}/v1"
        self.port = port
        self._thread: threading.Thread | None = None
        self._started = False

    def start(self) -> None:
        if self._started:
            raise RuntimeError("synthetic capture proxy already started")
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="relaylm-synthetic-llama-capture",
            daemon=True,
        )
        self._thread.start()
        self._started = True

    def snapshot(self) -> dict[str, Any]:
        with self._server.capture_lock:
            captures = [dict(item) for item in self._server.captures]
            request_count = self._server.request_count
        return {
            "format_version": _CAPTURE_FORMAT_VERSION,
            "proxy_base_url": self.base_url,
            "proxy_port": self.port,
            "upstream": f"http://127.0.0.1:{self._server.upstream_port}",
            "request_count": request_count,
            "chat_completion_capture_count": len(captures),
            "captures": captures,
        }

    def cleanup(self) -> dict[str, Any]:
        errors: list[str] = []
        if self._started:
            try:
                self._server.shutdown()
            except OSError as exc:
                errors.append(f"shutdown:{type(exc).__name__}")
            self._started = False
        try:
            self._server.server_close()
        except OSError as exc:
            errors.append(f"server_close:{type(exc).__name__}")
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                errors.append("thread_still_alive")
        snapshot = self.snapshot()
        snapshot.update(
            {
                "all_owned_processes_terminated": not errors,
                "external_processes_touched": 0,
                "errors": errors,
            }
        )
        return snapshot
