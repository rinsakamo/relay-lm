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
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        raw = self.rfile.read(int(self.headers.get("content-length", "0")))
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        type(self).capture.add(payload)
        body = json.dumps({
            "id": "chatcmpl-smoke",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    port = int(server.server_address[1])
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    with tempfile.TemporaryDirectory() as td:
        cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
        cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
        cfg["trace"] = {"enabled": True, "path": str(Path(td) / "trace.jsonl")}
        cfg["model_routes"]["relaylm-default"]["mode"] = "memory_light"
        cfg_path = Path(td) / "cfg.yaml"
        cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

        app = create_app(str(cfg_path))
        with TestClient(app) as client:
            payload = {
                "model": "relaylm-default",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": False,
            }
            resp = client.post("/v1/chat/completions", json=payload)
            require(resp.status_code == 200, resp.text)
            require(capture.last().get("model") == "local-model", capture.last())
            require("compile_decision_dry_run" not in capture.last(), capture.last())
            print("ok request path non-stream and no payload mutation")

        trace_text = (Path(td) / "trace.jsonl").read_text(encoding="utf-8")
        record = json.loads(trace_text.strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        dry = metadata.get("compile_decision_dry_run")
        require(isinstance(dry, dict), record)
        require(dry.get("decision_state") == "COMPILE_APPLY", dry)
        require(dry.get("apply_compiled_messages") is True, dry)
        require(dry.get("diagnostics_only") is False, dry)
        require(dry.get("selected_route") == "relaylm-default", dry)
        require(dry.get("selected_mode") == "memory_light", dry)
        require(dry.get("backend") == "local_backend", dry)
        require(dry.get("compiled_message_count") == 2, dry)
        require("messages" not in dry and "prompt" not in dry and "content" not in dry, dry)
        print("ok trace includes compile decision dry-run metadata")


    with tempfile.TemporaryDirectory() as td2:
        cfg2 = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
        cfg2["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
        cfg2["trace"] = {"enabled": True, "path": str(Path(td2) / "trace.jsonl")}
        cfg2["model_routes"]["relaylm-default"]["mode"] = "pass_through"
        cfg2_path = Path(td2) / "cfg.yaml"
        cfg2_path.write_text(yaml.safe_dump(cfg2), encoding="utf-8")

        app2 = create_app(str(cfg2_path))
        with TestClient(app2) as client:
            payload2 = {
                "model": "relaylm-default",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": False,
            }
            resp2 = client.post("/v1/chat/completions", json=payload2)
            require(resp2.status_code == 200, resp2.text)

        trace_text2 = (Path(td2) / "trace.jsonl").read_text(encoding="utf-8")
        record2 = json.loads(trace_text2.strip().splitlines()[-1])
        dry2 = record2.get("metadata", {}).get("compile_decision_dry_run")
        require(isinstance(dry2, dict), record2)
        require(dry2.get("selected_mode") == "pass_through", dry2)
        require(dry2.get("decision_state") == "COMPILE_DRY_RUN", dry2)
        require(dry2.get("apply_compiled_messages") is False, dry2)
        require(dry2.get("diagnostics_only") is True, dry2)
        require(dry2.get("compiled_message_count") != 1, dry2)
        print("ok pass_through compile count is not forwarded input count")

    server.shutdown()
    server.server_close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
