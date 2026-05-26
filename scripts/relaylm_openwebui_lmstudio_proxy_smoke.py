from __future__ import annotations

import json
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.app import create_app
from relaylm.config import load_config
from relaylm.routing import resolve_route


class _Capture:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.payloads.append(payload)

    def last(self) -> dict[str, Any]:
        with self._lock:
            if not self.payloads:
                raise AssertionError("no backend payload captured")
            return self.payloads[-1]


class _BackendHandler(BaseHTTPRequestHandler):
    capture: _Capture

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/v1/models":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"object": "list", "data": [{"id": "local-model", "object": "model"}]}).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        type(self).capture.add(payload)

        if payload.get("stream") is True:
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.end_headers()
            chunks = [
                'data: {"id":"chatcmpl-smoke","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant"}}]}\n\n',
                'data: {"id":"chatcmpl-smoke","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"ok"}}]}\n\n',
                "data: [DONE]\n\n",
            ]
            for c in chunks:
                self.wfile.write(c.encode("utf-8"))
                self.wfile.flush()
            return

        body = json.dumps(
            {
                "id": "chatcmpl-smoke",
                "object": "chat.completion",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _write_temp_config(base_url: str) -> Path:
    base = load_config(REPO_ROOT / "examples/config/openwebui_lmstudio.yaml").model_dump()
    base["backends"]["lmstudio_backend"]["base_url"] = f"{base_url}/v1"

    fd, path = tempfile.mkstemp(prefix="relaylm-openwebui-proxy-", suffix=".yaml")
    Path(path).write_text(yaml.safe_dump(base), encoding="utf-8")
    return Path(path)


def main() -> int:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        config_path = _write_temp_config(f"http://127.0.0.1:{port}")
        app = create_app(str(config_path))

        with TestClient(app) as client:
            models = client.get("/v1/models")
            require(models.status_code == 200, models.text)
            ids = [m.get("id") for m in models.json().get("data", []) if isinstance(m, dict)]
            require("relaylm-companion" in ids, ids)
            require("relaylm-work-assistant" in ids, ids)
            require("relaylm-code-reviewer" in ids, ids)
            print("ok /v1/models route ids")

            payload = {
                "model": "relaylm-work-assistant",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": False,
            }
            resp = client.post("/v1/chat/completions", json=payload)
            require(resp.status_code == 200, resp.text)
            backend_payload = capture.last()
            require(backend_payload.get("model") == "local-model", backend_payload)
            require(backend_payload.get("stream") is False, backend_payload)
            route = resolve_route(load_config(config_path), "relaylm-work-assistant")
            require(route.character_id == "work_assistant", route)
            print("ok non-stream proxy forward and model mapping")

            stream_payload = {
                "model": "relaylm-code-reviewer",
                "messages": [{"role": "user", "content": "hello stream"}],
                "stream": True,
            }
            with client.stream("POST", "/v1/chat/completions", json=stream_payload) as stream_resp:
                require(stream_resp.status_code == 200, stream_resp.status_code)
                body = "".join(stream_resp.iter_text())
            require("data:" in body and "[DONE]" in body, body)
            backend_payload_stream = capture.last()
            require(backend_payload_stream.get("model") == "local-model", backend_payload_stream)
            require(backend_payload_stream.get("stream") is True, backend_payload_stream)
            route2 = resolve_route(load_config(config_path), "relaylm-code-reviewer")
            require(route2.character_id == "code_reviewer", route2)
            print("ok stream proxy forward and sse")

    finally:
        server.shutdown()
        server.server_close()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
