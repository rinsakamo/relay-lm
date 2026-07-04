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

    def last_chat_payload(self) -> dict[str, Any]:
        with self._lock:
            for payload in reversed(self.payloads):
                if isinstance(payload.get("messages"), list):
                    return payload
        raise AssertionError("no backend chat payload captured")


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


def _last_backend_response_metadata(trace_path: Path) -> dict[str, Any]:
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    require(bool(lines), "trace is empty")
    for line in reversed(lines):
        record = json.loads(line)
        metadata = record.get("metadata") if isinstance(record, dict) else None
        if isinstance(metadata, dict) and metadata.get("event") == "backend_response":
            return metadata
    raise AssertionError("backend_response trace record is missing")


def _post_and_get_projection(
    client: TestClient,
    trace_path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = client.post("/v1/chat/completions", json=payload)
    require(response.status_code == 200, response.text)
    metadata = _last_backend_response_metadata(trace_path)
    require("relaymem_retrieval_artifact" not in metadata, metadata)
    projection = metadata.get("relaymem_primary_recall_projection")
    require(isinstance(projection, dict), metadata)
    require(projection.get("content_free") is True, projection)
    require(projection.get("content_included") is False, projection)
    require(projection.get("memory_text_included") is False, projection)
    require(projection.get("path_values_included") is False, projection)
    require(projection.get("digest_values_included") is False, projection)
    require(projection.get("lineage_values_included") is False, projection)
    require(projection.get("idempotency_values_included") is False, projection)
    require(projection.get("backend_prompt_included") is False, projection)
    return projection


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
        "relaymem_primary_recall_projection",
        "relayint_intent_artifact",
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
            cfg = yaml.safe_load(
                (REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8")
            )
            cfg["backends"]["local_backend"]["base_url"] = (
                f"http://127.0.0.1:{port}/v1"
            )
            cfg["trace"] = {"enabled": True, "path": str(trace_path)}
            cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
            cfg_path = Path(td) / "cfg.yaml"
            cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

            app = create_app(str(cfg_path))
            with TestClient(app) as client:
                design_payload = _scene_payload(
                    "design_talk", "RelayMEM retrieval design"
                )
                design = _post_and_get_projection(
                    client, trace_path, design_payload
                )
                require(
                    design["schema_version"]
                    == "relaymem.primary_recall_projection.v0",
                    design,
                )
                require(design["retrieval_scope"] == "project_context", design)
                require(
                    design["fallback_reason"] == "memory_store_disabled",
                    design,
                )
                require(design["selected_count"] == 0, design)
                require(design["ctx_block_present"] is False, design)
                require(design["estimated_tokens"] == 0, design)
                require(design["injection_performed"] is False, design)
                backend_payload = capture.last_chat_payload()
                _assert_no_backend_artifact(backend_payload)
                require(
                    backend_payload.get("metadata") == design_payload["metadata"],
                    backend_payload,
                )
                print("ok design_talk emits content-free retrieval projection")

                recovery = _post_and_get_projection(
                    client,
                    trace_path,
                    _scene_payload("recovery", "何の話だったっけ"),
                )
                require(
                    recovery["retrieval_scope"] == "current_context_only",
                    recovery,
                )
                require(
                    recovery["fallback_reason"]
                    == "unresolved_reference_requires_confirmation",
                    recovery,
                )
                require(recovery["persistence_block"] is True, recovery)
                require(recovery["selected_count"] == 0, recovery)
                _assert_no_backend_artifact(capture.last_chat_payload())
                print("ok recovery projection stays current-context-only")

                for scene_type in ("medical_or_safety", "formal_document"):
                    projection = _post_and_get_projection(
                        client,
                        trace_path,
                        _scene_payload(scene_type),
                    )
                    require(projection["selected_count"] == 0, projection)
                    require(
                        projection["fallback_reason"]
                        == "external_memory_blocked_by_scene_policy",
                        projection,
                    )
                    require(projection["persistence_block"] is True, projection)
                print("ok formal and medical projections block external memory")

                unknown = _post_and_get_projection(
                    client,
                    trace_path,
                    _scene_payload("future_scene"),
                )
                require(unknown["scene_type"] == "unknown", unknown)
                require(
                    unknown["fallback_reason"] == "scene_policy_blocks_memory",
                    unknown,
                )
                require(unknown["selected_count"] == 0, unknown)
                require(unknown["persistence_block"] is True, unknown)
                print("ok unknown scene projection fails closed")

                metadata = _last_backend_response_metadata(trace_path)
                projection_text = repr(
                    metadata.get("relaymem_primary_recall_projection")
                )
                for forbidden in (
                    "RelayMEM retrieval design",
                    "何の話だったっけ",
                    "memory/mem/",
                    "lineage_fingerprint",
                    "idempotency_key",
                    "page_digest",
                ):
                    require(forbidden not in projection_text, projection_text)
                print("ok trace contains only content-free recall projection")

        malformed = build_relaymem_retrieval_dry_run_artifact(
            relayscn_scene_policy_artifact={"bad": "shape"},
            relayint_intent_artifact=None,
            messages=[],
        )
        require(malformed["scene_type"] == "unknown", malformed)
        require(malformed["retrieval_scope"] == "current_context_only", malformed)
        require(
            malformed["fallback_reason"] == "scene_policy_blocks_memory", malformed
        )
        require(malformed["persistence_block"] is True, malformed)
        print("ok malformed RelaySCN retrieval policy fails closed")

        unsupported = build_relaymem_retrieval_dry_run_artifact(
            relayscn_scene_policy_artifact={
                "scene_state": {"scene_type": "future_scene"},
                "scene_policy": {"relaymem_retrieval_scope": "project_context"},
                "persistence_block": False,
                "persistence_block_reasons": [],
            },
            relayint_intent_artifact=None,
            messages=[],
        )
        require(unsupported["scene_type"] == "unknown", unsupported)
        require(
            unsupported["retrieval_scope"] == "current_context_only", unsupported
        )
        require(
            unsupported["fallback_reason"] == "scene_policy_blocks_memory",
            unsupported,
        )
        require(unsupported["persistence_block"] is True, unsupported)
        require(
            "unsupported_scene_type:future_scene"
            in unsupported["persistence_block_reasons"],
            unsupported,
        )
        print("ok syntactically valid unsupported RelaySCN scene fails closed")
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
