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
from relaylm.relayref import build_relayref_dry_run_artifact


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
                "id": "chatcmpl-relayref-smoke",
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


def _last_metadata(trace_path: Path) -> dict[str, Any]:
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    require(bool(lines), "trace is empty")
    record = json.loads(lines[-1])
    metadata = record.get("metadata")
    require(isinstance(metadata, dict), record)
    return metadata


def _post_and_get_relayref(
    client: TestClient,
    trace_path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    resp = client.post("/v1/chat/completions", json=payload)
    require(resp.status_code == 200, resp.text)
    artifact = _last_metadata(trace_path).get("relayint_intent_artifact")
    require(isinstance(artifact, dict), _last_metadata(trace_path))
    return artifact


def _assert_no_backend_artifact(payload: dict[str, Any]) -> None:
    forbidden = {
        "relayint_intent_artifact",
        "relayscn_scene_policy_artifact",
        "context_rewrite",
        "forced_sleep_candidate",
        "persistence_guard",
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
                normal_payload = {
                    "model": "relaylm-default",
                    "messages": [{"role": "user", "content": "design policy mvp"}],
                    "metadata": {
                        "scene_state": {
                            "scene_type": "design_talk",
                            "confidence": 0.95,
                            "stability": 0.9,
                        }
                    },
                    "stream": False,
                }
                normal = _post_and_get_relayref(client, trace_path, normal_payload)
                require(normal["mode"] in {"none", "suggest_reflect"}, normal)
                require(normal["apply_allowed"] is False, normal)
                require(normal["auto_resume_allowed"] is False, normal)
                require(normal["persistence_guard"]["persistence_block"] is False, normal)
                _assert_no_backend_artifact(capture.last())
                require(
                    capture.last().get("metadata") == normal_payload["metadata"],
                    capture.last(),
                )
                print("ok normal scene emits dry-run RelayREF without backend mutation")

                recovery_payload = {
                    "model": "relaylm-default",
                    "messages": [{"role": "user", "content": "何の話だったっけ"}],
                    "metadata": {
                        "scene_state": {
                            "scene_type": "recovery",
                            "confidence": 0.95,
                            "stability": 0.9,
                        },
                        "ctx_handoff_guess": "RelayREF recovery discussion",
                    },
                    "stream": False,
                }
                recovery = _post_and_get_relayref(client, trace_path, recovery_payload)
                require(recovery["mode"] == "context_repair", recovery)
                require(recovery["auto_resume_allowed"] is False, recovery)
                require(recovery["context_rewrite"]["applied"] is False, recovery)
                require(
                    recovery["ctx_handoff_guess"]["use_as"] == "confirmation_candidate",
                    recovery,
                )
                require(recovery["ctx_handoff_guess"]["auto_resume_allowed"] is False, recovery)
                require(recovery["persistence_guard"]["persistence_block"] is True, recovery)
                require(
                    "scene_type_is_recovery"
                    in recovery["persistence_guard"]["persistence_block_reasons"],
                    recovery,
                )
                require(recovery["forced_sleep_candidate"]["apply_allowed"] is False, recovery)
                _assert_no_backend_artifact(capture.last())
                require(
                    capture.last().get("metadata") == recovery_payload["metadata"],
                    capture.last(),
                )
                print("ok recovery scene emits context_repair and confirmation-only handoff")

                metadata = _last_metadata(trace_path)
                require(isinstance(metadata.get("relayint_intent_artifact"), dict), metadata)
                print("ok trace metadata includes relayint_intent_artifact")

        malformed = build_relayref_dry_run_artifact(relayscn_artifact={"bad": "shape"})
        require(malformed["diagnostics_only"] is True, malformed)
        require(malformed["apply_allowed"] is False, malformed)
        require(malformed["persistence_guard"]["persistence_block"] is True, malformed)
        require("malformed_relayscn_artifact" in malformed["mode_reasons"], malformed)
        print("ok malformed RelaySCN artifact fails closed")
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
