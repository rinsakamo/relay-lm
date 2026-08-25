from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.actual_model_fast_screening import ScreeningCallTiming
from relaylm.actual_model_fast_screening_artifacts import (
    ActualModelFastScreeningArtifactError,
    bind_fast_screening_timing_artifact,
    write_fast_screening_timing_artifact,
)


EXECUTION_ID = "amx-" + "a" * 64
RUN_ID = "amr-" + "b" * 64


def _call(
    phase: str,
    *,
    duration_ms: float,
    first_visible_ms: float | None = None,
) -> ScreeningCallTiming:
    return ScreeningCallTiming(
        phase=phase,  # type: ignore[arg-type]
        duration_ms=duration_ms,
        first_visible_ms=first_visible_ms,
        outcome="completed",
    )


def test_single_pass_timing_artifact_binds_each_turn_to_execution_identity() -> None:
    artifact = bind_fast_screening_timing_artifact(
        screening_id="screening-v1",
        condition_id="single-pass-off",
        replicate_id="r1",
        scenario_id="scenario-v1",
        execution_id=EXECUTION_ID,
        run_id=RUN_ID,
        execution_mode="single_pass",
        turn_count=2,
        scenario_elapsed_ms=42.5,
        calls=(
            _call("single_pass", duration_ms=10.0),
            _call("single_pass", duration_ms=12.0),
        ),
    )

    assert artifact.format_version == 2
    assert artifact.timing_id.startswith("amt-")
    assert len(artifact.timing_id) == 68
    assert artifact.run_id == RUN_ID
    assert artifact.execution_id == EXECUTION_ID
    assert artifact.scenario_elapsed_ms == 42.5
    assert tuple(turn.turn_index for turn in artifact.turns) == (1, 2)
    assert artifact.turns[0].response_provider_ms == 10.0
    assert artifact.turns[0].response_outcome == "completed"
    assert artifact.turns[0].first_visible_provider_ms is None
    assert artifact.turns[0].extraction_provider_ms is None
    assert artifact.turns[0].extraction_outcome is None
    assert artifact.to_mapping()["timing_id"] == artifact.timing_id


def test_two_pass_timing_artifact_separates_visible_response_from_extraction() -> None:
    artifact = bind_fast_screening_timing_artifact(
        screening_id="screening-v1",
        condition_id="two-pass-off-off",
        replicate_id="r1",
        scenario_id="scenario-v1",
        execution_id=EXECUTION_ID,
        run_id=RUN_ID,
        execution_mode="two_pass",
        turn_count=2,
        scenario_elapsed_ms=60.0,
        calls=(
            _call("pass1", duration_ms=8.0, first_visible_ms=2.0),
            _call("pass2", duration_ms=5.0),
            _call("pass1", duration_ms=9.0, first_visible_ms=2.5),
            _call("pass2", duration_ms=6.0),
        ),
    )

    assert artifact.turns[0].response_provider_ms == 8.0
    assert artifact.turns[0].response_outcome == "completed"
    assert artifact.turns[0].first_visible_provider_ms == 2.0
    assert artifact.turns[0].extraction_provider_ms == 5.0
    assert artifact.turns[0].extraction_outcome == "completed"
    assert artifact.turns[0].provider_total_ms == 13.0
    assert artifact.turns[1].provider_total_ms == 15.0


def test_two_pass_timing_allows_budget_gated_pass2_without_provider_call() -> None:
    artifact = bind_fast_screening_timing_artifact(
        screening_id="screening-v1",
        condition_id="two-pass-off-off",
        replicate_id="near-floor",
        scenario_id="scenario-v1",
        execution_id=EXECUTION_ID,
        run_id=RUN_ID,
        execution_mode="two_pass",
        turn_count=2,
        scenario_elapsed_ms=30.0,
        calls=(
            _call("pass1", duration_ms=8.0),
            _call("pass1", duration_ms=9.0),
        ),
    )

    assert tuple(turn.response_outcome for turn in artifact.turns) == (
        "completed",
        "completed",
    )
    assert tuple(turn.extraction_provider_ms for turn in artifact.turns) == (None, None)
    assert tuple(turn.extraction_outcome for turn in artifact.turns) == (None, None)


