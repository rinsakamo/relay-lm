from __future__ import annotations

import json
from pathlib import Path

import pytest

from relaylm.actual_model_vllm_launch_preflight import (
    OwnedVLLMRuntime,
    RuntimeCleanupReceipt,
    RuntimeListenerEndpoint,
)
from relaylm.lab_session import (
    EXPLORATORY_EVIDENCE_CLASS,
    ExploratoryLabSession,
    LabSessionError,
)


LAB_FINGERPRINT = "sha256:" + "a" * 64


class _FakeOwnedRuntime(OwnedVLLMRuntime):
    def __init__(self) -> None:
        self.cleanup_calls = 0

    def cleanup(self, **kwargs: object) -> RuntimeCleanupReceipt:
        self.cleanup_calls += 1
        return RuntimeCleanupReceipt(
            run_id="explore-runtime",
            owner_nonce="owner-nonce",
            controller_pid=10,
            controller_pgid=10,
            controller_session_id=10,
            root_pid=20,
            root_pgid=20,
            root_session_id=20,
            expected_listener=RuntimeListenerEndpoint("127.0.0.1", 23456),
            graceful_signal_pids=(20,),
            escalated_signal_pids=(),
            remaining_owned_pids=(),
            listener_disposition="absent",
            complete=True,
        )


def _session(*, runtime: OwnedVLLMRuntime | None = None) -> ExploratoryLabSession:
    return ExploratoryLabSession(
        session_id="lab3-session-1",
        lab_environment_fingerprint=LAB_FINGERPRINT,
        runtime=runtime,
    )


def test_exploratory_session_is_non_citable_by_construction() -> None:
    session = _session()

    status = session.status()

    assert status["evidence_class"] == EXPLORATORY_EVIDENCE_CLASS
    assert status["citable"] is False
    assert not hasattr(session, "to_qualification")
    assert not hasattr(session, "to_live_launch_admission_attestation")
    assert not hasattr(session, "to_frozen_experiment_identity")


def test_warm_owned_runtime_can_be_reused_across_distinct_trials() -> None:
    runtime = _FakeOwnedRuntime()
    session = _session(runtime=runtime)

    first = session.record_trial(
        trial_id="trial-1",
        condition_id="endpoint:auto-1",
        required_steps=("endpoint", "launch", "readiness", "cleanup"),
        completed_steps=("endpoint", "launch"),
        outcome="INCONCLUSIVE",
        detail_codes=("LISTENER_UNPROVEN",),
    )
    second = session.record_trial(
        trial_id="trial-2",
        condition_id="endpoint:auto-2",
        required_steps=("endpoint", "launch", "readiness", "cleanup"),
        completed_steps=("endpoint", "launch", "readiness", "cleanup"),
        outcome="PASS",
    )

    assert first.condition_id != second.condition_id
    assert session.runtime is runtime
    assert runtime.cleanup_calls == 0
    assert session.status()["trial_count"] == 2


def test_pass_requires_the_declared_rehearsal_steps_to_be_complete() -> None:
    session = _session()

    with pytest.raises(LabSessionError, match="required rehearsal steps"):
        session.record_trial(
            trial_id="trial-1",
            condition_id="condition-a",
            required_steps=("clean_checkout", "runtime_paths", "cleanup"),
            completed_steps=("clean_checkout", "runtime_paths"),
            outcome="PASS",
        )


