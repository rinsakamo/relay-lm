from __future__ import annotations

import json
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = Path(__file__).resolve().parent
for path in (REPO_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from relaylm.app import create_app
from relaylm_relayrun_runtime_checkpoint_dry_run_smoke import (  # type: ignore[import-not-found]
    _BackendHandler,
    _Capture,
    _build_store,
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _write_config(
    path: Path,
    *,
    port: int,
    trace_path: Path,
    store_root: Path,
    relayint_enabled: bool,
    preflight_enabled: bool,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["relayint_fast_path_dry_run_enabled"] = relayint_enabled
    cfg["relayint_quick_clarification_preflight_enabled"] = preflight_enabled
    cfg["relayint_quick_clarification_dry_run_only"] = True
    cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    cfg["memory"].update(
        {
            "root_path": str(store_root),
            "store_enabled": False,
            "retrieval_dry_run_only": True,
            "ctx_block_apply_enabled": False,
            "snippet_extraction_enabled": False,
            "snippet_dry_run_only": True,
            "snippet_apply_enabled": False,
            "snippet_runtime_injection_enabled": False,
            "snippet_runtime_dry_run_only": True,
            "token_budget_truncation_enabled": False,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _payload(content: Any, *, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "scene_state": {
            "scene_type": "design_talk",
            "confidence": 0.95,
            "stability": 0.9,
        }
    }
    if ctx is not None:
        metadata["ctx"] = ctx
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": content}],
        "metadata": metadata,
        "stream": False,
    }


def _post(
    *,
    port: int,
    store_root: Path,
    payload: dict[str, Any],
    capture: _Capture,
    relayint_enabled: bool,
    preflight_enabled: bool,
) -> tuple[dict[str, Any], dict[str, Any], Any]:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg_path = Path(td) / "cfg.yaml"
        _write_config(
            cfg_path,
            port=port,
            trace_path=trace_path,
            store_root=store_root,
            relayint_enabled=relayint_enabled,
            preflight_enabled=preflight_enabled,
        )
        app = create_app(str(cfg_path))
        original = json.loads(json.dumps(payload, ensure_ascii=False))
        before_count = capture.count()
        with TestClient(app) as client:
            resp = client.post("/v1/chat/completions", json=payload)
            require(resp.status_code == 200, resp.text)
            response_body = resp.json()
        require(payload == original, payload)
        require(capture.count() > before_count, capture.count())
        backend_payload = capture.get(before_count)
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        require(isinstance(metadata, dict), record)
        return backend_payload, metadata, response_body


def _preflight(metadata: dict[str, Any]) -> dict[str, Any]:
    artifact = metadata.get("relayint_quick_clarification_preflight")
    require(isinstance(artifact, dict), metadata)
    require(artifact.get("schema_version") == "relayint_quick_clarification_preflight.v0", artifact)
    require(artifact.get("enabled") is True, artifact)
    require(artifact.get("dry_run_only") is True, artifact)
    require(artifact.get("content_free") is True, artifact)
    require(artifact.get("candidate_labels_are_content_free") is True, artifact)
    safety = artifact.get("safety_gates")
    require(isinstance(safety, dict), artifact)
    require(safety.get("content_free") is True, artifact)
    require(safety.get("llm_call_allowed") is False, artifact)
    require(safety.get("mem_lookup_allowed") is False, artifact)
    require(safety.get("backend_payload_mutation_allowed") is False, artifact)
    require(safety.get("response_mutation_allowed") is False, artifact)
    require(safety.get("user_visible_apply_allowed") is False, artifact)
    require(artifact.get("llm_called") is False, artifact)
    require(artifact.get("mem_lookup_executed") is False, artifact)
    require(artifact.get("backend_payload_mutation_allowed") is False, artifact)
    require(artifact.get("response_mutation_allowed") is False, artifact)
    return artifact


def _assert_response_unchanged(response_body: Any) -> None:
    require(isinstance(response_body, dict), response_body)
    choices = response_body.get("choices")
    require(isinstance(choices, list) and choices, response_body)
    message = choices[0].get("message")
    require(isinstance(message, dict), response_body)
    require(message.get("content") == "ok", response_body)


def _assert_no_raw_content(artifact: dict[str, Any]) -> None:
    text = json.dumps(artifact, ensure_ascii=False)
    require("それで" not in text, artifact)
    require("some topic" not in text, artifact)
    require("hidden raw referable" not in text, artifact)
    require("https://example.invalid/relayint-clarification.png" not in text, artifact)


def _assert_default_false(root: Path, capture: _Capture, port: int) -> None:
    payload = _payload("それで")
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        relayint_enabled=True,
        preflight_enabled=False,
    )
    require("relayint_fast_path_dry_run" in metadata, metadata)
    require("relayint_quick_clarification_preflight" not in metadata, metadata)
    require(backend_payload.get("messages") == payload["messages"], backend_payload)
    _assert_response_unchanged(response_body)
    print("ok default-off RelayINT quick clarification preflight is absent")


def _assert_fast_path_disabled(root: Path, capture: _Capture, port: int) -> None:
    payload = _payload("それで")
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        relayint_enabled=False,
        preflight_enabled=True,
    )
    require("relayint_fast_path_dry_run" not in metadata, metadata)
    require("relayint_quick_clarification_preflight" not in metadata, metadata)
    require(backend_payload.get("messages") == payload["messages"], backend_payload)
    _assert_response_unchanged(response_body)
    print("ok RelayINT quick clarification preflight is absent without Fast Path source")


def _assert_ambiguous_reference_preflight(root: Path, capture: _Capture, port: int) -> None:
    payload = _payload(
        [
            {"type": "text", "text": "それで"},
            {"type": "image_url", "image_url": {"url": "https://example.invalid/relayint-clarification.png"}},
        ],
        ctx={"referable_items": [{"label": "hidden raw referable"}]},
    )
    # Placeholder referable would be ambiguous but includes no candidate kind; handoff
    # gives a content-free confirmation candidate without trusting raw values.
    payload["metadata"]["ctx"] = {"ctx_handoff_guess": {"summary": "hidden raw referable"}}
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        relayint_enabled=True,
        preflight_enabled=True,
    )
    fast_path = metadata.get("relayint_fast_path_dry_run")
    require(isinstance(fast_path, dict), metadata)
    require(fast_path.get("candidate_action") == "ask_clarification", fast_path)
    artifact = _preflight(metadata)
    require(artifact.get("source_artifact_schema_version") == "relayint_fast_path_dry_run.v0", artifact)
    require(artifact.get("source_candidate_action") == "ask_clarification", artifact)
    require(artifact.get("preflight_applicable") is True, artifact)
    require(artifact.get("clarification_type") == "reference_confirmation", artifact)
    require(artifact.get("suggested_response_mode") == "quick_clarification_candidate", artifact)
    require(artifact.get("candidate_count") == 1, artifact)
    require(artifact.get("candidate_label_kinds") == ["topic_anchor"], artifact)
    scene_gate = artifact.get("scene_gate")
    require(isinstance(scene_gate, dict), artifact)
    require(scene_gate.get("scene_type") == "design_talk", artifact)
    require(scene_gate.get("quick_clarification_allowed") is True, artifact)
    require(backend_payload.get("messages") == payload["messages"], backend_payload)
    _assert_response_unchanged(response_body)
    _assert_no_raw_content(artifact)
    print("ok ambiguous RelayINT reference emits content-free quick clarification preflight")


def _assert_resolved_reference_not_applicable(root: Path, capture: _Capture, port: int) -> None:
    payload = _payload("それで", ctx={"current_topic": "some topic"})
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        relayint_enabled=True,
        preflight_enabled=True,
    )
    fast_path = metadata.get("relayint_fast_path_dry_run")
    require(isinstance(fast_path, dict), metadata)
    require(fast_path.get("candidate_action") == "continue_without_clarification", fast_path)
    artifact = _preflight(metadata)
    require(artifact.get("source_candidate_action") == "continue_without_clarification", artifact)
    require(artifact.get("preflight_applicable") is False, artifact)
    require(artifact.get("clarification_type") == "none", artifact)
    require(artifact.get("candidate_count") == 0, artifact)
    require(artifact.get("candidate_label_kinds") == [], artifact)
    require(artifact.get("suggested_response_mode") == "no_quick_clarification", artifact)
    require(backend_payload.get("messages") == payload["messages"], backend_payload)
    _assert_response_unchanged(response_body)
    _assert_no_raw_content(artifact)
    print("ok resolved RelayINT reference marks quick clarification preflight not applicable")


def main() -> int:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        root = Path(td)
        store_root = root / "store"
        _build_store(store_root)
        capture = _Capture()
        _BackendHandler.capture = capture
        server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = int(server.server_address[1])
            _assert_default_false(store_root, capture, port)
            _assert_fast_path_disabled(store_root, capture, port)
            _assert_ambiguous_reference_preflight(store_root, capture, port)
            _assert_resolved_reference_not_applicable(store_root, capture, port)
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
