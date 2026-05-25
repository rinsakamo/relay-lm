"""RelaySOUL persona revision metadata and rollback dry-run contract helpers."""

from __future__ import annotations

from dataclasses import dataclass


ALLOWED_MODES = {"character_creation", "calibration", "normal_chat"}
ALLOWED_CHANGED_FILES = {
    "SOUL.md",
    "OUTPUT_POLICY.md",
    "RELATIONSHIP_ANCHOR.md",
    "STABLE_MEMORY_SUMMARY.md",
    "SCENE_STATE.md",
}


@dataclass(frozen=True)
class RelaySOULPersonaRevision:
    revision_id: str
    parent_revision_id: str | None
    mode: str
    changed_files: list[str]
    feedback_ids: list[str]
    patch_candidate_id: str | None
    patch_dry_run_status: str | None
    stable_prefix_hash_before: str | None
    stable_prefix_hash_after: str | None
    compile_dry_run_status: str | None
    applied_by: str | None
    rollback_available: bool

    def to_log_dict(self) -> dict[str, object]:
        return {
            "revision_id": self.revision_id,
            "parent_revision_id": self.parent_revision_id,
            "mode": self.mode,
            "changed_files": list(self.changed_files),
            "feedback_ids": list(self.feedback_ids),
            "patch_candidate_id": self.patch_candidate_id,
            "patch_dry_run_status": self.patch_dry_run_status,
            "stable_prefix_hash_before": self.stable_prefix_hash_before,
            "stable_prefix_hash_after": self.stable_prefix_hash_after,
            "compile_dry_run_status": self.compile_dry_run_status,
            "applied_by": self.applied_by,
            "rollback_available": self.rollback_available,
        }


@dataclass(frozen=True)
class RelaySOULRollbackSummary:
    rollback_status: str
    warning_reasons: list[str]
    blocking_reasons: list[str]
    revision: dict[str, object]
    stable_prefix_changed: bool
    content_free: bool

    def to_log_dict(self) -> dict[str, object]:
        return {
            "rollback_status": self.rollback_status,
            "warning_reasons": list(self.warning_reasons),
            "blocking_reasons": list(self.blocking_reasons),
            "revision": dict(self.revision),
            "stable_prefix_changed": self.stable_prefix_changed,
            "content_free": self.content_free,
        }


def build_relaysoul_rollback_summary(revision: RelaySOULPersonaRevision) -> RelaySOULRollbackSummary:
    warning_reasons: list[str] = []
    blocking_reasons: list[str] = []

    if revision.mode not in ALLOWED_MODES:
        blocking_reasons.append("unsupported_mode")

    unsupported_files = [f for f in revision.changed_files if f not in ALLOWED_CHANGED_FILES]
    if unsupported_files:
        blocking_reasons.append("unsupported_changed_file")

    if not revision.rollback_available:
        blocking_reasons.append("rollback_unavailable")

    if revision.parent_revision_id is None:
        warning_reasons.append("missing_parent_revision")

    stable_prefix_changed = (
        revision.stable_prefix_hash_before is not None
        and revision.stable_prefix_hash_after is not None
        and revision.stable_prefix_hash_before != revision.stable_prefix_hash_after
    )
    if stable_prefix_changed:
        warning_reasons.append("stable_prefix_changed")

    if revision.patch_dry_run_status == "blocked":
        blocking_reasons.append("patch_dry_run_blocked")

    if revision.compile_dry_run_status not in {None, "ok"}:
        warning_reasons.append("compile_dry_run_not_ok")

    if blocking_reasons:
        rollback_status = "blocked"
    elif warning_reasons:
        rollback_status = "warning"
    else:
        rollback_status = "ok"

    return RelaySOULRollbackSummary(
        rollback_status=rollback_status,
        warning_reasons=warning_reasons,
        blocking_reasons=blocking_reasons,
        revision=revision.to_log_dict(),
        stable_prefix_changed=stable_prefix_changed,
        content_free=True,
    )
