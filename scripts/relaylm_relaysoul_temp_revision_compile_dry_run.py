#!/usr/bin/env python3
"""RelaySOUL temporary persona revision compile dry-run.

Safety posture:
- no model API calls
- no mutation of source profile files
- no runtime behavior changes
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.compiler import (
    build_persona_source_budget_diagnostics,
    build_stable_prefix_hash_diagnostics,
    summarize_context_blocks,
)
from relaylm.diagnostics import RequestDiagnostics, build_relaysoul_runtime_feedback_summary
from relaylm.profile import ProfileFiles, build_profile_blocks

SCHEMA_VERSION = "mvp-soul-0"
ARTIFACT_TYPE = "relaysoul_temp_revision_compile_dry_run"

ALLOWED_TARGET_FILES = {
    "SOUL.md",
    "OUTPUT_POLICY.md",
    "RELATIONSHIP_ANCHOR.md",
    "STABLE_MEMORY_SUMMARY.md",
    "SCENE_STATE.md",
}
ALLOWED_RISK_LEVELS = {"low", "medium", "high"}
REQUIRED_FIELDS = [
    "target_file",
    "target_block",
    "operation",
    "reason",
    "patch_text",
    "source_feedback_ids",
    "risk_level",
    "requires_user_approval",
    "budget_effect",
    "stable_prefix_change_expected",
]


class DryRunShapeError(ValueError):
    """Raised when dry-run inputs are malformed."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _extract_candidates(payload: Any, source_path: str | Path) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise DryRunShapeError(
            f"Patch candidate JSON root must be an object: {source_path}"
        )

    items = payload.get("items")
    if not isinstance(items, list):
        raise DryRunShapeError(
            f"Patch candidate JSON must include list field 'items': {source_path}"
        )
    if not items:
        raise DryRunShapeError(
            f"Patch candidate JSON field 'items' must not be empty: {source_path}"
        )

    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise DryRunShapeError(
                f"Patch candidate at index {idx} must be an object: {source_path}"
            )
        normalized.append(item)
    return normalized


