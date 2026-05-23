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
