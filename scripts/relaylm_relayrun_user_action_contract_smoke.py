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
    user_action_dry_run_enabled: bool = False,
    user_action_dry_run_only: bool = True,
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
    cfg["relayrun_user_action_dry_run_enabled"] = user_action_dry_run_enabled
    cfg["relayrun_user_action_dry_run_only"] = user_action_dry_run_only
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
    user_action_dry_run_enabled: bool = False,
    user_action_dry_run_only: bool = True,
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
            user_action_dry_run_enabled=user_action_dry_run_enabled,
            user_action_dry_run_only=user_action_dry_run_only,
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


def _user_action_contract(metadata: dict[str, Any]) -> dict[str, Any]:
    artifact = _relayrun(metadata)
    contract = artifact.get("user_action_contract")
    require(isinstance(contract, dict), artifact)
    require(metadata.get("relayrun_artifact", {}).get("user_action_contract") == contract, metadata)
    return contract


def _assert_user_action_common(
    contract: dict[str, Any],
    *,
    disabled_expected: bool = True,
    dry_run_expected: bool = True,
) -> None:
    require(contract.get("schema_version") == "relayrun.user_action_contract.v0", contract)
    require(contract.get("diagnostics_only") is True, contract)
    require(contract.get("user_action_allowed") is False, contract)
    require(contract.get("user_action_attempted") is False, contract)
    require(contract.get("user_action_applied") is False, contract)
    require(contract.get("resume_allowed") is False, contract)
    require(contract.get("retry_allowed") is False, contract)
    require(contract.get("visible_recovery_apply_allowed") is False, contract)
    require(contract.get("response_body_mutation_allowed") is False, contract)
    require(contract.get("backend_payload_mutation_allowed") is False, contract)
    require(
        contract.get("accepted_action_kinds")
        == [
            "clarify_reference",
            "confirm_context_repair",
            "confirm_retry",
            "choose_recovery_action",
            "cancel_recovery",
        ],
        contract,
    )

    source_artifacts = contract.get("source_artifacts")
    require(isinstance(source_artifacts, dict), contract)
    waiting_source = source_artifacts.get("waiting_user_contract")
    apply_source = source_artifacts.get("visible_recovery_apply_preflight")
    gate_source = source_artifacts.get("output_relayscn_recovery_gate")
    require(isinstance(waiting_source, dict), contract)
    require(isinstance(apply_source, dict), contract)
    require(isinstance(gate_source, dict), contract)
    require(waiting_source.get("present") is True, contract)
    require(apply_source.get("present") is True, contract)
    require(gate_source.get("present") is True, contract)
    for projected in (waiting_source, apply_source, gate_source):
        require("source_artifacts" not in projected, contract)
        require("draft_prompt_for_output_pipeline" not in projected, contract)
        require("prompt" not in projected, contract)
        require("final_text" not in projected, contract)
    require(isinstance(waiting_source.get("blocked_reasons"), list), contract)
    require(isinstance(waiting_source.get("safety"), dict), contract)
    require(isinstance(apply_source.get("blocked_reasons"), list), contract)
    require(isinstance(apply_source.get("safety"), dict), contract)
    require(isinstance(gate_source.get("blocked_reasons"), list), contract)
    require(isinstance(gate_source.get("safety"), dict), contract)

    blocked_reasons = contract.get("blocked_reasons")
    require(isinstance(blocked_reasons, list), contract)
    require("user_action_api_not_implemented" in blocked_reasons, contract)
    require("visible_recovery_apply_not_allowed" in blocked_reasons, contract)
    require("content_policy_not_verified" in blocked_reasons, contract)
    if disabled_expected:
        require("user_action_dry_run_disabled" in blocked_reasons, contract)
    else:
        require("user_action_dry_run_disabled" not in blocked_reasons, contract)
    if dry_run_expected:
        require("user_action_dry_run_only" in blocked_reasons, contract)
    else:
        require("user_action_dry_run_only" not in blocked_reasons, contract)

    safety = contract.get("safety")
    require(isinstance(safety, dict), contract)
    require(safety.get("contains_user_content") is False, contract)
    require(safety.get("contains_backend_payload") is False, contract)
    require(safety.get("contains_response_text") is False, contract)
    require(safety.get("contains_prompt_text") is False, contract)
    require(safety.get("contains_snippet_text") is False, contract)
    require(safety.get("contains_final_text") is False, contract)
    require(safety.get("direct_user_output_allowed") is False, contract)
    require(safety.get("run_direct_text_finalization_allowed") is False, contract)
    require(safety.get("backend_payload_mutation_allowed") is False, contract)
    require(safety.get("response_body_mutation_allowed") is False, contract)


def _assert_backend_payload_not_mutated(backend_payload: dict[str, Any] | None) -> None:
    require(isinstance(backend_payload, dict), backend_payload)
    backend_text = json.dumps(backend_payload, ensure_ascii=False)
    require("user_action_contract" not in backend_text, backend_payload)
    require("relayrun.user_action_contract.v0" not in backend_text, backend_payload)
    require("visible_recovery_apply_preflight" not in backend_text, backend_payload)
    require("output_relayscn_recovery_gate" not in backend_text, backend_payload)
    require("recovery_response_generator" not in backend_text, backend_payload)
    require("visible_recovery_response_preflight" not in backend_text, backend_payload)
    require("recovery_response_draft" not in backend_text, backend_payload)
    require("recovery_apply_preflight" not in backend_text, backend_payload)
    require("waiting_user_contract" not in backend_text, backend_payload)
    require("recovery_transition_artifact" not in backend_text, backend_payload)