def _require_non_empty_string(item: dict[str, Any], field: str, idx: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise DryRunShapeError(
            f"Patch candidate at index {idx} must provide non-empty string field '{field}'"
        )
    return value


def _validate_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        missing = [field for field in REQUIRED_FIELDS if field not in item]
        if missing:
            raise DryRunShapeError(
                f"Patch candidate at index {idx} is missing required fields: {', '.join(missing)}"
            )

        target_file = _require_non_empty_string(item, "target_file", idx)
        if target_file not in ALLOWED_TARGET_FILES:
            raise DryRunShapeError(
                f"Patch candidate at index {idx} has invalid target_file: {target_file}"
            )

        risk_level = _require_non_empty_string(item, "risk_level", idx)
        if risk_level not in ALLOWED_RISK_LEVELS:
            raise DryRunShapeError(
                f"Patch candidate at index {idx} has invalid risk_level: {risk_level}"
            )

        requires_user_approval = item.get("requires_user_approval")
        if not isinstance(requires_user_approval, bool):
            raise DryRunShapeError(
                f"Patch candidate at index {idx} requires_user_approval must be bool"
            )

        stable_prefix_change_expected = item.get("stable_prefix_change_expected")
        if not isinstance(stable_prefix_change_expected, bool):
            raise DryRunShapeError(
                f"Patch candidate at index {idx} stable_prefix_change_expected must be bool"
            )

        source_feedback_ids = item.get("source_feedback_ids")
        if (
            not isinstance(source_feedback_ids, list)
            or not source_feedback_ids
            or any(not isinstance(fid, str) or not fid.strip() for fid in source_feedback_ids)
        ):
            raise DryRunShapeError(
                f"Patch candidate at index {idx} must provide non-empty string list source_feedback_ids"
            )

        if target_file == "SOUL.md":
            if risk_level != "high":
                raise DryRunShapeError(
                    f"Patch candidate at index {idx} targeting SOUL.md must have risk_level='high'"
                )
            if requires_user_approval is not True:
                raise DryRunShapeError(
                    "Patch candidate targeting SOUL.md must set requires_user_approval=true"
                )

        normalized.append(
            {
                "patch_id": item.get("patch_id") if isinstance(item.get("patch_id"), str) else None,
                "target_file": target_file,
                "target_block": _require_non_empty_string(item, "target_block", idx),
                "operation": _require_non_empty_string(item, "operation", idx),
                "reason": _require_non_empty_string(item, "reason", idx),
                "patch_text": _require_non_empty_string(item, "patch_text", idx),
                "source_feedback_ids": source_feedback_ids,
                "risk_level": risk_level,
                "requires_user_approval": requires_user_approval,
                "budget_effect": _require_non_empty_string(item, "budget_effect", idx),
                "stable_prefix_change_expected": stable_prefix_change_expected,
            }
        )
    return normalized


def _detect_optional_file(profile_dir: Path, candidates: list[str]) -> Path | None:
    for rel in candidates:
        path = profile_dir / rel
        if path.exists():
            return path
    return None


def _build_profile_files_for_dir(profile_dir: Path) -> ProfileFiles:
    common_runtime_policy = profile_dir / "common_runtime_policy.md"
    soul = profile_dir / "SOUL.md"
    output_policy = _detect_optional_file(profile_dir, ["OUTPUT_POLICY.md", "style.md"])

    if output_policy is None:
        raise DryRunShapeError("Missing output policy file: expected OUTPUT_POLICY.md or style.md")
    if not common_runtime_policy.exists():
        raise DryRunShapeError("Missing common_runtime_policy.md in profile dir")
    if not soul.exists():
        raise DryRunShapeError("Missing SOUL.md in profile dir")

    relationship_anchor = _detect_optional_file(
        profile_dir,
        ["RELATIONSHIP_ANCHOR.md", "relationship_anchor.md"],
    )
    stable_memory_summary = _detect_optional_file(
        profile_dir,
        ["STABLE_MEMORY_SUMMARY.md", "stable_memory_summary.md"],
    )
    scene_state = _detect_optional_file(profile_dir, ["SCENE_STATE.md"])

    return ProfileFiles(
        common_runtime_policy=common_runtime_policy,
        soul=soul,
        output_policy=output_policy,
        relationship_anchor=relationship_anchor,
        stable_memory_summary=stable_memory_summary,
        scene_state=scene_state,
    )


def _resolve_target_file(profile_dir: Path, target_file: str) -> Path:
    if target_file == "SOUL.md":
        return profile_dir / "SOUL.md"
    if target_file == "OUTPUT_POLICY.md":
        output_policy = profile_dir / "OUTPUT_POLICY.md"
        return output_policy if output_policy.exists() else profile_dir / "style.md"
    if target_file == "RELATIONSHIP_ANCHOR.md":
        existing = _detect_optional_file(profile_dir, ["RELATIONSHIP_ANCHOR.md", "relationship_anchor.md"])
        return existing if existing is not None else profile_dir / "RELATIONSHIP_ANCHOR.md"
    if target_file == "STABLE_MEMORY_SUMMARY.md":
        existing = _detect_optional_file(profile_dir, ["STABLE_MEMORY_SUMMARY.md", "stable_memory_summary.md"])
        return existing if existing is not None else profile_dir / "STABLE_MEMORY_SUMMARY.md"
    if target_file == "SCENE_STATE.md":
        return profile_dir / "SCENE_STATE.md"
    raise DryRunShapeError(f"Unsupported target_file mapping: {target_file}")


def _append_candidate_patch(target_path: Path, candidate: dict[str, Any]) -> None:
    patch_id = candidate.get("patch_id") or "unknown"
    block = (
        f"\n\n<!-- RELAYSOUL_DRY_RUN_PATCH_START candidate_id={patch_id} -->\n"
        f"target_file: {candidate['target_file']}\n"
        f"target_block: {candidate['target_block']}\n"
        f"operation: {candidate['operation']}\n"
        f"reason: {candidate['reason']}\n"
        f"patch_text:\n{candidate['patch_text']}\n"
        "<!-- RELAYSOUL_DRY_RUN_PATCH_END -->\n"
    )
    existing = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(existing.rstrip() + block, encoding="utf-8")


def _copy_profile_to_temp(profile_dir: Path, temp_dir: Path) -> None:
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    shutil.copytree(profile_dir, temp_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-dir", required=True)
    parser.add_argument("--patch-candidates", required=True)
    parser.add_argument("--temp-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    profile_dir = Path(args.profile_dir)
    temp_dir = Path(args.temp_dir)
    output_path = Path(args.output)

    payload = _read_json(args.patch_candidates)
    candidates = _validate_candidates(_extract_candidates(payload, args.patch_candidates))

    warnings: list[str] = []
    _copy_profile_to_temp(profile_dir, temp_dir)

    source_profile_files = _build_profile_files_for_dir(profile_dir)
    source_blocks = build_profile_blocks(source_profile_files)
    stable_prefix_hash_before, _ = build_stable_prefix_hash_diagnostics(source_blocks)

    changed_files: list[str] = []
    for candidate in candidates:
        target_path = _resolve_target_file(temp_dir, candidate["target_file"])
        _append_candidate_patch(target_path, candidate)
        canonical = candidate["target_file"]
        if canonical not in changed_files:
            changed_files.append(canonical)

    temp_profile_files = _build_profile_files_for_dir(temp_dir)
    temp_blocks = build_profile_blocks(temp_profile_files)
    stable_prefix_hash_after, _ = build_stable_prefix_hash_diagnostics(temp_blocks)

    context_block_summary = summarize_context_blocks(temp_blocks)
    persona_source_budget_diagnostics = build_persona_source_budget_diagnostics(temp_blocks)
    relaysoul_runtime_feedback_summary = build_relaysoul_runtime_feedback_summary(
        RequestDiagnostics(
            request_id="relaysoul-temp-revision-compile-dry-run",
            compiler_used=True,
            context_block_summary=context_block_summary,
            persona_source_budget_diagnostics=persona_source_budget_diagnostics,
            stable_prefix_hash=stable_prefix_hash_after,
        )
    )

    high_risk_candidate_count = sum(1 for item in candidates if item["risk_level"] == "high")
    soul_patch_candidate_present = any(item["target_file"] == "SOUL.md" for item in candidates)
    if soul_patch_candidate_present:
        warnings.append("soul_patch_candidate_present")
    if any(item["stable_prefix_change_expected"] for item in candidates):
        warnings.append("stable_prefix_change_expected_present")

    stable_prefix_changed = None
    if stable_prefix_hash_before is not None and stable_prefix_hash_after is not None:
        stable_prefix_changed = stable_prefix_hash_before != stable_prefix_hash_after

    revision_preview = {
        "mode": "calibration",
        "changed_files": changed_files,
        "candidate_count": len(candidates),
        "approval_required": any(item["requires_user_approval"] for item in candidates),
        "high_risk_candidate_count": high_risk_candidate_count,
    }

    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "inputs": {
            "profile_dir": str(profile_dir),
            "patch_candidates": args.patch_candidates,
        },
        "temp_dir": str(temp_dir),
        "changed_files": changed_files,
        "candidate_count": len(candidates),
        "high_risk_candidate_count": high_risk_candidate_count,
        "soul_patch_candidate_present": soul_patch_candidate_present,
        "revision_preview": revision_preview,
        "compile_dry_run_status": "ok",
        "stable_prefix_hash_before": stable_prefix_hash_before,
        "stable_prefix_hash_after": stable_prefix_hash_after,
        "stable_prefix_changed": stable_prefix_changed,
        "persona_source_budget_diagnostics": persona_source_budget_diagnostics,
        "context_block_summary": context_block_summary,
        "relaysoul_runtime_feedback_summary": relaysoul_runtime_feedback_summary,
        "warnings": warnings,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
