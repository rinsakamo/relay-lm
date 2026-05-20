"""Gated profile compile decisions for RelayLM MVP-2."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from relaylm.profile_plan import ProfileCompilePlan


@dataclass(frozen=True)
class CompileApplyDecision:
    should_apply: bool
    mode_applied: str | None
    profile_compile_ready: bool
    reason: str

    def to_log_dict(self) -> dict[str, Any]:
        return asdict(self)


def decide_compile_apply(
    *,
    mode_applied: str | None,
    plan: ProfileCompilePlan,
) -> CompileApplyDecision:
    """Decide whether compiled profile messages may be applied.

    MVP-2 keeps pass-through mode diagnostics-only. The first apply-eligible
    mode is memory_light, and it still requires a successful dry-run plan.
    """

    if not plan.enabled:
        return CompileApplyDecision(
            should_apply=False,
            mode_applied=mode_applied,
            profile_compile_ready=False,
            reason=plan.fallback_reason or "profile_compile_not_ready",
        )

    if mode_applied == "pass_through":
        return CompileApplyDecision(
            should_apply=False,
            mode_applied=mode_applied,
            profile_compile_ready=True,
            reason="pass_through_diagnostics_only",
        )

    if mode_applied == "memory_light":
        return CompileApplyDecision(
            should_apply=True,
            mode_applied=mode_applied,
            profile_compile_ready=True,
            reason="memory_light_compile_enabled",
        )

    return CompileApplyDecision(
        should_apply=False,
        mode_applied=mode_applied,
        profile_compile_ready=True,
        reason="compile_apply_not_enabled_for_mode",
    )
