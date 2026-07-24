#!/usr/bin/env python3
"""Emit GitHub Actions matrices for consolidated smoke workflows."""

from __future__ import annotations

import argparse
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


def _files(path: Path | None) -> list[str]:
    if path is None:
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _matrix(enabled: dict[str, bool], timeouts: dict[str, int]) -> dict[str, list[dict[str, object]]]:
    include = []
    for group, timeout in timeouts.items():
        if enabled.get(group, False):
            include.append({"group": group, "name": group.replace("_", "-"), "timeout": timeout})
    return {"include": include}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", choices=("runtime", "ui"), required=True)
    parser.add_argument("--kind", choices=("python", "frontend", "mixed"))
    parser.add_argument("--files", type=Path)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

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
