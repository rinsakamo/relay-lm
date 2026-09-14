"""Zero-generation physical admission gate for exact-RC external qualification.

The shared physical runner owns fresh-ref/environment/queue admission. This
module owns only the final repository-side execution-freeze check for the
future #1449 scientific owner. It never launches llama-server, calls a model,
runs a benchmark question, or invokes a judge.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from tools.external_qualification_readiness import (
    ExternalQualificationReadinessError,
    validate_launch_readiness,
)

EXPECTED_TARGET = "v1:external-qualification"
EXPECTED_BACKEND = "llama.cpp"
EXPECTED_RESOURCE_KEY = "llama-cpp:local-gpu"


class ExternalQualificationPhysicalGateError(
    ExternalQualificationReadinessError
):
    """The frozen release-qualification plan is not admissible for this target."""


def validate_physical_execution_freeze(
    raw: Mapping[str, object],
) -> dict[str, object]:
    """Validate one exact-RC execution freeze against the registered carriage."""

    normalized = validate_launch_readiness(raw)
    if normalized.get("status") != "EXECUTION_FROZEN":
        raise ExternalQualificationPhysicalGateError(
            "physical external qualification requires EXECUTION_FROZEN readiness"
        )

    carriage = normalized.get("physical_carriage")
    if not isinstance(carriage, Mapping):
        raise ExternalQualificationPhysicalGateError(
            "physical_carriage must be present after readiness validation"
        )
    expected = {
        "target": EXPECTED_TARGET,
        "backend": EXPECTED_BACKEND,
        "resource_key": EXPECTED_RESOURCE_KEY,
        "registered": True,
    }
    if dict(carriage) != expected:
        raise ExternalQualificationPhysicalGateError(
            "execution freeze does not bind the registered v1 external-qualification llama.cpp carriage"
        )

    release = normalized.get("relaylm_release")
    if not isinstance(release, Mapping):
        raise ExternalQualificationPhysicalGateError(
            "execution freeze must bind one exact RelayLM release identity"
        )
    comparator = normalized.get("comparator_participant_identity")
    if not isinstance(comparator, Mapping):
        raise ExternalQualificationPhysicalGateError(
            "execution freeze must bind one exact serious-comparator participant identity"
        )
    fingerprint = normalized.get("fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint.startswith("sha256:"):
        raise ExternalQualificationPhysicalGateError(
            "execution freeze must carry a deterministic readiness fingerprint"
        )
    return normalized


def _load_plan(path: Path) -> Mapping[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalQualificationPhysicalGateError(
            f"cannot load external qualification plan: {exc}"
        ) from exc
    if not isinstance(raw, Mapping):
        raise ExternalQualificationPhysicalGateError(
            "external qualification plan must be a JSON object"
        )
    return raw


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one exact-RC external qualification execution freeze "
            "inside the shared llama.cpp physical queue without spending any generation."
        )
    )
    parser.add_argument("--plan", required=True, type=Path)
    return parser.parse_args(list(sys.argv[1:] if argv is None else argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        normalized = validate_physical_execution_freeze(_load_plan(args.plan))
    except ExternalQualificationReadinessError as exc:
        print(f"external qualification physical gate blocked: {exc}", file=sys.stderr)
        return 2

    release = normalized["relaylm_release"]
    assert isinstance(release, Mapping)
    print(
        json.dumps(
            {
                "status": "EXECUTION_FROZEN",
                "target": EXPECTED_TARGET,
                "backend": EXPECTED_BACKEND,
                "resource_key": EXPECTED_RESOURCE_KEY,
                "readiness_fingerprint": normalized["fingerprint"],
                "relaylm_release_commit": release["commit"],
                "relaylm_release_version": release["version"],
                "semantic_generation_count": 0,
                "benchmark_question_count": 0,
                "judge_call_count": 0,
                "llama_server_launch_count": 0,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
