#!/usr/bin/env python3
"""Validate checked-in E2 value smoke scenarios without backend calls."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.relaylm_e2_value_smoke import (  # noqa: E402
    ARTIFACT_DIR,
    MIN_SCENARIO_TURNS,
    load_scenario,
)

SCENARIO_DIR = REPO_ROOT / "examples" / "value_smoke"


class ScenarioValidationError(RuntimeError):
    """Content-free validation failure for checked-in scenario examples."""


def _artifact_snapshot() -> set[Path]:
    if not ARTIFACT_DIR.exists():
        return set()
    return {path.resolve() for path in ARTIFACT_DIR.glob("*") if path.is_file()}


def main() -> int:
    scenario_paths = sorted(SCENARIO_DIR.glob("*.yaml"))
    if not scenario_paths:
        raise ScenarioValidationError("no checked-in E2 value smoke scenarios found")

    before_artifacts = _artifact_snapshot()
    seen_ids: set[str] = set()
    total_turns = 0

    for path in scenario_paths:
        scenario = load_scenario(path)
        if scenario.scenario_id in seen_ids:
            raise ScenarioValidationError("duplicate scenario_id found")
        seen_ids.add(scenario.scenario_id)
        if len(scenario.turns) < MIN_SCENARIO_TURNS:
            raise ScenarioValidationError("scenario has too few turns")
        for turn in scenario.turns:
            if not turn.user.strip() or not turn.probe.strip():
                raise ScenarioValidationError("scenario turn contains empty user/probe text")
        total_turns += len(scenario.turns)

    after_artifacts = _artifact_snapshot()
    if after_artifacts != before_artifacts:
        raise ScenarioValidationError("scenario validation wrote local artifacts")

    print(
        "E2 value smoke scenario validation passed: "
        f"scenarios={len(scenario_paths)} turns={total_turns} artifacts_written=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
