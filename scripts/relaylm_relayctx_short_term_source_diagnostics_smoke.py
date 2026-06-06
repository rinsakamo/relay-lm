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
from relaylm.diagnostics import build_relayctx_short_term_source_diagnostics
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
    mode: str,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["relayctx_short_term_source_diagnostics_enabled"] = True
    cfg["model_routes"]["relaylm-default"]["mode"] = mode
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


def _payload(messages: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": messages,
        "metadata": {
            "scene_state": {
                "scene_type": "design_talk",
                "confidence": 0.95,
                "stability": 0.9,
            }
        },
        "stream": False,
    }


def _post(
    *,
    port: int,
    store_root: Path,
    payload: dict[str, Any],
    capture: _Capture,
    mode: str,
) -> tuple[dict[str, Any], dict[str, Any], Any]:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg_path = Path(td) / "cfg.yaml"
        _write_config(
            cfg_path,
            port=port,
            trace_path=trace_path,
            store_root=store_root,
            mode=mode,
        )
        app = create_app(str(cfg_path))
        original = json.loads(json.dumps(payload))
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


def _diagnostics(metadata: dict[str, Any]) -> dict[str, Any]:
    artifact = metadata.get("relayctx_short_term_source_diagnostics")
    require(isinstance(artifact, dict), metadata)
    require(artifact.get("schema_version") == "relayctx_short_term_source_diagnostics.v0", artifact)
    require(artifact.get("diagnostics_only") is True, artifact)
    require(artifact.get("content_free") is True, artifact)
    require(artifact.get("short_term_storage_attempted") is False, artifact)
    require(artifact.get("short_term_restore_attempted") is False, artifact)
    require(artifact.get("short_term_injection_attempted") is False, artifact)
    require(artifact.get("short_term_source") == "openwebui_messages", artifact)
    safety = artifact.get("safety")
    require(isinstance(safety, dict), artifact)
    require(safety.get("contains_user_content") is False, artifact)
    require(safety.get("contains_backend_payload") is False, artifact)
    require(safety.get("contains_response_text") is False, artifact)
    require(safety.get("contains_prompt_text") is False, artifact)
    require(safety.get("contains_snippet_text") is False, artifact)
    require(safety.get("contains_final_text") is False, artifact)
    require(safety.get("stores_short_term_context") is False, artifact)
    require(safety.get("restores_cross_thread_context") is False, artifact)
    require(safety.get("rewrites_openwebui_messages") is False, artifact)
    require(safety.get("compresses_openwebui_messages") is False, artifact)
    require(safety.get("backend_payload_mutation_allowed") is False, artifact)
    require(safety.get("response_body_mutation_allowed") is False, artifact)
    return artifact


def _assert_response_unchanged(response_body: Any) -> None:
    require(isinstance(response_body, dict), response_body)
    choices = response_body.get("choices")
    require(isinstance(choices, list) and choices, response_body)
    message = choices[0].get("message")
    require(isinstance(message, dict), response_body)
    require(message.get("content") == "ok", response_body)


def _assert_no_artifact_in_backend(backend_payload: dict[str, Any]) -> None:
    text = json.dumps(backend_payload, ensure_ascii=False)
    require("relayctx_short_term_source_diagnostics" not in text, backend_payload)
    require("relayctx_short_term_source_diagnostics.v0" not in text, backend_payload)


def _assert_no_raw_content_in_artifact(artifact: dict[str, Any]) -> None:
    text = json.dumps(artifact, ensure_ascii=False)
    require("青いカモメ" not in text, artifact)
    require("OpenWebUI short term sentinel" not in text, artifact)
    require("assistant remembered the bird" not in text, artifact)
    require("relaymem candidate raw body" not in text, artifact)
    require("relaymem candidate raw snippet" not in text, artifact)
    require("ok" not in text, artifact)


def _assert_relaymem_selected_candidates_counted() -> None:
    artifact = build_relayctx_short_term_source_diagnostics(
        messages=[{"role": "user", "content": "OpenWebUI short term sentinel: 青いカモメ"}],
        enabled=True,
        relaymem_retrieval_artifact={
            "schema_version": "relaymem.retrieval_dry_run.v0",
            "selected_mem_candidates": [
                {"candidate_id": "mem-1", "content": "relaymem candidate raw body"},
                {"candidate_id": "mem-2", "snippet": "relaymem candidate raw snippet"},
            ],
        },
    )
    require(isinstance(artifact, dict), artifact)
    registry = artifact.get("source_registry")
    require(isinstance(registry, dict), artifact)
    relaymem_registry = registry.get("relaymem_retrieval")
    require(isinstance(relaymem_registry, dict), artifact)
    require(relaymem_registry.get("present") is True, artifact)
    require(relaymem_registry.get("candidate_count") == 2, artifact)
    require("selected_mem_candidates" not in json.dumps(artifact, ensure_ascii=False), artifact)
    _assert_no_raw_content_in_artifact(artifact)
    print("ok RelayMEM selected candidates are counted without copying candidate content")


