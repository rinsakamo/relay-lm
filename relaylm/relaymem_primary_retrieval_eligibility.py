"""Read-only lifecycle eligibility for ordinary Primary MEM retrieval."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import _relaymem_primary_current_state_impl as _impl
from ._relaymem_primary_page_writer_common import is_sha256
from .relaymem_primary_current_state import (
    PrimaryCurrentState,
    PrimaryCurrentStateError,
    resolve_primary_current_state,
)

_REASON_IDS = {
    "eligible_current_active",
    "excluded_prior_revision",
    "excluded_hidden",
    "excluded_prepared",
    "excluded_recovery_required",
    "excluded_corrupt",
    "excluded_unresolved_identity",
    "excluded_scope_mismatch",
    "excluded_unsafe",
}
_MAX_UNIQUE_RESOLUTIONS = 32


@dataclass(frozen=True, repr=False)
class PrimaryRetrievalEligibilityDecision:
    eligible: bool
    reason_id: str
    lifecycle_state: str
    mutation_state: str
    current_revision: int | None
    logical_memory_id: str | None = field(default=None, repr=False)
    current_physical_id: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.reason_id not in _REASON_IDS:
            raise ValueError("invalid eligibility reason")

    def __repr__(self) -> str:
        return (
            "PrimaryRetrievalEligibilityDecision("
            f"eligible={self.eligible!r}, reason_id={self.reason_id!r}, "
            f"lifecycle_state={self.lifecycle_state!r}, "
            f"mutation_state={self.mutation_state!r}, "
            f"current_revision={self.current_revision!r})"
        )

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "reason_id": self.reason_id,
            "lifecycle_state": self.lifecycle_state,
            "mutation_state": self.mutation_state,
            "current_revision": self.current_revision,
            "content_included": False,
            "path_included": False,
            "namespace_included": False,
            "identity_included": False,
            "digest_included": False,
        }


@dataclass(repr=False)
class PrimaryRetrievalEligibilityIndex:
    root: Path | None
    namespace: str | None
    state: _impl.PrimaryCorrectionStateIndex
    available: bool
    _cache: dict[str, PrimaryCurrentState | None] = field(default_factory=dict, repr=False)
    _resolution_count: int = field(default=0, repr=False)

    def __repr__(self) -> str:
        return (
            "PrimaryRetrievalEligibilityIndex("
            f"available={self.available!r}, cached_count={len(self._cache)!r})"
        )

    def evaluate(
        self,
        physical_identity: object,
        *,
        candidate_namespace: object | None = None,
    ) -> PrimaryRetrievalEligibilityDecision:
        if candidate_namespace is not None and candidate_namespace != self.namespace:
            return _decision(False, "excluded_scope_mismatch")
        if not self.available or self.root is None or self.namespace is None:
            return _decision(False, "excluded_unsafe")
        if not is_sha256(physical_identity):
            return _decision(False, "excluded_unresolved_identity")

        physical = str(physical_identity)
        logical = self.state.logical_by_physical.get(physical, physical)
        if "*" in self.state.invalid_logical or logical in self.state.invalid_logical:
            return _decision(False, "excluded_corrupt")
        if physical in self.state.pending_physical or logical in self.state.pending_logical:
            current = self._resolve(logical)
            if current is not None and current.lifecycle_state == "hidden":
                return _from_state(False, "excluded_recovery_required", current)
            if current is not None:
                return _from_state(False, "excluded_prepared", current)
            return _decision(False, "excluded_prepared")

        current = self._resolve(logical)
        if current is None:
            return _decision(False, "excluded_unresolved_identity")
        if (
            current.mutation_state == "corrupt"
            or not current.controls_valid
            or not current.page_valid
        ):
            return _from_state(False, "excluded_corrupt", current)
        if current.current_physical_id != physical:
            return _from_state(False, "excluded_prior_revision", current)
        if current.lifecycle_state == "hidden":
            reason = (
                "excluded_recovery_required"
                if current.mutation_state == "recovery_required"
                else "excluded_hidden"
            )
            return _from_state(False, reason, current)
        if current.mutation_state in {"prepared", "forget_prepared", "recovery_required"}:
            return _from_state(False, "excluded_prepared", current)
        if (
            current.lifecycle_state == "active"
            and current.mutation_state == "none"
            and current.retrieval_eligible is True
        ):
            return _from_state(True, "eligible_current_active", current)
        return _from_state(False, "excluded_unresolved_identity", current)

    def _resolve(self, logical: str) -> PrimaryCurrentState | None:
        if logical in self._cache:
            return self._cache[logical]
        if self._resolution_count >= _MAX_UNIQUE_RESOLUTIONS:
            return None
        self._resolution_count += 1
        try:
            value = resolve_primary_current_state(
                self.root, namespace=self.namespace or "", memory_id=logical
            )
        except PrimaryCurrentStateError:
            value = None
        self._cache[logical] = value
        return value


def load_primary_retrieval_eligibility_index(
    store_root: str | Path, *, namespace: str
) -> PrimaryRetrievalEligibilityIndex:
    if (
        not isinstance(namespace, str)
        or not namespace
        or namespace != namespace.strip()
        or any(character in namespace for character in "\0\n\r\t")
    ):
        return PrimaryRetrievalEligibilityIndex(
            None,
            None,
            _impl.empty_primary_current_state_index(invalid={"*"}),
            False,
        )
    try:
        state = _impl.load_primary_current_state_index(store_root, namespace=namespace)
    except PrimaryCurrentStateError:
        return PrimaryRetrievalEligibilityIndex(
            None,
            namespace,
            _impl.empty_primary_current_state_index(invalid={"*"}),
            False,
        )
    return PrimaryRetrievalEligibilityIndex(Path(store_root), namespace, state, True)


def _decision(eligible: bool, reason: str) -> PrimaryRetrievalEligibilityDecision:
    return PrimaryRetrievalEligibilityDecision(
        eligible=eligible,
        reason_id=reason,
        lifecycle_state="unknown",
        mutation_state="unknown",
        current_revision=None,
    )


def _from_state(
    eligible: bool,
    reason: str,
    state: PrimaryCurrentState,
) -> PrimaryRetrievalEligibilityDecision:
    return PrimaryRetrievalEligibilityDecision(
        eligible=eligible,
        reason_id=reason,
        lifecycle_state=state.lifecycle_state,
        mutation_state=state.mutation_state,
        current_revision=state.current_revision,
        logical_memory_id=state.memory_id,
        current_physical_id=state.current_physical_id,
    )


__all__ = [
    "PrimaryRetrievalEligibilityDecision",
    "PrimaryRetrievalEligibilityIndex",
    "load_primary_retrieval_eligibility_index",
]
