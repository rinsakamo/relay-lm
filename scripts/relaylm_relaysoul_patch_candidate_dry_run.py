#!/usr/bin/env python3
"""Parse RelaySOUL model-response patch candidates into a normalized dry-run artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_MODEL_RESPONSE_PATH = "examples/relaysoul/model_response_patch_candidates.json"
DEFAULT_SCHEMA_VERSION = "mvp-soul-0"

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


class PatchCandidateShapeError(ValueError):
    """Raised when model response patch candidate shape is invalid."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _extract_candidates(payload: Any, source_path: str | Path) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise PatchCandidateShapeError(
            f"Model response JSON root must be an object: {source_path}"
        )

    for key in ("items", "patch_candidates", "candidates"):
        if key in payload:
            candidates = payload[key]
            if not isinstance(candidates, list):
                raise PatchCandidateShapeError(
                    f"Model response field '{key}' must be a list: {source_path}"
                )
            if not candidates:
                raise PatchCandidateShapeError(
                    f"Model response field '{key}' must not be empty: {source_path}"
                )
            normalized: list[dict[str, Any]] = []
            for idx, candidate in enumerate(candidates):
                if not isinstance(candidate, dict):
                    raise PatchCandidateShapeError(
                        f"Patch candidate at index {idx} must be an object: {source_path}"
                    )
                normalized.append(candidate)
            return normalized

    raise PatchCandidateShapeError(
        "Model response must include one of list fields: items, patch_candidates, candidates"
    )


def _validate_feedback_refs_if_requested(
    *,
    feedback_path: str | None,
    normalized_items: list[dict[str, Any]],
) -> list[str]:
    if not feedback_path:
        return []

    feedback_payload = _read_json(feedback_path)
    if not isinstance(feedback_payload, dict):
        raise PatchCandidateShapeError(
            f"Feedback JSON root must be an object: {feedback_path}"
        )
    feedback_items = feedback_payload.get("items")
    if not isinstance(feedback_items, list):
        raise PatchCandidateShapeError(
            f"Feedback JSON must include list field 'items': {feedback_path}"
        )

    known_feedback_ids = {
        item.get("feedback_id")
        for item in feedback_items
        if isinstance(item, dict) and isinstance(item.get("feedback_id"), str)
    }

    warnings: list[str] = []
    for idx, item in enumerate(normalized_items):
        for feedback_id in item["source_feedback_ids"]:
            if feedback_id not in known_feedback_ids:
                warnings.append(
                    f"unknown_feedback_id:index={idx},feedback_id={feedback_id}"
                )
    return warnings


def _validate_and_normalize_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for idx, item in enumerate(items):
        missing = [field for field in REQUIRED_FIELDS if field not in item]
        if missing:
            raise PatchCandidateShapeError(
                f"Patch candidate at index {idx} is missing required fields: {', '.join(missing)}"
            )

        target_file = item["target_file"]
        if target_file not in ALLOWED_TARGET_FILES:
            raise PatchCandidateShapeError(
                f"Patch candidate at index {idx} has invalid target_file: {target_file}"
            )

        source_feedback_ids = item["source_feedback_ids"]
        if (
            not isinstance(source_feedback_ids, list)
            or not source_feedback_ids
            or any(not isinstance(fid, str) or not fid.strip() for fid in source_feedback_ids)
        ):
            raise PatchCandidateShapeError(
                f"Patch candidate at index {idx} must provide non-empty string list source_feedback_ids"
            )

        requires_user_approval = item["requires_user_approval"]
        if not isinstance(requires_user_approval, bool):
            raise PatchCandidateShapeError(
                f"Patch candidate at index {idx} requires_user_approval must be bool"
            )

        stable_prefix_change_expected = item["stable_prefix_change_expected"]
        if not isinstance(stable_prefix_change_expected, bool):
            raise PatchCandidateShapeError(
                f"Patch candidate at index {idx} stable_prefix_change_expected must be bool"
            )

        risk_level = item["risk_level"]
        if risk_level not in ALLOWED_RISK_LEVELS:
            raise PatchCandidateShapeError(
                f"Patch candidate at index {idx} has invalid risk_level: {risk_level}"
            )

        if target_file == "SOUL.md":
            if risk_level != "high":
                raise PatchCandidateShapeError(
                    f"Patch candidate at index {idx} targeting SOUL.md must have risk_level='high'"
                )
            if requires_user_approval is not True:
                raise PatchCandidateShapeError(
                    f"Patch candidate at index {idx} targeting SOUL.md must set requires_user_approval=true"
                )

        normalized.append(
            {
                "target_file": target_file,
                "target_block": str(item["target_block"]),
                "operation": str(item["operation"]),
                "reason": str(item["reason"]),
                "patch_text": str(item["patch_text"]),
                "source_feedback_ids": source_feedback_ids,
                "risk_level": risk_level,
                "requires_user_approval": requires_user_approval,
                "budget_effect": str(item["budget_effect"]),
                "stable_prefix_change_expected": stable_prefix_change_expected,
            }
        )

    return normalized


def _build_warnings(items: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if any(item["budget_effect"] != "neutral" for item in items):
        warnings.append("non_neutral_budget_effect_present")
    if any(item["stable_prefix_change_expected"] is True for item in items):
        warnings.append("stable_prefix_change_expected_present")
    if any(item["target_file"] == "SOUL.md" for item in items):
        warnings.append("soul_patch_candidate_present")
    return warnings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-response", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--feedback")
    parser.add_argument("--schema-version", default=DEFAULT_SCHEMA_VERSION)
    args = parser.parse_args()

    model_payload = _read_json(args.model_response)
    raw_candidates = _extract_candidates(model_payload, args.model_response)
    normalized_items = _validate_and_normalize_items(raw_candidates)

    warnings = _build_warnings(normalized_items)
    warnings.extend(
        _validate_feedback_refs_if_requested(
            feedback_path=args.feedback,
            normalized_items=normalized_items,
        )
    )

    artifact = {
        "schema_version": args.schema_version,
        "artifact_type": "patch_candidates",
        "source_model_response": args.model_response,
        "items": normalized_items,
        "candidate_count": len(normalized_items),
        "warnings": warnings,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