def _assert_pass_through_single_message(root: Path, capture: _Capture, port: int) -> None:
    payload = _payload([{"role": "user", "content": "OpenWebUI short term sentinel: 青いカモメ"}])
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        mode="pass_through",
    )
    artifact = _diagnostics(metadata)
    require(artifact.get("openwebui_messages_present") is True, artifact)
    require(artifact.get("openwebui_message_count") == 1, artifact)
    require(artifact.get("openwebui_recent_user_count") == 1, artifact)
    require(artifact.get("openwebui_recent_assistant_count") == 0, artifact)
    require(artifact.get("latest_user_message_present") is True, artifact)
    require(artifact.get("latest_user_message_chars") == len(payload["messages"][0]["content"]), artifact)
    require(artifact.get("short_term_candidate_present") is True, artifact)
    require(artifact.get("short_term_candidate_count") == 1, artifact)
    require(backend_payload.get("messages") == payload["messages"], backend_payload)
    _assert_no_artifact_in_backend(backend_payload)
    _assert_response_unchanged(response_body)
    _assert_no_raw_content_in_artifact(artifact)
    print("ok pass_through emits content-free RelayCTX source diagnostics")


def _assert_pass_through_multi_message(root: Path, capture: _Capture, port: int) -> None:
    messages = [
        {"role": "user", "content": "first turn: 青いカモメ"},
        {"role": "assistant", "content": "assistant remembered the bird"},
        {"role": "user", "content": "second turn asks about it"},
    ]
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=_payload(messages),
        capture=capture,
        mode="pass_through",
    )
    artifact = _diagnostics(metadata)
    require(artifact.get("openwebui_message_count") == 3, artifact)
    require(artifact.get("openwebui_recent_user_count") == 2, artifact)
    require(artifact.get("openwebui_recent_assistant_count") == 1, artifact)
    require(artifact.get("latest_user_message_chars") == len(messages[-1]["content"]), artifact)
    require(artifact.get("short_term_candidate_count") == 3, artifact)
    require(backend_payload.get("messages") == messages, backend_payload)
    _assert_no_artifact_in_backend(backend_payload)
    _assert_response_unchanged(response_body)
    _assert_no_raw_content_in_artifact(artifact)
    print("ok pass_through counts multi-message OpenWebUI history")


def _assert_memory_light_keeps_source_separate(root: Path, capture: _Capture, port: int) -> None:
    messages = [
        {"role": "user", "content": "memory light turn one: 青いカモメ"},
        {"role": "assistant", "content": "assistant remembered the bird"},
        {"role": "user", "content": "memory light turn two"},
    ]
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=_payload(messages),
        capture=capture,
        mode="memory_light",
    )
    artifact = _diagnostics(metadata)
    require(artifact.get("openwebui_message_count") == 3, artifact)
    require(artifact.get("openwebui_recent_user_count") == 2, artifact)
    require(artifact.get("openwebui_recent_assistant_count") == 1, artifact)
    registry = artifact.get("source_registry")
    require(isinstance(registry, dict), artifact)
    require(registry.get("openwebui_messages", {}).get("present") is True, artifact)
    require(registry.get("memory_seed", {}).get("present") is True, artifact)
    require(registry.get("relayctx_short_term", {}).get("source") == "openwebui_messages", artifact)
    backend_messages = backend_payload.get("messages")
    require(isinstance(backend_messages, list), backend_payload)
    require(backend_messages[-3:] == messages, backend_payload)
    _assert_no_artifact_in_backend(backend_payload)
    _assert_response_unchanged(response_body)
    _assert_no_raw_content_in_artifact(artifact)
    print("ok memory_light emits source diagnostics without mixing memory seed source")


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
            _assert_pass_through_single_message(store_root, capture, port)
            _assert_pass_through_multi_message(store_root, capture, port)
            _assert_memory_light_keeps_source_separate(store_root, capture, port)
            _assert_relaymem_selected_candidates_counted()
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
