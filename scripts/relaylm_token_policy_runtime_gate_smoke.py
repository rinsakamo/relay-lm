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


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _compile_and_decide(config: RelayLMConfig, model: str) -> tuple[dict, dict]:
    route = resolve_route(config, model)
    payload = {"model": model, "messages": [{"role": "user", "content": "hello"}], "stream": False}
    compiled = compile_chat_payload_if_enabled(config=config, route=route, payload=payload)
    require(compiled.payload.get("model") == model, compiled.payload)
    require(compiled.payload.get("stream") is False, compiled.payload)
    shadow_enabled, shadow_source = _resolve_token_policy_shadow_setting(config, route)
    signal = build_token_policy_signal(compiled.token_memory_dry_run)
    decision = build_token_policy_decision_artifact(
        signal,
        shadow_enabled=shadow_enabled,
        shadow_source=shadow_source,
    )
    require(decision.enforcement_enabled is False, decision)
    return signal.to_log_dict(), decision.to_log_dict()


def main() -> int:
    base = load_config(REPO_ROOT / "config.example.yaml")
    base_dict = base.model_dump()
    base_dict["model_routes"]["relaylm-default"]["mode"] = "memory_light"

    # shadow disabled + within budget
    cfg_disabled = RelayLMConfig.model_validate(base_dict)
    _, disabled_decision = _compile_and_decide(cfg_disabled, "relaylm-default")
    require(disabled_decision["policy_mode"] == "disabled", disabled_decision)
    require(disabled_decision["action"] == "none", disabled_decision)
    require(disabled_decision["enforcement_enabled"] is False, disabled_decision)
    disabled_readiness = build_token_policy_readiness_check(disabled_decision).to_log_dict()
    require(disabled_readiness["ready_for_shadow_evaluation"] is False, disabled_readiness)
    print("ok shadow disabled within budget runtime gate artifact")

    # shadow enabled + within budget
    cfg_shadow_dict = base.model_dump()
    cfg_shadow_dict["memory"]["token_policy_shadow_enabled"] = True
    cfg_shadow = RelayLMConfig.model_validate(cfg_shadow_dict)
    within_signal = build_token_policy_signal({"assembly": {"token_budget": 120, "estimated_tokens": 80}})
    within_shadow_decision = build_token_policy_decision_artifact(
        within_signal,
        shadow_enabled=True,
        shadow_source="global",
    ).to_log_dict()
    require(within_shadow_decision["policy_mode"] == "shadow", within_shadow_decision)
    require(within_shadow_decision["status"] == "ready_within_budget", within_shadow_decision)
    require(within_shadow_decision["action"] == "shadow_only", within_shadow_decision)
    require(within_shadow_decision["shadow_enabled"] is True, within_shadow_decision)
    require(within_shadow_decision["shadow_source"] == "global", within_shadow_decision)
    require(within_shadow_decision["enforcement_enabled"] is False, within_shadow_decision)
    within_shadow_readiness = build_token_policy_readiness_check(within_shadow_decision).to_log_dict()
    require(within_shadow_readiness["ready_for_shadow_evaluation"] is True, within_shadow_readiness)
    print("ok shadow enabled within budget runtime gate artifact")

    # shadow enabled + budget exceeded
    exceeded_signal = build_token_policy_signal({"assembly": {"token_budget": 100, "estimated_tokens": 140}})
    exceeded_decision = build_token_policy_decision_artifact(
        exceeded_signal,
        shadow_enabled=True,
        shadow_source="global",
    ).to_log_dict()
    require(exceeded_decision["status"] == "would_exceed_budget", exceeded_decision)
    require(exceeded_decision["action"] == "would_fallback", exceeded_decision)
    require(exceeded_decision["enforcement_enabled"] is False, exceeded_decision)
    exceeded_readiness = build_token_policy_readiness_check(exceeded_decision).to_log_dict()
    require(exceeded_readiness["ready_for_shadow_evaluation"] is True, exceeded_readiness)
    print("ok shadow enabled budget exceeded runtime gate artifact")

    # missing signal
    missing_decision = build_token_policy_decision_artifact(None, shadow_enabled=True).to_log_dict()
    require(missing_decision["status"] == "missing_signal", missing_decision)
    require(missing_decision["action"] == "none", missing_decision)
    require(missing_decision["enforcement_enabled"] is False, missing_decision)
    missing_readiness = build_token_policy_readiness_check(missing_decision).to_log_dict()
    require(missing_readiness["ready_for_shadow_evaluation"] is False, missing_readiness)
    require(missing_readiness["blocked_reason"] == "missing_signal", missing_readiness)
    print("ok missing signal runtime gate artifact")

    # invalid signal
    invalid_decision = build_token_policy_decision_artifact({"status": 999}, shadow_enabled=True).to_log_dict()
    require(invalid_decision["status"] == "invalid_signal", invalid_decision)
    require(invalid_decision["enforcement_enabled"] is False, invalid_decision)
    invalid_readiness = build_token_policy_readiness_check(invalid_decision).to_log_dict()
    require(invalid_readiness["ready_for_shadow_evaluation"] is False, invalid_readiness)
    require(invalid_readiness["blocked_reason"] == "invalid_signal", invalid_readiness)
    print("ok invalid signal runtime gate artifact")

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "trace.jsonl"
        trace_dict = cfg_shadow.model_dump()
        trace_dict["trace"] = {"enabled": True, "path": str(trace_path)}
        trace_cfg = RelayLMConfig.model_validate(trace_dict)
        signal_dict, decision_dict = _compile_and_decide(trace_cfg, "relaylm-default")
        diagnostics = RequestDiagnostics(
            request_id="req-runtime-gate",
            route_model="relaylm-default",
            token_policy_signal=signal_dict,
            token_policy_decision=decision_dict,
            token_policy_readiness=build_token_policy_readiness_check(decision_dict).to_log_dict(),
        )
        require(diagnostics.to_log_dict()["token_policy_decision"] == decision_dict, diagnostics)
        require(
            isinstance(diagnostics.to_log_dict().get("token_policy_readiness"), dict),
            diagnostics.to_log_dict(),
        )
        written = trace_runtime_event(
            config=trace_cfg,
            diagnostics=diagnostics,
            messages=[{"role": "user", "content": "hello"}],
        )
        require(written, "trace not written")
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[0])
        metadata = record.get("metadata")
        require(isinstance(metadata, dict), metadata)
        require(metadata.get("token_policy_decision") == decision_dict, metadata)
        require(isinstance(metadata.get("token_policy_readiness"), dict), metadata)
        print("ok runtime gate diagnostics and trace decision artifact")

    print("ok runtime gate would_fallback remains non-enforcing")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
