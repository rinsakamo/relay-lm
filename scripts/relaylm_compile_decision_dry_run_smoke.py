from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig
from relaylm.diagnostics import RequestDiagnostics, build_compile_decision_dry_run
from relaylm.trace_runtime import trace_runtime_event


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    dry = build_compile_decision_dry_run(
        decision_id="dec-1",
        plan_id="plan-1",
        result_id="res-1",
        selected_route="relaylm-default",
        selected_mode="memory_light",
        backend="default",
        character_id="default",
        compiled_message_count=2,
        blocking_reasons=None,
        omitted_block_ids=None,
        token_budget_status="within_budget",
    )

    require(dry["decision_state"] == "COMPILE_DRY_RUN", dry)
    require(dry["apply_compiled_messages"] is False, dry)
    require(dry["diagnostics_only"] is True, dry)
    require(isinstance(dry["blocking_reasons"], list), dry)
    require(isinstance(dry["omitted_block_ids"], list), dry)
    require("messages" not in dry and "prompt" not in dry, dry)
    print("ok compile decision dry-run defaults")

    diagnostics = RequestDiagnostics(
        request_id="req-1",
        route_model="relaylm-default",
        compile_decision_dry_run=dry,
        trace_enabled=True,
    )
    log_payload = diagnostics.to_log_dict()
    require(log_payload.get("compile_decision_dry_run") == dry, log_payload)
    print("ok diagnostics log includes compile decision dry-run")

    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        trace_path = Path(td) / "trace.jsonl"
        cfg["trace"] = {"enabled": True, "path": str(trace_path)}
        config = RelayLMConfig.model_validate(cfg)

        wrote = trace_runtime_event(
            config=config,
            diagnostics=diagnostics,
            messages=[{"role": "user", "content": "hello"}],
            response_text="ok",
            metadata={"phase": "smoke"},
        )
        require(wrote is True, wrote)
        content = trace_path.read_text(encoding="utf-8")
        require("compile_decision_dry_run" in content, content)
        print("ok trace metadata includes compile decision dry-run")

        config_disabled = config.model_copy(deep=True)
        config_disabled.trace.enabled = False
        wrote_disabled = trace_runtime_event(
            config=config_disabled,
            diagnostics=diagnostics,
            messages=[{"role": "user", "content": "hello"}],
            response_text="ok",
            metadata={"phase": "disabled"},
        )
        require(wrote_disabled is False, wrote_disabled)
        print("ok trace disabled path unchanged")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