def test_two_pass_timing_sidecar_preserves_failed_extraction_call() -> None:
    artifact = bind_fast_screening_timing_artifact(
        screening_id="screening-v1",
        condition_id="two-pass-off-off",
        replicate_id="r1",
        scenario_id="scenario-v1",
        execution_id=EXECUTION_ID,
        run_id=RUN_ID,
        execution_mode="two_pass",
        turn_count=1,
        scenario_elapsed_ms=20.0,
        calls=(
            ScreeningCallTiming(
                phase="pass1",
                duration_ms=8.0,
                first_visible_ms=None,
                outcome="completed",
            ),
            ScreeningCallTiming(
                phase="pass2",
                duration_ms=5.0,
                first_visible_ms=None,
                outcome="failed",
            ),
        ),
    )

    turn = artifact.turns[0]
    assert turn.response_outcome == "completed"
    assert turn.extraction_outcome == "failed"
    assert turn.extraction_provider_ms == 5.0
    assert artifact.to_mapping()["turns"][0]["extraction_outcome"] == "failed"


def test_timing_artifact_rejects_phase_sequence_drift() -> None:
    with pytest.raises(ActualModelFastScreeningArtifactError, match="phase sequence"):
        bind_fast_screening_timing_artifact(
            screening_id="screening-v1",
            condition_id="two-pass-off-off",
            replicate_id="r1",
            scenario_id="scenario-v1",
            execution_id=EXECUTION_ID,
            run_id=RUN_ID,
            execution_mode="two_pass",
            turn_count=1,
            scenario_elapsed_ms=20.0,
            calls=(
                _call("pass2", duration_ms=5.0),
                _call("pass1", duration_ms=8.0),
            ),
        )


def test_timing_artifact_rejects_noncanonical_run_identity() -> None:
    with pytest.raises(ValueError, match="run_id must be canonical"):
        bind_fast_screening_timing_artifact(
            screening_id="screening-v1",
            condition_id="single-pass-off",
            replicate_id="r1",
            scenario_id="scenario-v1",
            execution_id=EXECUTION_ID,
            run_id="../escape",
            execution_mode="single_pass",
            turn_count=1,
            scenario_elapsed_ms=20.0,
            calls=(_call("single_pass", duration_ms=10.0),),
        )


def test_timing_artifact_rejects_scenario_elapsed_below_provider_total() -> None:
    with pytest.raises(
        ActualModelFastScreeningArtifactError,
        match="scenario elapsed time cannot be below provider call total",
    ):
        bind_fast_screening_timing_artifact(
            screening_id="screening-v1",
            condition_id="two-pass-off-off",
            replicate_id="r1",
            scenario_id="scenario-v1",
            execution_id=EXECUTION_ID,
            run_id=RUN_ID,
            execution_mode="two_pass",
            turn_count=1,
            scenario_elapsed_ms=12.0,
            calls=(
                _call("pass1", duration_ms=8.0),
                _call("pass2", duration_ms=5.0),
            ),
        )


def test_timing_artifact_write_is_idempotent_and_conflict_safe(tmp_path: Path) -> None:
    artifact = bind_fast_screening_timing_artifact(
        screening_id="screening-v1",
        condition_id="single-pass-off",
        replicate_id="r1",
        scenario_id="scenario-v1",
        execution_id=EXECUTION_ID,
        run_id=RUN_ID,
        execution_mode="single_pass",
        turn_count=1,
        scenario_elapsed_ms=20.0,
        calls=(_call("single_pass", duration_ms=10.0),),
    )

    path = write_fast_screening_timing_artifact(artifact=artifact, artifact_root=tmp_path)
    assert path == tmp_path / "screening_timing" / f"{RUN_ID}.json"
    assert write_fast_screening_timing_artifact(
        artifact=artifact,
        artifact_root=tmp_path,
    ) == path

    with pytest.raises(ActualModelFastScreeningArtifactError, match="conflicting timing evidence"):
        write_fast_screening_timing_artifact(
            artifact=replace(artifact, scenario_elapsed_ms=21.0),
            artifact_root=tmp_path,
        )