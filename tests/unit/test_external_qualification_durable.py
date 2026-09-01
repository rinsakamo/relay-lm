from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tools.external_qualification import (
    DurableQuestion,
    DurableQuestionRun,
    ExactResumeError,
    ExternalQualificationError,
    FrozenExperimentIdentity,
    LiveLaunchAdmissionAttestation,
    freeze_experiment_identity,
)


def identity() -> FrozenExperimentIdentity:
    raw = {
            "repository": "rinsakamo/relay-lm",
            "candidate": "b" * 40,
            "prompt_core": "sha256:" + "1" * 64,
            "benchmark": "memconflict",
            "dataset": "dataset-sha256:" + "2" * 64,
            "harness": "harness-sha256:" + "3" * 64,
            "adapter": "adapter-sha256:" + "4" * 64,
            "model": "synthetic-model",
            "artifact": "artifact-sha256:" + "5" * 64,
            "tokenizer": "tokenizer-sha256:" + "6" * 64,
            "template": "template-v1",
            "backend": "synthetic-backend",
            "runtime": "synthetic-runtime",
            "decoding": {"temperature": 0},
            "reasoning": {"mode": "off"},
            "structured_output": "json-schema-v1",
            "context_capacity": 3072,
            "capacity_evidence": "synthetic-capacity-evidence",
            "hardware": {"gpu": "synthetic-gpu", "vram": 12_288},
            "execution_order": "dataset-order-v1",
            "retry_policy": "no semantic retry",
            "authority": {
                "status": "CURRENT_AUTHORITY_CONFIRMED",
                "source": "host-api",
                "repository_head": "b" * 40,
            },
            "launch_admission": {
                "backend": "synthetic-backend",
                "runtime": "synthetic-runtime",
                "model_runner": "synthetic-runner",
                "effective_gpu_reservation": 0.73,
                "admitted_context": 3072,
                "capacity_evidence": "synthetic-capacity-evidence",
                "launch_evidence_reference": "synthetic-launch-evidence",
                "runtime_ownership_evidence_reference": "synthetic-runtime-ownership-evidence",
            },
    }
    return FrozenExperimentIdentity.from_live_attestation(raw, live_attestation())


def questions() -> tuple[DurableQuestion, ...]:
    return (
        DurableQuestion.from_content("persona-0-q0", "first question", session_id="persona-0"),
        DurableQuestion.from_content("persona-0-q1", "second question", session_id="persona-0"),
        DurableQuestion.from_content("persona-1-q0", "third question", session_id="persona-1"),
    )


def live_attestation() -> LiveLaunchAdmissionAttestation:
    return LiveLaunchAdmissionAttestation.from_mapping(
        {
            "backend": "synthetic-backend",
            "runtime": "synthetic-runtime",
            "model_runner": "synthetic-runner",
            "effective_gpu_reservation": 0.73,
            "admitted_context": 3072,
            "capacity_evidence": "synthetic-capacity-evidence",
            "launch_evidence_reference": "synthetic-launch-evidence",
            "runtime_ownership_evidence_reference": "synthetic-runtime-ownership-evidence",
        }
    )


def test_freeze_identity_is_bound_to_final_live_launch_admission() -> None:
    frozen = freeze_experiment_identity(
        identity=identity(),
        live_attestation=live_attestation(),
    )
    assert frozen.to_mapping()["launch_admission"] == live_attestation().to_mapping()
    assert frozen.to_mapping()["context_capacity"] == 3072


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_runner", "other-runner"),
        ("effective_gpu_reservation", 0.72),
    ],
)
def test_freeze_identity_rejects_stale_live_runtime_facts(
    field: str,
    value: object,
) -> None:
    changed = identity().to_mapping()
    changed["launch_admission"][field] = value
    with pytest.raises(ExternalQualificationError, match=field):
        freeze_experiment_identity(
            identity=changed,
            live_attestation=live_attestation(),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("backend", "other-backend"),
        ("runtime", "other-runtime"),
        ("context_capacity", 3584),
        ("capacity_evidence", "other-capacity-evidence"),
    ],
)
def test_freeze_identity_rejects_mismatched_mirrored_live_facts(
    field: str,
    value: object,
) -> None:
    changed = identity().to_mapping()
    changed[field] = value
    with pytest.raises(ExternalQualificationError, match=field):
        freeze_experiment_identity(
            identity=changed,
            live_attestation=live_attestation(),
        )


def test_freeze_identity_rejects_missing_effective_gpu_reservation() -> None:
    changed = identity().to_mapping()
    del changed["launch_admission"]["effective_gpu_reservation"]
    with pytest.raises(ExternalQualificationError, match="effective_gpu_reservation"):
        freeze_experiment_identity(
            identity=changed,
            live_attestation=live_attestation(),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("admitted_context", 3584),
        ("capacity_evidence", "other-capacity-evidence"),
        ("launch_evidence_reference", "other-launch-evidence"),
        (
            "runtime_ownership_evidence_reference",
            "other-runtime-ownership-evidence",
        ),
    ],
)
def test_freeze_identity_rejects_mismatched_nested_live_facts(
    field: str,
    value: object,
) -> None:
    changed = identity().to_mapping()
    changed["launch_admission"][field] = value
    with pytest.raises(ExternalQualificationError, match=field):
        freeze_experiment_identity(
            identity=changed,
            live_attestation=live_attestation(),
        )


def test_new_durable_run_rejects_unattested_identity(tmp_path: Path) -> None:
    with pytest.raises(ExternalQualificationError, match="live-attested"):
        DurableQuestionRun.start(
            artifact_root=tmp_path,
            identity=FrozenExperimentIdentity.from_mapping(identity().to_mapping()),
            questions=questions(),
        )


