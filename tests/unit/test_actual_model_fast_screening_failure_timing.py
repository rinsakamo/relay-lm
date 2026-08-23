from __future__ import annotations

from relaylm.actual_model_fast_screening import ScreeningCallTiming
from relaylm.actual_model_fast_screening_artifacts import bind_fast_screening_timing_artifact


EXECUTION_ID = "amx-" + "a" * 64
RUN_ID = "amr-" + "b" * 64


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
