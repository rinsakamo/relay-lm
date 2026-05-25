"""RelaySOUL patch-candidate compile dry-run contract helpers."""

from __future__ import annotations

from dataclasses import dataclass


TARGET_FILE_TO_BLOCK_ID = {
    "SOUL.md": "character_soul_anchor",
    "OUTPUT_POLICY.md": "character_output_policy",
    "RELATIONSHIP_ANCHOR.md": "relationship_anchor",
    "STABLE_MEMORY_SUMMARY.md": "stable_memory_summary",
    "SCENE_STATE.md": "scene_state",
}


@dataclass(frozen=True)
class RelaySOULPatchCompileDryRun:
    compile_dry_run_status: str
    warning_reasons: list[str]
    blocking_reasons: list[str]
    patch_candidate_id: str | None
    target_files: list[str]
    target_block_ids: list[str]
    missing_target_block_ids: list[str]
    stable_prefix_target_files: list[str]
    dynamic_target_files: list[str]
    persona_budget_warning: bool
    stable_prefix_hash_present: bool
    content_free: bool

    def to_log_dict(self) -> dict[str, object]:
        return {
            "compile_dry_run_status": self.compile_dry_run_status,
            "warning_reasons": list(self.warning_reasons),
            "blocking_reasons": list(self.blocking_reasons),
            "patch_candidate_id": self.patch_candidate_id,
            "target_files": list(self.target_files),
            "target_block_ids": list(self.target_block_ids),
            "missing_target_block_ids": list(self.missing_target_block_ids),
            "stable_prefix_target_files": list(self.stable_prefix_target_files),
            "dynamic_target_files": list(self.dynamic_target_files),
            "persona_budget_warning": self.persona_budget_warning,
            "stable_prefix_hash_present": self.stable_prefix_hash_present,
            "content_free": self.content_free,
        }


def build_relaysoul_patch_compile_dry_run(
    patch_dry_run: dict[str, object] | None,
    compiled_request_log: dict[str, object] | None,
) -> RelaySOULPatchCompileDryRun:
    warning_reasons: list[str] = []
    blocking_reasons: list[str] = []

    patch_candidate_id: str | None = None
    target_files: list[str] = []
    target_block_ids: list[str] = []
    missing_target_block_ids: list[str] = []
    stable_prefix_target_files: list[str] = []
    dynamic_target_files: list[str] = []
    persona_budget_warning = False
    stable_prefix_hash_present = False

    if not isinstance(patch_dry_run, dict):
        blocking_reasons.append("missing_patch_dry_run")
    if not isinstance(compiled_request_log, dict):
        blocking_reasons.append("missing_compiled_request_log")

    if isinstance(patch_dry_run, dict):
        status = patch_dry_run.get("dry_run_status")
        if status == "blocked":
            blocking_reasons.append("patch_dry_run_blocked")
        elif status == "warning":
            warning_reasons.append("patch_dry_run_warning")

        candidate = patch_dry_run.get("candidate")
        if isinstance(candidate, dict):
            cid = candidate.get("candidate_id")
            if isinstance(cid, str):
                patch_candidate_id = cid
            raw_targets = candidate.get("target_files")
            if isinstance(raw_targets, list):
                target_files = [x for x in raw_targets if isinstance(x, str)]

    context_block_ids: set[str] = set()
    context_block_ids_observed = False
    dynamic_block_ids: set[str] = set()
    stable_prefix_block_ids: set[str] = set()

    if isinstance(compiled_request_log, dict):
        if compiled_request_log.get("compiler_used") is not True:
            blocking_reasons.append("compiler_not_used")

        stable_prefix_hash = compiled_request_log.get("stable_prefix_hash")
        stable_prefix_hash_present = isinstance(stable_prefix_hash, str) and stable_prefix_hash != ""

        raw_stable_ids = compiled_request_log.get("stable_prefix_block_ids")
        if isinstance(raw_stable_ids, list):
            stable_prefix_block_ids = {x for x in raw_stable_ids if isinstance(x, str)}

        summary = compiled_request_log.get("context_block_summary")
        if isinstance(summary, dict):
            raw_block_ids = summary.get("block_ids")
            if isinstance(raw_block_ids, list):
                context_block_ids_observed = True
                context_block_ids = {x for x in raw_block_ids if isinstance(x, str)}
            raw_dynamic = summary.get("dynamic_block_ids")
            if isinstance(raw_dynamic, list):
                dynamic_block_ids = {x for x in raw_dynamic if isinstance(x, str)}

        budget = compiled_request_log.get("persona_source_budget_diagnostics")
        if isinstance(budget, dict) and budget.get("budget_status") == "warning":
            persona_budget_warning = True
            warning_reasons.append("persona_source_budget_warning")

    for target_file in target_files:
        block_id = TARGET_FILE_TO_BLOCK_ID.get(target_file)
        if block_id is None:
            blocking_reasons.append("unsupported_target_file")
            continue

        target_block_ids.append(block_id)

        if context_block_ids_observed and block_id not in context_block_ids:
            missing_target_block_ids.append(block_id)
            if "target_block_missing_from_compile" not in warning_reasons:
                warning_reasons.append("target_block_missing_from_compile")

        if block_id in stable_prefix_block_ids:
            stable_prefix_target_files.append(target_file)
        if block_id in dynamic_block_ids:
            dynamic_target_files.append(target_file)

    if blocking_reasons:
        compile_dry_run_status = "blocked"
    elif warning_reasons:
        compile_dry_run_status = "warning"
    else:
        compile_dry_run_status = "ok"

    return RelaySOULPatchCompileDryRun(
        compile_dry_run_status=compile_dry_run_status,
        warning_reasons=warning_reasons,
        blocking_reasons=blocking_reasons,
        patch_candidate_id=patch_candidate_id,
        target_files=target_files,
        target_block_ids=target_block_ids,
        missing_target_block_ids=missing_target_block_ids,
        stable_prefix_target_files=stable_prefix_target_files,
        dynamic_target_files=dynamic_target_files,
        persona_budget_warning=persona_budget_warning,
        stable_prefix_hash_present=stable_prefix_hash_present,
        content_free=True,
    )