def test_fresh_run_persists_manifest_checkpoint_state_and_inflight_tail(tmp_path: Path) -> None:
    run = DurableQuestionRun.start(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    run.begin_question("persona-0-q0")
    run.append_request_evidence(
        question_id="persona-0-q0",
        evidence={"pass": "pass1", "status": "completed", "request_id": "req-0"},
    )
    run.mark_process_exited()

    assert (tmp_path / "run-manifest.json").is_file()
    assert (tmp_path / "checkpoint.json").is_file()
    assert (tmp_path / "run-state.json").is_file()
    assert (tmp_path / "question-observations.jsonl").is_file()
    assert (tmp_path / "request-evidence.jsonl").is_file()
    assert run.next_question().question_id == "persona-0-q0"
    assert run.health()["status"] == "PROCESS_EXITED"
    assert json.loads((tmp_path / "run-state.json").read_text())[
        "in_flight_questions"
    ] == ["persona-0-q0"]


def test_exact_resume_skips_completed_question_and_never_regenerates_it(tmp_path: Path) -> None:
    original = DurableQuestionRun.start(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    original.begin_question("persona-0-q0")
    original.commit_question(
        question_id="persona-0-q0",
        result={"answer": "durable answer", "pass1_status": "completed", "pass2_status": "completed"},
    )
    original.begin_question("persona-0-q1")
    original.mark_process_exited()

    resumed = DurableQuestionRun.resume(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    assert resumed.run_mode == "exact_infrastructure_resume"
    assert resumed.next_question().question_id == "persona-0-q1"
    with pytest.raises(ExternalQualificationError, match="already durably completed"):
        resumed.begin_question("persona-0-q0")

    resumed.commit_question(
        question_id="persona-0-q1",
        result={"answer": "second"},
    )
    resumed.begin_question("persona-1-q0")
    resumed.commit_question(question_id="persona-1-q0", result={"answer": "third"})
    assert resumed.next_question() is None
    assert [item["question_id"] for item in resumed.rebuild_completed_results()] == [
        "persona-0-q0",
        "persona-0-q1",
        "persona-1-q0",
    ]


@pytest.mark.parametrize("change", ["candidate", "prompt_core", "context_capacity", "authority"])
def test_exact_resume_requires_full_frozen_identity_match(tmp_path: Path, change: str) -> None:
    frozen = identity()
    DurableQuestionRun.start(
        artifact_root=tmp_path,
        identity=frozen,
        questions=questions(),
    )
    changed = deepcopy(frozen.to_mapping())
    if change == "context_capacity":
        changed[change] = 8192
    elif change == "authority":
        changed[change]["repository_head"] = "a" * 40
    else:
        changed[change] = str(changed[change]) + "-changed"

    with pytest.raises(ExactResumeError, match="frozen experiment identity"):
        DurableQuestionRun.resume(
            artifact_root=tmp_path,
            identity=FrozenExperimentIdentity.from_mapping(changed),
            questions=questions(),
        )


def test_exact_resume_rejects_changed_question_fingerprint_or_order(tmp_path: Path) -> None:
    frozen_questions = questions()
    DurableQuestionRun.start(
        artifact_root=tmp_path,
        identity=identity(),
        questions=frozen_questions,
    )
    changed = (
        DurableQuestion.from_content("persona-0-q0", "changed", session_id="persona-0"),
        *frozen_questions[1:],
    )
    with pytest.raises(ExactResumeError, match="question order or fingerprint"):
        DurableQuestionRun.resume(
            artifact_root=tmp_path,
            identity=identity(),
            questions=changed,
        )


def test_partial_final_record_is_preserved_and_does_not_claim_completion(tmp_path: Path) -> None:
    run = DurableQuestionRun.start(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    run.begin_question("persona-0-q0")
    observations = tmp_path / "question-observations.jsonl"
    with observations.open("a", encoding="utf-8") as handle:
        handle.write('{"event":"partial-tail"')

    resumed = DurableQuestionRun.resume(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    assert resumed.partial_tail_detected is True
    assert resumed.next_question().question_id == "persona-0-q0"
    assert observations.read_text().endswith('{"event":"partial-tail"')


def test_resume_rejects_inflight_evidence_after_durable_completion(tmp_path: Path) -> None:
    run = DurableQuestionRun.start(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    run.begin_question("persona-0-q0")
    run.commit_question(question_id="persona-0-q0", result={"answer": "done"})
    completed = json.loads(
        (tmp_path / "question-observations.jsonl").read_text(encoding="utf-8").splitlines()[-1]
    )
    completed["event"] = "in_flight"
    with (tmp_path / "question-observations.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(completed) + "\n")

    with pytest.raises(ExactResumeError, match="after completion"):
        DurableQuestionRun.resume(
            artifact_root=tmp_path,
            identity=identity(),
            questions=questions(),
        )


def test_aggregate_rebuilds_by_session_from_question_records(tmp_path: Path) -> None:
    run = DurableQuestionRun.start(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    for question in questions():
        run.begin_question(question.question_id)
        run.commit_question(question_id=question.question_id, result={"id": question.question_id})

    aggregate = run.rebuild_aggregate()
    assert list(aggregate["sessions"]) == ["persona-0", "persona-1"]
    assert [item["question_id"] for item in aggregate["sessions"]["persona-0"]] == [
        "persona-0-q0",
        "persona-0-q1",
    ]


def test_semantic_retry_is_not_a_resume_mode(tmp_path: Path) -> None:
    with pytest.raises(ExternalQualificationError, match="semantic retry"):
        DurableQuestionRun.start(
            artifact_root=tmp_path,
            identity=identity(),
            questions=questions(),
            run_mode="semantic_retry",
        )
