"""Phase I-1 scoped Primary MEM recall adapter.

The existing RelayMEM M2 dry-run remains the candidate-discovery owner.  This
adapter narrows those candidates to durable, reconciled Primary MEM pages from
one character-partitioned store root and one exact namespace, then rebuilds the
existing bounded snippet handoff consumed by RelayCTX.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

from ._relaymem_primary_page_writer_common import (
    EVENT_KINDS,
    FRONT_MATTER_KEYS,
    KIND_TARGET,
    MAX_PAGE_BYTES,
    PAGE_SCHEMA,
    TARGET_DIR,
    bad_text,
    is_sha256,
    parse_page_markdown,
    stable_hash,
)
from .token_budget import estimate_text_tokens

RUNTIME_SCHEMA = "relaymem.primary_recall_runtime.v0"
PROJECTION_SCHEMA = "relaymem.primary_recall_projection.v0"
_CHARACTER_PARTITION_VERSION = "relaymem-character-store-v0"
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_MAX_CONTROL_BYTES = 65_536
_MAX_MARKERS = 256
_MAX_MARKER_LINE_BYTES = 4_096
_PRIMARY_DIRS = tuple(TARGET_DIR.values())
_INDEX_SCHEMA = "relaymem.primary_index_entry.v0"
_LOG_SCHEMA = "relaymem.primary_log_entry.v0"


def resolve_relaymem_character_store_root(
    configured_root: object,
    character_id: object,
) -> str | None:
    """Resolve one opaque character partition below the configured store root.

    The configured root remains the operator-owned RelayMEM root.  Character
    values are not used as path components and are never returned by the public
    projection.
    """

    if not isinstance(configured_root, str) or not configured_root.strip():
        return None
    if configured_root != configured_root.strip() or "\x00" in configured_root:
        return None
    if not isinstance(character_id, str) or _TOKEN_RE.fullmatch(character_id) is None:
        return None
    root = Path(configured_root)
    if _path_has_symlink_component(root):
        return None
    if root.exists() and not root.is_dir():
        return None
    character_root = root / "characters"
    if character_root.is_symlink():
        return None
    if character_root.exists() and not character_root.is_dir():
        return None
    digest = stable_hash((_CHARACTER_PARTITION_VERSION, character_id))
    return str(character_root / digest)


def apply_relaymem_primary_recall_scope(
    retrieval_artifact: Mapping[str, Any] | None,
    *,
    scoped_store_root: object,
    expected_namespace: object,
    max_snippet_chars: int,
    max_snippet_candidates: int,
    snippet_budget: int,
    chars_per_token: int = 4,
) -> dict[str, Any]:
    """Narrow an existing M2 artifact to exact scoped Primary MEM evidence.

    No candidate discovery is performed here.  Only candidates already selected
    by the existing M2 path are revalidated against page, index, log, namespace,
    path, digest, and bounded-content contracts.
    """

    artifact = deepcopy(dict(retrieval_artifact or {}))
    attempted = isinstance(retrieval_artifact, Mapping)
    reasons: list[str] = []
    selected: list[dict[str, Any]] = []

    root = _safe_root(scoped_store_root)
    namespace = _token(expected_namespace)
    if root is None:
        reasons.append("character_store_scope_unavailable")
    if namespace is None:
        reasons.append("memory_namespace_invalid")

    original_decision = artifact.get("snippet_apply_decision")
    gate_allowed = original_decision in {"eligible_but_not_applied", "dry_run_only"}
    if not gate_allowed:
        reasons.append("existing_retrieval_gate_blocked")

    raw_candidates = artifact.get("selected_mem_candidates")
    candidates = (
        raw_candidates
        if isinstance(raw_candidates, Sequence)
        and not isinstance(raw_candidates, (str, bytes, bytearray))
        else []
    )
    if not candidates:
        reasons.append("existing_retrieval_selected_no_candidates")

    max_candidates = max(0, int(max_snippet_candidates))
    max_chars = max(1, int(max_snippet_chars))
    budget = max(1, int(snippet_budget))
    cpt = max(1, int(chars_per_token))
    used_tokens = 0
    seen_identities: set[str] = set()

    if root is not None and namespace is not None and gate_allowed:
        control, control_reasons = _load_control_state(root)
        reasons.extend(control_reasons)
        if control is not None:
            # M2 remains relevance owner. I-4D applies one bounded,
            # request-scoped read-only lifecycle view before snippet construction.
            from .relaymem_primary_retrieval_eligibility import (
                load_primary_retrieval_eligibility_index,
            )

            lifecycle_index = load_primary_retrieval_eligibility_index(
                root, namespace=namespace
            )
            for raw_candidate in candidates:
                if len(selected) >= max_candidates:
                    reasons.append("primary_recall_candidate_cap_reached")
                    break
                if not isinstance(raw_candidate, Mapping):
                    reasons.append("primary_recall_candidate_shape_invalid")
                    continue
                if raw_candidate.get("memory_layer") != "primary":
                    continue
                # M2 remains relevance owner.  Availability-only candidates are
                # not promoted into an ordinary recall prompt.
                if raw_candidate.get("reason") != "keyword_match":
                    continue
                loaded, blocked = _load_validated_page(
                    root,
                    raw_candidate,
                    expected_namespace=namespace,
                    control=control,
                )
                if loaded is None:
                    reasons.extend(blocked)
                    continue
                physical_identity = loaded["idempotency_key"]
                eligibility = lifecycle_index.evaluate(
                    physical_identity,
                    candidate_namespace=loaded.get("namespace"),
                )
                if not eligibility.eligible:
                    reasons.append(eligibility.reason_id)
                    continue
                identity = eligibility.logical_memory_id
                revision = eligibility.current_revision
                if identity is None or revision is None:
                    reasons.append("excluded_unresolved_identity")
                    continue
                loaded["physical_idempotency_key"] = physical_identity
                loaded["idempotency_key"] = identity
                loaded["revision"] = revision
                if identity in seen_identities:
                    reasons.append("primary_recall_duplicate_identity_deduped")
                    continue
                summary = loaded["summary"]
                if len(summary) > max_chars:
                    reasons.append("primary_recall_summary_exceeds_bound")
                    continue
                token_estimate = estimate_text_tokens(
                    summary, chars_per_token=cpt
                ).estimated_tokens
                if used_tokens + token_estimate > budget:
                    reasons.append("primary_recall_snippet_budget_exceeded")
                    continue
                seen_identities.add(identity)
                used_tokens += token_estimate
                selected.append(
                    {
                        **loaded,
                        "evidence_id": f"evidence:{len(selected)}",
                        "snippet_text": summary,
                        "snippet_chars": len(summary),
                        "estimated_tokens": token_estimate,
                    }
                )

    if not selected and "primary_recall_no_scoped_match" not in reasons:
        reasons.append("primary_recall_no_scoped_match")

    _replace_legacy_handoff(
        artifact,
        selected,
        original_decision=str(original_decision or "blocked"),
        snippet_budget=budget,
        reasons=_reason_ids(reasons),
    )
    runtime = {
        "schema_version": RUNTIME_SCHEMA,
        "runtime_private": True,
        "content_included": bool(selected),
        "request_local": True,
        "selected_count": len(selected),
        "selected_memories": selected,
        "blocked_reason_ids": _reason_ids(reasons),
    }
    projection = {
        "schema_version": PROJECTION_SCHEMA,
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "memory_text_included": False,
        "title_or_summary_included": False,
        "character_value_included": False,
        "namespace_value_included": False,
        "runtime_identifier_values_included": False,
        "path_values_included": False,
        "digest_values_included": False,
        "lineage_values_included": False,
        "idempotency_values_included": False,
        "backend_prompt_included": False,
        "retrieval_attempted": attempted,
        "scene_type": _token(artifact.get("scene_type")) or "unknown",
        "retrieval_scope": _token(artifact.get("retrieval_scope")) or "current_context_only",
        "fallback_reason": _projection_fallback_reason(artifact),
        "persistence_block": artifact.get("persistence_block") is True,
        "ctx_block_present": artifact.get("ctx_block") is not None,
        "selected_count": len(selected),
        "selected_layer_counts": {"primary": len(selected)},
        "character_scope_resolved": root is not None,
        "namespace_scope_valid": namespace is not None,
        "scope_matched": bool(selected),
        "injection_candidate_present": bool(selected),
        "estimated_chars": sum(item["snippet_chars"] for item in selected),
        "estimated_tokens": used_tokens,
        "memory_used": False,
        "blocked_reason_ids": _reason_ids(reasons),
    }
    artifact["primary_recall_runtime"] = runtime
    artifact["primary_recall_projection"] = projection
    return artifact


def _replace_legacy_handoff(
    artifact: dict[str, Any],
    selected: Sequence[Mapping[str, Any]],
    *,
    original_decision: str,
    snippet_budget: int,
    reasons: list[str],
) -> None:
    candidates: list[dict[str, Any]] = []
    snippets: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    ctx_entries: list[dict[str, Any]] = []
    plan_entries: list[dict[str, Any]] = []
    for index, item in enumerate(selected):
        evidence_id = str(item["evidence_id"])
        candidates.append(
            {
                "path": item["path"],
                "source": "mem_page",
                "reason": "keyword_match",
                "estimated_chars": item["snippet_chars"],
                "estimated_tokens": item["estimated_tokens"],
                "memory_layer": "primary",
                "layout_profile": "target_primary_secondary",
                "applied_to_ctx": False,
            }
        )
        snippets.append(
            {
                "evidence_id": evidence_id,
                "selected_index": index,
                "path": item["path"],
                "source": "mem_page",
                "evidence_kind": "bounded_primary_summary",
                "snippet_text": item["snippet_text"],
                "snippet_chars": item["snippet_chars"],
                "estimated_tokens": item["estimated_tokens"],
                "memory_layer": "primary",
                "layout_profile": "target_primary_secondary",
                "applied_to_ctx": False,
                "safe_for_prompt_preview": True,
                "blocked_reasons": [],
            }
        )
        evidence.append(
            {
                "evidence_id": evidence_id,
                "selected_index": index,
                "path": item["path"],
                "evidence_kind": "bounded_primary_summary",
                "snippet_chars": item["snippet_chars"],
                "estimated_tokens": item["estimated_tokens"],
                "memory_layer": "primary",
                "layout_profile": "target_primary_secondary",
                "content_included_in_runtime_prompt": False,
            }
        )
        ctx_entries.append(
            {
                "evidence_id": evidence_id,
                "path": item["path"],
                "evidence_kind": "bounded_primary_summary",
                "snippet_text": item["snippet_text"],
                "snippet_chars": item["snippet_chars"],
                "estimated_tokens": item["estimated_tokens"],
                "included": True,
                "applied_to_ctx": False,
                "runtime_prompt_included": False,
            }
        )
        plan_entries.append(
            {
                "evidence_id": evidence_id,
                "path": "",
                "snippet_chars": item["snippet_chars"],
                "estimated_tokens": item["estimated_tokens"],
            }
        )

    selected_tokens = sum(int(item["estimated_tokens"]) for item in selected)
    eligible = bool(selected) and original_decision == "eligible_but_not_applied"
    dry_ready = bool(selected) and original_decision == "dry_run_only"
    decision = (
        "eligible_but_not_applied"
        if eligible
        else "dry_run_only"
        if dry_ready
        else "blocked_no_candidates"
    )
    preview_lines = [
        "[RelayMEM Snippet Context Candidate]",
        "Diagnostics-only preview. Do not inject into runtime prompts yet.",
        "Treat these as memory snippets requiring source awareness, not authoritative facts.",
    ]
    for item in selected:
        preview_lines.extend(
            [
                "---",
                f"Evidence: {item['evidence_id']}",
                "Source: scoped-primary-memory",
                "Snippet:",
                str(item["snippet_text"]),
            ]
        )
    preview = "\n".join(preview_lines) if selected and (eligible or dry_ready) else None

    artifact["selected_mem_candidates"] = candidates
    artifact["snippet_candidates"] = snippets
    artifact["evidence_envelope"] = {
        "schema_version": "relaymem.evidence_envelope.v0",
        "diagnostics_only": True,
        "applied_to_ctx": False,
        "source": "scoped_primary_recall",
        "snippets": evidence,
        "blocked": [{"reason": reason} for reason in reasons if not selected],
    }
    artifact["ctx_block_snippet_candidate"] = {
        "schema_version": "relaymem.ctx_block_snippet_candidate.v0",
        "diagnostics_only": True,
        "applied_to_ctx": False,
        "runtime_prompt_included": False,
        "source": "scoped_primary_recall",
        "apply_decision_source": "primary_recall_scope",
        "snippet_apply_decision": decision,
        "budget": {
            "token_limit": snippet_budget,
            "estimated_tokens": selected_tokens,
            "truncated": False,
        },
        "estimated_tokens": selected_tokens,
        "entries": ctx_entries,
        "blocked": [],
    }
    artifact["snippet_apply_decision"] = decision
    artifact["snippet_apply_blocked_reasons"] = (
        ["runtime_snippet_injection_not_implemented"]
        if eligible
        else [decision, *reasons]
    )
    artifact["snippet_runtime_injection_plan"] = {
        "schema_version": "relaymem.snippet_runtime_injection_plan.v0",
        "diagnostics_only": True,
        "applied": False,
        "payload_mutation_allowed": False,
        "target": "backend_messages",
        "insertion_point": "before_latest_user",
        "source": "scoped_primary_recall",
        "apply_decision_source": "primary_recall_scope",
        "snippet_apply_decision": decision,
        "preview_text": preview,
        "estimated_tokens": selected_tokens if preview else 0,
        "source_entries": plan_entries if preview else [],
        "blocked_reasons": (
            [
                "runtime_snippet_injection_not_implemented",
                "backend_payload_mutation_disabled",
                "snippet_prompt_apply_disabled",
            ]
            if preview
            else [decision, *reasons]
        ),
    }


def _load_validated_page(
    root: Path,
    candidate: Mapping[str, Any],
    *,
    expected_namespace: str,
    control: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[dict[str, Any] | None, list[str]]:
    relative = candidate.get("path")
    if not isinstance(relative, str) or not _primary_relative_path(relative):
        return None, ["primary_recall_path_invalid"]
    path = root / PurePosixPath(relative)
    if _contains_symlink(root, path) or not path.is_file():
        return None, ["primary_recall_page_unsafe_or_missing"]
    try:
        raw = path.read_bytes()
    except OSError:
        return None, ["primary_recall_page_unreadable"]
    if not raw or len(raw) > MAX_PAGE_BYTES:
        return None, ["primary_recall_page_size_invalid"]
    try:
        markdown = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, ["primary_recall_page_utf8_invalid"]
    parsed = parse_page_markdown(markdown)
    if parsed.get("valid") is not True:
        return None, ["primary_recall_page_schema_invalid"]
    metadata = parsed["metadata"]
    if set(metadata) != set(FRONT_MATTER_KEYS):
        return None, ["primary_recall_page_schema_invalid"]
    fixed = {
        "schema_version": PAGE_SCHEMA,
        "memory_layer": "primary",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "summary_origin": "trusted_in_process_summary",
        "content_role": "evidence",
    }
    if any(metadata.get(key) != value for key, value in fixed.items()):
        return None, ["primary_recall_page_policy_invalid"]
    if metadata.get("namespace") != expected_namespace:
        return None, ["primary_recall_namespace_mismatch"]
    memory_kind = metadata.get("memory_kind")
    target_category = KIND_TARGET.get(str(memory_kind))
    if target_category is None:
        return None, ["primary_recall_memory_kind_invalid"]
    if metadata.get("source_event_kind") not in EVENT_KINDS:
        return None, ["primary_recall_event_kind_invalid"]
    identity = metadata.get("idempotency_key")
    lineage = metadata.get("lineage_fingerprint")
    if not is_sha256(identity) or not is_sha256(lineage):
        return None, ["primary_recall_lineage_invalid"]
    expected_path = f"{TARGET_DIR[target_category]}/{identity}.md"
    if relative != expected_path:
        return None, ["primary_recall_path_identity_mismatch"]
    summary = metadata.get("summary")
    title = metadata.get("title")
    if (
        not isinstance(summary, str)
        or not summary
        or summary != summary.strip()
        or bad_text(summary)
        or not isinstance(title, str)
        or title != title.strip()
        or bad_text(title)
    ):
        return None, ["primary_recall_page_content_invalid"]
    expected_body = f"# Primary memory\n\n## Summary\n\n{summary}\n"
    if parsed.get("body") != expected_body:
        return None, ["primary_recall_page_body_mismatch"]

    digest = sha256(raw).hexdigest()
    index_matches = [
        entry
        for entry in control["index"]
        if entry.get("page_relative_path") == relative
        and entry.get("idempotency_key") == identity
    ]
    log_matches = [
        entry
        for entry in control["log"]
        if entry.get("page_relative_path") == relative
        and entry.get("idempotency_key") == identity
    ]
    if len(index_matches) != 1 or len(log_matches) != 1:
        return None, ["primary_recall_reconciliation_missing_or_duplicate"]
    index_entry = index_matches[0]
    log_entry = log_matches[0]
    shared = {
        "page_relative_path": relative,
        "memory_layer": "primary",
        "memory_kind": memory_kind,
        "target_category": target_category,
        "namespace": expected_namespace,
        "source_event_kind": metadata["source_event_kind"],
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "idempotency_key": identity,
        "page_digest": digest,
    }
    if any(index_entry.get(key) != value for key, value in shared.items()):
        return None, ["primary_recall_index_mismatch"]
    if any(log_entry.get(key) != value for key, value in shared.items()):
        return None, ["primary_recall_log_mismatch"]
    if log_entry.get("lineage_fingerprint") != lineage:
        return None, ["primary_recall_log_lineage_mismatch"]
    if log_entry.get("index_entry_id") != index_entry.get("entry_id"):
        return None, ["primary_recall_index_log_link_mismatch"]
    return {
        "path": relative,
        "idempotency_key": identity,
        "lineage_fingerprint": lineage,
        "page_digest": digest,
        "summary": summary,
        "title": title,
        "memory_kind": memory_kind,
        "namespace": expected_namespace,
        "source_event_kind": metadata["source_event_kind"],
    }, []


def _load_control_state(
    root: Path,
) -> tuple[dict[str, list[dict[str, Any]]] | None, list[str]]:
    index, index_reason = _read_markers(
        root, "memory/mem/index.md", "# Index", "relaymem-primary-index-entry-v0"
    )
    log, log_reason = _read_markers(
        root, "memory/mem/log.md", "# Log", "relaymem-primary-log-entry-v0"
    )
    reasons = [reason for reason in (index_reason, log_reason) if reason]
    if reasons:
        return None, reasons
    assert index is not None and log is not None
    if any(not _valid_index_entry(entry) for entry in index):
        return None, ["primary_recall_index_invalid"]
    if any(not _valid_log_entry(entry) for entry in log):
        return None, ["primary_recall_log_invalid"]
    return {"index": index, "log": log}, []


def _read_markers(
    root: Path,
    relative: str,
    header: str,
    marker: str,
) -> tuple[list[dict[str, Any]] | None, str | None]:
    path = root / PurePosixPath(relative)
    if _contains_symlink(root, path) or not path.is_file():
        return None, "primary_recall_control_file_unsafe_or_missing"
    try:
        raw = path.read_bytes()
    except OSError:
        return None, "primary_recall_control_file_unreadable"
    if len(raw) > _MAX_CONTROL_BYTES:
        return None, "primary_recall_control_file_size_exceeded"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, "primary_recall_control_file_utf8_invalid"
    lines = text.splitlines()
    if not lines or lines[0] != header:
        return None, "primary_recall_control_file_header_mismatch"
    prefix = f"<!-- {marker} "
    suffix = " -->"
    entries: list[dict[str, Any]] = []
    for line in lines[1:]:
        if line.lstrip().startswith("<!-- relaymem-primary-") and marker not in line:
            return None, "primary_recall_control_file_schema_conflict"
        if marker not in line:
            continue
        if len(line.encode("utf-8")) > _MAX_MARKER_LINE_BYTES:
            return None, "primary_recall_control_marker_too_large"
        if not line.startswith(prefix) or not line.endswith(suffix):
            return None, "primary_recall_control_marker_malformed"
        if len(entries) >= _MAX_MARKERS:
            return None, "primary_recall_control_marker_count_exceeded"
        payload = line[len(prefix) : -len(suffix)]
        try:
            value = json.loads(payload)
        except json.JSONDecodeError:
            return None, "primary_recall_control_marker_malformed"
        if not isinstance(value, dict):
            return None, "primary_recall_control_marker_malformed"
        canonical = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        if canonical != payload:
            return None, "primary_recall_control_marker_noncanonical"
        entries.append(value)
    return entries, None


def _valid_index_entry(entry: Mapping[str, Any]) -> bool:
    expected_keys = {
        "schema_version", "entry_id", "page_relative_path", "memory_layer",
        "memory_kind", "target_category", "namespace", "source_event_kind",
        "promotion_policy", "safety_scope", "idempotency_key", "page_digest",
    }
    if set(entry) != expected_keys or any(not isinstance(value, str) or not value for value in entry.values()):
        return False
    if entry.get("schema_version") != _INDEX_SCHEMA:
        return False
    if not _valid_shared_control_entry(entry):
        return False
    expected = stable_hash(
        (
            "relaymem-primary-index-entry-v0",
            str(entry["idempotency_key"]),
            str(entry["page_digest"]),
            str(entry["page_relative_path"]),
        )
    )
    return entry.get("entry_id") == expected


def _valid_log_entry(entry: Mapping[str, Any]) -> bool:
    expected_keys = {
        "schema_version", "entry_id", "index_entry_id", "operation",
        "page_relative_path", "memory_layer", "memory_kind", "target_category",
        "namespace", "source_event_kind", "promotion_policy", "safety_scope",
        "lineage_fingerprint", "idempotency_key", "page_digest",
    }
    if set(entry) != expected_keys or any(not isinstance(value, str) or not value for value in entry.values()):
        return False
    if entry.get("schema_version") != _LOG_SCHEMA or entry.get("operation") != "primary_page_published":
        return False
    if not _valid_shared_control_entry(entry) or not is_sha256(entry.get("lineage_fingerprint")):
        return False
    expected_index = stable_hash(
        (
            "relaymem-primary-index-entry-v0",
            str(entry["idempotency_key"]),
            str(entry["page_digest"]),
            str(entry["page_relative_path"]),
        )
    )
    expected_log = stable_hash(
        (
            "relaymem-primary-log-entry-v0",
            str(entry["idempotency_key"]),
            str(entry["page_digest"]),
            str(entry["page_relative_path"]),
        )
    )
    return entry.get("index_entry_id") == expected_index and entry.get("entry_id") == expected_log


def _valid_shared_control_entry(entry: Mapping[str, Any]) -> bool:
    kind = entry.get("memory_kind")
    category = entry.get("target_category")
    identity = entry.get("idempotency_key")
    digest = entry.get("page_digest")
    relative = entry.get("page_relative_path")
    if (
        entry.get("memory_layer") != "primary"
        or entry.get("promotion_policy") != "free_to_update"
        or entry.get("safety_scope") != "ordinary_memory"
        or kind not in KIND_TARGET
        or category != KIND_TARGET[kind]
        or entry.get("source_event_kind") not in EVENT_KINDS
        or _token(entry.get("namespace")) is None
        or not is_sha256(identity)
        or not is_sha256(digest)
    ):
        return False
    expected_path = f"{TARGET_DIR[str(category)]}/{identity}.md"
    return relative == expected_path and _primary_relative_path(str(relative))


def _safe_root(value: object) -> Path | None:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        return None
    path = Path(value)
    if _path_has_symlink_component(path) or not path.exists() or not path.is_dir():
        return None
    try:
        return path.resolve(strict=True)
    except OSError:
        return None


def _path_has_symlink_component(path: Path) -> bool:
    absolute = path if path.is_absolute() else Path.cwd() / path
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _contains_symlink(root: Path, target: Path) -> bool:
    try:
        parts = target.relative_to(root).parts
    except ValueError:
        return True
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            return True
    try:
        resolved = target.resolve(strict=False)
    except OSError:
        return True
    return resolved != root and root not in resolved.parents


def _primary_relative_path(value: str) -> bool:
    if not value or value.startswith("/") or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    return (
        path.as_posix() == value
        and value.endswith(".md")
        and all(part not in {"", ".", ".."} for part in path.parts)
        and any(value.startswith(f"{directory}/") for directory in _PRIMARY_DIRS)
    )


def _token(value: object) -> str | None:
    if not isinstance(value, str) or _TOKEN_RE.fullmatch(value) is None or bad_text(value):
        return None
    return value


def _projection_fallback_reason(artifact: Mapping[str, Any]) -> str | None:
    artifact_reason = _token(artifact.get("fallback_reason"))
    store_diagnostics = artifact.get("store_diagnostics")
    if isinstance(store_diagnostics, Mapping):
        store_reason = _token(store_diagnostics.get("fallback_reason"))
        if (
            store_reason == "memory_store_disabled"
            and artifact_reason == "memory_store_not_configured"
        ):
            return store_reason
    return artifact_reason


def _reason_ids(values: Sequence[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        normalized = value if re.fullmatch(r"[a-z0-9][a-z0-9_:-]{0,127}", value) else "invalid_reason_id"
        if normalized not in output:
            output.append(normalized)
        if len(output) >= 32:
            break
    return output


__all__ = [
    "PROJECTION_SCHEMA",
    "RUNTIME_SCHEMA",
    "apply_relaymem_primary_recall_scope",
    "resolve_relaymem_character_store_root",
]
