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
from relaylm.relayscn import build_relayscn_scene_policy_artifact


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
        body = json.dumps(
            {
                "id": "chatcmpl-relayscn-smoke",
                "object": "chat.completion",
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "ok"}}
                ],
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


def _last_relayscn_artifact(trace_path: Path) -> dict[str, Any]:
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    require(bool(lines), "trace is empty")
    record = json.loads(lines[-1])
    artifact = record.get("metadata", {}).get("relayscn_scene_policy_artifact")
    require(isinstance(artifact, dict), record)
    return artifact


def _post_and_get_artifact(
    client: TestClient,
    trace_path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    resp = client.post("/v1/chat/completions", json=payload)
    require(resp.status_code == 200, resp.text)
    return _last_relayscn_artifact(trace_path)


def _assert_no_backend_artifact(payload: dict[str, Any]) -> None:
    forbidden = {
        "relayscn_scene_policy_artifact",
        "scene_policy",
        "persistence_block",
        "persistence_block_reasons",
        "diagnostics_required",
    }
    require(forbidden.isdisjoint(payload), payload)


def main() -> int:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with tempfile.TemporaryDirectory() as td:
            trace_path = Path(td) / "trace.jsonl"
            cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
            cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
            cfg["trace"] = {"enabled": True, "path": str(trace_path)}
            cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
            cfg_path = Path(td) / "cfg.yaml"
            cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

            app = create_app(str(cfg_path))
            with TestClient(app) as client:
                default_payload = {
                    "model": "relaylm-default",
                    "messages": [{"role": "user", "content": "hello"}],
                    "stream": False,
                }
                default_artifact = _post_and_get_artifact(client, trace_path, default_payload)
                require(default_artifact["diagnostics_only"] is True, default_artifact)
                require("scene_state" in default_artifact, default_artifact)
                require("scene_policy" in default_artifact, default_artifact)
                require(isinstance(default_artifact["persistence_block"], bool), default_artifact)
                require(
                    isinstance(default_artifact["persistence_block_reasons"], list),
                    default_artifact,
                )
                require(default_artifact["diagnostics_required"] is True, default_artifact)
                _assert_no_backend_artifact(capture.last())
                print(
                    "ok default request emits RelaySCN artifact "
                    "without backend artifact mutation"
                )

                recovery_payload = {
                    "model": "relaylm-default",
                    "messages": [{"role": "user", "content": "continue"}],
                    "metadata": {
                        "scene_state": {
                            "scene_type": "recovery",
                            "confidence": 0.95,
                            "stability": 0.9,
                        }
                    },
                    "stream": False,
                }
                recovery_artifact = _post_and_get_artifact(client, trace_path, recovery_payload)
                recovery_policy = recovery_artifact["scene_policy"]
                require(
                    recovery_policy["relaymem_retrieval_scope"] == "current_context_only",
                    recovery_artifact,
                )
                require(recovery_artifact["persistence_block"] is True, recovery_artifact)
                require(
                    "scene_type_is_recovery"
                    in recovery_artifact["persistence_block_reasons"],
                    recovery_artifact,
                )
                _assert_no_backend_artifact(capture.last())
                require(
                    capture.last().get("metadata") == recovery_payload["metadata"],
                    capture.last(),
                )
                print("ok recovery scene blocks persistence and keeps current_context_only")

                for scene_type, reason in (
                    ("formal_document", "scene_type_is_formal_document"),
                    ("medical_or_safety", "scene_type_is_medical_or_safety"),
                ):
                    artifact = _post_and_get_artifact(
                        client,
                        trace_path,
                        {
                            "model": "relaylm-default",
                            "messages": [{"role": "user", "content": scene_type}],
                            "metadata": {
                                "scene_state": {
                                    "scene_type": scene_type,
                                    "confidence": 0.95,
                                    "stability": 0.9,
                                }
                            },
                            "stream": False,
                        },
                    )
                    require(artifact["persistence_block"] is True, artifact)
                    require(reason in artifact["persistence_block_reasons"], artifact)
                print("ok formal_document and medical_or_safety scenes block persistence")

        unknown = build_relayscn_scene_policy_artifact(
            payload={"metadata": {"scene_state": {"scene_type": "future_scene"}}}
        )
        require(unknown["scene_state"]["scene_type"] == "unknown", unknown)
        require(unknown["persistence_block"] is True, unknown)
        require("unknown_scene" in unknown["persistence_block_reasons"], unknown)
        print("ok unknown scene fails closed")
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
