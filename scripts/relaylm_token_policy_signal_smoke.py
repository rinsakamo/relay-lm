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


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> int:
    within_signal = build_token_policy_signal(
        {"assembly": {"token_budget": 100, "estimated_tokens": 80}}
    )
    within_decision = build_token_policy_decision_artifact(within_signal)
    require(within_decision.status == "ready_within_budget", within_decision)
    require(within_decision.action == "none", within_decision)
    require(within_decision.policy_mode == "disabled", within_decision)
    require(within_decision.shadow_enabled is False, within_decision)
    require(within_decision.shadow_source == "global", within_decision)
    require(within_decision.enforcement_enabled is False, within_decision)
    print("ok token policy decision within budget")

    exceeded_signal = build_token_policy_signal(
        {"assembly": {"token_budget": 100, "estimated_tokens": 130}}
    )
    exceeded_decision = build_token_policy_decision_artifact(exceeded_signal)
    require(exceeded_decision.status == "would_exceed_budget", exceeded_decision)
    require(exceeded_decision.action == "none", exceeded_decision)
    print("ok token policy decision would exceed budget")

    missing_decision = build_token_policy_decision_artifact(None)
    require(missing_decision.status == "missing_signal", missing_decision)
    invalid_decision = build_token_policy_decision_artifact({"status": 123})
    require(invalid_decision.status == "invalid_signal", invalid_decision)
    print("ok token policy missing and invalid signals")

    shadow_decision = build_token_policy_decision_artifact(
        exceeded_signal,
        shadow_enabled=True,
    )
    require(shadow_decision.status == "would_exceed_budget", shadow_decision)
    require(shadow_decision.action == "would_fallback", shadow_decision)
    require(shadow_decision.policy_mode == "shadow", shadow_decision)
    require(shadow_decision.shadow_enabled is True, shadow_decision)
    require(shadow_decision.enforcement_enabled is False, shadow_decision)
    print("ok token policy shadow gate")

    config = load_config(REPO_ROOT / "config.example.yaml")
    route = resolve_route(config, "relaylm-default")
    request_data = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
    }
    compiled = compile_chat_payload_if_enabled(
        config=config,
        route=route,
        payload=request_data,
    )
    require(compiled.payload.get("model") == request_data["model"], compiled.payload)
    require(compiled.payload.get("stream") is False, compiled.payload)
    print("ok token policy compile path unchanged")

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "trace.jsonl"
        config_data = load_config(REPO_ROOT / "config.example.yaml").model_dump()
        config_data["trace"] = {"enabled": True, "path": str(trace_path)}
        config_data["memory"]["token_policy_shadow_enabled"] = True
        trace_config = RelayLMConfig.model_validate(config_data)
        diagnostics = RequestDiagnostics(
            request_id="req-token-policy-decision",
            token_policy_signal=exceeded_signal.to_log_dict(),
            token_policy_decision=shadow_decision.to_log_dict(),
        )
        written = trace_runtime_event(
            config=trace_config,
            diagnostics=diagnostics,
            message_count=1,
            response_present=False,
        )
        require(written, "trace record not written")
        metadata = json.loads(trace_path.read_text(encoding="utf-8"))["metadata"]
        require("token_policy_signal" not in metadata, metadata)
        require("token_policy_decision" not in metadata, metadata)
        require(metadata.get("projection_unsupported_artifact_count", 0) >= 2, metadata)
        print("ok unsupported token policy artifacts are default-denied")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
