"""Read-only I-7A/B held Apply / Discard preflight boundary.

The helper accepts one runtime-private held outcome candidate, validates its
identity/scope/source evidence, optionally rereads a related Primary MEM through
its existing current-state authority, and returns a content-free public
projection.  It never mutates B3 queue records, Primary MEM pages/index/logs,
workers, schedulers, or SOUL Lab UI state.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .relaymem_held_governance_contract import (
    ALREADY_FINAL_STATUSES,
    APPLIED_STATUS,
    B3_QUEUE_STATES,
    B3_TERMINAL_QUEUE_STATES,
    BLOCKED_STATUS,
    CORRUPT_STATUS,
    DISCARDED_STATUS,
    FAILED_STATUS,
    GOVERNABLE_HELD_STATUSES,
    HELD_APPLY_PREFLIGHT_SCHEMA,
    HELD_CANDIDATE_STATUSES,
    HELD_DISCARD_PREFLIGHT_SCHEMA,
    HELD_OUTCOME_CANDIDATE_SCHEMA,
    HELD_SOURCE_AUTHORITIES,
    HELD_SOURCE_EVIDENCE_REF_SCHEMA,
    HELD_STATUS,
    PUBLIC_EFFECTS,
    RECOVERY_REQUIRED_STATUS,
    RELATED_PRIMARY_BLOCKING_LIFECYCLES,
    RELATED_PRIMARY_BLOCKING_MUTATIONS,
    TERMINAL_FAILED_STATUS,
    TERMINAL_SUCCEEDED_STATUS,
)

_MAX_TOKEN = 128
_MAX_SCOPE = 128
_MAX_REASONS = 32
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_ACTIONS = frozenset({"apply", "discard"})
_TERMINAL_STATUS_REASON = {
    APPLIED_STATUS: "already_applied",
    DISCARDED_STATUS: "already_discarded",
    BLOCKED_STATUS: "candidate_blocked_not_held",
    FAILED_STATUS: "candidate_failed_not_held",
    RECOVERY_REQUIRED_STATUS: "candidate_recovery_required_not_held",
    CORRUPT_STATUS: "candidate_corrupt_not_held",
    TERMINAL_SUCCEEDED_STATUS: "candidate_terminal_succeeded",
    TERMINAL_FAILED_STATUS: "candidate_terminal_failed",
}
_QUEUE_TERMINAL_REASON = {
    "succeeded": "queue_terminal_succeeded",
    "failed": "queue_terminal_failed",
    "cancelled": "queue_terminal_cancelled",
    "dead_letter": "queue_terminal_dead_letter",
}


@dataclass(frozen=True)
class HeldGovernancePreflightResult:
    """Content-free I-7A/B preflight result."""

    schema_version: str
    action: str
    status: str
    read_only: bool
    candidate_id: str | None
    operation_id: str | None
    character_id: str | None
    namespace: str | None
    scope: str | None
    candidate_status: str | None
    queue_state: str | None
    related_memory_id: str | None
    related_memory_checked: bool
    reason_code: str
    blocked_reasons: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        """Return a bounded operator-facing projection without payload content."""

        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "action": self.action,
            "read_only": self.read_only,
            "candidate_id": self.candidate_id,
            "operation_id": self.operation_id,
            "character_id": self.character_id,
            "namespace": self.namespace,
            "scope": self.scope,
            "candidate_status": self.candidate_status,
            "queue_state": self.queue_state,
            "related_memory_id": self.related_memory_id,
            "related_memory_checked": self.related_memory_checked,
            "reason_code": self.reason_code,
            "blocked_reason_ids": list(self.blocked_reasons),
            "effects": dict(PUBLIC_EFFECTS[self.action]),
            "content_free": True,
            "runtime_private_evidence_omitted": True,
            "source_body_included": False,
            "model_output_included": False,
            "memory_content_included": False,
            "queue_payload_included": False,
            "primary_page_path_included": False,
            "queue_state_mutated": False,
            "primary_mem_mutated": False,
            "worker_started": False,
            "scheduler_started": False,
            "automatic_retry_or_release": False,
        }


class HeldGovernancePreflightError(RuntimeError):
    """Unexpected construction error safe for API translation."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def preflight_held_apply(
    candidate: Mapping[str, Any] | object,
    *,
    expected_character_id: str,
    expected_namespace: str,
    expected_scope: str,
    store_root: str | Path | None = None,
) -> HeldGovernancePreflightResult:
    """Compute read-only Apply preflight for one held outcome candidate."""

    return _preflight(
        "apply",
        candidate,
        expected_character_id=expected_character_id,
        expected_namespace=expected_namespace,
        expected_scope=expected_scope,
        store_root=store_root,
    )


