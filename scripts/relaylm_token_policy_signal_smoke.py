from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.config import RelayLMConfig, load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.token_policy_signal import build_token_policy_decision_artifact, build_token_policy_signal
from relaylm.trace_runtime import trace_runtime_event


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> int:
    within = build_token_policy_decision_artifact(
        build_token_policy_signal({"assembly": {"token_budget": 100, "estimated_tokens": 80}})
    )
    require((within.status, within.action, within.policy_mode) == ("ready_within_budget", "none", "disabled"), within)

    exceeded_signal = build_token_policy_signal(
        {"assembly": {"token_budget": 100, "estimated_tokens": 130}}
    )
    exceeded = build_token_policy_decision_artifact(exceeded_signal)
    require((exceeded.status, exceeded.action) == ("would_exceed_budget", "none"), exceeded)
    require(build_token_policy_decision_artifact(None).status == "missing_signal", "missing")
    require(build_token_policy_decision_artifact({"status": 123}).status == "invalid_signal", "invalid")

    shadow = build_token_policy_decision_artifact(exceeded_signal, shadow_enabled=True)
    require((shadow.action, shadow.policy_mode) == ("would_fallback", "shadow"), shadow)
    require(shadow.enforcement_enabled is False, shadow)
    print("ok token policy decision contracts")

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "trace.jsonl"
        data = load_config(ROOT / "config.example.yaml").model_dump()
        data["trace"] = {"enabled": True, "path": str(path)}
        config = RelayLMConfig.model_validate(data)
        diagnostics = RequestDiagnostics(
            request_id="token-policy",
            token_policy_signal=exceeded_signal.to_log_dict(),
            token_policy_decision=shadow.to_log_dict(),
        )
        require(trace_runtime_event(
            config=config,
            diagnostics=diagnostics,
            message_count=1,
            response_present=False,
        ), "trace")
        metadata = json.loads(path.read_text(encoding="utf-8"))["metadata"]
        require("token_policy_signal" not in metadata, metadata)
        require("token_policy_decision" not in metadata, metadata)
        print("ok unsupported policy diagnostics stay outside audit metadata")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
