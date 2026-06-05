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
    snippet_runtime_injection_enabled: bool = False,
    snippet_runtime_dry_run_only: bool = True,
    recovery_response_draft_enabled: bool = False,
    recovery_response_draft_dry_run_only: bool = True,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    cfg["relayrun_recovery_transition_enabled"] = False
    cfg["relayrun_recovery_transition_dry_run_only"] = True
    cfg["relayrun_waiting_user_contract_enabled"] = False
    cfg["relayrun_waiting_user_contract_dry_run_only"] = True
    cfg["relayrun_recovery_apply_preflight_enabled"] = False
    cfg["relayrun_recovery_apply_dry_run_only"] = True
    cfg["relayrun_recovery_response_draft_enabled"] = recovery_response_draft_enabled
    cfg["relayrun_recovery_response_draft_dry_run_only"] = recovery_response_draft_dry_run_only
    cfg["memory"].update(
        {
            "root_path": str(store_root),
            "store_enabled": True,
            "retrieval_dry_run_only": False,
            "ctx_block_apply_enabled": True,
            "snippet_extraction_enabled": True,
            "snippet_dry_run_only": False,
            "snippet_apply_enabled": True,
            "snippet_runtime_injection_enabled": snippet_runtime_injection_enabled,
            "snippet_runtime_dry_run_only": snippet_runtime_dry_run_only,
            "snippet_budget": 512,
            "max_snippet_chars": 160,
            "max_snippet_candidates": 3,
            "candidate_limit": 3,
            "token_budget_hint": 800,
            "token_budget_truncation_enabled": False,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _payload(content: str, scene_type: str) -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": content}],
        "metadata": {
            "scene_state": {
                "scene_type": scene_type,
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
    expected_status: int = 200,
    snippet_runtime_injection_enabled: bool = False,
    snippet_runtime_dry_run_only: bool = True,
    recovery_response_draft_enabled: bool = False,
    recovery_response_draft_dry_run_only: bool = True,
) -> tuple[dict[str, Any] | None, dict[str, Any], int, Any]:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg_path = Path(td) / "cfg.yaml"
        _write_config(
            cfg_path,
            port=port,
            trace_path=trace_path,
            store_root=store_root,
            snippet_runtime_injection_enabled=snippet_runtime_injection_enabled,
            snippet_runtime_dry_run_only=snippet_runtime_dry_run_only,
            recovery_response_draft_enabled=recovery_response_draft_enabled,
            recovery_response_draft_dry_run_only=recovery_response_draft_dry_run_only,
        )
        app = create_app(str(cfg_path))
        original = json.loads(json.dumps(payload))
        before_count = capture.count()
        with TestClient(app) as client:
            resp = client.post("/v1/chat/completions", json=payload)
            require(resp.status_code == expected_status, resp.text)
            response_body = resp.json()
        require(payload == original, payload)
        backend_payload = None
        if capture.count() > before_count:
            backend_payload = capture.get(before_count)
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        require(isinstance(metadata, dict), record)
        return backend_payload, metadata, resp.status_code, response_body


def _relayrun(metadata: dict[str, Any]) -> dict[str, Any]:
    artifact = metadata.get("relayrun_artifact")
    require(isinstance(artifact, dict), metadata)
    return artifact


def _draft(metadata: dict[str, Any]) -> dict[str, Any]:
    artifact = _relayrun(metadata)
    draft = artifact.get("recovery_response_draft")
    require(isinstance(draft, dict), artifact)
    require(metadata.get("relayrun_artifact", {}).get("recovery_response_draft") == draft, metadata)
    return draft


def _assert_draft_common(
    draft: dict[str, Any],
    *,
    disabled_expected: bool = True,
    dry_run_expected: bool = True,
) -> None:
    require(draft.get("schema_version") == "relayrun.recovery_response_draft.v0", draft)
    require(draft.get("diagnostics_only") is True, draft)
    require(draft.get("draft_only") is True, draft)
    require(draft.get("user_visible") is False, draft)
    require(draft.get("apply_allowed") is False, draft)
    require(draft.get("applied") is False, draft)
    blocked_reasons = draft.get("blocked_reasons")
    require(isinstance(blocked_reasons, list), draft)
    require("recovery_response_draft_not_implemented" in blocked_reasons, draft)
    if disabled_expected:
        require("recovery_response_draft_disabled" in blocked_reasons, draft)
    else:
        require("recovery_response_draft_disabled" not in blocked_reasons, draft)
    if dry_run_expected:
        require("recovery_response_draft_dry_run_only" in blocked_reasons, draft)
    else:
        require("recovery_response_draft_dry_run_only" not in blocked_reasons, draft)
    source_artifacts = draft.get("source_artifacts")
    require(isinstance(source_artifacts, dict), draft)
    require(isinstance(source_artifacts.get("recovery_apply_preflight"), dict), draft)
    safety = draft.get("safety")
    require(isinstance(safety, dict), draft)
    require(safety.get("direct_user_output_allowed") is False, draft)
    require(safety.get("final_text_generated") is False, draft)
    require(safety.get("passes_through_output_pipeline_required") is True, draft)
    require(safety.get("contains_user_content") is False, draft)
    require(safety.get("contains_backend_payload") is False, draft)
    require(safety.get("contains_response_text") is False, draft)
    require(safety.get("contains_prompt_text") is False, draft)


def _assert_backend_payload_not_mutated(backend_payload: dict[str, Any] | None) -> None:
    require(isinstance(backend_payload, dict), backend_payload)
    backend_text = json.dumps(backend_payload, ensure_ascii=False)
    require("recovery_response_draft" not in backend_text, backend_payload)
    require("relayrun.recovery_response_draft.v0" not in backend_text, backend_payload)
    require("recovery_apply_preflight" not in backend_text, backend_payload)
    require("waiting_user_contract" not in backend_text, backend_payload)
    require("recovery_transition_artifact" not in backend_text, backend_payload)


def _assert_no_raw_content(draft: dict[str, Any]) -> None:
    text = json.dumps(draft, ensure_ascii=False)
    require("Recover the current context" not in text, draft)
    require("それについて教えて" not in text, draft)
    require("Backend error recovery response draft check" not in text, draft)


def _assert_success_response_unchanged(response_body: Any) -> None:
    require(isinstance(response_body, dict), response_body)
    choices = response_body.get("choices")
    require(isinstance(choices, list) and choices, response_body)
    message = choices[0].get("message")
    require(isinstance(message, dict), response_body)
    require(message.get("content") == "ok", response_body)


def _assert_normal(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _, response_body = _post(
        port=port,
        store_root=root,
        payload=_payload("Normal recovery response draft check", "design_talk"),
        capture=capture,
    )
    draft = _draft(metadata)
    _assert_draft_common(draft)
    require(draft.get("source_transition_type") == "none", draft)
    require(draft.get("waiting_user_required") is False, draft)
    require(draft.get("suggested_message_kind") == "none", draft)
    require(draft.get("draft_prompt_for_output_pipeline") is None, draft)
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_success_response_unchanged(response_body)
    _assert_no_raw_content(draft)
    print("ok normal request emits recovery_response_draft with no suggested message")
    print("ok trace metadata includes recovery_response_draft")


def _assert_recovery_scene(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _, response_body = _post(
        port=port,
        store_root=root,
        payload=_payload("Recover the current context using RelayMEM.", "recovery"),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    draft = _draft(metadata)
    _assert_draft_common(draft)
    require(draft.get("source_transition_type") == "context_repair", draft)
    require(draft.get("waiting_user_required") is True, draft)
    require(draft.get("suggested_message_kind") == "context_repair_prompt", draft)
    require(draft.get("draft_prompt_for_output_pipeline") == "Ask the user to confirm or restate the current context before continuing.", draft)
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_success_response_unchanged(response_body)
    _assert_no_raw_content(draft)
    print("ok recovery scene emits context_repair_prompt draft only")


def _assert_unresolved_reference(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _, response_body = _post(
        port=port,
        store_root=root,
        payload=_payload("それについて教えて", "design_talk"),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    draft = _draft(metadata)
    _assert_draft_common(draft)
    require(draft.get("source_transition_type") == "ask_user_confirmation", draft)
    require(draft.get("waiting_user_required") is True, draft)
    require(draft.get("suggested_message_kind") == "ask_clarification", draft)
    require(draft.get("draft_prompt_for_output_pipeline") == "Ask the user to clarify the unresolved reference before using memory or continuing.", draft)
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_success_response_unchanged(response_body)
    _assert_no_raw_content(draft)
    print("ok unresolved reference emits ask_clarification draft only")


def _assert_backend_error(root: Path, capture: _Capture) -> None:
    backend_payload, metadata, status_code, response_body = _post(
        port=9,
        store_root=root,
        payload=_payload("Backend error recovery response draft check", "design_talk"),
        capture=capture,
        expected_status=502,
    )
    require(backend_payload is None, backend_payload)
    require(status_code == 502, status_code)
    require(isinstance(response_body, dict), response_body)
    require(response_body.get("error", {}).get("type") in {"backend_error", "backend_connection_error"}, response_body)
    draft = _draft(metadata)
    _assert_draft_common(draft)
    require(draft.get("source_transition_type") == "retry_safe_node", draft)
    require(draft.get("waiting_user_required") is True, draft)
    require(draft.get("suggested_message_kind") == "explain_backend_error", draft)
    require(draft.get("draft_prompt_for_output_pipeline") == "Explain that the backend request failed and ask whether to retry.", draft)
    _assert_no_raw_content(draft)
    print("ok backend error emits explain_backend_error draft only and preserves error behavior")


def _assert_enabled_still_draft_only(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _, response_body = _post(
        port=port,
        store_root=root,
        payload=_payload("Enabled recovery response draft remains draft only", "design_talk"),
        capture=capture,
        recovery_response_draft_enabled=True,
        recovery_response_draft_dry_run_only=False,
    )
    draft = _draft(metadata)
    _assert_draft_common(draft, disabled_expected=False, dry_run_expected=False)
    require(draft.get("user_visible") is False, draft)
    require(draft.get("apply_allowed") is False, draft)
    require(draft.get("applied") is False, draft)
    require(draft.get("safety", {}).get("final_text_generated") is False, draft)
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_success_response_unchanged(response_body)
    print("ok enabled non-dry-run recovery_response_draft still generates no final user-visible text")


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
            _assert_normal(store_root, capture, port)
            _assert_recovery_scene(store_root, capture, port)
            _assert_unresolved_reference(store_root, capture, port)
            _assert_backend_error(store_root, capture)
            _assert_enabled_still_draft_only(store_root, capture, port)
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