def preflight_held_discard(
    candidate: Mapping[str, Any] | object,
    *,
    expected_character_id: str,
    expected_namespace: str,
    expected_scope: str,
    store_root: str | Path | None = None,
) -> HeldGovernancePreflightResult:
    """Compute read-only Discard preflight for one held outcome candidate."""

    return _preflight(
        "discard",
        candidate,
        expected_character_id=expected_character_id,
        expected_namespace=expected_namespace,
        expected_scope=expected_scope,
        store_root=store_root,
    )


def preflight_held_governance(
    action: str,
    candidate: Mapping[str, Any] | object,
    *,
    expected_character_id: str,
    expected_namespace: str,
    expected_scope: str,
    store_root: str | Path | None = None,
) -> HeldGovernancePreflightResult:
    """Generic read-only I-7A/B preflight entrypoint."""

    return _preflight(
        action,
        candidate,
        expected_character_id=expected_character_id,
        expected_namespace=expected_namespace,
        expected_scope=expected_scope,
        store_root=store_root,
    )


def _preflight(
    action: str,
    candidate: Mapping[str, Any] | object,
    *,
    expected_character_id: str,
    expected_namespace: str,
    expected_scope: str,
    store_root: str | Path | None,
) -> HeldGovernancePreflightResult:
    if action not in _ACTIONS:
        return _result(action if isinstance(action, str) else "invalid", None, "invalid_input", "action_invalid")
    schema = HELD_APPLY_PREFLIGHT_SCHEMA if action == "apply" else HELD_DISCARD_PREFLIGHT_SCHEMA
    if not _token(expected_character_id) or not _token(expected_namespace) or not _token(expected_scope, _MAX_SCOPE):
        return _result(action, None, "invalid_input", "expected_scope_invalid", schema=schema)
    if not isinstance(candidate, Mapping):
        return _result(action, None, "invalid_input", "candidate_mapping_required", schema=schema)

    candidate_map = dict(candidate)
    candidate_id = _field(candidate_map, "candidate_id")
    operation_id = _field(candidate_map, "operation_id")
    character_id = _field(candidate_map, "character_id")
    namespace = _field(candidate_map, "namespace")
    scope = _field(candidate_map, "scope")
    status = _field(candidate_map, "status")
    queue_state = candidate_map.get("queue_state")
    related_memory_id = candidate_map.get("related_primary_memory_id")

    base = {
        "candidate_id": candidate_id if isinstance(candidate_id, str) else None,
        "operation_id": operation_id if isinstance(operation_id, str) else None,
        "character_id": character_id if isinstance(character_id, str) else None,
        "namespace": namespace if isinstance(namespace, str) else None,
        "scope": scope if isinstance(scope, str) else None,
        "candidate_status": status if isinstance(status, str) else None,
        "queue_state": queue_state if isinstance(queue_state, str) else None,
        "related_memory_id": related_memory_id if isinstance(related_memory_id, str) else None,
    }

    shape_reasons = _validate_candidate_shape(candidate_map)
    if shape_reasons:
        return _result(action, base, "invalid_input", shape_reasons[0], shape_reasons, schema=schema)

    if character_id != expected_character_id:
        return _result(action, base, "blocked", "wrong_character", schema=schema)
    if namespace != expected_namespace:
        return _result(action, base, "blocked", "wrong_namespace", schema=schema)
    if scope != expected_scope:
        return _result(action, base, "blocked", "wrong_scope", schema=schema)

    status_reason = _status_reason(status, queue_state)
    if status_reason:
        return _result(action, base, "blocked", status_reason, schema=schema)

    source_reasons = _validate_source_evidence(candidate_map)
    if source_reasons:
        return _result(action, base, "safe_failure", source_reasons[0], source_reasons, schema=schema)

    related_reason = _validate_related_primary(candidate_map, store_root)
    if related_reason:
        reason, checked = related_reason
        return _result(
            action,
            base,
            "safe_failure",
            reason,
            (reason,),
            schema=schema,
            related_memory_checked=checked,
        )

    return _result(
        action,
        base,
        "ready",
        "ready",
        (),
        schema=schema,
        related_memory_checked=related_memory_id is not None,
    )


