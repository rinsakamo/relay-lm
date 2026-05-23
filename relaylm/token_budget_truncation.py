"""Message-level token budget truncation helpers for RelayLM MVP-12."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from relaylm.token_budget import estimate_text_tokens


@dataclass(frozen=True)
class TokenBudgetTruncationResult:
    truncated_messages: list[dict[str, Any]]
    original_estimated_tokens: int
    truncated_estimated_tokens: int
    dropped_message_count: int
    dropped_roles: list[str]
    preserved_system: bool
    preserved_latest_user: bool
    over_budget_before: bool
    over_budget_after: bool
    blocked_reason: str | None = None

    def to_log_dict(self) -> dict[str, Any]:
        return asdict(self)


def apply_token_budget_message_truncation(
    *,
    messages: list[dict[str, Any]],
    token_budget: int,
    chars_per_token: int | float,
    keep_system: bool = True,
    keep_latest_user: bool = True,
) -> TokenBudgetTruncationResult:
    source = [dict(m) for m in messages if isinstance(m, dict)]
    original_tokens = _estimate_messages_tokens(source, chars_per_token)
    over_before = original_tokens > token_budget

    latest_user_index = _latest_role_index(source, "user") if keep_latest_user else None
    dropped_roles: list[str] = []
    kept: list[dict[str, Any]] = []
    dropped = 0

    for idx, message in enumerate(source):
        role = message.get("role")
        if keep_system and role == "system":
            kept.append(message)
            continue
        if latest_user_index is not None and idx == latest_user_index:
            kept.append(message)
            continue
        kept.append(message)

    if over_before:
        drop_order = _drop_candidate_indexes(kept, keep_system=keep_system, latest_user_index=_latest_role_index(kept, "user") if keep_latest_user else None)
        for idx in drop_order:
            current_tokens = _estimate_messages_tokens(kept, chars_per_token)
            if current_tokens <= token_budget:
                break
            msg = kept[idx]
            if msg is None:  # already dropped
                continue
            role = msg.get("role")
            dropped_roles.append(role if isinstance(role, str) else "unknown")
            kept[idx] = None  # type: ignore[assignment]
            dropped += 1

    truncated = [m for m in kept if isinstance(m, dict)]
    truncated_tokens = _estimate_messages_tokens(truncated, chars_per_token)
    over_after = truncated_tokens > token_budget
    blocked_reason = None
    if over_after:
        blocked_reason = "preserved_messages_exceed_budget"

    preserved_system = any(m.get("role") == "system" for m in truncated) if keep_system else False
    preserved_latest_user = False
    if keep_latest_user:
        original_latest = _latest_role_index(source, "user")
        if original_latest is not None:
            original_user = source[original_latest]
            preserved_latest_user = any(m is original_user for m in truncated)

    return TokenBudgetTruncationResult(
        truncated_messages=truncated,
        original_estimated_tokens=original_tokens,
        truncated_estimated_tokens=truncated_tokens,
        dropped_message_count=dropped,
        dropped_roles=dropped_roles,
        preserved_system=preserved_system,
        preserved_latest_user=preserved_latest_user,
        over_budget_before=over_before,
        over_budget_after=over_after,
        blocked_reason=blocked_reason,
    )


def _estimate_messages_tokens(messages: list[dict[str, Any]], chars_per_token: int | float) -> int:
    rendered = "\n".join(
        f"{_safe_str(m.get('role'))}: {_safe_str(m.get('content'))}" for m in messages if isinstance(m, dict)
    )
    return estimate_text_tokens(rendered, chars_per_token=int(chars_per_token)).estimated_tokens


def _safe_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


def _latest_role_index(messages: list[dict[str, Any]], role: str) -> int | None:
    for idx in range(len(messages) - 1, -1, -1):
        if messages[idx].get("role") == role:
            return idx
    return None


def _drop_candidate_indexes(
    messages: list[dict[str, Any]],
    *,
    keep_system: bool,
    latest_user_index: int | None,
) -> list[int]:
    assistants: list[int] = []
    older_users: list[int] = []
    others: list[int] = []
    for idx, m in enumerate(messages):
        role = m.get("role")
        if keep_system and role == "system":
            continue
        if latest_user_index is not None and idx == latest_user_index:
            continue
        if role == "assistant":
            assistants.append(idx)
        elif role == "user":
            older_users.append(idx)
        else:
            others.append(idx)
    return assistants + older_users + others
