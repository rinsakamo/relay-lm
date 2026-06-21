"""RelayMEM primary memory write-preflight helpers.

MEM-M3b is helper-only. It consumes M3a Primary MEM candidate metadata plus a
content-free source-lineage artifact and builds write-preflight operation
artifacts. It does not write memory, mutate RelaySOUL, invoke RelaySLP, expose a
Lab API, or change visible response delivery.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

_LINEAGE_SCHEMA_VERSION = "relaymem.primary_source_lineage.v0"
_SCHEMA_VERSION = "relaymem.primary_write_preflight_dry_run.v0"
_PROJECTION_SCHEMA_VERSION = "relaymem.primary_write_preflight_projection.v0"
_KNOWN_SOURCE_EVENT_KINDS = {"turn", "session", "communication", "manual_import"}
_KNOWN_PROMOTION_POLICIES = {
    "free_to_update",
    "review_required",
    "explicit_approval_required",
    "never_auto_promote",
}
_TARGET_CATEGORIES = {
    "recent_project_event": "primary_projects",
    "relationship_moment": "primary_relationships",
    "session_episode": "primary_sessions",
    "scene_bound_memory": "primary_scenes",
    "experience_event": "primary_scenes",
}
_EXPECTED_SAFETY_SCOPES = {
    "free_to_update": "ordinary_memory",
    "review_required": "held_for_review",
    "explicit_approval_required": "approval_required",
    "never_auto_promote": "blocked",
}
_AUTONOMOUS_PROMOTION_POLICY = "free_to_update"
_MAX_TOKEN_LENGTH = 128


def build_relaymem_primary_source_lineage(
    *,
    source_event_kind: str = "turn",
    source_event_id: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    turn_index: int | None = None,
    namespace: str = "default",
) -> dict[str, Any]:
    """Build a content-free source-lineage artifact for M3b preflight.

    IDs supplied here are runtime-private stable identifiers. The returned
    lineage stores only a deterministic fingerprint and bounded shape metadata.
    Raw source text is never accepted or returned.
    """

    event_kind, event_kind_reasons = _validated_event_kind(source_event_kind)
    safe_namespace, namespace_reasons = _required_token(
        namespace,
        reason="source_namespace_invalid",
    )
    safe_source_event_id, source_event_id_reasons = _optional_token(
        source_event_id,
        reason="source_event_id_invalid",
    )
    safe_run_id, run_id_reasons = _optional_token(
        run_id,
        reason="run_id_invalid",
    )
    safe_session_id, session_id_reasons = _optional_token(
        session_id,
        reason="session_id_invalid",
    )
    safe_turn_index, turn_index_reasons = _optional_non_negative_int(
        turn_index,
        reason="turn_index_invalid",
    )
    blocked_reasons = _dedupe(
        event_kind_reasons
        + namespace_reasons
        + source_event_id_reasons
        + run_id_reasons
        + session_id_reasons
        + turn_index_reasons
    )
    blocked_reasons.extend(
        reason
        for reason in _lineage_identity_reasons(
            source_event_id=safe_source_event_id,
            run_id=safe_run_id,
            session_id=safe_session_id,
            turn_index=safe_turn_index,
        )
        if reason not in blocked_reasons
    )

    fingerprint = ""
    if not blocked_reasons:
        fingerprint = _stable_hash(
            [
                "relaymem-primary-source-lineage-v0",
                event_kind,
                safe_namespace,
                safe_source_event_id or "",
                safe_run_id or "",
                safe_session_id or "",
                "" if safe_turn_index is None else str(safe_turn_index),
            ]
        )

    return {
        "schema_version": _LINEAGE_SCHEMA_VERSION,
        "content_free": True,
        "content_included": False,
        "raw_text_included": False,
        "source_event_kind": event_kind,
        "namespace": safe_namespace,
        "valid": not blocked_reasons,
        "lineage_fingerprint": fingerprint,
        "lineage_shape": {
            "source_event_id_present": safe_source_event_id is not None,
            "run_id_present": safe_run_id is not None,
            "session_id_present": safe_session_id is not None,
            "turn_index_present": safe_turn_index is not None,
        },
        "blocked_reasons": blocked_reasons,
    }


def build_relaymem_primary_write_preflight_dry_run(
    *,
    candidates: Sequence[Mapping[str, Any]] | None,
    source_lineage_artifact: Mapping[str, Any] | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
) -> dict[str, Any]:
    """Build Primary MEM write-preflight operations without writing memory."""

    safe_candidates = [item for item in candidates or [] if isinstance(item, Mapping)]
    parsed_lineage = _parse_source_lineage(source_lineage_artifact)
    global_blocked_reasons = _global_blocked_reasons(
        enabled=enabled,
        parsed_lineage=parsed_lineage,
    )
    operations = [
        _operation(
            candidate=candidate,
            parsed_lineage=parsed_lineage,
            global_blocked_reasons=global_blocked_reasons,
            enabled=enabled,
            dry_run_only=dry_run_only,
            apply_enabled=apply_enabled,
        )
        for candidate in safe_candidates
    ]
    projection = _projection(
        operations=operations,
        candidate_count=len(safe_candidates),
        global_blocked_reasons=global_blocked_reasons,
        parsed_lineage=parsed_lineage,
    )
    return {
        "schema_version": _SCHEMA_VERSION,
        "diagnostics_only": True,
        "helper_only": True,
        "read_only": True,
        "enabled": bool(enabled),
        "dry_run_only": bool(dry_run_only),
        "apply_enabled": bool(apply_enabled),
        "write_apply_supported": False,
        "apply_allowed": False,
        "writes_memory": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "lab_api_exposed": False,
        "source_lineage_valid": parsed_lineage["valid"],
        "candidate_count": len(safe_candidates),
        "operation_count": len(operations),
        "operations": operations,
        "blocked_reasons": global_blocked_reasons,
        "projection": projection,
    }


def _parse_source_lineage(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, Mapping):
        return _malformed_lineage(["source_lineage_missing"])
    if artifact.get("schema_version") != _LINEAGE_SCHEMA_VERSION:
        return _malformed_lineage(["source_lineage_schema_mismatch"])
    if artifact.get("valid") is not True:
        reasons = _string_list(artifact.get("blocked_reasons"))
        return _malformed_lineage(reasons or ["source_lineage_invalid"])

    fingerprint = artifact.get("lineage_fingerprint")
    if not _is_sha256_hex(fingerprint):
        return _malformed_lineage(["source_lineage_fingerprint_invalid"])

    event_kind, event_kind_reasons = _validated_event_kind(
        artifact.get("source_event_kind")
    )
    namespace, namespace_reasons = _required_token(
        artifact.get("namespace"),
        reason="source_namespace_invalid",
    )
    reasons = _dedupe(event_kind_reasons + namespace_reasons)
    if reasons:
        return _malformed_lineage(reasons)

    return {
        "valid": True,
        "lineage_fingerprint": fingerprint,
        "source_event_kind": event_kind,
        "namespace": namespace,
        "blocked_reasons": [],
    }


def _malformed_lineage(reasons: Sequence[str]) -> dict[str, Any]:
    return {
        "valid": False,
        "lineage_fingerprint": "",
        "source_event_kind": "unknown",
        "namespace": "unknown",
        "blocked_reasons": _dedupe(reasons),
    }


def _operation(
    *,
    candidate: Mapping[str, Any],
    parsed_lineage: Mapping[str, Any],
    global_blocked_reasons: Sequence[str],
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
) -> dict[str, Any]:
    candidate_id, candidate_id_reasons = _required_token(
        candidate.get("candidate_id"),
        reason="candidate_id_invalid",
    )
    memory_layer, memory_layer_reasons = _required_token(
        candidate.get("memory_layer"),
        reason="memory_layer_invalid",
    )
    memory_kind, memory_kind_reasons = _required_token(
        candidate.get("memory_kind"),
        reason="memory_kind_invalid",
    )
    promotion_policy, promotion_policy_reasons = _required_token(
        candidate.get("promotion_policy"),
        reason="promotion_policy_invalid",
    )
    safety_scope, safety_scope_reasons = _required_token(
        candidate.get("safety_scope"),
        reason="safety_scope_invalid",
    )
    candidate_source_event_kind, candidate_event_kind_reasons = _validated_event_kind(
        candidate.get("source_event_kind")
    )

    candidate_blocked_reasons = _dedupe(
        candidate_id_reasons
        + memory_layer_reasons
        + memory_kind_reasons
        + promotion_policy_reasons
        + safety_scope_reasons
        + candidate_event_kind_reasons
    )
    if memory_layer and memory_layer != "primary":
        candidate_blocked_reasons.append("unsupported_memory_layer")
    if memory_kind and memory_kind not in _TARGET_CATEGORIES:
        candidate_blocked_reasons.append("unsupported_memory_kind")
    if promotion_policy and promotion_policy not in _KNOWN_PROMOTION_POLICIES:
        candidate_blocked_reasons.append("unsupported_promotion_policy")
    expected_safety_scope = _EXPECTED_SAFETY_SCOPES.get(promotion_policy)
    if expected_safety_scope and safety_scope != expected_safety_scope:
        candidate_blocked_reasons.append("promotion_policy_safety_scope_mismatch")
    if (
        parsed_lineage.get("valid") is True
        and candidate_source_event_kind
        != str(parsed_lineage.get("source_event_kind", "unknown"))
    ):
        candidate_blocked_reasons.append("source_event_kind_mismatch")

    promotion_reasons: list[str] = []
    if (
        promotion_policy in _KNOWN_PROMOTION_POLICIES
        and promotion_policy != _AUTONOMOUS_PROMOTION_POLICY
    ):
        promotion_reasons.append(
            f"promotion_policy_blocks_autonomous_apply:{promotion_policy}"
        )

    structural_blocked_reasons = _dedupe(
        list(global_blocked_reasons) + candidate_blocked_reasons
    )
    blocked_reasons = _dedupe(structural_blocked_reasons + promotion_reasons)
    status = _status_for_reasons(
        structural_reasons=structural_blocked_reasons,
        promotion_policy=promotion_policy,
    )

    idempotency_key = ""
    if (
        parsed_lineage.get("valid") is True
        and not candidate_blocked_reasons
        and candidate_id
    ):
        idempotency_key = _stable_hash(
            [
                "relaymem-primary-write-preflight-v0",
                str(parsed_lineage.get("namespace", "unknown")),
                str(parsed_lineage.get("source_event_kind", "unknown")),
                str(parsed_lineage.get("lineage_fingerprint", "")),
                candidate_id,
                candidate_source_event_kind,
                memory_layer,
                memory_kind,
                promotion_policy,
            ]
        )

    preflight_apply_eligible = (
        status == "eligible"
        and bool(enabled)
        and bool(apply_enabled)
        and not bool(dry_run_only)
    )
    return {
        "schema_version": "relaymem.primary_write_preflight_operation.v0",
        "candidate_id": candidate_id,
        "source_event_kind": candidate_source_event_kind,
        "memory_layer": memory_layer or "unknown",
        "memory_kind": memory_kind or "unknown",
        "promotion_policy": promotion_policy or "unknown",
        "safety_scope": safety_scope or "unknown",
        "target_category": _target_category(memory_kind),
        "preflight_status": status,
        "preflight_apply_eligible": preflight_apply_eligible,
        "idempotency_key": idempotency_key,
        "idempotency_key_included_in_projection": False,
        "blocked_reasons": blocked_reasons,
        "content_included": False,
        "raw_text_included": False,
        "raw_affect_estimates_included": False,
        "writes_memory": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "applied": False,
    }


def _projection(
    *,
    operations: Sequence[Mapping[str, Any]],
    candidate_count: int,
    global_blocked_reasons: Sequence[str],
    parsed_lineage: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": _PROJECTION_SCHEMA_VERSION,
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "raw_text_included": False,
        "raw_affect_estimates_included": False,
        "lineage_fingerprint_included": False,
        "idempotency_key_included": False,
        "writes_memory": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "source_lineage_valid": parsed_lineage.get("valid") is True,
        "candidate_count": candidate_count,
        "operation_count": len(operations),
        "status_counts": _count_by_key(operations, "preflight_status"),
        "promotion_policy_counts": _count_by_key(operations, "promotion_policy"),
        "blocked_reasons": _dedupe(
            list(global_blocked_reasons)
            + [
                reason
                for operation in operations
                for reason in _string_list(operation.get("blocked_reasons"))
            ]
        ),
        "operations": [
            {
                "candidate_id": str(operation.get("candidate_id", "")),
                "source_event_kind": str(
                    operation.get("source_event_kind", "unknown")
                ),
                "memory_layer": str(operation.get("memory_layer", "unknown")),
                "memory_kind": str(operation.get("memory_kind", "unknown")),
                "promotion_policy": str(operation.get("promotion_policy", "unknown")),
                "target_category": str(operation.get("target_category", "unknown")),
                "preflight_status": str(operation.get("preflight_status", "blocked")),
                "preflight_apply_eligible": operation.get("preflight_apply_eligible") is True,
            }
            for operation in operations
        ],
    }


def _global_blocked_reasons(
    *,
    enabled: bool,
    parsed_lineage: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if not enabled:
        reasons.append("primary_write_preflight_disabled")
    if parsed_lineage.get("valid") is not True:
        reasons.extend(_string_list(parsed_lineage.get("blocked_reasons")))
    return _dedupe(reasons)


def _lineage_identity_reasons(
    *,
    source_event_id: str | None,
    run_id: str | None,
    session_id: str | None,
    turn_index: int | None,
) -> list[str]:
    if source_event_id:
        return []
    if run_id:
        return []
    if session_id and turn_index is not None:
        return []
    return ["source_lineage_missing"]


def _status_for_reasons(
    *,
    structural_reasons: Sequence[str],
    promotion_policy: str,
) -> str:
    if structural_reasons:
        return "blocked"
    if promotion_policy == "review_required":
        return "held"
    if promotion_policy == _AUTONOMOUS_PROMOTION_POLICY:
        return "eligible"
    return "blocked"


def _target_category(memory_kind: str | None) -> str:
    if not memory_kind:
        return "unknown"
    return _TARGET_CATEGORIES.get(memory_kind, "unknown")


def _stable_hash(parts: Sequence[str]) -> str:
    digest = sha256()
    for part in parts:
        digest.update(part.encode("utf-8", "surrogatepass"))
        digest.update(b"\0")
    return digest.hexdigest()


def _is_sha256_hex(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value)


def _count_by_key(items: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _string_list(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _dedupe(reasons: Sequence[str]) -> list[str]:
    output: list[str] = []
    for reason in reasons:
        text = str(reason)
        if text and text not in output:
            output.append(text)
    return output


def _validated_event_kind(value: object) -> tuple[str, list[str]]:
    if isinstance(value, str) and value in _KNOWN_SOURCE_EVENT_KINDS:
        return value, []
    return "unknown", ["source_event_kind_invalid"]


def _required_token(value: object, *, reason: str) -> tuple[str, list[str]]:
    if not isinstance(value, str):
        return "", [reason]
    token = value.strip()
    if not token or len(token) > _MAX_TOKEN_LENGTH:
        return "", [reason]
    return token, []


def _optional_token(value: object, *, reason: str) -> tuple[str | None, list[str]]:
    if value is None:
        return None, []
    token, reasons = _required_token(value, reason=reason)
    return (token or None), reasons


def _optional_non_negative_int(
    value: object,
    *,
    reason: str,
) -> tuple[int | None, list[str]]:
    if value is None:
        return None, []
    if isinstance(value, bool):
        return None, [reason]
    if isinstance(value, int) and value >= 0:
        return value, []
    return None, [reason]