def _validate_candidate_shape(candidate: Mapping[str, Any]) -> tuple[str, ...]:
    required = {
        "schema_version",
        "runtime_private",
        "content_included",
        "candidate_id",
        "operation_id",
        "character_id",
        "namespace",
        "scope",
        "status",
        "queue_state",
        "source_authority",
        "source_evidence_digest",
        "source_evidence_present",
        "source_evidence_corrupt",
        "source_evidence_ambiguous",
        "source_content_included",
        "related_primary_memory_id",
        "related_primary_expected_revision",
        "related_primary_physical_id",
    }
    if set(candidate) != required:
        return ("candidate_shape_mismatch",)
    if candidate.get("schema_version") != HELD_OUTCOME_CANDIDATE_SCHEMA:
        return ("candidate_schema_invalid",)
    if candidate.get("runtime_private") is not True:
        return ("candidate_runtime_private_required",)
    if candidate.get("content_included") is not False:
        return ("candidate_content_must_be_omitted",)
    if candidate.get("source_content_included") is not False:
        return ("source_content_must_be_omitted",)
    for key in ("candidate_id", "operation_id", "character_id", "namespace", "scope"):
        limit = _MAX_SCOPE if key == "scope" else _MAX_TOKEN
        if not _token(candidate.get(key), limit):
            return (f"{key}_invalid",)
    if candidate.get("status") not in HELD_CANDIDATE_STATUSES:
        return ("candidate_status_invalid",)
    queue_state = candidate.get("queue_state")
    if queue_state is not None and queue_state not in B3_QUEUE_STATES:
        return ("queue_state_invalid",)
    if candidate.get("source_authority") not in HELD_SOURCE_AUTHORITIES:
        return ("source_authority_invalid",)
    if not _is_sha256(candidate.get("source_evidence_digest")):
        return ("source_evidence_digest_invalid",)
    for key in (
        "source_evidence_present",
        "source_evidence_corrupt",
        "source_evidence_ambiguous",
    ):
        if type(candidate.get(key)) is not bool:
            return (f"{key}_invalid",)
    related_id = candidate.get("related_primary_memory_id")
    related_revision = candidate.get("related_primary_expected_revision")
    related_physical = candidate.get("related_primary_physical_id")
    if related_id is None:
        if related_revision is not None or related_physical is not None:
            return ("related_primary_shape_invalid",)
    else:
        if not _is_sha256(related_id):
            return ("related_primary_memory_id_invalid",)
        if type(related_revision) is not int or related_revision < 1:
            return ("related_primary_expected_revision_invalid",)
        if related_physical is not None and not _is_sha256(related_physical):
            return ("related_primary_physical_id_invalid",)
    return ()


def _validate_source_evidence(candidate: Mapping[str, Any]) -> tuple[str, ...]:
    if candidate.get("source_evidence_present") is not True:
        return ("source_evidence_missing",)
    if candidate.get("source_evidence_corrupt") is True:
        return ("source_evidence_corrupt",)
    if candidate.get("source_evidence_ambiguous") is True:
        return ("source_evidence_ambiguous",)
    if candidate.get("source_authority") not in HELD_SOURCE_AUTHORITIES:
        return ("source_authority_invalid",)
    return ()


