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
    recovery_response_generator_enabled: bool = False,
    recovery_response_generator_dry_run_only: bool = True,
    output_relayscn_recovery_gate_enabled: bool = False,
    output_relayscn_recovery_gate_dry_run_only: bool = True,
    visible_recovery_apply_preflight_enabled: bool = False,
    visible_recovery_apply_preflight_dry_run_only: bool = True,
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
    cfg["relayrun_recovery_response_draft_enabled"] = False
    cfg["relayrun_recovery_response_draft_dry_run_only"] = True
    cfg["relayrun_visible_recovery_preflight_enabled"] = False
    cfg["relayrun_visible_recovery_dry_run_only"] = True
    cfg["relayrun_recovery_response_generator_enabled"] = recovery_response_generator_enabled
    cfg["relayrun_recovery_response_generator_dry_run_only"] = recovery_response_generator_dry_run_only
    cfg["relayrun_output_relayscn_recovery_gate_enabled"] = output_relayscn_recovery_gate_enabled
    cfg["relayrun_output_relayscn_recovery_gate_dry_run_only"] = output_relayscn_recovery_gate_dry_run_only
    cfg["relayrun_visible_recovery_apply_preflight_enabled"] = visible_recovery_apply_preflight_enabled
    cfg["relayrun_visible_recovery_apply_preflight_dry_run_only"] = visible_recovery_apply_preflight_dry_run_only
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
    recovery_response_generator_enabled: bool = False,
    recovery_response_generator_dry_run_only: bool = True,
    output_relayscn_recovery_gate_enabled: bool = False,
    output_relayscn_recovery_gate_dry_run_only: bool = True,
    visible_recovery_apply_preflight_enabled: bool = False,
    visible_recovery_apply_preflight_dry_run_only: bool = True,
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
            recovery_response_generator_enabled=recovery_response_generator_enabled,
            recovery_response_generator_dry_run_only=recovery_response_generator_dry_run_only,
            output_relayscn_recovery_gate_enabled=output_relayscn_recovery_gate_enabled,
            output_relayscn_recovery_gate_dry_run_only=output_relayscn_recovery_gate_dry_run_only,
            visible_recovery_apply_preflight_enabled=visible_recovery_apply_preflight_enabled,
            visible_recovery_apply_preflight_dry_run_only=visible_recovery_apply_preflight_dry_run_only,
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


def _apply_preflight(metadata: dict[str, Any]) -> dict[str, Any]:
    artifact = _relayrun(metadata)
    apply_preflight = artifact.get("visible_recovery_apply_preflight")
    require(isinstance(apply_preflight, dict), artifact)
    require(
        metadata.get("relayrun_artifact", {}).get("visible_recovery_apply_preflight")
        == apply_preflight,
        metadata,
    )
    return apply_preflight


