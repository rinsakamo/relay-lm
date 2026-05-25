from __future__ import annotations

import copy
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig
from relaylm.diagnostics import RequestDiagnostics, build_relaysoul_runtime_feedback_summary
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.request_scope import RequestScopeIdentity, build_scope_resolution_diagnostics
from relaylm.routing import resolve_route
from relaylm.token_policy_signal import (
    build_token_policy_decision_artifact,
    build_token_policy_readiness_check,
    build_token_policy_signal,
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _config(
    *,
    scene_state_path: str | None = None,
    mode: str = "memory_light",
    route_user_id: str | None = None,
) -> RelayLMConfig:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["model_routes"]["relaylm-default"]["mode"] = mode
    if route_user_id is not None:
        cfg["model_routes"]["relaylm-default"]["user_id"] = route_user_id
    cfg["characters"]["default"]["memory_seed_path"] = "examples/memory/default_memories.yaml"
    if scene_state_path is not None:
        cfg["characters"]["default"]["scene_state"] = scene_state_path
    return RelayLMConfig.model_validate(cfg)


def _diagnostics_for(config: RelayLMConfig, payload: dict[str, object], *, conflict_scope: bool = False) -> RequestDiagnostics:
    route = resolve_route(config, "relaylm-default")
    compiled = compile_chat_payload_if_enabled(config=config, route=route, payload=payload)
    token_policy_signal = build_token_policy_signal(compiled.token_memory_dry_run)
    token_policy_decision = build_token_policy_decision_artifact(token_policy_signal)
    token_policy_readiness = build_token_policy_readiness_check(token_policy_decision).to_log_dict()

    if conflict_scope:
        request_scope = RequestScopeIdentity(
            user_id="u-conflict",
            user_type=None,
            room_id=None,
            scene_id=None,
            session_id=None,
            source="headers",
            missing_fields=["room_id", "scene_id", "session_id"],
        )
    else:
        request_scope = RequestScopeIdentity(
            user_id=None,
            user_type=None,
            room_id=None,
            scene_id=None,
            session_id=None,
            source="missing",
            missing_fields=["user_id", "room_id", "scene_id", "session_id"],
        )

    scope_resolution = build_scope_resolution_diagnostics(route, request_scope).to_log_dict()

    return RequestDiagnostics(
        request_id="smoke",
        route_model=route.route_model,
        backend_model=route.backend_model,
        backend_name=route.backend_name,
        character_id=route.character_id,
        mode_requested=route.mode_requested,
        mode_applied=route.mode_applied,
        stream_enabled=False,
        compiler_used=compiled.compiler_used,
        memory_block_used=compiled.memory_block_used,
        memory_source=compiled.memory_source,
        memory_selection_summary=(
            compiled.memory_selection_summary.to_log_dict() if compiled.memory_selection_summary else None
        ),
        token_memory_dry_run=compiled.token_memory_dry_run,
        token_policy_readiness=token_policy_readiness,
        stable_prefix_hash=compiled.stable_prefix_hash,
        stable_prefix_block_ids=compiled.stable_prefix_block_ids,
        memory_adapter_readiness=compiled.memory_adapter_readiness,
        memory_adapter_conflicts=compiled.memory_adapter_conflicts,
        context_block_summary=compiled.context_block_summary,
        persona_source_budget_diagnostics=compiled.persona_source_budget_diagnostics,
        scope_resolution_diagnostics=scope_resolution,
    )


def main() -> int:
    payload = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
    }
    before = copy.deepcopy(payload)

    diagnostics = _diagnostics_for(_config(), payload)
    summary = build_relaysoul_runtime_feedback_summary(diagnostics)
    require(summary["stable_prefix_hash_present"] is True, summary)
    require(summary["scene_state_present"] is True, summary)
    require(summary["persona_budget_status"] in {"ok", "warning"}, summary)
    require("source_char_counts" not in str(summary), summary)
    require(payload == before, payload)
    print("ok runtime feedback summary basic")

    with tempfile.TemporaryDirectory() as tmpdir:
        scene = Path(tmpdir) / "SCENE_STATE.md"
        scene.write_text("Y" * 1300, encoding="utf-8")
        diagnostics_over = _diagnostics_for(_config(scene_state_path=str(scene)), payload)
        summary_over = build_relaysoul_runtime_feedback_summary(diagnostics_over)
        require(summary_over["feedback_status"] == "warning", summary_over)
        require("persona_source_budget_warning" in summary_over["warning_reasons"], summary_over)
        print("ok budget warning reflected in feedback")

    diagnostics_conflict = _diagnostics_for(
        _config(route_user_id="route-user"),
        payload,
        conflict_scope=True,
    )
    summary_conflict = build_relaysoul_runtime_feedback_summary(diagnostics_conflict)
    require("scope_resolution_conflict" in summary_conflict["warning_reasons"], summary_conflict)
    print("ok scope conflict reflected in feedback")

    route_pt = resolve_route(_config(mode="pass_through"), "relaylm-default")
    compiled_pt = compile_chat_payload_if_enabled(config=_config(mode="pass_through"), route=route_pt, payload=payload)
    require(compiled_pt.compiler_used is False, compiled_pt.to_log_dict())
    print("ok pass_through compiler remains disabled")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
