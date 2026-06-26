"""Public RelayMEM M3d Primary MEM writer-handoff boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

from . import _relaymem_primary_writer_handoff_impl as _impl
from ._relaymem_primary_page_writer_common import (
    KIND_TARGET,
    TARGET_DIR,
    is_sha256,
    parse_page_markdown,
    stable_hash,
)
from .relaymem_primary_lifecycle_page import (
    HIDDEN_PAGE_BODY,
    validate_hidden_primary_metadata,
)

_M3C_RESULT_SCHEMA = "relaymem.primary_page_candidate_dry_run.v0"
_M3C_CANDIDATE_SCHEMA = "relaymem.primary_page_candidate.v0"
_SCHEMA_REJECTION = "relaymem.primary_page_candidate_dry_run.rejected.v0"
_SCHEMA_REASON = "primary_page_candidate_artifact_schema_mismatch"
_IDEMPOTENCY_REASON = "primary_page_candidate_idempotency_key_mismatch"
_EVENT_KINDS = {"turn", "session", "communication", "manual_import"}
_MEMORY_KINDS = set(KIND_TARGET)
_MAX_TOKEN = 128


def build_relaymem_primary_writer_handoff_preflight(
    *,
    page_candidate_artifact: Mapping[str, Any] | None,
    root_path: str | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
) -> dict[str, Any]:
    """Revalidate M3b idempotency before delegating to M3d."""

    artifact = page_candidate_artifact
    replace_schema_reason = _has_idempotency_mismatch(artifact)
    if replace_schema_reason and isinstance(artifact, Mapping):
        artifact = dict(artifact)
        artifact["schema_version"] = _SCHEMA_REJECTION

    result = _impl.build_relaymem_primary_writer_handoff_preflight(
        page_candidate_artifact=artifact,
        root_path=root_path,
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
    )
    if replace_schema_reason:
        _replace_reason(result, _SCHEMA_REASON, _IDEMPOTENCY_REASON)
    return result


def build_relaymem_primary_lifecycle_writer_handoff_preflight(
    *,
    page_candidate_artifact: Mapping[str, Any] | None,
    root_path: str | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
) -> dict[str, Any]:
    """Validate one strict hidden M3c candidate and build the normal M3d handoff."""

    candidate, reasons = _parse_hidden_candidate(page_candidate_artifact)
    if type(enabled) is not bool:
        reasons.append("primary_writer_handoff_enabled_invalid")
        enabled = False
    if type(dry_run_only) is not bool:
        reasons.append("primary_writer_handoff_dry_run_only_invalid")
        dry_run_only = True
    if type(apply_enabled) is not bool:
        reasons.append("primary_writer_handoff_apply_enabled_invalid")
        apply_enabled = False
    if not enabled:
        reasons.append("primary_writer_handoff_disabled")

    store_state = _impl._empty_store_state()
    handoffs: list[dict[str, Any]] = []
    if not reasons and candidate is not None:
        store_state = _impl._inspect_store_target(
            root_path=root_path,
            target_relative_path=str(candidate["target_relative_path"]),
            expected_page_digest=str(candidate["page_digest"]),
            expected_page_bytes=int(candidate["page_bytes"]),
        )
        if store_state["valid"] is not True:
            reasons.extend(store_state["blocked_reasons"])
        elif apply_enabled and not dry_run_only and candidate["writer_handoff_eligible"] is not True:
            reasons.append("primary_page_candidate_writer_handoff_not_eligible")
        else:
            handoffs.append(
                _impl._build_handoff(
                    candidate=candidate,
                    store_state=store_state,
                    enabled=enabled,
                    dry_run_only=dry_run_only,
                    apply_enabled=apply_enabled,
                    upstream_writer_handoff_eligible=bool(
                        candidate["writer_handoff_eligible"]
                    ),
                )
            )

    reasons = list(dict.fromkeys(reason for reason in reasons if reason))
    projection = _impl._build_projection(
        handoffs=handoffs,
        blocked_reasons=reasons,
        store_state=store_state,
    )
    return {
        "schema_version": "relaymem.primary_writer_handoff_preflight.v0",
        "diagnostics_only": True,
        "helper_only": True,
        "read_only": True,
        "runtime_private_handoffs": True,
        "enabled": bool(enabled),
        "dry_run_only": bool(dry_run_only),
        "apply_enabled": bool(apply_enabled),
        "write_apply_supported": False,
        "apply_allowed": False,
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "lab_api_exposed": False,
        "runtime_wired": False,
        "visible_response_changed": False,
        "store_root_configured": bool(root_path),
        "page_candidate_valid": candidate is not None and not reasons,
        "handoff_count": len(handoffs),
        "handoffs": handoffs,
        "blocked_reasons": reasons,
        "projection": projection,
    }


def _parse_hidden_candidate(
    value: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    reasons: list[str] = []
    if not isinstance(value, Mapping) or value.get("schema_version") != _M3C_RESULT_SCHEMA:
        return None, ["primary_page_candidate_artifact_schema_mismatch"]
    if value.get("lifecycle_candidate") != "hidden":
        reasons.append("primary_page_candidate_lifecycle_variant_invalid")
    pages = value.get("page_candidates")
    if (
        value.get("page_candidate_count") != 1
        or not isinstance(pages, Sequence)
        or isinstance(pages, (str, bytes))
        or len(pages) != 1
        or not isinstance(pages[0], Mapping)
    ):
        return None, [*reasons, "primary_page_candidate_cardinality_invalid"]
    page = dict(pages[0])
    if page.get("schema_version") != _M3C_CANDIDATE_SCHEMA:
        reasons.append("primary_page_candidate_schema_mismatch")
    expected_flags = {
        "runtime_private": True,
        "content_included": True,
        "raw_source_text_included": False,
        "raw_message_history_included": False,
        "raw_affect_estimates_included": False,
        "memory_layer": "primary",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "summary_origin": "lifecycle_projection",
        "status": "ready",
        "writer_handoff_eligible": True,
        "writes_memory": False,
        "applied": False,
    }
    for key, expected in expected_flags.items():
        if page.get(key) is not expected if isinstance(expected, bool) else page.get(key) != expected:
            reasons.append(f"primary_page_candidate_{key}_invalid")
    namespace = page.get("namespace")
    candidate_id = page.get("candidate_id")
    event_kind = page.get("source_event_kind")
    memory_kind = page.get("memory_kind")
    lineage = page.get("lineage_fingerprint")
    physical = page.get("idempotency_key")
    if not _token(namespace) or not _token(candidate_id):
        reasons.append("primary_page_candidate_identity_invalid")
    if event_kind not in _EVENT_KINDS or memory_kind not in _MEMORY_KINDS:
        reasons.append("primary_page_candidate_kind_invalid")
    if not is_sha256(lineage) or not is_sha256(physical):
        reasons.append("primary_page_candidate_digest_identity_invalid")
    if all(
        (
            _token(namespace),
            _token(candidate_id),
            event_kind in _EVENT_KINDS,
            memory_kind in _MEMORY_KINDS,
            is_sha256(lineage),
            is_sha256(physical),
        )
    ):
        expected_physical = stable_hash(
            (
                "relaymem-primary-write-preflight-v0",
                str(namespace),
                str(event_kind),
                str(lineage),
                str(candidate_id),
                str(event_kind),
                "primary",
                str(memory_kind),
                "free_to_update",
            )
        )
        if physical != expected_physical:
            reasons.append("primary_page_candidate_idempotency_key_mismatch")
    category = KIND_TARGET.get(str(memory_kind))
    expected_path = (
        f"{TARGET_DIR[category]}/{physical}.md"
        if category is not None and is_sha256(physical)
        else ""
    )
    if page.get("target_category") != category or page.get("target_relative_path") != expected_path:
        reasons.append("primary_page_candidate_target_path_mismatch")
    markdown = page.get("page_markdown")
    if not isinstance(markdown, str) or not markdown:
        reasons.append("primary_page_candidate_page_markdown_invalid")
        encoded = b""
    else:
        try:
            encoded = markdown.encode("utf-8")
        except UnicodeEncodeError:
            encoded = b""
            reasons.append("primary_page_candidate_page_utf8_invalid")
    if page.get("page_bytes") != len(encoded) or page.get("page_digest") != sha256(encoded).hexdigest():
        reasons.append("primary_page_candidate_page_digest_mismatch")
    parsed = parse_page_markdown(markdown if isinstance(markdown, str) else "")
    if (
        parsed.get("valid") is not True
        or parsed.get("body") != HIDDEN_PAGE_BODY
        or not validate_hidden_primary_metadata(
            parsed.get("metadata"),
            expected_namespace=str(namespace) if isinstance(namespace, str) else None,
            expected_memory_kind=str(memory_kind) if isinstance(memory_kind, str) else None,
            expected_source_event_kind=str(event_kind) if isinstance(event_kind, str) else None,
            expected_lineage_fingerprint=str(lineage) if isinstance(lineage, str) else None,
            expected_physical_id=str(physical) if isinstance(physical, str) else None,
        )
    ):
        reasons.append("primary_page_candidate_hidden_page_invalid")
    if reasons:
        return None, list(dict.fromkeys(reasons))
    return page, []


def _has_idempotency_mismatch(value: object) -> bool:
    if not isinstance(value, Mapping) or value.get("schema_version") != _M3C_RESULT_SCHEMA:
        return False
    candidates = value.get("page_candidates")
    if (
        not isinstance(candidates, Sequence)
        or isinstance(candidates, (str, bytes))
        or len(candidates) != 1
        or not isinstance(candidates[0], Mapping)
    ):
        return False
    candidate = candidates[0]
    if candidate.get("schema_version") != _M3C_CANDIDATE_SCHEMA:
        return False

    namespace = candidate.get("namespace")
    source_event_kind = candidate.get("source_event_kind")
    lineage_fingerprint = candidate.get("lineage_fingerprint")
    candidate_id = candidate.get("candidate_id")
    memory_kind = candidate.get("memory_kind")
    key = candidate.get("idempotency_key")
    if (
        not _token(namespace)
        or source_event_kind not in _EVENT_KINDS
        or not _sha(lineage_fingerprint)
        or not _token(candidate_id)
        or memory_kind not in _MEMORY_KINDS
        or not _sha(key)
        or candidate.get("memory_layer") != "primary"
        or candidate.get("promotion_policy") != "free_to_update"
    ):
        return False

    expected = _stable(
        (
            "relaymem-primary-write-preflight-v0",
            namespace,
            source_event_kind,
            lineage_fingerprint,
            candidate_id,
            source_event_kind,
            "primary",
            memory_kind,
            "free_to_update",
        )
    )
    return key != expected


def _replace_reason(result: dict[str, Any], old: str, new: str) -> None:
    result["blocked_reasons"] = [
        new if reason == old else reason for reason in result.get("blocked_reasons", [])
    ]
    projection = result.get("projection")
    if isinstance(projection, dict):
        projection["blocked_reasons"] = [
            new if reason == old else reason
            for reason in projection.get("blocked_reasons", [])
        ]


def _token(value: object) -> bool:
    return (
        isinstance(value, str)
        and value == value.strip()
        and 0 < len(value) <= _MAX_TOKEN
        and not any(char in value for char in "\n\r\t")
        and not any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value)
    )


def _sha(value: object) -> bool:
    return is_sha256(value)


def _stable(parts: Sequence[str]) -> str:
    return stable_hash(parts)


__all__ = [
    "build_relaymem_primary_lifecycle_writer_handoff_preflight",
    "build_relaymem_primary_writer_handoff_preflight",
]
