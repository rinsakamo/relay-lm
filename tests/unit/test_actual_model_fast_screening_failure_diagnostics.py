from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from relaylm.actual_model_fast_screening import (
    ScreeningCallTiming,
    ScreeningTimingRecorder,
    instrument_screening_provider,
)
from relaylm.actual_model_fast_screening_artifacts import (
    bind_fast_screening_timing_artifact,
    write_fast_screening_timing_artifact,
)
from relaylm.providers.openai_compatible import ProviderProtocolError


class _FailingExtractionProvider:
    async def generate_extraction(self, _):
        raise ProviderProtocolError("provider extraction top-level shape is invalid")


class _UnsafeFailureProvider:
    async def generate_extraction(self, _):
        raise RuntimeError("raw semantic payload must not be persisted")


def test_instrumented_pass2_failure_records_sanitized_provider_exception_identity() -> None:
    ticks = iter((1_000_000, 3_000_000))
    recorder = ScreeningTimingRecorder(clock_ns=lambda: next(ticks))
    provider = instrument_screening_provider(
        _FailingExtractionProvider(),
        recorder=recorder,
    )

    async def run() -> None:
        with pytest.raises(
            ProviderProtocolError,
            match="provider extraction top-level shape is invalid",
        ):
            await provider.generate_extraction(object())

    asyncio.run(run())

    assert len(recorder.calls) == 1
    call = recorder.calls[0]
    assert call.phase == "pass2"
    assert call.outcome == "failed"
    assert call.failure_exception_type == "ProviderProtocolError"
    assert call.failure_exception_message == "provider extraction top-level shape is invalid"


def test_untrusted_exception_message_is_not_persisted() -> None:
    ticks = iter((1_000_000, 2_000_000))
    recorder = ScreeningTimingRecorder(clock_ns=lambda: next(ticks))
    provider = instrument_screening_provider(
        _UnsafeFailureProvider(),
        recorder=recorder,
    )

    async def run() -> None:
        with pytest.raises(RuntimeError, match="raw semantic payload"):
            await provider.generate_extraction(object())

    asyncio.run(run())

    call = recorder.calls[0]
    assert call.failure_exception_type == "RuntimeError"
    assert call.failure_exception_message is None


def test_failed_pass2_writes_separate_diagnostic_sidecar_without_changing_timing_wire(
    tmp_path: Path,
) -> None:
    run_id = f"amr-{'b' * 64}"
    calls = (
        ScreeningCallTiming(
            phase="pass1",
            duration_ms=1.0,
            first_visible_ms=None,
            outcome="completed",
        ),
        ScreeningCallTiming(
            phase="pass2",
            duration_ms=2.0,
            first_visible_ms=None,
            outcome="failed",
            failure_exception_type="ProviderProtocolError",
            failure_exception_message="provider extraction top-level shape is invalid",
        ),
    )
    artifact = bind_fast_screening_timing_artifact(
        screening_id="stage-r0-vllm-reference-v2",
        condition_id="reference-baseline",
        replicate_id="0",
        scenario_id="response-persona-correction-v1",
        execution_id=f"amx-{'a' * 64}",
        run_id=run_id,
        execution_mode="two_pass",
        turn_count=1,
        scenario_elapsed_ms=4.0,
        calls=calls,
    )

    timing_mapping = artifact.to_mapping()
    assert "failure_exception_type" not in timing_mapping["turns"][0]
    assert "failure_exception_message" not in timing_mapping["turns"][0]

    write_fast_screening_timing_artifact(
        artifact=artifact,
        artifact_root=tmp_path,
    )

    sidecar = tmp_path / "screening_failure_diagnostics" / f"{run_id}.json"
    assert sidecar.exists()
    mapping = json.loads(sidecar.read_text(encoding="utf-8"))
    assert mapping["format_version"] == 1
    assert mapping["run_id"] == run_id
    assert mapping["diagnostic_id"].startswith("amfd-")
    assert mapping["failures"] == [
        {
            "turn_index": 1,
            "phase": "pass2",
            "exception_type": "ProviderProtocolError",
            "exception_message": "provider extraction top-level shape is invalid",
        }
    ]
