"""CW-A4 RelaySLP Character Workspace candidate/proposal planner core.

This module is side-effect free unless ``write_candidates=True`` is passed.  It
plans content-free public projections for RelaySLP-maintained Memory Wiki,
Scene Wiki, and Relationship workspace maintenance candidates from bounded
user-asserted governed source evidence.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from ._constants import REQUIRED_SOURCE_FILENAMES
from ._pathing import classify_character_workspace_path
from ._types import CharacterWorkspaceValidationResult
from ._validation import validate_character_workspace

SLP_RUN_SCHEMA_VERSION = "relaylm.character_workspace_slp_run.v0"
SLP_CANDIDATE_SCHEMA_VERSION = "relaylm.character_workspace_candidate.v0"
SLP_PROPOSAL_SCHEMA_VERSION = "relaylm.character_workspace_proposal.v0"
SLP_PROJECTION_SCHEMA_VERSION = "relaylm.character_workspace_slp_projection.v0"
SLP_GENERATED_BY = "relaylm.character_workspace_slp"

DEFAULT_MAX_SOURCE_FILES = 32
DEFAULT_MAX_CANDIDATES = 64
DEFAULT_MAX_READ_BYTES = 64 * 1024

_SOURCE_ROOTS = (
    ".relaylm/sources/conversations",
    ".relaylm/sources/corrections",
    ".relaylm/sources/imports",
)
_WRITE_PREFIXES = (
    "memory/inbox/",
    "scenes/_inbox/",
    "relationships/_inbox/",
    "proposals/memory/",
    "proposals/scene/",
    "proposals/relationship/",
)
_FORBIDDEN_WRITE_PREFIXES = (
    ".relaylm/build/",
    ".relaylm/state/",
    ".relaylm/queue/",
)
_UPPERCASE_SOURCES = frozenset({*REQUIRED_SOURCE_FILENAMES, "LORE.md"})
_SCENE_HINTS = (
    "scene",
    "scenario",
    "situation",
    "context",
    "home scene",
    "場面",
    "シーン",
    "状況",
)
_RELATIONSHIP_HINTS = (
    "relationship",
    "familiarity",
    "trust",
    "important person",
    "most_important_person",
    "public/private",
    "関係",
    "親密",
    "信頼",
    "大切な人",
)
_IMPORTANT_RELATIONSHIP_HINTS = (
    "most_important_person",
    "important_role",
    "role assignment",
    "important parameter",
    "public/private familiarity",
)
_SENSITIVE_HINTS = (
    "password",
    "secret",
    "credential",
    "diagnosis",
    "medical",
    "health",
    "religion",
    "political",
    "sexual",
    "住所",
    "パスワード",
    "秘密",
    "病気",
    "診断",
    "宗教",
    "政治",
)
_TEXT_KEYS = (
    "content",
    "text",
    "message",
    "summary_text",
    "title",
    "user_text",
    "assistant_text",
)
_ROLE_KEYS = ("role", "speaker", "source_role", "message_role")


@dataclass(frozen=True)
class WorkspaceSourceEvidence:
    relative_path: str
    stable_ref: str
    content_hash: str
    roles: tuple[str, ...]
    text_for_private_planning: str
    malformed: bool = False
    reason_ids: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SLP_PROJECTION_SCHEMA_VERSION,
            "source_ref": self.stable_ref,
            "content_hash": self.content_hash,
            "roles": self.roles,
            "reason_ids": self.reason_ids,
            "content_free": True,
        }


@dataclass(frozen=True)
class CharacterWorkspaceCandidate:
    schema_version: str
    candidate_id: str
    candidate_kind: str
    target_domain: str
    target_path: str
    source_evidence_refs: tuple[str, ...]
    risk_level: str
    approval_required: bool
    auto_apply_eligible: bool
    apply_default: str
    reason_ids: tuple[str, ...]
    content_hash: str
    created_by: str = SLP_GENERATED_BY

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "candidate_kind": self.candidate_kind,
            "target_domain": self.target_domain,
            "target_path": self.target_path,
            "source_evidence_refs": list(self.source_evidence_refs),
            "risk_level": self.risk_level,
            "approval_required": self.approval_required,
            "auto_apply_eligible": self.auto_apply_eligible,
            "apply_default": self.apply_default,
            "reason_ids": list(self.reason_ids),
            "content_hash": self.content_hash,
            "created_by": self.created_by,
        }

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "candidate_kind": self.candidate_kind,
            "target_domain": self.target_domain,
            "target_path": self.target_path,
            "source_evidence_ref_count": len(self.source_evidence_refs),
            "risk_level": self.risk_level,
            "approval_required": self.approval_required,
            "auto_apply_eligible": self.auto_apply_eligible,
            "apply_default": self.apply_default,
            "reason_ids": list(self.reason_ids),
            "content_hash": self.content_hash,
            "created_by": self.created_by,
            "content_free": True,
        }


@dataclass(frozen=True)
class CharacterWorkspaceProposal:
    schema_version: str
    proposal_id: str
    proposal_kind: str
    target_domain: str
    target_path: str
    approval_required: bool
    blocked_reason_ids: tuple[str, ...]
    public_summary: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "proposal_id": self.proposal_id,
            "proposal_kind": self.proposal_kind,
            "target_domain": self.target_domain,
            "target_path": self.target_path,
            "approval_required": self.approval_required,
            "blocked_reason_ids": list(self.blocked_reason_ids),
            "public_summary": dict(self.public_summary),
        }

    def to_public_dict(self) -> dict[str, Any]:
        return {**self.to_dict(), "content_free": True}


@dataclass(frozen=True)
class CharacterWorkspaceSLPRun:
    schema_version: str
    generated_by: str
    status: str
    is_valid: bool
    character_id: str | None
    dry_run: bool
    write_candidates: bool
    candidates: tuple[CharacterWorkspaceCandidate, ...]
    proposals: tuple[CharacterWorkspaceProposal, ...]
    written_paths: tuple[str, ...]
    reason_ids: tuple[str, ...]
    blocked_reason_ids: tuple[str, ...]
    source_evidence_count: int
    source_evidence_refs: tuple[str, ...]
    content_free: bool = True

    def to_public_dict(self) -> dict[str, Any]:
        candidate_counts = _candidate_counts(self.candidates)
        proposal_counts = _proposal_counts(self.proposals)
        return {
            "schema_version": SLP_PROJECTION_SCHEMA_VERSION,
            "generated_by": self.generated_by,
            "status": self.status,
            "is_valid": self.is_valid,
            "character_id": self.character_id,
            "dry_run": self.dry_run,
            "write_candidates": self.write_candidates,
            "candidate_count": len(self.candidates),
            "proposal_count": len(self.proposals),
            "source_evidence_count": self.source_evidence_count,
            "source_evidence_ref_count": len(self.source_evidence_refs),
            "memory_candidates_count": candidate_counts.get("memory", 0),
            "memory_inbox_additions_count": candidate_counts.get("memory_inbox_addition", 0),
            "memory_consolidation_candidates_count": candidate_counts.get("memory_page_update", 0),
            "scene_candidates_count": candidate_counts.get("scene", 0),
            "scene_inbox_additions_count": candidate_counts.get("scene_inbox_addition", 0),
            "relationship_candidates_count": candidate_counts.get("relationship", 0),
            "relationship_note_count": candidate_counts.get("relationship_note", 0),
            "sensitive_candidates_count": candidate_counts.get("sensitive", 0),
            "approval_required_count": candidate_counts.get("approval_required", 0) + proposal_counts.get("approval_required", 0),
            "auto_apply_eligible_count": candidate_counts.get("auto_apply_eligible", 0),
            "written_path_count": len(self.written_paths),
            "written_paths": self.written_paths,
            "reason_ids": self.reason_ids,
            "blocked_reason_ids": self.blocked_reason_ids,
            "candidate_summaries": tuple(candidate.to_public_dict() for candidate in self.candidates),
            "proposal_summaries": tuple(proposal.to_public_dict() for proposal in self.proposals),
            "content_free": True,
            "raw_source_body_included": False,
            "raw_memory_body_included": False,
            "raw_scene_body_included": False,
            "raw_relationship_body_included": False,
            "absolute_paths_included": False,
            "queue_payload_included": False,
            "uppercase_source_mutated": False,
            "build_artifacts_mutated": False,
            "state_mutated": False,
            "queue_mutated": False,
            "current_turn_response_effect": False,
            "worker_started": False,
        }

    def to_private_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_by": self.generated_by,
            "status": self.status,
            "is_valid": self.is_valid,
            "character_id": self.character_id,
            "dry_run": self.dry_run,
            "write_candidates": self.write_candidates,
            "candidates": tuple(candidate.to_dict() for candidate in self.candidates),
            "proposals": tuple(proposal.to_dict() for proposal in self.proposals),
            "written_paths": self.written_paths,
            "reason_ids": self.reason_ids,
            "blocked_reason_ids": self.blocked_reason_ids,
            "source_evidence_count": self.source_evidence_count,
            "source_evidence_refs": self.source_evidence_refs,
            "content_free": True,
        }


def plan_character_workspace_slp_candidates(
    root: str | Path,
    *,
    dry_run: bool = True,
    write_candidates: bool = False,
    max_source_files: int = DEFAULT_MAX_SOURCE_FILES,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    max_read_bytes: int = DEFAULT_MAX_READ_BYTES,
) -> CharacterWorkspaceSLPRun:
    """Plan CW-A4 SLP workspace candidates from governed source evidence."""

    root_path = Path(root)
    dry_run = not write_candidates
    preflight_errors = _preflight_root_errors(root_path)
    if preflight_errors:
        return _run(root_path, status="invalid_workspace", is_valid=False, dry_run=dry_run, write_candidates=write_candidates, reason_ids=preflight_errors, blocked_reason_ids=preflight_errors)

    symlink_errors = _find_symlink_escape_errors(root_path)
    if symlink_errors:
        return _run(root_path, status="path_escape_rejected", is_valid=False, dry_run=dry_run, write_candidates=write_candidates, reason_ids=symlink_errors, blocked_reason_ids=symlink_errors)

    validation = validate_character_workspace(root_path, character_id=root_path.name, public=False)
    assert isinstance(validation, CharacterWorkspaceValidationResult)
    if not validation.is_valid:
        reasons = tuple(validation.reason_ids or (validation.status.value,))
        return _run(root_path, status=validation.status.value, is_valid=False, dry_run=dry_run, write_candidates=write_candidates, reason_ids=reasons, blocked_reason_ids=reasons)

    evidence, evidence_reasons, malformed = _load_source_evidence(root_path, max_source_files=max_source_files, max_read_bytes=max_read_bytes)
    if malformed:
        reasons = _dedupe((*evidence_reasons, "malformed_source_evidence"))
        return _run(root_path, status="malformed_source_evidence", is_valid=False, dry_run=dry_run, write_candidates=write_candidates, reason_ids=reasons, blocked_reason_ids=reasons, source_evidence_count=len(evidence), source_evidence_refs=tuple(item.stable_ref for item in evidence))
    if not evidence:
        return _run(root_path, status="no_candidates", is_valid=True, dry_run=dry_run, write_candidates=write_candidates, reason_ids=_dedupe((*evidence_reasons, "source_evidence_missing")))

    candidates, proposals, candidate_reasons = _plan_candidates(evidence, max_candidates=max_candidates)
    reasons = _dedupe((*evidence_reasons, *candidate_reasons))
    status = "planned" if candidates or proposals else "no_candidates"
    written_paths: tuple[str, ...] = ()
    blocked_reason_ids: tuple[str, ...] = ()
    if write_candidates and (candidates or proposals):
        written_paths, blocked_reason_ids = _write_candidate_artifacts(root_path, candidates, proposals)
        if blocked_reason_ids:
            status = "write_blocked"
            reasons = _dedupe((*reasons, *blocked_reason_ids))

    return _run(
        root_path,
        status=status,
        is_valid=not blocked_reason_ids,
        dry_run=not write_candidates,
        write_candidates=write_candidates,
        candidates=candidates,
        proposals=proposals,
        written_paths=written_paths,
        reason_ids=reasons,
        blocked_reason_ids=blocked_reason_ids,
        source_evidence_count=len(evidence),
        source_evidence_refs=tuple(item.stable_ref for item in evidence),
    )


def build_character_workspace_slp_projection(
    root: str | Path,
    *,
    write_candidates: bool = False,
    max_source_files: int = DEFAULT_MAX_SOURCE_FILES,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    max_read_bytes: int = DEFAULT_MAX_READ_BYTES,
) -> dict[str, Any]:
    return plan_character_workspace_slp_candidates(
        root,
        write_candidates=write_candidates,
        max_source_files=max_source_files,
        max_candidates=max_candidates,
        max_read_bytes=max_read_bytes,
    ).to_public_dict()


def _run(root: Path, *, status: str, is_valid: bool, dry_run: bool, write_candidates: bool, candidates: tuple[CharacterWorkspaceCandidate, ...] = (), proposals: tuple[CharacterWorkspaceProposal, ...] = (), written_paths: tuple[str, ...] = (), reason_ids: Iterable[str] = (), blocked_reason_ids: Iterable[str] = (), source_evidence_count: int = 0, source_evidence_refs: tuple[str, ...] = ()) -> CharacterWorkspaceSLPRun:
    character_id = root.name if root.name and ".." not in root.parts else None
    return CharacterWorkspaceSLPRun(SLP_RUN_SCHEMA_VERSION, SLP_GENERATED_BY, status, is_valid, character_id, dry_run, write_candidates, candidates, proposals, written_paths, _dedupe(reason_ids), _dedupe(blocked_reason_ids), source_evidence_count, source_evidence_refs, True)


def _preflight_root_errors(root: Path) -> tuple[str, ...]:
    if ".." in root.parts:
        return ("path_traversal_rejected",)
    if not root.exists() or not root.is_dir():
        return ("workspace_root_missing_or_not_directory",)
    if root.is_symlink():
        return ("symlink_escape_rejected",)
    return ()


def _find_symlink_escape_errors(root: Path) -> tuple[str, ...]:
    try:
        root_resolved = root.resolve()
    except OSError:
        return ("workspace_root_resolve_failed",)
    for path in root.rglob("*"):
        if not path.is_symlink():
            continue
        try:
            resolved = path.resolve()
        except OSError:
            return ("symlink_escape_rejected",)
        if not _is_relative_to(resolved, root_resolved):
            return ("symlink_escape_rejected",)
    return ()


def _load_source_evidence(root: Path, *, max_source_files: int, max_read_bytes: int) -> tuple[tuple[WorkspaceSourceEvidence, ...], tuple[str, ...], bool]:
    if max_source_files < 1 or max_read_bytes < 1:
        return (), ("source_limit_invalid",), True
    paths: list[Path] = []
    reasons: list[str] = []
    root_resolved = root.resolve()
    capped = False
    for source_root in _SOURCE_ROOTS:
        directory = root / source_root
        if not directory.exists():
            continue
        if not directory.is_dir() or directory.is_symlink():
            return (), ("source_root_invalid",), True
        for path in directory.rglob("*"):
            if path.is_dir():
                continue
            if len(paths) >= max_source_files:
                capped = True
                break
            try:
                resolved = path.resolve()
            except OSError:
                return (), ("source_file_resolve_failed",), True
            if path.is_symlink() or not _is_relative_to(resolved, root_resolved):
                return (), ("symlink_escape_rejected",), True
            paths.append(path)
        if capped:
            reasons.append("source_file_limit_reached")
            break

    evidence: list[WorkspaceSourceEvidence] = []
    for path in paths:
        rel = path.relative_to(root).as_posix()
        classification = classify_character_workspace_path(rel)
        if classification.reason_ids:
            return (), tuple(classification.reason_ids), True
        raw, read_reason, read_failed = _read_bounded_bytes(path, max_read_bytes=max_read_bytes)
        if read_failed:
            return (), (read_reason or "source_file_read_failed",), True
        if read_reason:
            reasons.append(read_reason)
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return (), ("source_file_not_utf8",), True
        if any(ord(character) < 32 and character not in "\n\r\t" for character in text):
            return (), ("source_file_control_character",), True
        content_hash = _hash_text(text)
        user_text, assistant_text = _role_texts_from_source(text)
        roles = tuple(sorted(role for role, body in (("user", user_text), ("assistant", assistant_text)) if body.strip())) or ("unknown",)
        stable_ref = "src:" + _hash_parts(rel, content_hash)[:24]
        evidence.append(WorkspaceSourceEvidence(rel, stable_ref, content_hash, roles, user_text))
    return tuple(evidence), _dedupe(reasons), False


def _read_bounded_bytes(path: Path, *, max_read_bytes: int) -> tuple[bytes, str | None, bool]:
    try:
        with path.open("rb") as handle:
            raw = handle.read(max_read_bytes + 1)
    except OSError:
        return b"", "source_file_read_failed", True
    if len(raw) > max_read_bytes:
        return b"", "source_read_limit_reached", False
    return raw, None, False


def _role_texts_from_source(text: str) -> tuple[str, str]:
    parsed = _try_json(text)
    user_parts: list[str] = []
    assistant_parts: list[str] = []
    if parsed is not None:
        _collect_role_texts(parsed, user_parts, assistant_parts)
    else:
        _collect_plaintext_role_lines(text, user_parts, assistant_parts)
    return _normalise_planning_text(user_parts), _normalise_planning_text(assistant_parts)


def _try_json(text: str) -> object | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _collect_role_texts(value: object, user_parts: list[str], assistant_parts: list[str]) -> None:
    if isinstance(value, Mapping):
        role = _role_from_mapping(value)
        if role in {"user", "human"}:
            user_parts.extend(_text_values_from_mapping(value))
            return
        if role in {"assistant", "model", "ai"}:
            assistant_parts.extend(_text_values_from_mapping(value))
            return
        for item in value.values():
            _collect_role_texts(item, user_parts, assistant_parts)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _collect_role_texts(item, user_parts, assistant_parts)


def _role_from_mapping(value: Mapping[str, object]) -> str | None:
    for key in _ROLE_KEYS:
        role = value.get(key)
        if isinstance(role, str):
            return role.strip().lower()
    return None


def _text_values_from_mapping(value: Mapping[str, object]) -> tuple[str, ...]:
    parts: list[str] = []
    for key in _TEXT_KEYS:
        item = value.get(key)
        if isinstance(item, str):
            parts.append(item)
    return tuple(parts)


def _collect_plaintext_role_lines(text: str, user_parts: list[str], assistant_parts: list[str]) -> None:
    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered.startswith("user:"):
            user_parts.append(stripped.split(":", 1)[1].strip())
        elif lowered.startswith("assistant:") or lowered.startswith("model:"):
            assistant_parts.append(stripped.split(":", 1)[1].strip())


def _normalise_planning_text(parts: Iterable[str]) -> str:
    return "\n".join(part.strip() for part in parts if part and part.strip())


def _plan_candidates(evidence_items: tuple[WorkspaceSourceEvidence, ...], *, max_candidates: int) -> tuple[tuple[CharacterWorkspaceCandidate, ...], tuple[CharacterWorkspaceProposal, ...], tuple[str, ...]]:
    candidates: list[CharacterWorkspaceCandidate] = []
    proposals: list[CharacterWorkspaceProposal] = []
    reasons: list[str] = []
    for evidence in evidence_items:
        if len(candidates) >= max_candidates:
            reasons.append("candidate_limit_reached")
            break
        user_text = evidence.text_for_private_planning
        has_user = bool(user_text.strip())
        assistant_only = "assistant" in evidence.roles and not has_user
        if assistant_only:
            blocked = _candidate("memory_inbox_addition", "memory", "proposals/memory/blocked-" + evidence.content_hash[:12] + ".json", evidence, "medium", True, False, ("assistant_only_speculation", "blocked_from_user_fact_candidate"))
            candidates.append(blocked)
            reasons.append("assistant_only_speculation_blocked")
            continue
        if not has_user:
            reasons.append("source_user_assertion_evidence_missing")
            continue
        lowered = user_text.lower()
        suffix = _target_suffix(evidence, user_text)
        sensitive = _contains_any(lowered, _SENSITIVE_HINTS)
        memory_reason_ids = ["user_assertion_evidence_present"]
        if sensitive:
            memory_reason_ids.append("sensitive_memory_candidate")
        memory = _candidate("memory_inbox_addition", "memory", f"memory/inbox/memory-{suffix}.md", evidence, "high" if sensitive else "low", True, False, tuple(memory_reason_ids))
        candidates.append(memory)
        proposals.append(_proposal_for_candidate(memory, proposal_kind="append_inbox_page"))
        if len(candidates) >= max_candidates:
            reasons.append("candidate_limit_reached")
            break
        if _contains_any(lowered, _SCENE_HINTS):
            scene = _candidate("scene_inbox_addition", "scene", f"scenes/_inbox/scene-{suffix}.md", evidence, "low", True, False, ("scene_candidate_signal", "relayscn_authority_preserved"))
            candidates.append(scene)
            proposals.append(_proposal_for_candidate(scene, proposal_kind="append_inbox_page"))
        if len(candidates) >= max_candidates:
            reasons.append("candidate_limit_reached")
            break
        if _contains_any(lowered, _RELATIONSHIP_HINTS):
            important = _contains_any(lowered, _IMPORTANT_RELATIONSHIP_HINTS)
            rel = _candidate(
                "relationship_parameter_proposal" if important else "relationship_note",
                "relationship",
                f"relationships/_inbox/relationship-{suffix}.md",
                evidence,
                "medium" if important else "low",
                True,
                False,
                ("relationship_candidate_signal", "relayrel_authority_preserved", *(("important_relationship_parameter_requires_approval",) if important else ())),
            )
            candidates.append(rel)
            proposals.append(_proposal_for_candidate(rel, proposal_kind="uppercase_source_change_required" if important else "relationship_update"))
    return tuple(candidates), tuple(proposals), _dedupe(reasons)


def _target_suffix(evidence: WorkspaceSourceEvidence, user_text: str) -> str:
    return _hash_parts(_hash_text(user_text), evidence.stable_ref)[:16]


def _candidate(kind: str, domain: str, target_path: str, evidence: WorkspaceSourceEvidence, risk_level: str, approval_required: bool, auto_apply_eligible: bool, reason_ids: tuple[str, ...]) -> CharacterWorkspaceCandidate:
    content_hash = _hash_parts(kind, domain, target_path, evidence.stable_ref, _hash_text(evidence.text_for_private_planning), *reason_ids)
    return CharacterWorkspaceCandidate(SLP_CANDIDATE_SCHEMA_VERSION, "cw-a4-candidate:" + content_hash[:32], kind, domain, target_path, (evidence.stable_ref,), risk_level, approval_required, auto_apply_eligible, "dry_run_only", reason_ids, content_hash, SLP_GENERATED_BY)


def _proposal_for_candidate(candidate: CharacterWorkspaceCandidate, *, proposal_kind: str) -> CharacterWorkspaceProposal:
    proposal_hash = _hash_parts(candidate.candidate_id, proposal_kind, candidate.target_path)
    summary = {
        "content_free": True,
        "domain": candidate.target_domain,
        "risk_level": candidate.risk_level,
        "source_count": len(candidate.source_evidence_refs),
        "candidate_kind": candidate.candidate_kind,
        "candidate_id": candidate.candidate_id,
        "candidate_target_path": candidate.target_path,
        "uppercase_source_write": False,
        "runtime_prompt_injection": False,
        "queue_or_worker_authority": False,
    }
    return CharacterWorkspaceProposal(SLP_PROPOSAL_SCHEMA_VERSION, "cw-a4-proposal:" + proposal_hash[:32], proposal_kind, candidate.target_domain, _proposal_path(candidate, proposal_hash), True, tuple(reason for reason in candidate.reason_ids if reason.startswith("assistant_only")), summary)


def _proposal_path(candidate: CharacterWorkspaceCandidate, proposal_hash: str) -> str:
    domain = {"memory": "memory", "scene": "scene", "relationship": "relationship"}.get(candidate.target_domain, "memory")
    return f"proposals/{domain}/{proposal_hash[:16]}.json"


def _write_candidate_artifacts(root: Path, candidates: tuple[CharacterWorkspaceCandidate, ...], proposals: tuple[CharacterWorkspaceProposal, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    written: list[str] = []
    errors: list[str] = []

    candidate_writes = [
        (candidate.target_path, _candidate_markdown(candidate))
        for candidate in candidates
        if not _candidate_is_blocked(candidate) and candidate.target_path.endswith(".md")
    ]
    candidate_written, candidate_errors = _write_artifact_batch(root, candidate_writes)
    written.extend(candidate_written)
    errors.extend(candidate_errors)
    if errors:
        errors.append("proposal_write_skipped_after_candidate_write_failure")
        return tuple(dict.fromkeys(written)), _dedupe(errors)

    proposal_writes = [(proposal.target_path, _json_text(proposal.to_dict())) for proposal in proposals]
    proposal_written, proposal_errors = _write_artifact_batch(root, proposal_writes)
    written.extend(proposal_written)
    errors.extend(proposal_errors)
    return tuple(dict.fromkeys(written)), _dedupe(errors)


def _write_artifact_batch(root: Path, writes: Iterable[tuple[str, str]]) -> tuple[list[str], list[str]]:
    written: list[str] = []
    errors: list[str] = []
    for relative_path, text in writes:
        path_errors = _validate_write_path(relative_path)
        if path_errors:
            errors.extend(path_errors)
            continue
        target = root / relative_path
        try:
            root_resolved = root.resolve()
            parent = target.parent
            if _path_has_symlink(root, parent):
                errors.append("write_path_symlink_rejected")
                continue
            parent.mkdir(parents=True, exist_ok=True)
            parent_errors = _validate_resolved_workspace_destination(root_resolved, parent)
            if parent_errors:
                errors.extend(parent_errors)
                continue
            if target.is_symlink():
                errors.append("write_path_symlink_rejected")
                continue
            if target.exists():
                target_errors = _validate_resolved_workspace_destination(root_resolved, target)
                if target_errors:
                    errors.extend(target_errors)
                    continue
                if target.is_dir():
                    errors.append("write_path_conflict")
                    continue
                existing = target.read_text(encoding="utf-8")
                if existing == text:
                    written.append(relative_path)
                    continue
                errors.append("candidate_artifact_conflict")
                continue
            target.write_text(text, encoding="utf-8")
            written.append(relative_path)
        except OSError:
            errors.append("candidate_artifact_write_failed")
        except UnicodeDecodeError:
            errors.append("candidate_artifact_conflict_not_utf8")
    return written, errors


def _path_has_symlink(root: Path, path: Path) -> bool:
    root_resolved = root.resolve()
    current = root
    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        return True
    for part in relative_parts:
        current = current / part
        if current.is_symlink():
            return True
        try:
            if current.exists() and not _is_relative_to(current.resolve(), root_resolved):
                return True
        except OSError:
            return True
    return False


def _validate_resolved_workspace_destination(root_resolved: Path, path: Path) -> tuple[str, ...]:
    try:
        resolved = path.resolve()
    except OSError:
        return ("write_path_resolve_failed",)
    if not _is_relative_to(resolved, root_resolved):
        return ("write_path_escape_rejected",)
    relative = resolved.relative_to(root_resolved).as_posix()
    if any(relative == prefix.rstrip("/") or relative.startswith(prefix) for prefix in _FORBIDDEN_WRITE_PREFIXES):
        return ("forbidden_workspace_mutation",)
    return ()


def _candidate_is_blocked(candidate: CharacterWorkspaceCandidate) -> bool:
    return any(reason.startswith("assistant_only") or reason.startswith("blocked_") for reason in candidate.reason_ids)


def _validate_write_path(relative_path: str) -> tuple[str, ...]:
    normalized = str(PurePosixPath(relative_path)).replace("\\", "/")
    if normalized != relative_path or normalized.startswith("/") or ".." in PurePosixPath(normalized).parts:
        return ("write_path_escape_rejected",)
    if normalized in _UPPERCASE_SOURCES:
        return ("uppercase_source_write_rejected",)
    if any(normalized.startswith(prefix) for prefix in _FORBIDDEN_WRITE_PREFIXES):
        return ("forbidden_workspace_mutation",)
    if not any(normalized.startswith(prefix) for prefix in _WRITE_PREFIXES):
        return ("write_path_not_allowlisted",)
    if not (normalized.endswith(".md") or normalized.endswith(".json")):
        return ("write_path_not_allowlisted",)
    classification = classify_character_workspace_path(normalized)
    if classification.reason_ids or classification.domain not in {"memory", "scene", "relationship"}:
        return ("write_path_not_allowlisted",)
    return ()


def _candidate_markdown(candidate: CharacterWorkspaceCandidate) -> str:
    return (
        "# RelaySLP workspace candidate\n\n"
        f"schema_version:: {candidate.schema_version}\n"
        f"candidate_id:: {candidate.candidate_id}\n"
        f"candidate_kind:: {candidate.candidate_kind}\n"
        f"target_domain:: {candidate.target_domain}\n"
        f"risk_level:: {candidate.risk_level}\n"
        f"approval_required:: {str(candidate.approval_required).lower()}\n"
        f"auto_apply_eligible:: {str(candidate.auto_apply_eligible).lower()}\n"
        f"apply_default:: {candidate.apply_default}\n"
        f"content_hash:: {candidate.content_hash}\n"
        f"source_evidence_refs:: {','.join(candidate.source_evidence_refs)}\n"
        f"reason_ids:: {','.join(candidate.reason_ids)}\n\n"
        "This candidate is generated from governed source evidence for explicit review. The public projection remains content-free; review protected source evidence before applying.\n"
    )


def _candidate_counts(candidates: tuple[CharacterWorkspaceCandidate, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.target_domain] = counts.get(candidate.target_domain, 0) + 1
        counts[candidate.candidate_kind] = counts.get(candidate.candidate_kind, 0) + 1
        if candidate.risk_level == "high" or "sensitive_memory_candidate" in candidate.reason_ids:
            counts["sensitive"] = counts.get("sensitive", 0) + 1
        if candidate.approval_required:
            counts["approval_required"] = counts.get("approval_required", 0) + 1
        if candidate.auto_apply_eligible:
            counts["auto_apply_eligible"] = counts.get("auto_apply_eligible", 0) + 1
    return counts


def _proposal_counts(proposals: tuple[CharacterWorkspaceProposal, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for proposal in proposals:
        counts[proposal.target_domain] = counts.get(proposal.target_domain, 0) + 1
        if proposal.approval_required:
            counts["approval_required"] = counts.get("approval_required", 0) + 1
    return counts


def _json_text(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_parts(*parts: object) -> str:
    encoded = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _contains_any(text: str, hints: Iterable[str]) -> bool:
    return any(hint.lower() in text for hint in hints)


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