def _assert_no_raw_content(contract: dict[str, Any]) -> None:
    text = json.dumps(contract, ensure_ascii=False)
    require("Normal user action contract check" not in text, contract)
    require("Recover the current context" not in text, contract)
    require("それについて教えて" not in text, contract)
    require("Backend error user action contract check" not in text, contract)
    require("RELAYRUN_SNIPPET_SENTINEL" not in text, contract)
    require("Ask the user to confirm or restate the current context before continuing." not in text, contract)
    require(
        "Ask the user to clarify the unresolved reference before using memory or continuing."
        not in text,
        contract,
    )
    require("Explain that the backend request failed and ask whether to retry." not in text, contract)
    require("draft_prompt_for_output_pipeline" not in text, contract)
    require("source_artifacts" in contract, contract)
    for projected in contract.get("source_artifacts", {}).values():
        require(isinstance(projected, dict), contract)
        require("source_artifacts" not in projected, contract)


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
        payload=_payload("Normal user action contract check", "design_talk"),
        capture=capture,
    )
    contract = _user_action_contract(metadata)
    _assert_user_action_common(contract)
    require(contract.get("user_action_required") is False, contract)
    require(contract.get("required_action_kind") == "none", contract)
    require(contract.get("source_message_kind") == "none", contract)
    require(contract.get("allowed_message_intent") == "none", contract)
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_success_response_unchanged(response_body)
    _assert_no_raw_content(contract)
    print("ok normal request emits user_action_contract without required action")


def _assert_recovery_scene(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _, response_body = _post(
        port=port,
        store_root=root,
        payload=_payload("Recover the current context using RelayMEM.", "recovery"),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    contract = _user_action_contract(metadata)
    _assert_user_action_common(contract)
    require(contract.get("user_action_required") is True, contract)
    require(contract.get("required_action_kind") == "confirm_context_repair", contract)
    require(contract.get("source_waiting_user_reason") == "recovery_context_repair", contract)
    require(contract.get("source_message_kind") == "context_repair_prompt", contract)
    require("waiting_user_action_required" in contract.get("blocked_reasons", []), contract)
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_success_response_unchanged(response_body)
    _assert_no_raw_content(contract)
    print("ok recovery scene maps to confirm_context_repair user action")


def _assert_unresolved_reference(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _, response_body = _post(
        port=port,
        store_root=root,
        payload=_payload("それについて教えて", "design_talk"),
        capture=capture,
        snippet_runtime_injection_enabled=True,
        snippet_runtime_dry_run_only=False,
    )
    contract = _user_action_contract(metadata)
    _assert_user_action_common(contract)
    require(contract.get("user_action_required") is True, contract)
    require(contract.get("required_action_kind") == "clarify_reference", contract)
    require(contract.get("source_waiting_user_reason") == "unresolved_reference", contract)
    require(contract.get("source_message_kind") == "ask_clarification", contract)
    require("waiting_user_action_required" in contract.get("blocked_reasons", []), contract)
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_success_response_unchanged(response_body)
    _assert_no_raw_content(contract)
    print("ok unresolved reference maps to clarify_reference user action")


def _assert_backend_error(root: Path, capture: _Capture) -> None:
    backend_payload, metadata, status_code, response_body = _post(
        port=9,
        store_root=root,
        payload=_payload("Backend error user action contract check", "design_talk"),
        capture=capture,
        expected_status=502,
    )
    require(backend_payload is None, backend_payload)
    require(status_code == 502, status_code)
    require(isinstance(response_body, dict), response_body)
    require(response_body.get("error", {}).get("type") in {"backend_error", "backend_connection_error"}, response_body)
    contract = _user_action_contract(metadata)
    _assert_user_action_common(contract)
    require(contract.get("user_action_required") is True, contract)
    require(contract.get("required_action_kind") == "confirm_retry", contract)
    require(contract.get("source_waiting_user_reason") == "backend_error_recovery_confirmation", contract)
    require(contract.get("source_message_kind") == "explain_backend_error", contract)
    require("waiting_user_action_required" in contract.get("blocked_reasons", []), contract)
    _assert_no_raw_content(contract)
    print("ok backend error maps to confirm_retry user action and preserves existing error behavior")


def _assert_enabled_non_dry_run_still_blocked(root: Path, capture: _Capture, port: int) -> None:
    backend_payload, metadata, _, response_body = _post(
        port=port,
        store_root=root,
        payload=_payload("Enabled user action contract remains blocked", "design_talk"),
        capture=capture,
        user_action_dry_run_enabled=True,
        user_action_dry_run_only=False,
    )
    contract = _user_action_contract(metadata)
    _assert_user_action_common(contract, disabled_expected=False, dry_run_expected=False)
    require(contract.get("user_action_allowed") is False, contract)
    require("user_action_api_not_implemented" in contract.get("blocked_reasons", []), contract)
    _assert_backend_payload_not_mutated(backend_payload)
    _assert_success_response_unchanged(response_body)
    _assert_no_raw_content(contract)
    print("ok enabled non-dry-run user action contract remains blocked by not implemented")


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
