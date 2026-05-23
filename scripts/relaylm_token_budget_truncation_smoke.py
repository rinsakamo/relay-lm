from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.token_budget_truncation import apply_token_budget_message_truncation


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    messages = [
        {"role": "system", "content": "system anchor"},
        {"role": "user", "content": "old user context"},
        {"role": "assistant", "content": "assistant history " * 20},
        {"role": "user", "content": "latest user question"},
    ]
    original = copy.deepcopy(messages)

    within = apply_token_budget_message_truncation(
        messages=messages,
        token_budget=10_000,
        chars_per_token=4,
    )
    require(within.dropped_message_count == 0, within)
    require(within.truncated_messages == messages, within)
    print("ok truncation within budget unchanged")

    over = apply_token_budget_message_truncation(
        messages=messages,
        token_budget=30,
        chars_per_token=4,
    )
    require(over.dropped_message_count > 0, over)
    require(any(r == "assistant" for r in over.dropped_roles), over)
    require(any(m.get("role") == "system" for m in over.truncated_messages), over)
    require(any(m.get("role") == "user" and "latest user" in str(m.get("content")) for m in over.truncated_messages), over)
    print("ok truncation over budget drops older messages")

    blocked = apply_token_budget_message_truncation(
        messages=[
            {"role": "system", "content": "S" * 300},
            {"role": "user", "content": "U" * 300},
        ],
        token_budget=20,
        chars_per_token=4,
    )
    require(blocked.over_budget_after is True, blocked)
    require(blocked.blocked_reason == "preserved_messages_exceed_budget", blocked)
    print("ok truncation blocked when preserved exceeds budget")

    malformed = apply_token_budget_message_truncation(
        messages=[
            {"role": "system", "content": None},
            {"role": "assistant", "content": {"x": "y"}},
            {"role": "user", "content": 12345},
        ],
        token_budget=25,
        chars_per_token=4,
    )
    require(isinstance(malformed.truncated_messages, list), malformed)
    print("ok truncation handles malformed content safely")

    require(messages == original, {"messages": messages, "original": original})
    print("ok truncation does not mutate input")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
