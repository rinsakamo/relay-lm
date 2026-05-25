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
            "id": "chatcmpl-shadow-delta-smoke",
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
    fd, path = tempfile.mkstemp(prefix="relaylm-shadow-delta-", suffix=".yaml")
    Path(path).write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return Path(path)


def _last_meta(trace_path: Path) -> dict[str, Any]:
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    require(lines, "empty trace")
    rec = json.loads(lines[-1])
    meta = rec.get("metadata")
    require(isinstance(meta, dict), meta)
    return meta


def main() -> int:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            trace = Path(tmpdir) / "trace.jsonl"
            cfg_path = _write_config(f"http://127.0.0.1:{port}", trace)
            app = create_app(str(cfg_path))
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
            before = copy.deepcopy(payload)
            with TestClient(app) as client:
                res = client.post("/v1/chat/completions", json=payload)
            require(res.status_code == 200, res.text)
            require(payload == before, (payload, before))
            _ = capture.last()
            meta = _last_meta(trace)
            delta = meta.get("memory_adapter_shadow_delta")
            require(isinstance(delta, dict), delta)
            require(delta.get("delta_status") == "improved", delta)
            require(delta.get("scope_improved") is True, delta)
            require(delta.get("readiness_improved") is True, delta)
            require(delta.get("candidate_ids_changed") is False, delta)
            require(delta.get("selected_candidate_ids_changed") is False, delta)
            changed_fields = delta.get("changed_scope_fields")
            require(isinstance(changed_fields, list), delta)
            for field in ("user_id", "room_id", "scene_id", "session_id"):
                require(field in changed_fields, changed_fields)
            print("ok shadow delta reports improved scope/readiness without candidate changes")

            # conflict but route-priority merge should not regress
            trace_conflict = Path(tmpdir) / "trace-conflict.jsonl"
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
            cfg["trace"]["path"] = str(trace_conflict)
            cfg["model_routes"]["relaylm-default"]["user_id"] = "route-user"
            Path(cfg_path).write_text(yaml.safe_dump(cfg), encoding="utf-8")
            app_conflict = create_app(str(cfg_path))
            conflict_payload = copy.deepcopy(payload)
            conflict_payload["metadata"]["user_id"] = "request-user"
            with TestClient(app_conflict) as client:
                res2 = client.post("/v1/chat/completions", json=conflict_payload)
            require(res2.status_code == 200, res2.text)
            meta2 = _last_meta(trace_conflict)
            delta2 = meta2.get("memory_adapter_shadow_delta")
            require(isinstance(delta2, dict), delta2)
            require(delta2.get("candidate_ids_changed") is False, delta2)
            require(delta2.get("selected_candidate_ids_changed") is False, delta2)
            require(delta2.get("delta_status") != "regressed", delta2)
            print("ok shadow delta conflict path does not regress candidates")

            # pass-through leaves delta unset
            trace_pass = Path(tmpdir) / "trace-pass.jsonl"
            cfg_pass = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
            cfg_pass["trace"]["path"] = str(trace_pass)
            cfg_pass["model_routes"]["relaylm-default"]["mode"] = "pass_through"
            Path(cfg_path).write_text(yaml.safe_dump(cfg_pass), encoding="utf-8")
            app_pass = create_app(str(cfg_path))
            with TestClient(app_pass) as client:
                res3 = client.post("/v1/chat/completions", json={"model": "relaylm-default", "messages": [{"role": "user", "content": "x"}], "stream": False})
            require(res3.status_code == 200, res3.text)
            meta3 = _last_meta(trace_pass)
            require(meta3.get("memory_adapter_shadow_delta") is None, meta3)
            print("ok pass-through keeps shadow delta unset")
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

