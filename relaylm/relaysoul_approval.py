"""RelaySOUL approval summary dry-run contract helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RelaySOULApprovalSummary:
    approval_status: str
    warning_reasons: list[str]
    blocking_reasons: list[str]
    patch_candidate_id: str | None
    revision_id: str | None
    mode: str | None
    target_files: list[str]
    changed_files: list[str]
    target_changed_file_mismatch: bool
    stable_prefix_changed: bool | None
    content_free: bool

    def to_log_dict(self) -> dict[str, object]:
        return {
            "approval_status": self.approval_status,
            "warning_reasons": list(self.warning_reasons),
            "blocking_reasons": list(self.blocking_reasons),
            "patch_candidate_id": self.patch_candidate_id,
            "revision_id": self.revision_id,
            "mode": self.mode,
            "target_files": list(self.target_files),
            "changed_files": list(self.changed_files),
            "target_changed_file_mismatch": self.target_changed_file_mismatch,
            "stable_prefix_changed": self.stable_prefix_changed,
            "content_free": self.content_free,
        }


def build_relaysoul_approval_summary(
    patch_dry_run: dict[str, object] | None,
    rollback_summary: dict[str, object] | None,
) -> RelaySOULApprovalSummary:
    warning_reasons: list[str] = []
    blocking_reasons: list[str] = []

    patch_candidate_id: str | None = None
    revision_id: str | None = None
    mode: str | None = None
    target_files: list[str] = []
    changed_files: list[str] = []
    target_changed_file_mismatch = False
    stable_prefix_changed: bool | None = None

    if not isinstance(patch_dry_run, dict):
        blocking_reasons.append("missing_patch_dry_run")
    if not isinstance(rollback_summary, dict):
        blocking_reasons.append("missing_rollback_summary")

    if isinstance(patch_dry_run, dict):
        if patch_dry_run.get("dry_run_status") == "blocked":
            blocking_reasons.append("patch_dry_run_blocked")
        if patch_dry_run.get("dry_run_status") == "warning":
            warning_reasons.append("patch_dry_run_warning")

        candidate = patch_dry_run.get("candidate")
        if isinstance(candidate, dict):
            c_id = candidate.get("candidate_id")
            c_mode = candidate.get("mode")
            c_targets = candidate.get("target_files")
            if isinstance(c_id, str):
                patch_candidate_id = c_id
            if isinstance(c_mode, str):
                mode = c_mode
            if isinstance(c_targets, list):
                target_files = [t for t in c_targets if isinstance(t, str)]

    revision_patch_candidate_id: str | None = None
    revision_mode: str | None = None
    if isinstance(rollback_summary, dict):
        if rollback_summary.get("rollback_status") == "blocked":
            blocking_reasons.append("rollback_summary_blocked")
        if rollback_summary.get("rollback_status") == "warning":
            warning_reasons.append("rollback_summary_warning")

        spc = rollback_summary.get("stable_prefix_changed")
        if isinstance(spc, bool):
            stable_prefix_changed = spc
            if spc:
                warning_reasons.append("stable_prefix_changed")

        revision = rollback_summary.get("revision")
        if isinstance(revision, dict):
            r_id = revision.get("revision_id")
            r_mode = revision.get("mode")
            r_changed = revision.get("changed_files")
            r_patch_id = revision.get("patch_candidate_id")
            if isinstance(r_id, str):
                revision_id = r_id
            if isinstance(r_mode, str):
                revision_mode = r_mode
            if isinstance(r_changed, list):
                changed_files = [f for f in r_changed if isinstance(f, str)]
            if isinstance(r_patch_id, str):
                revision_patch_candidate_id = r_patch_id

    if patch_candidate_id and revision_patch_candidate_id and patch_candidate_id != revision_patch_candidate_id:
        blocking_reasons.append("patch_candidate_id_mismatch")
    if mode and revision_mode and mode != revision_mode:
        blocking_reasons.append("mode_mismatch")
    if mode is None and revision_mode is not None:
        mode = revision_mode

    if target_files and changed_files and set(target_files) != set(changed_files):
        target_changed_file_mismatch = True
        blocking_reasons.append("target_changed_file_mismatch")

    if blocking_reasons:
        approval_status = "blocked"
    elif warning_reasons:
        approval_status = "warning"
    else:
        approval_status = "ok"

    return RelaySOULApprovalSummary(
        approval_status=approval_status,
        warning_reasons=warning_reasons,
        blocking_reasons=blocking_reasons,
        patch_candidate_id=patch_candidate_id,
        revision_id=revision_id,
        mode=mode,
        target_files=target_files,
        changed_files=changed_files,
        target_changed_file_mismatch=target_changed_file_mismatch,
        stable_prefix_changed=stable_prefix_changed,
        content_free=True,
    )
