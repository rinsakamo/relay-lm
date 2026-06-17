from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.app import _resolve_token_policy_shadow_setting
from relaylm.config import RelayLMConfig, load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import resolve_route
from relaylm.token_policy_signal import (
    build_token_policy_decision_artifact,
    build_token_policy_readiness_check,
    build_token_policy_signal,
)
from relaylm.trace_runtime import trace_runtime_event


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _compile_and_decide(config: RelayLMConfig, model: str) -> tuple[dict, dict]:
    route = resolve_route(config, model)
    compiled = compile_chat_payload_if_enabled(
        config=config,
        route=route,
        payload={
            "model": model,
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )
    enabled, source = _resolve_token_policy_shadow_setting(config, route)
    signal = build_token_policy_signal(compiled.token_memory_dry_run)
    decision = build_token_policy_decision_artifact(
        signal,
        shadow_enabled=enabled,
        shadow_source=source,
    )
    require(decision.enforcement_enabled is False, decision)
    return signal.to_log_dict(), decision.to_log_dict()


def main() -> int:
    base = load_config(REPO_ROOT / "config.example.yaml")
    base_data = base.model_dump()
    base_data["model_routes"]["relaylm-default"]["mode"] = "memory_light"

    disabled_config = RelayLMConfig.model_validate(base_data)
    _, disabled = _compile_and_decide(disabled_config, "relaylm-default")
    disabled_ready = build_token_policy_readiness_check(disabled).to_log_dict()
    require(disabled["policy_mode"] == "disabled", disabled)
    require(disabled["action"] == "none", disabled)
    require(disabled_ready["ready_for_shadow_evaluation"] is False, disabled_ready)
    print("ok shadow disabled runtime gate")

    within_signal = build_token_policy_signal(
        {"assembly": {"token_budget": 120, "estimated_tokens": 80}}
    )
    within = build_token_policy_decision_artifact(
        within_signal,
        shadow_enabled=True,
        shadow_source="global",
    ).to_log_dict()
    within_ready = build_token_policy_readiness_check(within).to_log_dict()
    require(within["status"] == "ready_within_budget", within)
    require(within["action"] == "shadow_only", within)
    require(within_ready["ready_for_shadow_evaluation"] is True, within_ready)
    print("ok shadow enabled within budget runtime gate")

    exceeded_signal = build_token_policy_signal(
        {"assembly": {"token_budget": 100, "estimated_tokens": 140}}
    )
    exceeded = build_token_policy_decision_artifact(
        exceeded_signal,
        shadow_enabled=True,
        shadow_source="global",
    ).to_log_dict()
    exceeded_ready = build_token_policy_readiness_check(exceeded).to_log_dict()
    require(exceeded["status"] == "would_exceed_budget", exceeded)
    require(exceeded["action"] == "would_fallback", exceeded)
    require(exceeded_ready["ready_for_shadow_evaluation"] is True, exceeded_ready)
    print("ok budget exceeded runtime gate remains non-enforcing")

    missing = build_token_policy_decision_artifact(None, shadow_enabled=True).to_log_dict()
    missing_ready = build_token_policy_readiness_check(missing).to_log_dict()
    require(missing["status"] == "missing_signal", missing)
    require(missing_ready["blocked_reason"] == "missing_signal", missing_ready)

    invalid = build_token_policy_decision_artifact(
        {"status": 999},
        shadow_enabled=True,
    ).to_log_dict()
    invalid_ready = build_token_policy_readiness_check(invalid).to_log_dict()
    require(invalid["status"] == "invalid_signal", invalid)
    require(invalid_ready["blocked_reason"] == "invalid_signal", invalid_ready)

    unknown_ready = build_token_policy_readiness_check(
        {
            "status": "experimental_status",
            "shadow_enabled": True,
            "enforcement_enabled": False,
        }
    ).to_log_dict()
    require(
        unknown_ready["blocked_reason"] == "unknown_status:experimental_status",
        unknown_ready,
    )
    print("ok missing invalid and unknown gate states")

    shadow_data = base.model_dump()
    shadow_data["memory"]["token_policy_shadow_enabled"] = True
    shadow_config = RelayLMConfig.model_validate(shadow_data)
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "trace.jsonl"
        trace_data = shadow_config.model_dump()
        trace_data["trace"] = {"enabled": True, "path": str(trace_path)}
        trace_config = RelayLMConfig.model_validate(trace_data)
        signal_data, decision_data = _compile_and_decide(
            trace_config,
            "relaylm-default",
        )
        diagnostics = RequestDiagnostics(
            request_id="req-runtime-gate",
            route_model="relaylm-default",
            token_policy_signal=signal_data,
            token_policy_decision=decision_data,
            token_policy_readiness=build_token_policy_readiness_check(
                decision_data
            ).to_log_dict(),
        )
        require(
            trace_runtime_event(
                config=trace_config,
                diagnostics=diagnostics,
                message_count=1,
                response_present=False,
            ),
            "trace not written",
        )
        metadata = json.loads(trace_path.read_text(encoding="utf-8"))["metadata"]
        require("token_policy_signal" not in metadata, metadata)
        require("token_policy_decision" not in metadata, metadata)
        require("token_policy_readiness" not in metadata, metadata)
        print("ok runtime gate diagnostics stay outside audit metadata")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
