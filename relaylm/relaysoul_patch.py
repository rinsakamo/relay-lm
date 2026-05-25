"""RelaySOUL patch-candidate dry-run contract helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ALLOWED_TARGET_FILES = {
    "SOUL.md",
    "OUTPUT_POLICY.md",
    "RELATIONSHIP_ANCHOR.md",
    "STABLE_MEMORY_SUMMARY.md",
    "SCENE_STATE.md",
}
ALLOWED_MODES = {"character_creation", "calibration", "normal_chat"}
TARGET_FILE_TO_BLOCK_ID = {
    "SOUL.md": "character_soul_anchor",
    "OUTPUT_POLICY.md": "character_output_policy",
    "RELATIONSHIP_ANCHOR.md": "relationship_anchor",
    "STABLE_MEMORY_SUMMARY.md": "stable_memory_summary",
    "SCENE_STATE.md": "scene_state",
}


@dataclass(frozen=True)
class RelaySOULPatchCandidate:
    candidate_id: str
    mode: str
    target_files: list[str]
    feedback_ids: list[str]
    feedback_labels: list[str]
    freeform_notes_present: bool

    def to_log_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "mode": self.mode,
            "target_files": list(self.target_files),
            "feedback_ids": list(self.feedback_ids),
            "feedback_labels": list(self.feedback_labels),
            "freeform_notes_present": self.freeform_notes_present,
        }


@dataclass(frozen=True)
class RelaySOULPatchDryRun:
    dry_run_status: str
    warning_reasons: list[str]
    blocking_reasons: list[str]
    candidate: dict[str, object]
    runtime_feedback_summary: dict[str, object] | None
    target_budget_status: dict[str, str | None]
    stable_prefix_hash_present: bool
    content_free: bool

    def to_log_dict(self) -> dict[str, object]:
        return {
            "dry_run_status": self.dry_run_status,
            "warning_reasons": list(self.warning_reasons),
            "blocking_reasons": list(self.blocking_reasons),
            "candidate": dict(self.candidate),
            "runtime_feedback_summary": (
                dict(self.runtime_feedback_summary) if isinstance(self.runtime_feedback_summary, dict) else None
            ),
            "target_budget_status": dict(self.target_budget_status),
            "stable_prefix_hash_present": self.stable_prefix_hash_present,
            "content_free": self.content_free,
        }


def build_relaysoul_patch_candidate_dry_run(
    candidate: RelaySOULPatchCandidate,
    runtime_feedback_summary: dict[str, object] | None,
    persona_source_budget_diagnostics: dict[str, object] | None,
) -> RelaySOULPatchDryRun:
    warning_reasons: list[str] = []
    blocking_reasons: list[str] = []

    unsupported_targets = [target for target in candidate.target_files if target not in ALLOWED_TARGET_FILES]
    if unsupported_targets:
        blocking_reasons.append("unsupported_target_file")
    if candidate.mode not in ALLOWED_MODES:
        blocking_reasons.append("unsupported_mode")
    if candidate.mode == "normal_chat" and "SOUL.md" in candidate.target_files:
        blocking_reasons.append("soul_patch_not_allowed_in_normal_chat")

    if isinstance(runtime_feedback_summary, dict) and runtime_feedback_summary.get("feedback_status") == "warning":
        warning_reasons.append("runtime_feedback_warning")

    source_ratios = {}
    if isinstance(persona_source_budget_diagnostics, dict):
        if persona_source_budget_diagnostics.get("budget_status") == "warning":
            warning_reasons.append("persona_source_budget_warning")
        raw = persona_source_budget_diagnostics.get("source_budget_ratios")
        if isinstance(raw, dict):
            source_ratios = raw

    target_budget_status: dict[str, str | None] = {}
    for target_file in candidate.target_files:
        block_id = TARGET_FILE_TO_BLOCK_ID.get(target_file)
        if block_id is None:
            target_budget_status[target_file] = None
            continue
        ratio = source_ratios.get(block_id)
        if isinstance(ratio, (int, float)) and ratio > 1.0:
            target_budget_status[target_file] = "over_budget"
        else:
            target_budget_status[target_file] = None

    if blocking_reasons:
        dry_run_status = "blocked"
    elif warning_reasons:
        dry_run_status = "warning"
    else:
        dry_run_status = "ok"

    return RelaySOULPatchDryRun(
        dry_run_status=dry_run_status,
        warning_reasons=warning_reasons,
        blocking_reasons=blocking_reasons,
        candidate=candidate.to_log_dict(),
        runtime_feedback_summary=runtime_feedback_summary if isinstance(runtime_feedback_summary, dict) else None,
        target_budget_status=target_budget_status,
        stable_prefix_hash_present=bool(
            isinstance(runtime_feedback_summary, dict)
            and runtime_feedback_summary.get("stable_prefix_hash_present") is True
        ),
        content_free=True,
    )
