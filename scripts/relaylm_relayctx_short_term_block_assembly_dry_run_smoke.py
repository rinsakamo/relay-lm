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
    mode: str,
    extraction_enabled: bool,
    assembly_enabled: bool,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["relayctx_short_term_source_diagnostics_enabled"] = extraction_enabled
    cfg["relayctx_short_term_extraction_dry_run_enabled"] = extraction_enabled
    cfg["relayctx_short_term_block_assembly_dry_run_enabled"] = assembly_enabled
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


def _payload(messages: list[dict[str, Any]]) -> dict[str, Any]:
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
    extraction_enabled: bool,
    assembly_enabled: bool,
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
            extraction_enabled=extraction_enabled,
            assembly_enabled=assembly_enabled,
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


def _assembly(metadata: dict[str, Any]) -> dict[str, Any]:
    artifact = metadata.get("relayctx_short_term_block_assembly_dry_run")
    require(isinstance(artifact, dict), metadata)
    require(artifact.get("schema_version") == "relayctx_short_term_block_assembly_dry_run.v0", artifact)
    require(artifact.get("enabled") is True, artifact)
    require(artifact.get("dry_run_only") is True, artifact)
    require(artifact.get("attempted") is True, artifact)
    require(artifact.get("applied") is False, artifact)
    require(artifact.get("source") == "relayctx_short_term_extraction_dry_run", artifact)
    require(artifact.get("content_free") is True, artifact)
    require(artifact.get("persistence_allowed") is False, artifact)
    require(artifact.get("restore_allowed") is False, artifact)
    require(artifact.get("injection_allowed") is False, artifact)
    require(artifact.get("backend_payload_mutation_allowed") is False, artifact)
    require(artifact.get("response_mutation_allowed") is False, artifact)
    require(artifact.get("openwebui_message_mutation_allowed") is False, artifact)
    require(isinstance(artifact.get("blocked_reasons"), list), artifact)
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
    require("relayctx_short_term_block_assembly_dry_run" not in text, backend_payload)
    require("relayctx_short_term_block_assembly_dry_run.v0" not in text, backend_payload)


def _assert_no_raw_content(value: Any) -> None:
    text = json.dumps(value, ensure_ascii=False)
    require("今日の合言葉は青いカモメ" not in text, value)
    require("青いカモメ" not in text, value)
    require("この一時設定を優先してください" not in text, value)
    require("今日は温かいお茶ではなく冷たい水" not in text, value)
    require("https://example.invalid/relayctx-block-image.png" not in text, value)
    require("relaymem candidate raw body" not in text, value)
    require("relaymem candidate raw snippet" not in text, value)


def _messages() -> list[dict[str, Any]]:
    return [
        {"role": "user", "content": "今日の合言葉は青いカモメ"},
        {"role": "user", "content": "この一時設定を優先してください"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "今日は温かいお茶ではなく冷たい水"},
                {
                    "type": "image_url",
                    "image_url": {"url": "https://example.invalid/relayctx-block-image.png"},
                },
            ],
        },
    ]


def _assert_default_false(root: Path, capture: _Capture, port: int) -> None:
    messages = _messages()
    payload = _payload(messages)
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        mode="pass_through",
        extraction_enabled=True,
        assembly_enabled=False,
    )
    require("relayctx_short_term_block_assembly_dry_run" not in metadata, metadata)
    require(isinstance(metadata.get("relayctx_short_term_extraction_dry_run"), dict), metadata)
    require(backend_payload.get("messages") == messages, backend_payload)
    _assert_no_artifact_in_backend(backend_payload)
    _assert_response_unchanged(response_body)
    print("ok default-off RelayCTX block assembly dry run is absent and safe")


def _assert_extraction_missing(root: Path, capture: _Capture, port: int) -> None:
    messages = _messages()
    payload = _payload(messages)
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        mode="pass_through",
        extraction_enabled=False,
        assembly_enabled=True,
    )
    artifact = _assembly(metadata)
    require(artifact.get("input_extraction_present") is False, artifact)
    require(artifact.get("input_short_term_candidate_count") == 0, artifact)
    require(artifact.get("assembled_block_present") is False, artifact)
    require("extraction_missing" in artifact.get("blocked_reasons"), artifact)
    require(backend_payload.get("messages") == messages, backend_payload)
    _assert_no_artifact_in_backend(backend_payload)
    _assert_response_unchanged(response_body)
    _assert_no_raw_content(artifact)
    print("ok RelayCTX block assembly dry run blocks safely when extraction is missing")


def _assert_enabled_mode(root: Path, capture: _Capture, port: int, *, mode: str) -> None:
    messages = _messages()
    payload = _payload(messages)
    backend_payload, metadata, response_body = _post(
        port=port,
        store_root=root,
        payload=payload,
        capture=capture,
        mode=mode,
        extraction_enabled=True,
        assembly_enabled=True,
    )
    extraction = metadata.get("relayctx_short_term_extraction_dry_run")
    require(isinstance(extraction, dict), metadata)
    artifact = _assembly(metadata)
    require(artifact.get("input_extraction_present") is True, artifact)
    require(artifact.get("input_short_term_candidate_count") == extraction.get("short_term_candidate_count"), artifact)
    require(artifact.get("assembled_block_present") is True, artifact)
    require(artifact.get("assembled_block_type") == "relayctx_short_term", artifact)
    require(artifact.get("assembled_block_source") == "openwebui_messages", artifact)
    require(artifact.get("assembled_block_priority") == "current_thread_over_memory_seed", artifact)
    require(artifact.get("assembled_block_token_budget_hint") == 400, artifact)
    require(artifact.get("temporary_fact_count") == extraction.get("temporary_fact_candidate_count"), artifact)
    require(artifact.get("temporary_preference_count") == extraction.get("temporary_preference_candidate_count"), artifact)
    require(artifact.get("instruction_count") == extraction.get("instruction_candidate_count"), artifact)
    require(artifact.get("override_count") == extraction.get("override_candidate_count"), artifact)
    require(artifact.get("contradiction_count") == extraction.get("contradiction_candidate_count"), artifact)
    require(artifact.get("temporary_fact_count") == 1, artifact)
    require(artifact.get("temporary_preference_count") == 1, artifact)
    require(artifact.get("instruction_count") == 1, artifact)
    require(artifact.get("override_count") == 2, artifact)
    require(artifact.get("contradiction_count") == 1, artifact)
    require(
        artifact.get("priority_order")
        == [
            "current_user_instruction",
            "openwebui_recent_messages",
            "relayctx_short_term",
            "memory_seed",
        ],
        artifact,
    )
    require(artifact.get("blocked_reasons") == [], artifact)
    backend_messages = backend_payload.get("messages")
    require(isinstance(backend_messages, list), backend_payload)
    if mode == "pass_through":
        require(backend_messages == messages, backend_payload)
    else:
        require(backend_messages[-len(messages) :] == messages, backend_payload)
    require(payload["messages"] == messages, payload)
    _assert_no_artifact_in_backend(backend_payload)
    _assert_response_unchanged(response_body)
    _assert_no_raw_content(artifact)
    _assert_no_raw_content(extraction)
    print(f"ok {mode} emits content-free RelayCTX block assembly dry-run metadata")


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
            _assert_extraction_missing(store_root, capture, port)
            _assert_enabled_mode(store_root, capture, port, mode="pass_through")
            _assert_enabled_mode(store_root, capture, port, mode="memory_light")
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
