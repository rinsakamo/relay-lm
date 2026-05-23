from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig, load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import resolve_route
from relaylm.token_policy_signal import (
    build_token_policy_decision_artifact,
    build_token_policy_signal,
)
from relaylm.trace_runtime import trace_runtime_event


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    within_signal = build_token_policy_signal({"assembly": {"token_budget": 100, "estimated_tokens": 80}})
    within_decision = build_token_policy_decision_artifact(within_signal)
    require(within_decision.status == "ready_within_budget", within_decision)
    require(within_decision.action == "none", within_decision)
    require(within_decision.policy_mode == "disabled", within_decision)
    require(within_decision.shadow_enabled is False, within_decision)
    require(within_decision.shadow_source == "global", within_decision)
    require(within_decision.enforcement_enabled is False, within_decision)
    print("ok token policy decision within budget")

    exceeded_signal = build_token_policy_signal({"assembly": {"token_budget": 100, "estimated_tokens": 130}})
    exceeded_decision = build_token_policy_decision_artifact(exceeded_signal)
    require(exceeded_decision.status == "would_exceed_budget", exceeded_decision)
    require(exceeded_decision.action == "none", exceeded_decision)
    print("ok token policy decision would exceed budget")

    missing_decision = build_token_policy_decision_artifact(None)
    require(missing_decision.status == "missing_signal", missing_decision)
    print("ok token policy decision missing signal")

    invalid_decision = build_token_policy_decision_artifact({"status": 123})
    require(invalid_decision.status == "invalid_signal", invalid_decision)
    print("ok token policy decision invalid signal")

    shadow_enabled_decision = build_token_policy_decision_artifact(exceeded_signal, shadow_enabled=True)
    require(shadow_enabled_decision.status == "would_exceed_budget", shadow_enabled_decision)
    require(shadow_enabled_decision.action == "would_fallback", shadow_enabled_decision)
    require(shadow_enabled_decision.policy_mode == "shadow", shadow_enabled_decision)
    require(shadow_enabled_decision.shadow_enabled is True, shadow_enabled_decision)
    require(shadow_enabled_decision.shadow_source == "global", shadow_enabled_decision)
    require(shadow_enabled_decision.enforcement_enabled is False, shadow_enabled_decision)
    print("ok token policy decision shadow gate enabled")

    global_true_decision = build_token_policy_decision_artifact(within_signal, shadow_enabled=True)
    require(global_true_decision.status == "ready_within_budget", global_true_decision)
    require(global_true_decision.action == "shadow_only", global_true_decision)
    print("ok token policy decision global true")

    character_override_false = build_token_policy_decision_artifact(
        exceeded_signal,
        shadow_enabled=False,
        shadow_source="character",
    )
    require(character_override_false.status == "would_exceed_budget", character_override_false)
    require(character_override_false.action == "none", character_override_false)
    require(character_override_false.shadow_source == "character", character_override_false)
    print("ok token policy decision character override false")

    config = load_config(REPO_ROOT / "config.example.yaml")
    route = resolve_route(config, "relaylm-default")
    payload = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
    }
    compiled = compile_chat_payload_if_enabled(config=config, route=route, payload=payload)
    require(compiled.payload.get("model") == payload["model"], compiled.payload)
    require(compiled.payload.get("stream") is False, compiled.payload)
    print("ok token policy decision compile path unchanged")

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "trace.jsonl"
        base = load_config(REPO_ROOT / "config.example.yaml")
        config_dict = base.model_dump()
        config_dict["trace"] = {"enabled": True, "path": str(trace_path)}
        config_dict["memory"]["token_policy_shadow_enabled"] = True
        trace_config = RelayLMConfig.model_validate(config_dict)

        diagnostics = RequestDiagnostics(
            request_id="req-token-policy-decision",
            token_policy_signal=exceeded_signal.to_log_dict(),
            token_policy_decision=shadow_enabled_decision.to_log_dict(),
        )
        written = trace_runtime_event(
            config=trace_config,
            diagnostics=diagnostics,
            messages=[{"role": "user", "content": "hello"}],
        )
        require(written, "trace record not written")
        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[0])
        metadata = record.get("metadata")
        require(isinstance(metadata, dict), metadata)
        require(metadata.get("token_policy_decision") == shadow_enabled_decision.to_log_dict(), metadata)
        print("ok token policy decision trace metadata")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
