from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.diagnostics import RequestDiagnostics


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    diagnostics = RequestDiagnostics(
        request_id="request-001",
        route_model="relaylm-default",
        backend_model="local-model",
        backend_name="local_backend",
        character_id="default",
        mode_requested="pass_through",
        mode_applied="pass_through",
        stream_enabled=False,
        compiler_used=False,
        runtime_ctx_injection_result={
            "schema_version": "relaymem.runtime_ctx_injection_result.v0",
            "applied": False,
        },
        runtime_snippet_injection_result={
            "schema_version": "relaymem.runtime_snippet_injection_result.v0",
            "applied": False,
        },
        relayrun_artifact={
            "schema_version": "relayrun.runtime_checkpoint.v0",
            "diagnostics_only": True,
            "applied": False,
            "run_id": "run-001",
            "run_status": "diagnostics_only",
            "resume_mode": "none",
            "node_statuses": [],
            "resume_preflight": {
                "schema_version": "relayrun.resume_preflight.v0",
                "diagnostics_only": True,
                "resume_allowed": False,
                "resume_attempted": False,
                "resume_applied": False,
                "checkpoint_read_attempted": False,
                "checkpoint_read_ok": False,
                "checkpoint_schema_valid": False,
                "content_free": None,
                "source_checkpoint_path": None,
                "blocked_reasons": [
                    "resume_not_implemented",
                    "resume_disabled",
                    "resume_dry_run_only",
                ],
                "future_resume_required_gates": [
                    "explicit_config_enabled",
                    "valid_checkpoint_schema",
                    "content_free_checkpoint",
                    "safe_resume_mode",
                    "user_or_policy_confirmation",
                ],
            },
            "recovery_transition_artifact": {
                "schema_version": "relayrun.recovery_transition.v0",
                "diagnostics_only": True,
                "user_visible": False,
                "apply_allowed": False,
                "applied": False,
                "transition_created": False,
                "proposed_transition_type": "none",
                "source_node": None,
                "next_node": None,
                "resume_mode": "none",
                "required_user_action": None,
                "blocked_reasons": [
                    "recovery_transition_not_implemented",
                    "recovery_transition_disabled",
                    "recovery_transition_dry_run_only",
                ],
                "safety": {
                    "passes_through_output_pipeline": True,
                    "direct_user_output_allowed": False,
                    "contains_user_content": False,
                    "contains_backend_payload": False,
                    "contains_response_text": False,
                },
            },
            "checkpoint_persisted": False,
            "checkpoint_write_attempted": False,
            "checkpoint_writer_failed": False,
            "persisted_path": None,
            "persisted_bytes": None,
            "content_free": True,
            "checkpoint_persistence_plan": {
                "schema_version": "relayrun.checkpoint_persistence_plan.v0",
                "diagnostics_only": True,
                "write_allowed": False,
                "checkpoint_persisted": False,
                "target_root": ".relayrun/checkpoints",
                "target_path_preview": ".relayrun/checkpoints/run-001/request-001.json",
                "run_id": "run-001",
                "turn_id": "request-001",
                "blocked_reasons": [
                    "checkpoint_persistence_not_implemented",
                    "checkpoint_write_disabled",
                ],
                "resume_allowed_after_persist": False,
            },
            "checkpoint_writer_preflight": {
                "schema_version": "relayrun.checkpoint_writer_preflight.v0",
                "diagnostics_only": True,
                "write_allowed": False,
                "preflight_passed": False,
                "checkpoint_write_attempted": False,
                "directory_creation_attempted": False,
                "target_root": ".relayrun/checkpoints",
                "target_path_preview": ".relayrun/checkpoints/run-001/request-001.json",
                "path_safety": {
                    "root_relative": True,
                    "path_traversal_detected": False,
                    "absolute_path_detected": False,
                },
                "content_policy": {
                    "content_free": True,
                    "backend_payload_included": False,
                    "response_text_included": False,
                    "raw_user_message_included": False,
                },
                "blocked_reasons": [
                    "checkpoint_write_disabled",
                    "checkpoint_dry_run_only",
                ],
                "future_writer_required_gates": [
                    "explicit_config_enabled",
                    "safe_target_root",
                    "content_free_payload",
                    "atomic_write",
                    "idempotent_run_turn_key",
                ],
            },
        },
    )

    headers = diagnostics.to_headers()
    require(headers["x-relaylm-request-id"] == "request-001", f"bad request id header: {headers}")
    require(headers["x-relaylm-mode"] == "pass_through", f"bad mode header: {headers}")
    require(headers["x-relaylm-run-id"] == "run-001", f"bad run id header: {headers}")
    require(headers["x-relaylm-run-status"] == "diagnostics_only", f"bad run status header: {headers}")
    require(headers["x-relaylm-resume-mode"] == "none", f"bad resume mode header: {headers}")
    require("x-relaylm-fallback-reason" not in headers, f"unexpected fallback header: {headers}")
    print("ok diagnostics headers")

    payload = diagnostics.to_log_dict()
    require(payload["request_id"] == "request-001", f"bad request_id: {payload}")
    require(payload["route_model"] == "relaylm-default", f"bad route_model: {payload}")
    require(payload["backend_model"] == "local-model", f"bad backend_model: {payload}")
    require(payload["backend_name"] == "local_backend", f"bad backend_name: {payload}")
    require(payload["character_id"] == "default", f"bad character_id: {payload}")
    require(payload["mode_applied"] == "pass_through", f"bad mode_applied: {payload}")
    require(payload["stream_enabled"] is False, f"bad stream_enabled: {payload}")
    require(payload["compiler_used"] is False, f"bad compiler_used: {payload}")
    runtime_ctx = payload.get("runtime_ctx_injection_result")
    require(isinstance(runtime_ctx, dict), f"missing runtime ctx diagnostics: {payload}")
    require(runtime_ctx.get("applied") is False, f"bad runtime ctx diagnostics: {payload}")
    runtime_snippet = payload.get("runtime_snippet_injection_result")
    require(
        isinstance(runtime_snippet, dict),
        f"missing runtime snippet diagnostics: {payload}",
    )
    require(
        runtime_snippet.get("applied") is False,
        f"bad runtime snippet diagnostics: {payload}",
    )
    relayrun = payload.get("relayrun_artifact")
    require(isinstance(relayrun, dict), f"missing relayrun diagnostics: {payload}")
    require(relayrun.get("diagnostics_only") is True, f"bad relayrun diagnostics: {payload}")
    resume_preflight = relayrun.get("resume_preflight")
    require(isinstance(resume_preflight, dict), f"missing resume preflight: {payload}")
    require(resume_preflight.get("resume_allowed") is False, f"bad resume preflight: {payload}")
    require(resume_preflight.get("resume_attempted") is False, f"bad resume preflight: {payload}")
    require(resume_preflight.get("resume_applied") is False, f"bad resume preflight: {payload}")
    transition = relayrun.get("recovery_transition_artifact")
    require(isinstance(transition, dict), f"missing recovery transition: {payload}")
    require(transition.get("user_visible") is False, f"bad recovery transition: {payload}")
    require(transition.get("applied") is False, f"bad recovery transition: {payload}")
    require(relayrun.get("checkpoint_persisted") is False, f"bad relayrun diagnostics: {payload}")
    require(relayrun.get("checkpoint_write_attempted") is False, f"bad relayrun diagnostics: {payload}")
    require(relayrun.get("content_free") is True, f"bad relayrun diagnostics: {payload}")
    plan = relayrun.get("checkpoint_persistence_plan")
    require(isinstance(plan, dict), f"missing checkpoint persistence plan: {payload}")
    require(plan.get("diagnostics_only") is True, f"bad checkpoint persistence plan: {payload}")
    require(plan.get("write_allowed") is False, f"bad checkpoint persistence plan: {payload}")
    require(plan.get("checkpoint_persisted") is False, f"bad checkpoint persistence plan: {payload}")
    preflight = relayrun.get("checkpoint_writer_preflight")
    require(isinstance(preflight, dict), f"missing checkpoint writer preflight: {payload}")
    require(preflight.get("diagnostics_only") is True, f"bad checkpoint writer preflight: {payload}")
    require(preflight.get("write_allowed") is False, f"bad checkpoint writer preflight: {payload}")
    require(preflight.get("preflight_passed") is False, f"bad checkpoint writer preflight: {payload}")
    require(
        preflight.get("checkpoint_write_attempted") is False,
        f"bad checkpoint writer preflight: {payload}",
    )
    require(
        preflight.get("directory_creation_attempted") is False,
        f"bad checkpoint writer preflight: {payload}",
    )
    print("ok diagnostics log payload")

    fallback = RequestDiagnostics(
        request_id="request-002",
        mode_applied="pass_through",
        fallback_reason="route_not_found",
    )
    fallback_headers = fallback.to_headers()
    require(
        fallback_headers["x-relaylm-fallback-reason"] == "route_not_found",
        f"bad fallback header: {fallback_headers}",
    )
    print("ok fallback header")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