def test_successful_trial_yields_only_a_non_citable_procedure_hint() -> None:
    session = _session()
    session.record_trial(
        trial_id="trial-ready",
        condition_id="mechanical-condition-v3",
        required_steps=(
            "clean_checkout",
            "runtime_paths",
            "environment",
            "endpoint",
            "launch",
            "readiness",
            "cleanup",
        ),
        completed_steps=(
            "clean_checkout",
            "runtime_paths",
            "environment",
            "endpoint",
            "launch",
            "readiness",
            "cleanup",
        ),
        outcome="PASS",
    )

    hint = session.procedure_hint("trial-ready")
    mapping = hint.to_mapping()

    assert mapping["evidence_class"] == EXPLORATORY_EVIDENCE_CLASS
    assert mapping["citable"] is False
    assert mapping["qualification_authority"] is False
    assert mapping["condition_id"] == "mechanical-condition-v3"
    assert "gpu_free_bytes" not in mapping
    assert "pid" not in mapping
    assert "listener" not in mapping
    assert "semantic_request_count" not in mapping


def test_failed_or_inconclusive_trial_cannot_produce_a_procedure_hint() -> None:
    session = _session()
    session.record_trial(
        trial_id="trial-failed",
        condition_id="condition-a",
        required_steps=("launch", "cleanup"),
        completed_steps=("launch",),
        outcome="INCONCLUSIVE",
    )

    with pytest.raises(LabSessionError, match="successful rehearsal"):
        session.procedure_hint("trial-failed")


def test_trial_ids_are_unique_and_free_text_is_not_accepted() -> None:
    session = _session()
    session.record_trial(
        trial_id="trial-1",
        condition_id="condition-a",
        required_steps=("launch",),
        completed_steps=(),
        outcome="INCONCLUSIVE",
    )

    with pytest.raises(LabSessionError, match="trial_id"):
        session.record_trial(
            trial_id="trial-1",
            condition_id="condition-b",
            required_steps=("launch",),
            completed_steps=(),
            outcome="FAIL",
        )

    with pytest.raises(LabSessionError, match="condition_id"):
        session.record_trial(
            trial_id="trial-2",
            condition_id="contains free text and spaces",
            required_steps=("launch",),
            completed_steps=(),
            outcome="FAIL",
        )


def test_stop_delegates_cleanup_to_the_existing_owned_runtime_and_is_idempotent() -> None:
    runtime = _FakeOwnedRuntime()
    session = _session(runtime=runtime)

    first = session.stop()
    second = session.stop()

    assert first is not None
    assert first.complete is True
    assert second is first
    assert runtime.cleanup_calls == 1
    assert session.status()["state"] == "STOPPED"


def test_stopped_session_rejects_new_trials() -> None:
    session = _session()
    session.stop()

    with pytest.raises(LabSessionError, match="stopped"):
        session.record_trial(
            trial_id="trial-1",
            condition_id="condition-a",
            required_steps=("launch",),
            completed_steps=(),
            outcome="FAIL",
        )


def test_saved_notes_are_explicitly_non_citable_and_content_free(tmp_path: Path) -> None:
    session = _session()
    session.record_trial(
        trial_id="trial-ready",
        condition_id="mechanical-condition-v1",
        required_steps=("endpoint", "launch", "cleanup"),
        completed_steps=("endpoint", "launch", "cleanup"),
        outcome="PASS",
        detail_codes=("PROCEDURE_READY",),
    )
    path = tmp_path / "notes" / "lab3.json"

    session.save_notes(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    encoded = json.dumps(payload, sort_keys=True)

    assert payload["evidence_class"] == EXPLORATORY_EVIDENCE_CLASS
    assert payload["citable"] is False
    assert payload["lab_environment_fingerprint"] == LAB_FINGERPRINT
    assert payload["trials"][0]["condition_id"] == "mechanical-condition-v1"
    for prohibited in (
        "gpu_free_bytes",
        "gpu_memory_utilization",
        "pid",
        "listener",
        "prompt",
        "semantic_request_count",
        "live_launch_admission",
        "frozen_experiment",
    ):
        assert prohibited not in encoded


def test_invalid_lab_environment_fingerprint_is_rejected() -> None:
    with pytest.raises(LabSessionError, match="lab_environment_fingerprint"):
        ExploratoryLabSession(
            session_id="lab3-session-1",
            lab_environment_fingerprint="sha256:not-a-digest",
        )
