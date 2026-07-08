from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import load_config
from relaylm.relayrun_runtime_artifact import _build_relayrun_runtime_artifact
from relaylm.relayrun_lazy_recovery import RECOVERY_DETAIL_ARTIFACT_KEYS
from relaylm.routing import resolve_route


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _write_config(path: Path) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["trace"] = {"enabled": False, "path": None}
    cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    # Keep every RelayRUN detail gate default-off so a completed request can take
    # the lazy ordinary path. The failed-path assertion below proves app wiring
    # still falls back to full detail when a status requires it.
    cfg["relayrun_checkpoint_write_enabled"] = False
    cfg["relayrun_checkpoint_dry_run_only"] = True
    cfg["relayrun_checkpoint_index_enabled"] = False
    cfg["relayrun_resume_preflight_enabled"] = False
    cfg["relayrun_recovery_transition_enabled"] = False
    cfg["relayrun_waiting_user_contract_enabled"] = False
    cfg["relayrun_recovery_apply_preflight_enabled"] = False
    cfg["relayrun_recovery_response_draft_enabled"] = False
    cfg["relayrun_visible_recovery_preflight_enabled"] = False
    cfg["relayrun_recovery_response_generator_enabled"] = False
    cfg["relayrun_output_relayscn_recovery_gate_enabled"] = False
    cfg["relayrun_visible_recovery_apply_preflight_enabled"] = False
    cfg["relayrun_user_action_dry_run_enabled"] = False
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _base_artifact_kwargs(*, backend_forward_status: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as td:
        cfg_path = Path(td) / "config.yaml"
        _write_config(cfg_path)
        config = load_config(str(cfg_path))
        route = resolve_route(config, "relaylm-default")
        return {
            "config": config,
            "request_id": "req-phase5d2b-runtime-smoke",
            "run_id": "run-phase5d2b-runtime-smoke",
            "route": route,
            "stream_enabled": False,
            "relayrel_relationship_projection": {
                "schema_version": "relayrel.relationship_projection.v0",
                "diagnostics_only": True,
                "content_free": True,
            },
            "relayemo_artifact": None,
            "relayscn_scene_policy_artifact": {
                "schema_version": "relayscn.scene_policy_artifact.v0",
                "diagnostics_only": True,
                "scene_state": {
                    "scene_type": "design_talk",
                    "confidence": 0.95,
                    "stability": 0.95,
                },
                "scene_policy": {
                    "schema_version": "relayscn.scene_policy.v0",
                    "persistence_block": False,
                    "persistence_block_reasons": [],
                },
                "persistence_block": False,
                "persistence_block_reasons": [],
            },
            "relayint_intent_artifact": {
                "schema_version": "relayint.reference_repair.v0",
                "diagnostics_only": True,
                "unresolved_reference_detected": False,
                "mode_reasons": [],
            },
            "relaymem_retrieval_artifact": {
                "schema_version": "relaymem.retrieval_dry_run.v0",
                "diagnostics_only": True,
                "apply_decision": "dry_run",
                "snippet_apply_decision": "dry_run",
            },
            "runtime_ctx_injection_result": {
                "schema_version": "relaymem.runtime_ctx_injection.v0",
                "diagnostics_only": True,
                "applied": True,
                "blocked_reasons": [],
            },
            "runtime_snippet_injection_result": {
                "schema_version": "relaymem.runtime_snippet_injection.v0",
                "diagnostics_only": True,
                "applied": False,
                "blocked_reasons": [],
            },
            "relayctx_short_term_runtime_injection_apply_result": None,
            "token_budget_truncation": None,
            "backend_forward_status": backend_forward_status,
            "stream_started": False,
            "first_token_sent": False,
        }


def _find_node(artifact: dict[str, Any], node_name: str) -> dict[str, Any]:
    nodes = artifact.get("node_statuses")
    require(isinstance(nodes, list), artifact)
    for node in nodes:
        if isinstance(node, dict) and node.get("node_name") == node_name:
            return node
    raise AssertionError((node_name, artifact))


def _assert_lazy_completed_path() -> None:
    artifact = _build_relayrun_runtime_artifact(
        **_base_artifact_kwargs(backend_forward_status="completed")
    )
    require(artifact.get("schema_version") == "relayrun.runtime_checkpoint.v0", artifact)
    require(artifact.get("content_free") is True, artifact)
    require(artifact.get("blocked_reasons") == [], artifact)
    recovery_detail = artifact.get("recovery_detail")
    require(isinstance(recovery_detail, dict), artifact)
    require(recovery_detail.get("constructed") is False, recovery_detail)
    require(
        recovery_detail.get("reason") == "ordinary_path_no_blocked_or_checkpoint_need",
        recovery_detail,
    )
    require(recovery_detail.get("required_reasons") == [], recovery_detail)
    require(recovery_detail.get("content_free") is True, recovery_detail)
    require(recovery_detail.get("contains_user_content") is False, recovery_detail)
    require(recovery_detail.get("contains_backend_payload") is False, recovery_detail)
    require(recovery_detail.get("contains_response_text") is False, recovery_detail)
    for key in RECOVERY_DETAIL_ARTIFACT_KEYS:
        require(artifact.get(key) is None, (key, artifact.get(key)))
    require(_find_node(artifact, "backend_forward").get("node_status") == "completed", artifact)
    require(_find_node(artifact, "relaymem_runtime_ctx").get("node_status") == "completed", artifact)
    print("ok app runtime completed path uses lazy recovery detail")


def _assert_relayemo_session_state_fallback_stays_ordinary() -> None:
    kwargs = _base_artifact_kwargs(backend_forward_status="completed")
    kwargs["config"] = kwargs["config"].model_copy(
        update={
            "relayemo_enabled": True,
            "relayemo_session_state_enabled": True,
        }
    )
    kwargs["relayemo_artifact"] = {
        "schema_version": "relayemo.runtime.v0",
        "session_state_enabled": True,
        "session_key_source": "unavailable",
        "previous_state_found": False,
        "state_updated": False,
        "state_persisted": False,
        "state_storage": "process_memory",
        "fallback_reason": "session_key_unavailable",
        "blocked_reasons": [],
        "assistant_emotion_state": {"mode": "expressive_support_estimate"},
        "user_affect_estimate": {"confidence": 0.8},
    }

    artifact = _build_relayrun_runtime_artifact(**kwargs)
    relayemo = _find_node(artifact, "relayemo")
    require(relayemo.get("node_status") == "completed", relayemo)
    require(relayemo.get("blocked_reasons") == [], relayemo)
    require(relayemo.get("fallback_reason") == "session_key_unavailable", relayemo)
    require(artifact.get("blocked_reasons") == [], artifact)

    recovery_detail = artifact.get("recovery_detail")
    require(isinstance(recovery_detail, dict), artifact)
    require(recovery_detail.get("constructed") is False, recovery_detail)
    require(
        recovery_detail.get("reason") == "ordinary_path_no_blocked_or_checkpoint_need",
        recovery_detail,
    )
    require(recovery_detail.get("required_reasons") == [], recovery_detail)
    print("ok RelayEMO session-key persistence fallback stays on lazy ordinary path")


def _assert_failed_path_keeps_full_detail() -> None:
    kwargs = _base_artifact_kwargs(backend_forward_status="failed")
    kwargs["backend_forward_blocked_reasons"] = ["BackendRequestError"]
    artifact = _build_relayrun_runtime_artifact(**kwargs)
    recovery_detail = artifact.get("recovery_detail")
    require(isinstance(recovery_detail, dict), artifact)
    require(recovery_detail.get("constructed") is True, recovery_detail)
    required_reasons = recovery_detail.get("required_reasons")
    require(isinstance(required_reasons, list), recovery_detail)
    require("backend_forward_status:failed" in required_reasons, recovery_detail)
    require(isinstance(artifact.get("resume_preflight"), dict), artifact)
    require(isinstance(artifact.get("recovery_transition_artifact"), dict), artifact)
    require(isinstance(artifact.get("checkpoint_persistence_plan"), dict), artifact)
    require(isinstance(artifact.get("checkpoint_writer_preflight"), dict), artifact)
    require(_find_node(artifact, "backend_forward").get("node_status") == "failed", artifact)
    print("ok app runtime failed path keeps full recovery detail")


def main() -> int:
    _assert_lazy_completed_path()
    _assert_relayemo_session_state_fallback_stays_ordinary()
    _assert_failed_path_keeps_full_detail()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
