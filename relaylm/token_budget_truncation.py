"""Message-level token budget truncation helpers for RelayLM MVP-12."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from relaylm.config import RelayLMConfig
from relaylm.pipeline_context import PipelineContext, replace_pipeline_forwarded_payload
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


def apply_token_budget_truncation_phase(
    *,
    config: RelayLMConfig,
    pipeline_context: PipelineContext,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Apply token budget truncation as one CTX Repack phase.

    This is the final CTX Repack mutation gate on the forwarded payload: it
    must keep running after RelayMEM runtime injection and RelayCTX
    short-term injection (see ``relaylm.relayctx_repack``) so a payload grown
    by those earlier stages still gets truncated against
    ``config.memory.token_budget``.
    """

    forwarded_payload, token_budget_truncation = _maybe_apply_token_budget_truncation(
        config=config,
        payload=pipeline_context.forwarded_payload,
    )
    forwarded_payload = replace_pipeline_forwarded_payload(
        pipeline_context,
        forwarded_payload,
        "token_budget_truncation",
    )
    return forwarded_payload, token_budget_truncation


def run_token_budget_truncation_stage(
    *,
    config: RelayLMConfig,
    pipeline_context: PipelineContext,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Stage entry point for the token_budget_truncation stage.

    Thin wrapper around ``apply_token_budget_truncation_phase`` so
    ``handle_managed_chat_completion`` can invoke this stage through
    ``run_stage`` with a stage-named entry point (matching the
    ``run_<component>_stage`` convention used by the other pipeline stages),
    while keeping ``apply_token_budget_truncation_phase`` itself as the
    stable phase function other callers
    (``scripts/relaylm_ctx_repack_final_gate_smoke.py``, re-exported from
    ``relaylm.relayctx_repack`` for backward compatibility) already depend
    on. Note: ``apply_token_budget_truncation_phase`` mutates
    ``pipeline_context`` internally (via ``replace_pipeline_forwarded_payload``)
    as it always has; this wrapper does not add, remove, or relocate any of
    that mutation, and this stage's position as the FINAL pre-backend
    payload-mutation gate must not move.
    """

    return apply_token_budget_truncation_phase(
        config=config,
        pipeline_context=pipeline_context,
    )


def _maybe_apply_token_budget_truncation(
    *,
    config: RelayLMConfig,
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    forwarded_payload = dict(payload)
    forwarded_messages = _extract_repack_messages(payload)
    result = _build_token_budget_truncation_dry_run(
        config=config,
        forwarded_messages=forwarded_messages,
    )
    if result is None:
        return forwarded_payload, None

    if not config.memory.token_budget_truncation_enabled:
        return forwarded_payload, result

    blocked_reason = result.get("blocked_reason")
    over_after = result.get("over_budget_after") is True
    dropped_message_count = result.get("dropped_message_count")
    truncated_messages = result.get("truncated_messages")
    if (
        blocked_reason
        or over_after
        or not isinstance(truncated_messages, list)
        or not isinstance(dropped_message_count, int)
        or dropped_message_count <= 0
    ):
        result["applied"] = False
        result["apply_mode"] = "runtime_apply"
        return forwarded_payload, result

    original_messages = payload.get("messages")
    if not isinstance(original_messages, list):
        return forwarded_payload, result

    forwarded_payload["messages"] = [
        m for m in truncated_messages if isinstance(m, dict)
    ]
    result["applied"] = True
    result["apply_mode"] = "runtime_apply"
    return forwarded_payload, result


def _build_token_budget_truncation_dry_run(
    *,
    config: RelayLMConfig,
    forwarded_messages: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if config.memory.token_budget is None:
        return None
    result = apply_token_budget_message_truncation(
        messages=forwarded_messages,
        token_budget=config.memory.token_budget,
        chars_per_token=config.memory.chars_per_token,
        keep_system=True,
        keep_latest_user=True,
    ).to_log_dict()
    result["enforcement_enabled"] = config.memory.token_budget_truncation_enabled
    result["applied"] = False
    result["apply_mode"] = "dry_run"
    return result


def _extract_repack_messages(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list):
        return []
    return [message for message in raw_messages if isinstance(message, dict)]


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
