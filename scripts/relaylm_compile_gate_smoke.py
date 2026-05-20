from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.compile_gate import decide_compile_apply
from relaylm.config import load_config
from relaylm.profile_plan import build_profile_compile_plan
from relaylm.routing import resolve_route


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    config = load_config(REPO_ROOT / "config.example.yaml")
    route = resolve_route(config, "relaylm-default")
    incoming_messages = [{"role": "user", "content": "hello"}]
    plan = build_profile_compile_plan(
        config=config,
        route=route,
        incoming_messages=incoming_messages,
    )
    require(plan.enabled is True, plan)

    pass_through_decision = decide_compile_apply(
        mode_applied="pass_through",
        plan=plan,
    )
    require(pass_through_decision.should_apply is False, pass_through_decision)
    require(pass_through_decision.profile_compile_ready is True, pass_through_decision)
    require(pass_through_decision.reason == "pass_through_diagnostics_only", pass_through_decision)
    print("ok pass-through diagnostics-only decision")

    memory_light_decision = decide_compile_apply(
        mode_applied="memory_light",
        plan=plan,
    )
    require(memory_light_decision.should_apply is True, memory_light_decision)
    require(memory_light_decision.profile_compile_ready is True, memory_light_decision)
    require(memory_light_decision.reason == "memory_light_compile_enabled", memory_light_decision)
    print("ok memory-light compile apply decision")

    broken_config = config.model_copy(deep=True)
    broken_config.characters["default"].soul = "missing/SOUL.md"
    fallback_plan = build_profile_compile_plan(
        config=broken_config,
        route=route,
        incoming_messages=incoming_messages,
    )
    fallback_decision = decide_compile_apply(
        mode_applied="memory_light",
        plan=fallback_plan,
    )
    require(fallback_decision.should_apply is False, fallback_decision)
    require(fallback_decision.profile_compile_ready is False, fallback_decision)
    require(fallback_decision.reason == "FileNotFoundError", fallback_decision)
    print("ok fallback compile decision")

    payload = memory_light_decision.to_log_dict()
    require(payload["should_apply"] is True, payload)
    require(payload["reason"] == "memory_light_compile_enabled", payload)
    print("ok compile decision log payload")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
