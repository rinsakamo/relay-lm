"""RelaySOUL artifact persistence dry-run contract helpers."""

from __future__ import annotations

from dataclasses import dataclass


ALLOWED_ARTIFACT_KINDS = {"patch_dry_run", "patch_compile_dry_run", "rollback_summary", "approval_summary"}


@dataclass(frozen=True)
class RelaySOULArtifactPersistenceDryRun:
    persistence_status: str
    artifact_kind: str | None
    artifact_id: str | None
    parent_artifact_id: str | None
    warning_reasons: list[str]
    blocking_reasons: list[str]
    content_free: bool
    persistence_ready: bool

    def to_log_dict(self) -> dict[str, object]:
        return {
            "persistence_status": self.persistence_status,
            "artifact_kind": self.artifact_kind,
            "artifact_id": self.artifact_id,
            "parent_artifact_id": self.parent_artifact_id,
            "warning_reasons": list(self.warning_reasons),
            "blocking_reasons": list(self.blocking_reasons),
            "content_free": self.content_free,
            "persistence_ready": self.persistence_ready,
        }


def _extract_status(kind: str, artifact: dict[str, object]) -> str | None:
    if kind == "patch_dry_run":
        status = artifact.get("dry_run_status")
    elif kind == "patch_compile_dry_run":
        status = artifact.get("compile_dry_run_status")
    elif kind == "rollback_summary":
        status = artifact.get("rollback_status")
    elif kind == "approval_summary":
        status = artifact.get("approval_status")
    else:
        return None
    return status if isinstance(status, str) else None


def build_relaysoul_artifact_persistence_dry_run(
    artifact_kind: str,
    artifact: dict[str, object] | None,
) -> RelaySOULArtifactPersistenceDryRun:
    warning_reasons: list[str] = []
    blocking_reasons: list[str] = []

    kind: str | None = artifact_kind if isinstance(artifact_kind, str) else None
    artifact_id: str | None = None
    parent_artifact_id: str | None = None

    if kind not in ALLOWED_ARTIFACT_KINDS:
        blocking_reasons.append("unsupported_artifact_kind")

    if not isinstance(artifact, dict):
        blocking_reasons.append("missing_artifact")
    else:
        if artifact.get("content_free") is not True:
            blocking_reasons.append("artifact_not_content_free")

        status = _extract_status(kind or "", artifact)
        if status == "blocked":
            warning_reasons.append("artifact_status_blocked")
        elif status == "warning":
            warning_reasons.append("artifact_status_warning")

        if kind == "patch_dry_run":
            candidate = artifact.get("candidate")
            if isinstance(candidate, dict):
                value = candidate.get("candidate_id")
                artifact_id = value if isinstance(value, str) else None


        elif kind == "patch_compile_dry_run":
            cid = artifact.get("patch_candidate_id")
            artifact_id = cid if isinstance(cid, str) and cid != "" else None
            parent_artifact_id = cid if isinstance(cid, str) and cid != "" else None
            if parent_artifact_id is None:
                warning_reasons.append("missing_parent_artifact_id")

        elif kind == "rollback_summary":
            revision = artifact.get("revision")
            if isinstance(revision, dict):
                rid = revision.get("revision_id")
                pid = revision.get("parent_revision_id")
                artifact_id = rid if isinstance(rid, str) else None
                parent_artifact_id = pid if isinstance(pid, str) and pid != "" else None
                if parent_artifact_id is None:
                    warning_reasons.append("missing_parent_artifact_id")

        elif kind == "approval_summary":
            rid = artifact.get("revision_id")
            cid = artifact.get("patch_candidate_id")
            artifact_id = rid if isinstance(rid, str) and rid != "" else None
            if artifact_id is None and isinstance(cid, str):
                artifact_id = cid
            parent_artifact_id = cid if isinstance(cid, str) and cid != "" else None
            if parent_artifact_id is None:
                warning_reasons.append("missing_parent_artifact_id")

        if artifact_id is None or artifact_id == "":
            blocking_reasons.append("missing_artifact_id")

    persistence_status = "blocked" if blocking_reasons else ("warning" if warning_reasons else "ok")

    return RelaySOULArtifactPersistenceDryRun(
        persistence_status=persistence_status,
        artifact_kind=kind,
        artifact_id=artifact_id,
        parent_artifact_id=parent_artifact_id,
        warning_reasons=warning_reasons,
        blocking_reasons=blocking_reasons,
        content_free=True,
        persistence_ready=persistence_status != "blocked",
    )
