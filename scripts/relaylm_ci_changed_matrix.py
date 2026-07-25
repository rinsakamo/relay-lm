#!/usr/bin/env python3
"""Emit GitHub Actions matrices for consolidated smoke workflows."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path

from relaylm_ci_consolidated_smoke import GROUPS, changed_outputs

RUNTIME_TIMEOUTS = {
    "client_instruction": 30,
    "relayctx_tts_stream": 45,
    "relayrun_lazy_recovery": 30,
    "token_estimation": 30,
    "merged_review_residuals": 30,
    "e1r1_trusted_home_scene_admission": 30,
    "e1r2_character_store_bootstrap": 30,
    "soul_lab_management": 30,
    "subjective_mem_lifecycle": 45,
}

UI_KINDS = {
    "python": {
        "lab_observation": 60,
        "lab_observation_regressions": 90,
        "primary_mem_correct": 60,
        "primary_mem_correct_regressions": 60,
        "home_conversation_regressions": 45,
        "forget_lifecycle": 60,
        "forget_lifecycle_regressions": 90,
    },
    "frontend": {
        "soul_lab_build": 30,
        "lab_observation_frontend": 30,
        "primary_mem_correct_frontend": 30,
        "home_conversation_frontend": 30,
        "forget_lifecycle_frontend": 30,
    },
    "mixed": {
        "pin_unpin": 60,
        "held_governance": 60,
        "lifecycle_visibility": 45,
    },
}

UI_MATRIX_KINDS = frozenset({"python", "frontend", "mixed"})


def _files(path: Path | None) -> list[str]:
    if path is None:
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _matrix(enabled: dict[str, bool], timeouts: Mapping[str, int]) -> dict[str, list[dict[str, object]]]:
    include = []
    for group, timeout in timeouts.items():
        if enabled.get(group, False):
            include.append({"group": group, "name": group.replace("_", "-"), "timeout": timeout})
    return {"include": include}


def _invalid_timeouts(timeouts: Mapping[str, int]) -> list[str]:
    return sorted(
        group
        for group, timeout in timeouts.items()
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0
    )


def validate_matrix_coverage(
    groups: Mapping[str, Mapping[str, object]] = GROUPS,
    runtime_timeouts: Mapping[str, int] = RUNTIME_TIMEOUTS,
    ui_kinds: Mapping[str, Mapping[str, int]] = UI_KINDS,
) -> None:
    """Fail closed when a selected smoke group cannot enter exactly one matrix."""

    runtime_groups = set(groups.get("runtime", {}))
    runtime_matrix_groups = set(runtime_timeouts)
    runtime_missing = sorted(runtime_groups - runtime_matrix_groups)
    runtime_unknown = sorted(runtime_matrix_groups - runtime_groups)
    runtime_invalid = _invalid_timeouts(runtime_timeouts)
    if runtime_missing or runtime_unknown or runtime_invalid:
        raise ValueError(
            "runtime matrix coverage drift: "
            f"missing={runtime_missing!r} unknown={runtime_unknown!r} "
            f"invalid_timeouts={runtime_invalid!r}"
        )

    ui_kind_names = set(ui_kinds)
    missing_kinds = sorted(UI_MATRIX_KINDS - ui_kind_names)
    unknown_kinds = sorted(ui_kind_names - UI_MATRIX_KINDS)

    ui_owners: dict[str, list[str]] = {}
    invalid_ui_timeouts: list[str] = []
    for kind, timeouts in ui_kinds.items():
        for group in timeouts:
            ui_owners.setdefault(group, []).append(kind)
        invalid_ui_timeouts.extend(
            f"{kind}/{group}" for group in _invalid_timeouts(timeouts)
        )

    ui_groups = set(groups.get("ui", {}))
    ui_matrix_groups = set(ui_owners)
    ui_missing = sorted(ui_groups - ui_matrix_groups)
    ui_unknown = sorted(ui_matrix_groups - ui_groups)
    ui_duplicates = sorted(
        f"{group}:{','.join(sorted(kinds))}"
        for group, kinds in ui_owners.items()
        if len(kinds) != 1
    )
    if (
        missing_kinds
        or unknown_kinds
        or ui_missing
        or ui_unknown
        or ui_duplicates
        or invalid_ui_timeouts
    ):
        raise ValueError(
            "ui matrix coverage drift: "
            f"missing_kinds={missing_kinds!r} unknown_kinds={unknown_kinds!r} "
            f"missing={ui_missing!r} unknown={ui_unknown!r} "
            f"duplicates={ui_duplicates!r} "
            f"invalid_timeouts={sorted(invalid_ui_timeouts)!r}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", choices=("runtime", "ui"), required=True)
    parser.add_argument("--kind", choices=("python", "frontend", "mixed"))
    parser.add_argument("--files", type=Path)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    validate_matrix_coverage()
    enabled = changed_outputs(args.workflow, _files(args.files), args.all)
    if args.workflow == "runtime":
        matrix = _matrix(enabled, RUNTIME_TIMEOUTS)
    else:
        if args.kind is None:
            parser.error("--kind is required for the ui workflow")
        matrix = _matrix(enabled, UI_KINDS[args.kind])
    print(json.dumps(matrix, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