def _assert_apply_preflight_common(
    apply_preflight: dict[str, Any],
    *,
    disabled_expected: bool = True,
    dry_run_expected: bool = True,
) -> None:
    require(
        apply_preflight.get("schema_version") == "relayrun.visible_recovery_apply_preflight.v0",
        apply_preflight,
    )
    require(apply_preflight.get("diagnostics_only") is True, apply_preflight)
    require(apply_preflight.get("apply_allowed") is False, apply_preflight)
    require(apply_preflight.get("apply_attempted") is False, apply_preflight)
    require(apply_preflight.get("applied") is False, apply_preflight)
    require(apply_preflight.get("response_body_mutation_allowed") is False, apply_preflight)
    require(apply_preflight.get("backend_payload_mutation_allowed") is False, apply_preflight)
    require(apply_preflight.get("user_visible_allowed") is False, apply_preflight)
    require(apply_preflight.get("final_text_generated") is False, apply_preflight)
    require(apply_preflight.get("output_pipeline_required") is True, apply_preflight)
    require(apply_preflight.get("output_side_relayscn_gate_required") is True, apply_preflight)

    source_artifacts = apply_preflight.get("source_artifacts")
    require(isinstance(source_artifacts, dict), apply_preflight)
    gate_source = source_artifacts.get("output_relayscn_recovery_gate")
    generator_source = source_artifacts.get("recovery_response_generator")
    visible_source = source_artifacts.get("visible_recovery_response_preflight")
    require(isinstance(gate_source, dict), apply_preflight)
    require(isinstance(generator_source, dict), apply_preflight)
    require(isinstance(visible_source, dict), apply_preflight)
    require(gate_source.get("present") is True, apply_preflight)
    require(generator_source.get("present") is True, apply_preflight)
    require(visible_source.get("present") is True, apply_preflight)
    for projected in (gate_source, generator_source, visible_source):
        require("source_artifacts" not in projected, apply_preflight)
        require("draft_prompt_for_output_pipeline" not in projected, apply_preflight)
        require("prompt" not in projected, apply_preflight)
        require("final_text" not in projected, apply_preflight)
    require(isinstance(gate_source.get("blocked_reasons"), list), apply_preflight)
    require(isinstance(gate_source.get("safety"), dict), apply_preflight)
    require(isinstance(generator_source.get("blocked_reasons"), list), apply_preflight)
    require(isinstance(generator_source.get("safety"), dict), apply_preflight)
    require(isinstance(visible_source.get("blocked_reasons"), list), apply_preflight)
    require(isinstance(visible_source.get("pipeline_preflight"), dict), apply_preflight)
    require(isinstance(visible_source.get("required_pipeline_nodes"), list), apply_preflight)

    blocked_reasons = apply_preflight.get("blocked_reasons")
    require(isinstance(blocked_reasons, list), apply_preflight)
    require("visible_recovery_apply_not_implemented" in blocked_reasons, apply_preflight)
    require("response_body_mutation_not_implemented" in blocked_reasons, apply_preflight)
    require("output_pipeline_not_executed" in blocked_reasons, apply_preflight)
    require("output_relayscn_recovery_gate_not_passed" in blocked_reasons, apply_preflight)
    require("output_relayscn_user_visible_not_allowed" in blocked_reasons, apply_preflight)
    require("generated_text_missing" in blocked_reasons, apply_preflight)
    require("recovery_response_generator_not_allowed" in blocked_reasons, apply_preflight)
    require("visible_recovery_not_allowed" in blocked_reasons, apply_preflight)
    require("content_policy_not_verified" in blocked_reasons, apply_preflight)
    if disabled_expected:
        require("visible_recovery_apply_preflight_disabled" in blocked_reasons, apply_preflight)
    else:
        require("visible_recovery_apply_preflight_disabled" not in blocked_reasons, apply_preflight)
    if dry_run_expected:
        require("visible_recovery_apply_preflight_dry_run_only" in blocked_reasons, apply_preflight)
    else:
        require("visible_recovery_apply_preflight_dry_run_only" not in blocked_reasons, apply_preflight)

    safety = apply_preflight.get("safety")
    require(isinstance(safety, dict), apply_preflight)
    require(safety.get("contains_user_content") is False, apply_preflight)
    require(safety.get("contains_backend_payload") is False, apply_preflight)
    require(safety.get("contains_response_text") is False, apply_preflight)
    require(safety.get("contains_prompt_text") is False, apply_preflight)
    require(safety.get("contains_snippet_text") is False, apply_preflight)
    require(safety.get("contains_final_text") is False, apply_preflight)
    require(safety.get("direct_user_output_allowed") is False, apply_preflight)
    require(safety.get("run_direct_text_finalization_allowed") is False, apply_preflight)
    require(safety.get("backend_payload_mutation_allowed") is False, apply_preflight)
    require(safety.get("response_body_mutation_allowed") is False, apply_preflight)


def _assert_backend_payload_not_mutated(backend_payload: dict[str, Any] | None) -> None:
    require(isinstance(backend_payload, dict), backend_payload)
    backend_text = json.dumps(backend_payload, ensure_ascii=False)
    require("visible_recovery_apply_preflight" not in backend_text, backend_payload)
    require("relayrun.visible_recovery_apply_preflight.v0" not in backend_text, backend_payload)
    require("output_relayscn_recovery_gate" not in backend_text, backend_payload)
    require("recovery_response_generator" not in backend_text, backend_payload)
    require("visible_recovery_response_preflight" not in backend_text, backend_payload)
    require("recovery_response_draft" not in backend_text, backend_payload)
    require("recovery_apply_preflight" not in backend_text, backend_payload)
    require("waiting_user_contract" not in backend_text, backend_payload)
    require("recovery_transition_artifact" not in backend_text, backend_payload)


