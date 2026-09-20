from __future__ import annotations

import ast
import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

from tools import v1_external_qualification_synthetic_capture as capture


_TRUNCATED_CONTENT = '{"facts":[{"what":"drawer seven"},{"what":"drawer seven"'
_RESPONSE_BODY = json.dumps(
    {
        "id": "synthetic-response",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": _TRUNCATED_CONTENT,
                },
                "finish_reason": "length",
            }
        ],
        "usage": {
            "prompt_tokens": 321,
            "completion_tokens": 4096,
            "total_tokens": 4417,
        },
    },
    separators=(",", ":"),
).encode("utf-8")


class _UpstreamHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(_RESPONSE_BODY)))
        self.end_headers()
        self.wfile.write(_RESPONSE_BODY)

    def do_GET(self) -> None:  # noqa: N802
        body = b'{"data":[]}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _start_upstream() -> tuple[ThreadingHTTPServer, threading.Thread]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _UpstreamHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_capture_proxy_preserves_chat_response_and_records_truncation(
    tmp_path: Path,
) -> None:
    upstream, upstream_thread = _start_upstream()
    port = int(upstream.server_address[1])
    proxy = capture.SyntheticLlamaCaptureProxy(
        upstream_base_url=f"http://127.0.0.1:{port}/v1",
        artifact_root=(tmp_path / "capture").resolve(),
    )
    try:
        proxy.start()
        with httpx.Client(timeout=5.0, trust_env=False) as client:
            response = client.post(
                f"{proxy.base_url}/chat/completions",
                json={"model": "synthetic", "messages": [{"role": "user", "content": "x"}]},
            )
        assert response.status_code == 200
        assert response.content == _RESPONSE_BODY
    finally:
        evidence = proxy.cleanup()
        upstream.shutdown()
        upstream.server_close()
        upstream_thread.join(timeout=5.0)

    assert evidence["errors"] == []
    assert evidence["all_owned_processes_terminated"] is True
    assert evidence["request_count"] == 1
    assert evidence["chat_completion_capture_count"] == 1
    item = evidence["captures"][0]
    assert item["status_code"] == 200
    assert item["response_body_sha256"] == hashlib.sha256(_RESPONSE_BODY).hexdigest()
    assert item["response_body_bytes"] == len(_RESPONSE_BODY)

    summary = item["summary"]
    assert summary["finish_reason"] == "length"
    assert summary["completion_tokens"] == 4096
    assert summary["message_content_chars"] == len(_TRUNCATED_CONTENT)
    assert summary["message_content_json_parseable"] is False
    assert summary["field_occurrences"]["facts"] == 1
    assert summary["field_occurrences"]["what"] == 2

    raw_path = Path(item["response_body_path"])
    metadata_path = Path(item["metadata_path"])
    assert raw_path.read_bytes() == _RESPONSE_BODY
    assert hashlib.sha256(metadata_path.read_bytes()).hexdigest() == item["metadata_sha256"]


def test_capture_proxy_does_not_capture_non_chat_routes(tmp_path: Path) -> None:
    upstream, upstream_thread = _start_upstream()
    port = int(upstream.server_address[1])
    proxy = capture.SyntheticLlamaCaptureProxy(
        upstream_base_url=f"http://127.0.0.1:{port}/v1",
        artifact_root=(tmp_path / "capture-models").resolve(),
    )
    try:
        proxy.start()
        with httpx.Client(timeout=5.0, trust_env=False) as client:
            response = client.get(f"http://127.0.0.1:{proxy.port}/v1/models")
        assert response.status_code == 200
        assert response.json() == {"data": []}
    finally:
        evidence = proxy.cleanup()
        upstream.shutdown()
        upstream.server_close()
        upstream_thread.join(timeout=5.0)

    assert evidence["request_count"] == 1
    assert evidence["chat_completion_capture_count"] == 0
    assert evidence["captures"] == []


def test_capture_proxy_has_no_scientific_ledger_dependency() -> None:
    source = Path(capture.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "ScientificSpendLedger" not in imported_names
