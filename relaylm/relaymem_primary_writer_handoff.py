"""RelayMEM M3d Primary MEM writer-handoff preflight.

This helper consumes the exact M3c Primary MEM page-candidate artifact, revalidates
its runtime-private page payload and the configured store target, and produces a
bounded runtime-private writer handoff. It never writes files, updates indexes or
logs, invokes RelaySLP, mutates RelaySOUL, exposes a Lab API, or changes visible
response delivery.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

_RESULT_SCHEMA = "relaymem.primary_writer_handoff_preflight.v0"
_HANDOFF_SCHEMA = "relaymem.primary_writer_handoff.v0"
_PROJECTION_SCHEMA = "relaymem.primary_writer_handoff_projection.v0"
_M3C_RESULT_SCHEMA = "relaymem.primary_page_candidate_dry_run.v0"
_M3C_CANDIDATE_SCHEMA = "relaymem.primary_page_candidate.v0"
_PAGE_SCHEMA = "relaymem.primary_page.v0"

_EVENT_KINDS = {"turn", "session", "communication", "manual_import"}
_KIND_TARGET = {
    "recent_project_event": "primary_projects",
    "relationship_moment": "primary_relationships",
    "session_episode": "primary_sessions",
    "scene_bound_memory": "primary_scenes",
    "experience_event": "primary_scenes",
}
_TARGET_DIR = {
    "primary_projects": "memory/mem/primary/projects",
    "primary_relationships": "memory/mem/primary/relationships",
    "primary_sessions": "memory/mem/primary/sessions",
    "primary_scenes": "memory/mem/primary/scenes",
}
_FRONT_MATTER_KEYS = (
    "summary",
    "schema_version",
    "memory_layer",
    "memory_kind",
    "source_event_kind",
    "promotion_policy",
    "safety_scope",
    "namespace",
    "lineage_fingerprint",
    "idempotency_key",
    "summary_origin",
    "content_role",
    "title",
)
_MAX_TOKEN = 128
_MAX_TITLE = 160
_MAX_SUMMARY = 2048
_MAX_PAGE_BYTES = 8192
_FORBIDDEN_CONTENT_KEYS = {
    "raw_source_text",
    "source_text",
    "raw_text",
    "messages",
    "source_messages",
    "message_history",
    "raw_message_history",
    "raw_affect",
    "raw_affect_estimates",
    "affect_estimates",
}


def build_relaymem_primary_writer_handoff_preflight(
    *,
    page_candidate_artifact: Mapping[str, Any] | None,
    root_path: str | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
) -> dict[str, Any]:
    """Build a bounded Primary MEM writer handoff without writing memory."""

    parsed = _parse_m3c_result(page_candidate_artifact)
    reasons: list[str] = []
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
    if parsed.get("valid") is not True:
        reasons.extend(_strings(parsed.get("blocked_reasons")))

    store_state = _empty_store_state()
    handoffs: list[dict[str, Any]] = []
    if not reasons:
        candidate = parsed["candidate"]
        store_state = _inspect_store_target(
            root_path=root_path,
            target_relative_path=candidate["target_relative_path"],
            expected_page_digest=candidate["page_digest"],
            expected_page_bytes=candidate["page_bytes"],
        )
        if store_state["valid"] is not True:
            reasons.extend(store_state["blocked_reasons"])
        elif (
            apply_enabled
            and not dry_run_only
            and parsed["upstream_writer_handoff_eligible"] is not True
        ):
            reasons.append("primary_page_candidate_writer_handoff_not_eligible")
        else:
            handoffs.append(
                _build_handoff(
                    candidate=candidate,
                    store_state=store_state,
                    enabled=enabled,
                    dry_run_only=dry_run_only,
                    apply_enabled=apply_enabled,
                    upstream_writer_handoff_eligible=parsed[
                        "upstream_writer_handoff_eligible"
                    ],
                )
            )

    reasons = _dedupe(reasons)
    projection = _build_projection(
        handoffs=handoffs,
        blocked_reasons=reasons,
        store_state=store_state,
    )
    return {
        "schema_version": _RESULT_SCHEMA,
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
        "page_candidate_valid": parsed.get("valid") is True,
        "handoff_count": len(handoffs),
        "handoffs": handoffs,
        "blocked_reasons": reasons,
        "projection": projection,
    }


def _parse_m3c_result(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return _invalid("primary_page_candidate_artifact_missing")
    if value.get("schema_version") != _M3C_RESULT_SCHEMA:
        return _invalid("primary_page_candidate_artifact_schema_mismatch")

    reasons = _exact(
        value,
        {
            "diagnostics_only": True,
            "helper_only": True,
            "read_only": True,
            "runtime_private_candidates": True,
            "enabled": True,
            "write_apply_supported": False,
            "apply_allowed": False,
            "writes_memory": False,
            "mutates_soul": False,
            "invokes_slp": False,
            "lab_api_exposed": False,
        },
        "primary_page_candidate_artifact_",
    )
    if _contains_forbidden_content_key(value):
        reasons.append("primary_page_candidate_artifact_forbidden_content_field")
    upstream_dry_run_only = value.get("dry_run_only")
    upstream_apply_enabled = value.get("apply_enabled")
    if type(upstream_dry_run_only) is not bool:
        reasons.append("primary_page_candidate_artifact_dry_run_only_invalid")
    if type(upstream_apply_enabled) is not bool:
        reasons.append("primary_page_candidate_artifact_apply_enabled_invalid")
    if _strings(value.get("blocked_reasons")):
        reasons.append("primary_page_candidate_artifact_blocked")

    candidates = value.get("page_candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return _invalid(*(reasons + ["primary_page_candidates_invalid"]))
    candidate_count = value.get("page_candidate_count")
    if (
        isinstance(candidate_count, bool)
        or not isinstance(candidate_count, int)
        or candidate_count != len(candidates)
    ):
        reasons.append("primary_page_candidate_count_mismatch")
    if len(candidates) != 1 or not isinstance(candidates[0], Mapping):
        return _invalid(*(reasons + ["primary_page_candidate_cardinality_invalid"]))

    candidate = _parse_candidate(candidates[0])
    if candidate.get("valid") is not True:
        reasons.extend(candidate["blocked_reasons"])
    if reasons:
        return _invalid(*reasons)

    expected_upstream_eligible = bool(upstream_apply_enabled) and not bool(
        upstream_dry_run_only
    )
    if candidate["writer_handoff_eligible"] is not expected_upstream_eligible:
        return _invalid("primary_page_candidate_writer_handoff_eligibility_mismatch")
    return {
        "valid": True,
        "candidate": candidate,
        "upstream_writer_handoff_eligible": expected_upstream_eligible,
        "blocked_reasons": [],
    }


def _parse_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != _M3C_CANDIDATE_SCHEMA:
        return _invalid("primary_page_candidate_schema_mismatch")

    reasons = _exact(
        value,
        {
            "runtime_private": True,
            "content_included": True,
            "raw_source_text_included": False,
            "raw_message_history_included": False,
            "raw_affect_estimates_included": False,
            "memory_layer": "primary",
            "promotion_policy": "free_to_update",
            "safety_scope": "ordinary_memory",
            "summary_origin": "trusted_in_process_summary",
            "status": "ready",
            "writes_memory": False,
            "applied": False,
        },
        "primary_page_candidate_",
    )
    if _strings(value.get("blocked_reasons")):
        reasons.append("primary_page_candidate_blocked")
    writer_handoff_eligible = value.get("writer_handoff_eligible")
    if type(writer_handoff_eligible) is not bool:
        reasons.append("primary_page_candidate_writer_handoff_eligible_invalid")

    fields: dict[str, str] = {}
    for key in ("candidate_id", "namespace"):
        fields[key], field_reasons = _token(
            value.get(key), f"primary_page_candidate_{key}_invalid"
        )
        reasons.extend(field_reasons)

    source_event_kind = value.get("source_event_kind")
    if not isinstance(source_event_kind, str) or source_event_kind not in _EVENT_KINDS:
        reasons.append("primary_page_candidate_source_event_kind_invalid")
        source_event_kind = "unknown"

    memory_kind = value.get("memory_kind")
    if not isinstance(memory_kind, str) or memory_kind not in _KIND_TARGET:
        reasons.append("primary_page_candidate_memory_kind_unsupported")
        memory_kind = "unknown"
    target_category = value.get("target_category")
    if not isinstance(target_category, str) or target_category not in _TARGET_DIR:
        reasons.append("primary_page_candidate_target_category_unsupported")
        target_category = "unknown"
    expected_category = _KIND_TARGET.get(memory_kind)
    if expected_category is not None and target_category != expected_category:
        reasons.append("primary_page_candidate_memory_kind_target_category_mismatch")

    lineage_fingerprint = value.get("lineage_fingerprint")
    idempotency_key = value.get("idempotency_key")
    page_digest = value.get("page_digest")
    if not _sha(lineage_fingerprint):
        reasons.append("primary_page_candidate_lineage_fingerprint_invalid")
    if not _sha(idempotency_key):
        reasons.append("primary_page_candidate_idempotency_key_invalid")
    if not _sha(page_digest):
        reasons.append("primary_page_candidate_page_digest_invalid")

    target_relative_path = value.get("target_relative_path")
    expected_path = (
        f"{_TARGET_DIR[target_category]}/{idempotency_key}.md"
        if target_category in _TARGET_DIR and _sha(idempotency_key)
        else ""
    )
    reasons.extend(_path_reasons(target_relative_path, expected_path))

    page_markdown = value.get("page_markdown")
    page_bytes = value.get("page_bytes")
    summary_chars = value.get("summary_chars")
    if not isinstance(page_markdown, str) or not page_markdown:
        reasons.append("primary_page_candidate_page_markdown_invalid")
        page_markdown = ""
        encoded = b""
    else:
        try:
            encoded = page_markdown.encode("utf-8")
        except UnicodeEncodeError:
            encoded = b""
            reasons.append("primary_page_candidate_page_utf8_invalid")
    if len(encoded) > _MAX_PAGE_BYTES:
        reasons.append("primary_page_candidate_page_size_exceeded")
    if (
        isinstance(page_bytes, bool)
        or not isinstance(page_bytes, int)
        or page_bytes != len(encoded)
    ):
        reasons.append("primary_page_candidate_page_bytes_mismatch")
    if encoded and _sha(page_digest) and sha256(encoded).hexdigest() != page_digest:
        reasons.append("primary_page_candidate_page_digest_mismatch")
    if isinstance(summary_chars, bool) or not isinstance(summary_chars, int):
        reasons.append("primary_page_candidate_summary_chars_invalid")
        summary_chars = -1

    parsed_page = _parse_page_markdown(page_markdown)
    if parsed_page.get("valid") is not True:
        reasons.extend(parsed_page["blocked_reasons"])
    else:
        metadata = parsed_page["metadata"]
        expected_metadata = {
            "schema_version": _PAGE_SCHEMA,
            "memory_layer": "primary",
            "memory_kind": memory_kind,
            "source_event_kind": source_event_kind,
            "promotion_policy": "free_to_update",
            "safety_scope": "ordinary_memory",
            "namespace": fields.get("namespace", ""),
            "lineage_fingerprint": lineage_fingerprint,
            "idempotency_key": idempotency_key,
            "summary_origin": "trusted_in_process_summary",
            "content_role": "evidence",
        }
        for key, expected in expected_metadata.items():
            if metadata.get(key) != expected:
                reasons.append(f"primary_page_candidate_page_{key}_mismatch")
        summary = metadata.get("summary", "")
        title = metadata.get("title", "")
        if (
            not isinstance(summary, str)
            or not summary
            or summary != summary.strip()
            or len(summary) > _MAX_SUMMARY
        ):
            reasons.append("primary_page_candidate_page_summary_invalid")
        elif summary_chars != len(summary):
            reasons.append("primary_page_candidate_page_summary_chars_mismatch")
        if (
            not isinstance(title, str)
            or title != title.strip()
            or len(title) > _MAX_TITLE
        ):
            reasons.append("primary_page_candidate_page_title_invalid")
        expected_body = f"# Primary memory\n\n## Summary\n\n{summary.strip()}\n"
        if parsed_page.get("body") != expected_body:
            reasons.append("primary_page_candidate_page_body_mismatch")

    reasons = _dedupe(reasons)
    if reasons:
        return _invalid(*reasons)
    return {
        "valid": True,
        "candidate_id": fields["candidate_id"],
        "namespace": fields["namespace"],
        "source_event_kind": source_event_kind,
        "memory_layer": "primary",
        "memory_kind": memory_kind,
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "target_category": target_category,
        "target_relative_path": target_relative_path,
        "lineage_fingerprint": lineage_fingerprint,
        "idempotency_key": idempotency_key,
        "summary_chars": summary_chars,
        "page_markdown": page_markdown,
        "page_bytes": page_bytes,
        "page_digest": page_digest,
        "status": "ready",
        "writer_handoff_eligible": writer_handoff_eligible,
        "blocked_reasons": [],
    }


def _parse_page_markdown(markdown: str) -> dict[str, Any]:
    if not markdown.startswith("---\n"):
        return _invalid("primary_page_candidate_page_front_matter_missing")
    remainder = markdown[4:]
    marker = "\n---\n"
    if marker not in remainder:
        return _invalid("primary_page_candidate_page_front_matter_invalid")
    front_matter, body = remainder.split(marker, 1)
    lines = front_matter.splitlines()
    metadata: dict[str, str] = {}
    keys: list[str] = []
    for line in lines:
        key, separator, raw_value = line.partition(": ")
        if not separator or not key or key in metadata:
            return _invalid("primary_page_candidate_page_front_matter_invalid")
        try:
            parsed_value = json.loads(raw_value)
        except (json.JSONDecodeError, TypeError):
            return _invalid("primary_page_candidate_page_front_matter_invalid")
        if not isinstance(parsed_value, str) or _bad(parsed_value):
            return _invalid("primary_page_candidate_page_front_matter_invalid")
        keys.append(key)
        metadata[key] = parsed_value
    if tuple(keys) != _FRONT_MATTER_KEYS:
        return _invalid("primary_page_candidate_page_front_matter_keys_invalid")
    return {"valid": True, "metadata": metadata, "body": body, "blocked_reasons": []}


def _inspect_store_target(
    *,
    root_path: str | None,
    target_relative_path: str,
    expected_page_digest: str,
    expected_page_bytes: int,
) -> dict[str, Any]:
    state = _empty_store_state()
    if not isinstance(root_path, str):
        state["blocked_reasons"] = ["memory_store_root_not_configured"]
        return state
    safe_root = root_path.strip()
    if (
        not safe_root
        or _bad(safe_root)
        or any(char in safe_root for char in "\n\r\t")
    ):
        state["blocked_reasons"] = ["memory_store_root_invalid"]
        return state

    root = Path(safe_root)
    if root.is_symlink():
        state["blocked_reasons"] = ["memory_store_root_symlink_blocked"]
        return state
    if not root.exists() or not root.is_dir():
        state["blocked_reasons"] = ["memory_store_root_missing"]
        return state
    try:
        root_resolved = root.resolve(strict=True)
    except OSError:
        state["blocked_reasons"] = ["memory_store_root_unresolvable"]
        return state

    target = root / PurePosixPath(target_relative_path)
    parent = target.parent
    if _path_contains_symlink(root, parent):
        state["blocked_reasons"] = ["memory_store_target_symlink_blocked"]
        return state
    if not parent.exists() or not parent.is_dir():
        state["blocked_reasons"] = ["memory_store_primary_target_directory_missing"]
        return state
    try:
        parent_resolved = parent.resolve(strict=True)
    except OSError:
        state["blocked_reasons"] = ["memory_store_target_unresolvable"]
        return state
    if root_resolved != parent_resolved and root_resolved not in parent_resolved.parents:
        state["blocked_reasons"] = ["memory_store_target_outside_root"]
        return state

    state["root_present"] = True
    state["target_parent_present"] = True
    if target.is_symlink():
        state["blocked_reasons"] = ["memory_store_target_symlink_blocked"]
        return state
    if not target.exists():
        state["valid"] = True
        return state

    state["target_exists"] = True
    if not target.is_file():
        state["blocked_reasons"] = ["memory_store_target_not_file"]
        return state
    try:
        with target.open("rb") as handle:
            existing = handle.read(_MAX_PAGE_BYTES + 1)
    except OSError:
        state["blocked_reasons"] = ["memory_store_target_unreadable"]
        return state
    if len(existing) > _MAX_PAGE_BYTES:
        state["blocked_reasons"] = ["memory_store_target_size_exceeded"]
        return state
    try:
        existing.decode("utf-8")
    except UnicodeDecodeError:
        state["blocked_reasons"] = ["memory_store_target_malformed_utf8"]
        return state
    existing_digest = sha256(existing).hexdigest()
    state["target_digest_matches"] = (
        existing_digest == expected_page_digest and len(existing) == expected_page_bytes
    )
    if not state["target_digest_matches"]:
        state["blocked_reasons"] = ["memory_store_target_conflict"]
        return state
    state["valid"] = True
    state["idempotent_noop"] = True
    return state


def _build_handoff(
    *,
    candidate: Mapping[str, Any],
    store_state: Mapping[str, Any],
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
    upstream_writer_handoff_eligible: bool,
) -> dict[str, Any]:
    status = "already_applied" if store_state["idempotent_noop"] else "ready"
    writer_apply_eligible = (
        status == "ready"
        and enabled
        and apply_enabled
        and not dry_run_only
        and upstream_writer_handoff_eligible
    )
    return {
        "schema_version": _HANDOFF_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "raw_source_text_included": False,
        "raw_message_history_included": False,
        "raw_affect_estimates_included": False,
        "candidate_id": candidate["candidate_id"],
        "source_event_kind": candidate["source_event_kind"],
        "memory_layer": "primary",
        "memory_kind": candidate["memory_kind"],
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "namespace": candidate["namespace"],
        "target_category": candidate["target_category"],
        "target_relative_path": candidate["target_relative_path"],
        "lineage_fingerprint": candidate["lineage_fingerprint"],
        "idempotency_key": candidate["idempotency_key"],
        "page_markdown": candidate["page_markdown"],
        "page_bytes": candidate["page_bytes"],
        "page_digest": candidate["page_digest"],
        "preflight_status": status,
        "target_exists": store_state["target_exists"],
        "target_digest_matches": store_state["target_digest_matches"],
        "idempotent_noop": store_state["idempotent_noop"],
        "upstream_writer_handoff_eligible": upstream_writer_handoff_eligible,
        "writer_apply_eligible": writer_apply_eligible,
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
        "applied": False,
        "blocked_reasons": [],
    }


def _build_projection(
    *,
    handoffs: Sequence[Mapping[str, Any]],
    blocked_reasons: Sequence[str],
    store_state: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": _PROJECTION_SCHEMA,
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "store_root_path_included": False,
        "candidate_id_included": False,
        "namespace_included": False,
        "target_path_included": False,
        "lineage_fingerprint_included": False,
        "idempotency_key_included": False,
        "page_markdown_included": False,
        "page_digest_included": False,
        "raw_source_text_included": False,
        "raw_message_history_included": False,
        "raw_affect_estimates_included": False,
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
        "handoff_count": len(handoffs),
        "status_counts": _counts(handoffs, "preflight_status"),
        "target_category_counts": _counts(handoffs, "target_category"),
        "writer_apply_eligible_count": sum(
            1 for item in handoffs if item.get("writer_apply_eligible") is True
        ),
        "root_present": store_state.get("root_present") is True,
        "target_parent_present": store_state.get("target_parent_present") is True,
        "target_exists": store_state.get("target_exists") is True,
        "target_digest_matches": store_state.get("target_digest_matches") is True,
        "idempotent_noop": store_state.get("idempotent_noop") is True,
        "blocked_reasons": list(blocked_reasons),
        "handoffs": [
            {
                "operation_index": index,
                "source_event_kind": item["source_event_kind"],
                "memory_layer": "primary",
                "memory_kind": item["memory_kind"],
                "promotion_policy": item["promotion_policy"],
                "safety_scope": item["safety_scope"],
                "target_category": item["target_category"],
                "preflight_status": item["preflight_status"],
                "target_exists": item["target_exists"],
                "target_digest_matches": item["target_digest_matches"],
                "idempotent_noop": item["idempotent_noop"],
                "writer_apply_eligible": item["writer_apply_eligible"],
                "page_bytes": item["page_bytes"],
            }
            for index, item in enumerate(handoffs)
        ],
    }


def _path_reasons(value: object, expected_path: str) -> list[str]:
    if not isinstance(value, str) or not value:
        return ["primary_page_candidate_target_path_invalid"]
    if _bad(value) or "\\" in value or value.startswith("/"):
        return ["primary_page_candidate_target_path_invalid"]
    path = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in path.parts):
        return ["primary_page_candidate_target_path_invalid"]
    if path.as_posix() != value or value != expected_path:
        return ["primary_page_candidate_target_path_mismatch"]
    if not value.endswith(".md"):
        return ["primary_page_candidate_target_path_invalid"]
    if not any(value.startswith(f"{directory}/") for directory in _TARGET_DIR.values()):
        return ["primary_page_candidate_target_path_outside_primary_scope"]
    return []


def _path_contains_symlink(root: Path, candidate: Path) -> bool:
    current = root
    try:
        parts = candidate.relative_to(root).parts
    except ValueError:
        return True
    for part in parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _empty_store_state() -> dict[str, Any]:
    return {
        "valid": False,
        "root_present": False,
        "target_parent_present": False,
        "target_exists": False,
        "target_digest_matches": False,
        "idempotent_noop": False,
        "blocked_reasons": [],
    }


def _contains_forbidden_content_key(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key in _FORBIDDEN_CONTENT_KEYS:
                return True
            if _contains_forbidden_content_key(item):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_contains_forbidden_content_key(item) for item in value)
    return False


def _exact(
    value: Mapping[str, Any],
    expected: Mapping[str, Any],
    prefix: str,
) -> list[str]:
    reasons: list[str] = []
    for key, wanted in expected.items():
        actual = value.get(key)
        if isinstance(wanted, bool):
            matches = type(actual) is bool and actual is wanted
        else:
            matches = actual == wanted
        if not matches:
            reasons.append(f"{prefix}{key}_invalid")
    return reasons


def _token(value: object, reason: str) -> tuple[str, list[str]]:
    if not isinstance(value, str):
        return "", [reason]
    normalized = value.strip()
    if (
        value != normalized
        or not normalized
        or len(normalized) > _MAX_TOKEN
        or _bad(normalized)
        or any(char in normalized for char in "\n\r\t")
    ):
        return "", [reason]
    return normalized, []


def _bad(value: str) -> bool:
    return any(
        (ord(char) < 32 and char not in "\n\t")
        or 0xD800 <= ord(char) <= 0xDFFF
        for char in value
    )


def _sha(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _strings(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _invalid(*reasons: str) -> dict[str, Any]:
    return {"valid": False, "blocked_reasons": _dedupe(reasons)}


def _counts(items: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return counts


__all__ = ["build_relaymem_primary_writer_handoff_preflight"]
