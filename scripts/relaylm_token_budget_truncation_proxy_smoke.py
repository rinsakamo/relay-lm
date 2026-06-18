from __future__ import annotations

import copy
import json
import os
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
        type(self).capture.add(json.loads(raw.decode("utf-8")) if raw else {})
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


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _write_config(
    base_url: str,
    *,
    trunc_enabled: bool,
    token_budget: int,
    trace_path: Path,
) -> Path:
    raw = load_config(REPO_ROOT / "config.example.yaml").model_dump()
    backend_name = next(iter(raw["backends"]))
    route = raw["model_routes"]["relaylm-default"]
    route["backend"] = backend_name
    route["mode"] = "memory_light"
    character_id = route.get("character_id")
    if isinstance(character_id, str) and character_id in raw["characters"]:
        raw["characters"][character_id]["memory_seed_path"] = None
    raw["backends"][backend_name]["base_url"] = f"{base_url}/v1"
    raw["backends"][backend_name]["api_key"] = None
    raw["memory"]["token_budget_truncation_enabled"] = trunc_enabled
    raw["memory"]["token_budget"] = token_budget
    raw["memory"]["chars_per_token"] = 4
    raw["trace"] = {"enabled": True, "path": str(trace_path)}

    fd, path = tempfile.mkstemp(prefix="relaylm-proxy-smoke-", suffix=".yaml")
    os.close(fd)
    result = Path(path)
    result.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return result


def _compiled_messages(config_path: Path, payload: dict[str, Any]) -> list[dict[str, Any]]:
    config = RelayLMConfig.model_validate(
        yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    )
    route = resolve_route(config, str(payload.get("model", "")))
    compiled = compile_chat_payload_if_enabled(
        config=config,
        route=route,
        payload=payload,
    )
    messages = compiled.payload.get("messages")
    if not isinstance(messages, list):
        raise AssertionError(compiled.payload)
    return messages


def _post_and_capture(
    config_path: Path,
    payload: dict[str, Any],
    capture: _Capture,
) -> tuple[dict[str, Any], dict[str, str]]:
    app = create_app(str(config_path))
    with TestClient(app) as client:
        response = client.post("/v1/chat/completions", json=payload)
    require(response.status_code == 200, response.text)
    return capture.last(), dict(response.headers)


def _trace_truncation(trace_path: Path) -> dict[str, Any]:
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    require(bool(lines), "trace lines empty")
    metadata = json.loads(lines[-1]).get("metadata")
    require(isinstance(metadata, dict), metadata)
    truncation = metadata.get("token_budget_truncation")
    require(isinstance(truncation, dict), metadata)
    return truncation


def main() -> int:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    payload = {
        "model": "relaylm-default",
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "assistant", "content": "assistant " * 20_000},
            {"role": "assistant", "content": "assistant 2 " * 20_000},
            {"role": "user", "content": "latest user"},
        ],
        "stream": False,
        "temperature": 0.2,
    }

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            trace_default = root / "trace-default.jsonl"
            cfg_default = _write_config(
                f"http://127.0.0.1:{server.server_address[1]}",
                trunc_enabled=False,
                token_budget=30,
                trace_path=trace_default,
            )
            baseline = _compiled_messages(cfg_default, copy.deepcopy(payload))
            backend_default, headers = _post_and_capture(cfg_default, payload, capture)
            require(backend_default.get("messages") == baseline, backend_default)
            require(headers.get("x-relaylm-mode") == "memory_light", headers)
            require(headers.get("x-relaylm-memory-block-used") == "false", headers)
            require(headers.get("x-relaylm-compiler-used") == "true", headers)
            require(_trace_truncation(trace_default).get("applied") is False, trace_default)
            print("ok proxy truncation default disabled keeps backend payload unchanged")

            trace_apply = root / "trace-apply.jsonl"
            cfg_apply = _write_config(
                f"http://127.0.0.1:{server.server_address[1]}",
                trunc_enabled=True,
                token_budget=50_000,
                trace_path=trace_apply,
            )
            baseline_apply = _compiled_messages(cfg_apply, copy.deepcopy(payload))
            backend_apply, _ = _post_and_capture(cfg_apply, payload, capture)
            backend_messages = backend_apply.get("messages")
            require(isinstance(backend_messages, list), backend_apply)
            require(len(backend_messages) < len(baseline_apply), backend_apply)
            require(backend_messages[0].get("role") == "system", backend_apply)
            require(backend_messages[-1].get("role") == "user", backend_apply)
            require(backend_apply.get("model") == "local-model", backend_apply)
            require(backend_apply.get("stream") is False, backend_apply)
            require(backend_apply.get("temperature") == 0.2, backend_apply)
            require(_trace_truncation(trace_apply).get("applied") is True, trace_apply)
            print("ok proxy truncation enabled sends bounded backend payload")

            blocked_payload = {
                "model": "relaylm-default",
                "messages": [
                    {"role": "system", "content": "S" * 200},
                    {"role": "user", "content": "U" * 200},
                ],
                "stream": False,
            }
            trace_blocked = root / "trace-blocked.jsonl"
            cfg_blocked = _write_config(
                f"http://127.0.0.1:{server.server_address[1]}",
                trunc_enabled=True,
                token_budget=5,
                trace_path=trace_blocked,
            )
            blocked_baseline = _compiled_messages(
                cfg_blocked,
                copy.deepcopy(blocked_payload),
            )
            backend_blocked, _ = _post_and_capture(
                cfg_blocked,
                blocked_payload,
                capture,
            )
            require(backend_blocked.get("messages") == blocked_baseline, backend_blocked)
            blocked = _trace_truncation(trace_blocked)
            require(blocked.get("applied") is False, blocked)
            require(blocked.get("blocked_reason") == "preserved_messages_exceed_budget", blocked)
            print("ok proxy truncation blocked keeps backend payload unchanged")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
