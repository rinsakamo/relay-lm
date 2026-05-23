"""Policy-ready summary helpers for token memory dry-run signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TokenPolicySignal:
    status: str
    token_budget: int | None
    estimated_tokens: int | None
    over_budget_by: int | None

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "token_budget": self.token_budget,
            "estimated_tokens": self.estimated_tokens,
            "over_budget_by": self.over_budget_by,
        }


@dataclass(frozen=True)
class TokenPolicyDecisionArtifact:
    status: str
    action: str
    policy_mode: str
    shadow_enabled: bool
    enforcement_enabled: bool
    signal_status: str | None
    token_budget: int | None
    estimated_tokens: int | None
    over_budget_by: int | None

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "action": self.action,
            "policy_mode": self.policy_mode,
            "shadow_enabled": self.shadow_enabled,
            "enforcement_enabled": self.enforcement_enabled,
            "signal_status": self.signal_status,
            "token_budget": self.token_budget,
            "estimated_tokens": self.estimated_tokens,
            "over_budget_by": self.over_budget_by,
        }


def build_token_policy_signal(token_memory_dry_run: dict[str, Any] | None) -> TokenPolicySignal:
    if token_memory_dry_run is None:
        return TokenPolicySignal(
            status="missing_dry_run",
            token_budget=None,
            estimated_tokens=None,
            over_budget_by=None,
        )

    assembly = token_memory_dry_run.get("assembly")
    if not isinstance(assembly, dict):
        return TokenPolicySignal(
            status="missing_assembly",
            token_budget=None,
            estimated_tokens=None,
            over_budget_by=None,
        )

    token_budget = assembly.get("token_budget")
    estimated_tokens = assembly.get("estimated_tokens")
    if not isinstance(token_budget, int) or not isinstance(estimated_tokens, int):
        return TokenPolicySignal(
            status="incomplete_assembly",
            token_budget=token_budget if isinstance(token_budget, int) else None,
            estimated_tokens=estimated_tokens if isinstance(estimated_tokens, int) else None,
            over_budget_by=None,
        )

    if estimated_tokens > token_budget:
        return TokenPolicySignal(
            status="budget_exceeded",
            token_budget=token_budget,
            estimated_tokens=estimated_tokens,
            over_budget_by=estimated_tokens - token_budget,
        )

    return TokenPolicySignal(
        status="within_budget",
        token_budget=token_budget,
        estimated_tokens=estimated_tokens,
        over_budget_by=0,
    )


def build_token_policy_decision_artifact(
    token_policy_signal: dict[str, Any] | TokenPolicySignal | None,
    *,
    shadow_enabled: bool = False,
) -> TokenPolicyDecisionArtifact:
    policy_mode = "shadow" if shadow_enabled else "disabled"
    if token_policy_signal is None:
        return TokenPolicyDecisionArtifact(
            status="missing_signal",
            action="none",
            policy_mode=policy_mode,
            shadow_enabled=shadow_enabled,
            enforcement_enabled=False,
            signal_status=None,
            token_budget=None,
            estimated_tokens=None,
            over_budget_by=None,
        )

    if isinstance(token_policy_signal, TokenPolicySignal):
        signal_dict = token_policy_signal.to_log_dict()
    elif isinstance(token_policy_signal, dict):
        signal_dict = token_policy_signal
    else:
        return TokenPolicyDecisionArtifact(
            status="invalid_signal",
            action="none",
            policy_mode=policy_mode,
            shadow_enabled=shadow_enabled,
            enforcement_enabled=False,
            signal_status=None,
            token_budget=None,
            estimated_tokens=None,
            over_budget_by=None,
        )

    signal_status = signal_dict.get("status")
    token_budget = signal_dict.get("token_budget")
    estimated_tokens = signal_dict.get("estimated_tokens")
    over_budget_by = signal_dict.get("over_budget_by")

    if not isinstance(signal_status, str):
        return TokenPolicyDecisionArtifact(
            status="invalid_signal",
            action="none",
            policy_mode=policy_mode,
            shadow_enabled=shadow_enabled,
            enforcement_enabled=False,
            signal_status=None,
            token_budget=None,
            estimated_tokens=None,
            over_budget_by=None,
        )

    if signal_status == "within_budget":
        return TokenPolicyDecisionArtifact(
            status="ready_within_budget",
            action="shadow_only" if shadow_enabled else "none",
            policy_mode=policy_mode,
            shadow_enabled=shadow_enabled,
            enforcement_enabled=False,
            signal_status=signal_status,
            token_budget=token_budget if isinstance(token_budget, int) else None,
            estimated_tokens=estimated_tokens if isinstance(estimated_tokens, int) else None,
            over_budget_by=over_budget_by if isinstance(over_budget_by, int) else None,
        )

    if signal_status == "budget_exceeded":
        return TokenPolicyDecisionArtifact(
            status="would_exceed_budget",
            action="would_fallback" if shadow_enabled else "none",
            policy_mode=policy_mode,
            shadow_enabled=shadow_enabled,
            enforcement_enabled=False,
            signal_status=signal_status,
            token_budget=token_budget if isinstance(token_budget, int) else None,
            estimated_tokens=estimated_tokens if isinstance(estimated_tokens, int) else None,
            over_budget_by=over_budget_by if isinstance(over_budget_by, int) else None,
        )

    if signal_status in {"missing_dry_run", "missing_assembly", "incomplete_assembly"}:
        return TokenPolicyDecisionArtifact(
            status="missing_signal",
            action="none",
            policy_mode=policy_mode,
            shadow_enabled=shadow_enabled,
            enforcement_enabled=False,
            signal_status=signal_status,
            token_budget=token_budget if isinstance(token_budget, int) else None,
            estimated_tokens=estimated_tokens if isinstance(estimated_tokens, int) else None,
            over_budget_by=over_budget_by if isinstance(over_budget_by, int) else None,
        )

    return TokenPolicyDecisionArtifact(
        status="invalid_signal",
        action="none",
        policy_mode=policy_mode,
        shadow_enabled=shadow_enabled,
        enforcement_enabled=False,
        signal_status=signal_status,
        token_budget=token_budget if isinstance(token_budget, int) else None,
        estimated_tokens=estimated_tokens if isinstance(estimated_tokens, int) else None,
        over_budget_by=over_budget_by if isinstance(over_budget_by, int) else None,
    )