def _assert_no_raw_content(apply_preflight: dict[str, Any]) -> None:
    text = json.dumps(apply_preflight, ensure_ascii=False)
    require("Normal visible recovery apply preflight check" not in text, apply_preflight)
    require("Recover the current context" not in text, apply_preflight)
    require("それについて教えて" not in text, apply_preflight)
    require("Backend error visible recovery apply preflight check" not in text, apply_preflight)
    require("RELAYRUN_SNIPPET_SENTINEL" not in text, apply_preflight)
    require("Ask the user to confirm or restate the current context before continuing." not in text, apply_preflight)
    require(
        "Ask the user to clarify the unresolved reference before using memory or continuing."
        not in text,
        apply_preflight,
    )
    require("Explain that the backend request failed and ask whether to retry." not in text, apply_preflight)
    require("draft_prompt_for_output_pipeline" not in text, apply_preflight)
    require("source_artifacts" in apply_preflight, apply_preflight)
    for projected in apply_preflight.get("source_artifacts", {}).values():
        require(isinstance(projected, dict), apply_preflight)
        require("source_artifacts" not in projected, apply_preflight)


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
        payload=_payload("Normal visible recovery apply preflight check", "design_talk"),
        capture=capture,
    )
    apply_preflight = _apply_preflight(metadata)
    _assert_apply_preflight_common(apply_preflight)
    require(apply_preflight.get("source_message_kind") == "none", apply_preflight)
    require(apply_preflight.get("allowed_message_intent") == "none", apply_preflight)
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_success_response_unchanged(response_body)
    _assert_no_raw_content(apply_preflight)
    print("ok normal request emits visible_recovery_apply_preflight with no intent")


def _assert_recovery_scene(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _, response_body = _post(
        port=port,
        store_root=root,
        payload=_payload("Recover the current context using RelayMEM.", "recovery"),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    apply_preflight = _apply_preflight(metadata)
    _assert_apply_preflight_common(apply_preflight)
    require(apply_preflight.get("source_message_kind") == "context_repair_prompt", apply_preflight)
    require(
        apply_preflight.get("allowed_message_intent") == "confirm_or_restate_context",
        apply_preflight,
    )
    require("waiting_user_confirmation_required" in apply_preflight.get("blocked_reasons", []), apply_preflight)
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_success_response_unchanged(response_body)
    _assert_no_raw_content(apply_preflight)
    print("ok recovery scene maps context_repair_prompt to visible recovery apply preflight intent")


def _assert_unresolved_reference(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _, response_body = _post(
        port=port,
        store_root=root,
        payload=_payload("それについて教えて", "design_talk"),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    apply_preflight = _apply_preflight(metadata)
    _assert_apply_preflight_common(apply_preflight)
    require(apply_preflight.get("source_message_kind") == "ask_clarification", apply_preflight)
    require(
        apply_preflight.get("allowed_message_intent") == "clarify_unresolved_reference",
        apply_preflight,
    )
    require("waiting_user_confirmation_required" in apply_preflight.get("blocked_reasons", []), apply_preflight)
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_success_response_unchanged(response_body)
    _assert_no_raw_content(apply_preflight)
    print("ok unresolved reference maps ask_clarification to visible recovery apply preflight intent")


def _assert_backend_error(root: Path, capture: _Capture) -> None:
    backend_payload, metadata, status_code, response_body = _post(
        port=9,
        store_root=root,
        payload=_payload("Backend error visible recovery apply preflight check", "design_talk"),
        capture=capture,
        expected_status=502,
    )
    require(backend_payload is None, backend_payload)
    require(status_code == 502, status_code)
    require(isinstance(response_body, dict), response_body)
    require(response_body.get("error", {}).get("type") in {"backend_error", "backend_connection_error"}, response_body)
    apply_preflight = _apply_preflight(metadata)
    _assert_apply_preflight_common(apply_preflight)
    require(apply_preflight.get("source_message_kind") == "explain_backend_error", apply_preflight)
    require(
        apply_preflight.get("allowed_message_intent") == "explain_backend_error_and_ask_retry",
        apply_preflight,
    )
    require("waiting_user_confirmation_required" in apply_preflight.get("blocked_reasons", []), apply_preflight)
    _assert_no_raw_content(apply_preflight)
    print("ok backend error maps explain_backend_error and preserves existing error behavior")


def _assert_enabled_non_dry_run_still_blocked(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _, response_body = _post(
        port=port,
        store_root=root,
        payload=_payload("Enabled visible recovery apply preflight remains blocked", "design_talk"),
        capture=capture,
        visible_recovery_apply_preflight_enabled=True,
        visible_recovery_apply_preflight_dry_run_only=False,
    )
    apply_preflight = _apply_preflight(metadata)
    _assert_apply_preflight_common(apply_preflight, disabled_expected=False, dry_run_expected=False)
    require(apply_preflight.get("apply_allowed") is False, apply_preflight)
    require(
        "visible_recovery_apply_not_implemented" in apply_preflight.get("blocked_reasons", []),
        apply_preflight,
    )
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_success_response_unchanged(response_body)
    _assert_no_raw_content(apply_preflight)
    print("ok enabled non-dry-run visible recovery apply preflight remains blocked by not implemented")


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
            _assert_enabled_non_dry_run_still_blocked(store_root, capture, port)
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