def _validate_related_primary(
    candidate: Mapping[str, Any], store_root: str | Path | None
) -> tuple[str, bool] | None:
    related_id = candidate.get("related_primary_memory_id")
    if related_id is None:
        return None
    expected_revision = candidate.get("related_primary_expected_revision")
    assert type(expected_revision) is int
    if store_root is None:
        return "related_primary_store_root_required", False
    try:
        from .relaymem_primary_current_state import (  # pylint: disable=import-outside-toplevel
            PrimaryCurrentStateError,
            resolve_primary_current_state,
        )
        state = resolve_primary_current_state(
            store_root,
            namespace=str(candidate["namespace"]),
            memory_id=str(related_id),
            expected_revision=expected_revision,
        )
    except ImportError as exc:
        raise HeldGovernancePreflightError("primary_current_state_unavailable") from exc
    except PrimaryCurrentStateError as exc:  # type: ignore[name-defined]
        return _map_primary_error(exc.code), True

    if state.lifecycle_state in RELATED_PRIMARY_BLOCKING_LIFECYCLES:
        return "related_primary_hidden", True
    if state.mutation_state in RELATED_PRIMARY_BLOCKING_MUTATIONS:
        return f"related_primary_{state.mutation_state}", True
    if not state.controls_valid or not state.page_valid:
        return "related_primary_corrupt", True
    if state.current_revision != expected_revision:
        return "related_primary_prior", True
    expected_physical = candidate.get("related_primary_physical_id")
    if expected_physical is not None and state.current_physical_id != expected_physical:
        return "related_primary_prior", True
    if not state.retrieval_eligible:
        return "related_primary_not_retrieval_eligible", True
    return None


def _status_reason(status: object, queue_state: object) -> str | None:
    if status not in GOVERNABLE_HELD_STATUSES:
        assert isinstance(status, str)
        return _TERMINAL_STATUS_REASON.get(status, "candidate_not_held")
    if queue_state in B3_TERMINAL_QUEUE_STATES:
        assert isinstance(queue_state, str)
        return _QUEUE_TERMINAL_REASON[queue_state]
    return None


def _map_primary_error(code: str) -> str:
    return {
        "target_not_found": "related_primary_not_found",
        "not_found_or_wrong_scope": "related_primary_not_found",
        "target_corrupt": "related_primary_corrupt",
        "store_unavailable": "related_primary_store_unavailable",
        "stale_revision": "related_primary_prior",
        "target_not_active": "related_primary_hidden",
        "operation_conflict": "related_primary_prepared",
        "invalid_request": "related_primary_invalid",
    }.get(code, "related_primary_corrupt")


def _result(
    action: str,
    base: Mapping[str, Any] | None,
    status: str,
    reason: str,
    reasons: tuple[str, ...] | None = None,
    *,
    schema: str | None = None,
    related_memory_checked: bool = False,
) -> HeldGovernancePreflightResult:
    if action not in _ACTIONS:
        action = "apply"
    projection_base = dict(base or {})
    reason_tuple = _dedupe(reasons if reasons is not None else (reason,))
    return HeldGovernancePreflightResult(
        schema_version=schema or (
            HELD_APPLY_PREFLIGHT_SCHEMA if action == "apply" else HELD_DISCARD_PREFLIGHT_SCHEMA
        ),
        action=action,
        status=status,
        read_only=True,
        candidate_id=projection_base.get("candidate_id"),
        operation_id=projection_base.get("operation_id"),
        character_id=projection_base.get("character_id"),
        namespace=projection_base.get("namespace"),
        scope=projection_base.get("scope"),
        candidate_status=projection_base.get("candidate_status"),
        queue_state=projection_base.get("queue_state"),
        related_memory_id=projection_base.get("related_memory_id"),
        related_memory_checked=related_memory_checked,
        reason_code=reason,
        blocked_reasons=reason_tuple,
    )


def _field(candidate: Mapping[str, Any], key: str) -> object:
    return candidate.get(key)


def _token(value: object, limit: int = _MAX_TOKEN) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= limit
        and _TOKEN_RE.fullmatch(value) is not None
    )


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if _token(value) and value not in result:
            result.append(value)
        if len(result) >= _MAX_REASONS:
            break
    return tuple(result)


__all__ = [
    "HELD_APPLY_PREFLIGHT_SCHEMA",
    "HELD_DISCARD_PREFLIGHT_SCHEMA",
    "HELD_OUTCOME_CANDIDATE_SCHEMA",
    "HELD_SOURCE_EVIDENCE_REF_SCHEMA",
    "HeldGovernancePreflightError",
    "HeldGovernancePreflightResult",
    "preflight_held_apply",
    "preflight_held_discard",
    "preflight_held_governance",
]
