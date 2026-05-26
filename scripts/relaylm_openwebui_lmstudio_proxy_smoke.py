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
from relaylm.config import RelayLMConfig
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
        body = json.dumps(
            {
                "object": "list",
                "data": [{"id": "local-model", "object": "model", "owned_by": "fake-backend"}],
            }
        ).encode("utf-8")
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
            chunks = [
                'data: {"id":"chatcmpl-smoke","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"ok"}}]}\n\n',
                "data: [DONE]\n\n",
            ]
            body = "".join(chunks).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("cache-control", "no-cache")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        response = {
            "id": "chatcmpl-smoke",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
        }
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _temp_config(base_url: str) -> Path:
    base = yaml.safe_load((REPO_ROOT / "examples/config/openwebui_lmstudio.yaml").read_text(encoding="utf-8"))
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

    config_path = _temp_config(f"http://127.0.0.1:{port}")

    try:
        config = RelayLMConfig.model_validate(yaml.safe_load(config_path.read_text(encoding="utf-8")) or {})
        for route_model, expected_character in {
            "relaylm-companion": "companion",
            "relaylm-work-assistant": "work_assistant",
            "relaylm-code-reviewer": "code_reviewer",
        }.items():
            route = resolve_route(config, route_model)
            require(route.character_id == expected_character, route)
        print("ok route-specific character resolution")

        app = create_app(str(config_path))
        with TestClient(app) as client:
            models_resp = client.get("/v1/models")
            require(models_resp.status_code == 200, models_resp.text)
            data = models_resp.json().get("data", [])
            ids = [x.get("id") for x in data if isinstance(x, dict)]
            require("relaylm-companion" in ids, ids)
            require("relaylm-work-assistant" in ids, ids)
            require("relaylm-code-reviewer" in ids, ids)
            print("ok /v1/models route ids")

            non_stream_payload = {
                "model": "relaylm-companion",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": False,
            }
            non_stream_resp = client.post("/v1/chat/completions", json=non_stream_payload)
            require(non_stream_resp.status_code == 200, non_stream_resp.text)
            require(isinstance(non_stream_resp.json(), dict), non_stream_resp.text)
            forwarded = capture.last()
            require(forwarded.get("model") == "local-model", forwarded)
            require(forwarded.get("stream") is False, forwarded)
            print("ok non-stream proxy forwarding")

            stream_payload = {
                "model": "relaylm-code-reviewer",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
            }
            with client.stream("POST", "/v1/chat/completions", json=stream_payload) as stream_resp:
                require(stream_resp.status_code == 200, stream_resp.status_code)
                body = "".join(stream_resp.iter_text())
            require("data:" in body and "[DONE]" in body, body)
            forwarded_stream = capture.last()
            require(forwarded_stream.get("model") == "local-model", forwarded_stream)
            require(forwarded_stream.get("stream") is True, forwarded_stream)
            print("ok stream proxy forwarding and sse")

    finally:
        server.shutdown()
        server.server_close()
        try:
            config_path.unlink(missing_ok=True)
        except OSError:
            pass

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
