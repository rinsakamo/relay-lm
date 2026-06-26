"""Public I-4C2 apply semantics over the lower-level recovery engine."""
from __future__ import annotations

from typing import Any

from ._relaymem_primary_forget_impl import PrimaryForgetError
from .relaymem_primary_current_state import resolve_primary_current_state
from .relaymem_primary_forget_recovery import (
    PrimaryForgetApplyResult,
    apply_primary_memory_forget as _apply_primary_memory_forget,
)


def apply_primary_memory_forget(**kwargs: Any) -> PrimaryForgetApplyResult:
    """Normalize a valid stale retry only after a fresh canonical lifecycle reread.

    The lower-level I-4C1 token validation resolves the caller's expected active
    revision before it can observe the winner's lifecycle transition, so a
    different valid pre-issued Forget operation can surface ``stale_revision``.
    I-4C2 owns the public lifecycle result:

    - finalized ``hidden / none`` becomes bounded ``already_hidden``;
    - in-flight ``hidden / prepared|recovery_required`` becomes
      ``target_not_active``;
    - ``hidden / corrupt`` remains a corruption failure;
    - an active stale revision retains the original ``stale_revision``.
    """

    try:
        return _apply_primary_memory_forget(**kwargs)
    except PrimaryForgetError as exc:
        if exc.code != "stale_revision":
            raise
        try:
            state = resolve_primary_current_state(
                kwargs["store_root"],
                namespace=kwargs["namespace"],
                memory_id=kwargs["memory_id"],
            )
        except Exception:
            raise exc
        if state.lifecycle_state != "hidden":
            raise exc
        if state.mutation_state == "corrupt":
            raise PrimaryForgetError("target_corrupt") from exc
        if state.mutation_state in {"prepared", "recovery_required"}:
            raise PrimaryForgetError("target_not_active") from exc
        if state.mutation_state != "none":
            raise exc
        return PrimaryForgetApplyResult(
            status="already_hidden",
            prepared_present=False,
            hidden_successor_present=True,
            page_converged=True,
            index_converged=True,
            log_converged=True,
            tombstone_present=True,
            tombstone_created=False,
            applied_receipt_present=False,
            idempotent_replay=False,
            lifecycle_state="hidden",
            mutation_state="none",
            retrieval_eligible=False,
            prior_revision=int(kwargs["expected_revision"]),
            result_revision=state.current_revision,
            recovery_required=False,
            reason_ids=("target_already_hidden",),
        )


__all__ = ["apply_primary_memory_forget"]
