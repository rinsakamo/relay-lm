from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import load_config
from relaylm.profile_plan import build_profile_compile_plan
from relaylm.routing import resolve_route


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    config = load_config(REPO_ROOT / "config.example.yaml")
    route = resolve_route(config, "relaylm-default")
    incoming_messages = [
        {"role": "system", "content": "Keep this session concise."},
        {"role": "user", "content": "hello"},
    ]

    plan = build_profile_compile_plan(
        config=config,
        route=route,
        incoming_messages=incoming_messages,
    )
    require(plan.enabled is True, plan)
    require(plan.route_model == "relaylm-default", plan)
    require(plan.character_id == "default", plan)
    require(plan.compiled_block_count == 4, plan)
    require(plan.compiled_message_count == 2, plan)
    require(plan.incoming_message_count == 2, plan)
    require(plan.incoming_system_message_count == 1, plan)
    require(plan.fallback_reason is None, plan)
    print("ok profile compile dry-run plan")

    payload = plan.to_log_dict()
    require(payload["enabled"] is True, payload)
    require(payload["compiled_block_count"] == 4, payload)
    require(payload["compiled_message_count"] == 2, payload)
    print("ok profile compile plan log payload")

    broken_config = config.model_copy(deep=True)
    broken_config.characters["default"].soul = "missing/SOUL.md"
    fallback_plan = build_profile_compile_plan(
        config=broken_config,
        route=route,
        incoming_messages=incoming_messages,
    )
    require(fallback_plan.enabled is False, fallback_plan)
    require(fallback_plan.fallback_reason == "FileNotFoundError", fallback_plan)
    print("ok profile compile fallback plan")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
