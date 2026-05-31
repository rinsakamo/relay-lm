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
from relaylm.relaymem_retrieval import build_relaymem_retrieval_dry_run_artifact


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
                "id": "chatcmpl-relaymem-retrieval-smoke",
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


def _post_and_get_retrieval(
    client: TestClient,
    trace_path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    resp = client.post("/v1/chat/completions", json=payload)
    require(resp.status_code == 200, resp.text)
    artifact = _last_metadata(trace_path).get("relaymem_retrieval_artifact")
    require(isinstance(artifact, dict), _last_metadata(trace_path))
    return artifact


def _scene_payload(scene_type: str, content: str | None = None) -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": content or scene_type}],
        "metadata": {
            "scene_state": {
                "scene_type": scene_type,
                "confidence": 0.95,
                "stability": 0.9,
            }
        },
        "stream": False,
    }


def _assert_no_backend_artifact(payload: dict[str, Any]) -> None:
    forbidden = {
        "relaymem_retrieval_artifact",
        "relayref_artifact",
        "relayscn_scene_policy_artifact",
        "ctx_block",
        "selected",
        "blocked",
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
                design_payload = _scene_payload("design_talk", "RelayMEM retrieval design")
                design = _post_and_get_retrieval(client, trace_path, design_payload)
                require(design["artifact_version"] == "relaymem_retrieval.v0", design)
                require(design["diagnostics_only"] is True, design)
                require(design["apply_allowed"] is False, design)
                require(design["retrieval_scope"] == "project_context", design)
                require(design["fallback_reason"] == "memory_store_not_configured", design)
                require(design["selected"] == [], design)
                require(design["ctx_block"] is None, design)
                require(design["used_tokens"] == 0, design)
                _assert_no_backend_artifact(capture.last())
                require(
                    capture.last().get("metadata") == design_payload["metadata"],
                    capture.last(),
                )
                print("ok design_talk emits dry-run retrieval with no store fallback")

                recovery_payload = _scene_payload("recovery", "何の話だったっけ")
                recovery = _post_and_get_retrieval(client, trace_path, recovery_payload)
                require(recovery["retrieval_scope"] == "current_context_only", recovery)
                require(recovery["selected"] == [], recovery)
                require(
                    recovery["fallback_reason"] == "unresolved_reference_requires_confirmation",
                    recovery,
                )
                require(recovery["persistence_block"] is True, recovery)
                require("scene_type_is_recovery" in recovery["persistence_block_reasons"], recovery)
                _assert_no_backend_artifact(capture.last())
                print("ok recovery retrieval stays current-context-only and blocked")

                for scene_type in ("medical_or_safety", "formal_document"):
                    artifact = _post_and_get_retrieval(
                        client,
                        trace_path,
                        _scene_payload(scene_type),
                    )
                    require(artifact["selected"] == [], artifact)
                    require(
                        artifact["fallback_reason"] == "external_memory_blocked_by_scene_policy",
                        artifact,
                    )
                    require(artifact["persistence_block"] is True, artifact)
                print("ok formal and medical scenes block external memory")

                unknown = _post_and_get_retrieval(
                    client,
                    trace_path,
                    _scene_payload("future_scene"),
                )
                require(unknown["scene_type"] == "unknown", unknown)
                require(unknown["fallback_reason"] == "scene_policy_blocks_memory", unknown)
                require(unknown["selected"] == [], unknown)
                require(unknown["persistence_block"] is True, unknown)
                print("ok unknown scene fails closed")

                metadata = _last_metadata(trace_path)
                require(isinstance(metadata.get("relaymem_retrieval_artifact"), dict), metadata)
                print("ok trace metadata includes relaymem_retrieval_artifact")

        malformed = build_relaymem_retrieval_dry_run_artifact(
            relayscn_scene_policy_artifact={"bad": "shape"},
            relayref_artifact=None,
            messages=[],
        )
        require(malformed["scene_type"] == "unknown", malformed)
        require(malformed["retrieval_scope"] == "current_context_only", malformed)
        require(malformed["fallback_reason"] == "scene_policy_blocks_memory", malformed)
        require(malformed["persistence_block"] is True, malformed)
        print("ok malformed RelaySCN retrieval policy fails closed")
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
