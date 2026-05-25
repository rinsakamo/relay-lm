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
from relaylm.config import RelayLMConfig
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import resolve_route


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


class _Capture:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.payloads.append(payload)

    def last(self) -> dict[str, Any]:
        with self._lock:
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
            "id": "chatcmpl-shadow-smoke",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
        }
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _write_config(base_url: str, trace_path: Path) -> Path:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    backend_name = next(iter(cfg["backends"].keys()))
    cfg["backends"][backend_name]["base_url"] = f"{base_url}/v1"
    cfg["backends"][backend_name]["api_key"] = None
    cfg["model_routes"]["relaylm-default"]["backend"] = backend_name
    cfg["model_routes"]["relaylm-default"]["mode"] = "memory_light"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    fd, path = tempfile.mkstemp(prefix="relaylm-shadow-scope-", suffix=".yaml")
    Path(path).write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return Path(path)


def _read_last_meta(trace_path: Path) -> dict[str, Any]:
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    require(lines, "empty trace")
    record = json.loads(lines[-1])
    metadata = record.get("metadata")
    require(isinstance(metadata, dict), metadata)
    return metadata


def main() -> int:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = Path(tmpdir) / "trace.jsonl"
            config_path = _write_config(f"http://127.0.0.1:{port}", trace_path)
            app = create_app(str(config_path))
            payload = {
                "model": "relaylm-default",
                "messages": [{"role": "user", "content": "hello"}],
                "metadata": {
                    "user_id": "meta-user",
                    "room_id": "meta-room",
                    "scene_id": "meta-scene",
                    "session_id": "meta-session",
                },
                "stream": False,
            }
            before_payload = copy.deepcopy(payload)
            with TestClient(app) as client:
                response = client.post("/v1/chat/completions", json=payload)
            require(response.status_code == 200, response.text)
            require(payload == before_payload, (payload, before_payload))
            _ = capture.last()
            meta = _read_last_meta(trace_path)
            base = meta.get("memory_adapter_dry_run")
            shadow = meta.get("memory_adapter_shadow_dry_run")
            base_ready = meta.get("memory_adapter_readiness")
            shadow_ready = meta.get("memory_adapter_shadow_readiness")
            require(isinstance(base, dict), base)
            require(isinstance(shadow, dict), shadow)
            require(isinstance(base_ready, dict), base_ready)
            require(isinstance(shadow_ready, dict), shadow_ready)
            require(base.get("scope_isolation_status") == "partial_scope", base)
            require(shadow.get("scope_isolation_status") == "ok", shadow)
            require(shadow.get("shadow_source") == "scope_resolution_merged_scope", shadow)
            require(base.get("candidate_ids") == shadow.get("candidate_ids"), (base, shadow))
            require(base.get("selected_candidate_ids") == shadow.get("selected_candidate_ids"), (base, shadow))
            require(base_ready.get("blocked_reason") == "partial_scope", base_ready)
            require(shadow_ready.get("blocked_reason") is None, shadow_ready)
            print("ok shadow dry-run uses merged scope and preserves candidate diagnostics")

            # conflict case: route user_id wins over request user_id
            trace_conflict = Path(tmpdir) / "trace-conflict.jsonl"
            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            cfg["trace"]["path"] = str(trace_conflict)
            cfg["model_routes"]["relaylm-default"]["user_id"] = "route-user"
            Path(config_path).write_text(yaml.safe_dump(cfg), encoding="utf-8")
            app_conflict = create_app(str(config_path))
            conflict_payload = copy.deepcopy(payload)
            conflict_payload["metadata"]["user_id"] = "request-user"
            with TestClient(app_conflict) as client:
                response2 = client.post("/v1/chat/completions", json=conflict_payload)
            require(response2.status_code == 200, response2.text)
            meta2 = _read_last_meta(trace_conflict)
            scope_diag = meta2.get("scope_resolution_diagnostics")
            shadow2 = meta2.get("memory_adapter_shadow_dry_run")
            require(isinstance(scope_diag, dict), scope_diag)
            require(scope_diag.get("resolution_status") == "conflict", scope_diag)
            require("user_id" in scope_diag.get("conflict_fields", []), scope_diag)
            require(isinstance(shadow2, dict), shadow2)
            shadow_scope = shadow2.get("scope")
            require(isinstance(shadow_scope, dict), shadow_scope)
            require(shadow_scope.get("user_id") == "route-user", shadow_scope)
            print("ok shadow dry-run uses route-priority merged scope for conflicts")

            # pass-through: shadow diagnostics unset
            trace_pass = Path(tmpdir) / "trace-pass.jsonl"
            cfg_pass = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            cfg_pass["trace"]["path"] = str(trace_pass)
            cfg_pass["model_routes"]["relaylm-default"]["mode"] = "pass_through"
            Path(config_path).write_text(yaml.safe_dump(cfg_pass), encoding="utf-8")
            app_pass = create_app(str(config_path))
            with TestClient(app_pass) as client:
                response3 = client.post("/v1/chat/completions", json={"model": "relaylm-default", "messages": [{"role": "user", "content": "x"}], "stream": False})
            require(response3.status_code == 200, response3.text)
            meta3 = _read_last_meta(trace_pass)
            require(meta3.get("memory_adapter_dry_run") is None, meta3)
            require(meta3.get("memory_adapter_shadow_dry_run") is None, meta3)
            require(meta3.get("memory_adapter_shadow_readiness") is None, meta3)
            require(meta3.get("memory_adapter_shadow_conflicts") is None, meta3)
            print("ok pass-through keeps shadow adapter diagnostics unset")
        return 0
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
