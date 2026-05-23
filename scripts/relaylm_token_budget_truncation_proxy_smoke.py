from __future__ import annotations

import copy
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
from relaylm.config import RelayLMConfig, load_config
from relaylm.request_compiler import compile_chat_payload_if_enabled
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

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        type(self).capture.add(payload)
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



def _write_config(base_url: str, trunc_enabled: bool, token_budget: int, trace_path: Path) -> Path:
    base = load_config(REPO_ROOT / "config.example.yaml").model_dump()
    backend_name = next(iter(base["backends"].keys()))
    base["backends"][backend_name]["base_url"] = f"{base_url}/v1"
    base["backends"][backend_name]["api_key"] = None
    base["model_routes"]["relaylm-default"]["backend"] = backend_name
    base["model_routes"]["relaylm-default"]["mode"] = "memory_light"
    base["memory"]["token_budget_truncation_enabled"] = trunc_enabled
    base["memory"]["token_budget"] = token_budget
    base["memory"]["chars_per_token"] = 4
    base["trace"] = {"enabled": True, "path": str(trace_path)}

    fd, path = tempfile.mkstemp(prefix="relaylm-proxy-smoke-", suffix=".yaml")
    Path(path).write_text(yaml.safe_dump(base), encoding="utf-8")
    return Path(path)




def _compiled_messages(config_path: Path, payload: dict[str, Any]) -> list[dict[str, Any]]:
    config = RelayLMConfig.model_validate(yaml.safe_load(config_path.read_text(encoding="utf-8")) or {})
    route = resolve_route(config, str(payload.get("model", "")))
    compiled = compile_chat_payload_if_enabled(config=config, route=route, payload=payload)
    messages = compiled.payload.get("messages")
    if not isinstance(messages, list):
        raise AssertionError(compiled.payload)
    return messages


def _post_and_capture(config_path: Path, payload: dict[str, Any], capture: _Capture) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    app = create_app(str(config_path))
    with TestClient(app) as client:
        response = client.post("/v1/chat/completions", json=payload)
    require(response.status_code == 200, response.text)
    require(isinstance(response.json(), dict), response.text)
    return response.json(), capture.last(), dict(response.headers)


def _assert_trace_applied(trace_path: Path, expected: bool) -> None:
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    require(lines, "trace lines empty")
    record = json.loads(lines[-1])
    metadata = record.get("metadata")
    require(isinstance(metadata, dict), metadata)
    tbt = metadata.get("token_budget_truncation")
    require(isinstance(tbt, dict), metadata)
    require(tbt.get("applied") is expected, tbt)


def main() -> int:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        payload = {
            "model": "relaylm-default",
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "assistant", "content": "assistant " * 20},
                {"role": "assistant", "content": "assistant 2 " * 20},
                {"role": "user", "content": "latest user"},
            ],
            "stream": False,
            "temperature": 0.2,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            trace_default = Path(tmpdir) / "trace-default.jsonl"
            cfg_default = _write_config(f"http://127.0.0.1:{port}", False, 30, trace_default)
            baseline = _compiled_messages(cfg_default, copy.deepcopy(payload))
            _, backend_payload_default, headers_default = _post_and_capture(cfg_default, payload, capture)
            require(backend_payload_default.get("messages") == baseline, backend_payload_default)
            require(headers_default.get("x-relaylm-mode") == "memory_light", headers_default)
            require(headers_default.get("x-relaylm-memory-block-used") == "true", headers_default)
            require(headers_default.get("x-relaylm-compiler-used") == "true", headers_default)
            _assert_trace_applied(trace_default, expected=False)
            print("ok proxy truncation default disabled keeps backend payload unchanged")

            trace_apply = Path(tmpdir) / "trace-apply.jsonl"
            cfg_apply = _write_config(f"http://127.0.0.1:{port}", True, 300, trace_apply)
            baseline_apply = _compiled_messages(cfg_apply, copy.deepcopy(payload))
            _, backend_payload_apply, _ = _post_and_capture(cfg_apply, payload, capture)
            backend_messages = backend_payload_apply.get("messages")
            require(isinstance(backend_messages, list), backend_payload_apply)
            require(len(backend_messages) < len(baseline_apply), backend_payload_apply)
            require(backend_messages[0].get("role") == "system", backend_payload_apply)
            require(backend_messages[-1].get("role") == "user", backend_payload_apply)
            require(backend_payload_apply.get("model") == payload["model"].replace("relaylm-default", "local-model"), backend_payload_apply)
            require(backend_payload_apply.get("stream") == payload["stream"], backend_payload_apply)
            require(backend_payload_apply.get("temperature") == payload["temperature"], backend_payload_apply)
            _assert_trace_applied(trace_apply, expected=True)
            print("ok proxy truncation enabled over budget sends truncated backend payload")

            blocked_payload = {
                "model": "relaylm-default",
                "messages": [
                    {"role": "system", "content": "S" * 200},
                    {"role": "user", "content": "U" * 200},
                ],
                "stream": False,
            }
            trace_blocked = Path(tmpdir) / "trace-blocked.jsonl"
            cfg_blocked = _write_config(f"http://127.0.0.1:{port}", True, 5, trace_blocked)
            blocked_baseline = _compiled_messages(cfg_blocked, copy.deepcopy(blocked_payload))
            _, backend_payload_blocked, _ = _post_and_capture(cfg_blocked, blocked_payload, capture)
            require(backend_payload_blocked.get("messages") == blocked_baseline, backend_payload_blocked)

            lines = trace_blocked.read_text(encoding="utf-8").strip().splitlines()
            require(lines, "trace blocked empty")
            meta = json.loads(lines[-1]).get("metadata")
            require(isinstance(meta, dict), meta)
            trunc = meta.get("token_budget_truncation")
            require(isinstance(trunc, dict), meta)
            require(trunc.get("applied") is False, trunc)
            require(isinstance(trunc.get("blocked_reason"), str) and trunc.get("blocked_reason"), trunc)
            print("ok proxy truncation blocked keeps backend payload unchanged")

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
