from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import load_config
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import resolve_route
from relaylm.token_policy_signal import build_token_policy_signal


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    within = build_token_policy_signal(
        {
            "assembly": {
                "token_budget": 100,
                "estimated_tokens": 80,
            }
        }
    )
    require(within.status == "within_budget", within)
    require(within.over_budget_by == 0, within)
    print("ok token policy signal within budget")

    exceeded = build_token_policy_signal(
        {
            "assembly": {
                "token_budget": 100,
                "estimated_tokens": 130,
            }
        }
    )
    require(exceeded.status == "budget_exceeded", exceeded)
    require(exceeded.over_budget_by == 30, exceeded)
    print("ok token policy signal budget exceeded")

    missing = build_token_policy_signal(None)
    require(missing.status == "missing_dry_run", missing)
    print("ok token policy signal missing dry run")

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
    print("ok token policy signal compile path unchanged")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
