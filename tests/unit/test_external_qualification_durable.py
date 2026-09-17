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
    ScientificSpendLedger,
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
                "branch": "v1",
                "source": "host-api",
                "repository_head": "b" * 40,
                "repository_tree": "c" * 40,
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


def _extended_live_attestation() -> dict[str, object]:
    return {
        **live_attestation().to_mapping(),
        "capacity_evidence": {
            "kind": "synthetic-live-capacity",
            "gpu_identity": {
                "name": "synthetic-gpu",
                "driver_version": "synthetic-driver",
                "memory_total_mib": "12288",
                "memory_used_mib": "100",
            },
            "context": 3072,
            "slots": 1,
        },
        "runtime_identity": {
            "upstream_revision": "a" * 40,
            "build_info": "b10874-aaaaaaaaa",
            "model_alias": "synthetic-model",
            "model_path": "/immutable/model.gguf",
            "artifact_sha256": "5" * 64,
            "chat_template_sha256": "6" * 64,
            "context_limit": 3072,
            "total_slots": 1,
            "context_shift_enabled": False,
        },
        "gpu_identity": {
            "name": "synthetic-gpu",
            "driver_version": "synthetic-driver",
            "memory_total_mib": "12288",
        },
        "launch_observation": {
            "runtime_evidence_path": "/tmp/live-0001/runtime.json",
            "runtime_ownership_evidence_path": "/tmp/live-0001/owner.json",
            "pid": 1234,
            "memory_used_mib": "100",
            "observed_at": "t1",
        },
    }


def _extended_identity() -> dict[str, object]:
    raw = identity().to_mapping()
    live = _extended_live_attestation()
    raw["capacity_evidence"] = live["capacity_evidence"]
    raw["launch_admission"] = live
    raw["artifact"] = "artifact:sha256:" + "5" * 64
    raw["template"] = "template:sha256:" + "6" * 64
    raw["backend"] = live["backend"]
    raw["runtime"] = live["runtime"]
    raw["context_capacity"] = live["admitted_context"]
    return raw


def test_extended_live_identity_excludes_volatile_launch_observations() -> None:
    frozen = freeze_experiment_identity(
        identity=_extended_identity(),
        live_attestation=_extended_live_attestation(),
    )
    launch = frozen.to_mapping()["launch_admission"]
    assert "launch_observation" not in launch
    assert "launch_evidence_reference" not in launch
    assert "runtime_ownership_evidence_reference" not in launch
    assert launch["capacity_evidence"]["gpu_identity"] == {
        "name": "synthetic-gpu",
        "driver_version": "synthetic-driver",
        "memory_total_mib": "12288",
    }

    changed = _extended_live_attestation()
    changed["launch_observation"]["runtime_evidence_path"] = "/tmp/live-0002/runtime.json"
    changed["launch_observation"]["runtime_ownership_evidence_path"] = "/tmp/live-0002/owner.json"
    changed["launch_observation"]["pid"] = 5678
    changed["launch_observation"]["memory_used_mib"] = "900"
    changed["launch_observation"]["observed_at"] = "t2"
    changed["capacity_evidence"]["gpu_identity"]["memory_used_mib"] = "900"
    resumed = freeze_experiment_identity(
        identity=_extended_identity(),
        live_attestation=changed,
    )
    assert resumed.fingerprint == frozen.fingerprint

    changed["gpu_identity"]["driver_version"] = "different-driver"
    with pytest.raises(ExternalQualificationError, match="gpu_identity"):
        freeze_experiment_identity(
            identity=_extended_identity(),
            live_attestation=changed,
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


def _participant_result(slot: str, *, calls: int = 0) -> dict[str, object]:
    return {
        "slot": slot,
        "observation": {
            "quality": {},
            "tokens": {
                "model_input_tokens": 0,
                "model_output_tokens": 0,
                "model_call_count": calls,
            },
            "latency": {
                "ttft_ms": 0.0,
                "query_latency_ms": 0.0,
                "end_to_end_ms": 0.0,
            },
            "resources": {
                "peak_gpu_memory_bytes": 0,
                "peak_cpu_memory_bytes": 0,
                "persistent_storage_bytes": 0,
                "notes": [],
            },
            "known_limitations": [],
            "failure": None,
        },
        "semantic_generation_count": 0,
        "answer_model_generation_count": 0,
        "judge_call_count": 0,
    }


def _commit_participant(
    run: DurableQuestionRun,
    slot: str,
    *,
    enabled_slots: tuple[str, ...] = (
        "same_model_direct",
        "serious_comparator",
        "relaylm_exact_rc",
    ),
) -> None:
    run.commit_participant(
        question_id="persona-0-q0",
        slot=slot,
        participant_identity={"slot": slot, "identity": f"identity-{slot}"},
        result=_participant_result(slot),
        request_evidence=({"slot": slot, "durable": True},),
        enabled_slots=enabled_slots,
    )


def test_scientific_spend_ledger_is_atomic_and_fresh_reuse_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "scientific-spend.json"
    ledger = ScientificSpendLedger.open(
        path=path,
        owner_id="owner-2957",
        campaign_fingerprint="sha256:" + "a" * 64,
        mode="fresh_run",
    )
    ledger.record_pre_call_barrier(payload={"SCIENTIFIC_SPEND": "UNSPENT"})
    assert ledger.state == "UNSPENT"
    assert json.loads(path.read_text())["state"] == "UNSPENT"
    ledger.consume_before_first_scientific_call()
    assert json.loads(path.read_text())["state"] == "CONSUMED"
    with pytest.raises(ExactResumeError, match="fresh scientific campaign"):
        ScientificSpendLedger.open(
            path=path,
            owner_id="owner-2957",
            campaign_fingerprint="sha256:" + "a" * 64,
            mode="fresh_run",
        )
    resumed = ScientificSpendLedger.open(
        path=path,
        owner_id="owner-2957",
        campaign_fingerprint="sha256:" + "a" * 64,
        mode="exact_infrastructure_resume",
    )
    assert resumed.state == "CONSUMED"


def test_participant_resume_after_a_then_c_failure_skips_a(tmp_path: Path) -> None:
    run = DurableQuestionRun.start(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    run.begin_question("persona-0-q0")
    _commit_participant(run, "same_model_direct")
    resumed = DurableQuestionRun.resume(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    assert resumed.completed_participant_slots("persona-0-q0") == (
        "same_model_direct",
    )
    _commit_participant(resumed, "serious_comparator")
    _commit_participant(resumed, "relaylm_exact_rc")
    resumed.commit_question(
        question_id="persona-0-q0",
        result={"participants": resumed.rebuild_participant_results("persona-0-q0")},
    )
    assert resumed.next_question().question_id == "persona-0-q1"


def test_participant_resume_after_a_and_c_then_d_failure_skips_both(
    tmp_path: Path,
) -> None:
    run = DurableQuestionRun.start(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    run.begin_question("persona-0-q0")
    _commit_participant(run, "same_model_direct")
    _commit_participant(run, "serious_comparator")
    resumed = DurableQuestionRun.resume(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    assert resumed.completed_participant_slots("persona-0-q0") == (
        "same_model_direct",
        "serious_comparator",
    )
    _commit_participant(resumed, "relaylm_exact_rc")
    assert resumed.completed_participant_slots("persona-0-q0") == (
        "same_model_direct",
        "serious_comparator",
        "relaylm_exact_rc",
    )


def test_process_stop_after_participant_fsync_before_question_commit_resumes_exactly(
    tmp_path: Path,
) -> None:
    run = DurableQuestionRun.start(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    run.begin_question("persona-0-q0")
    _commit_participant(run, "same_model_direct")
    resumed = DurableQuestionRun.resume(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    assert resumed.next_question().question_id == "persona-0-q0"
    assert resumed.participant_record(
        question_id="persona-0-q0", slot="same_model_direct"
    ) is not None
    _commit_participant(resumed, "serious_comparator")
    _commit_participant(resumed, "relaylm_exact_rc")
    resumed.commit_question(
        question_id="persona-0-q0",
        result={"participants": resumed.rebuild_participant_results("persona-0-q0")},
    )
    assert resumed.next_question().question_id == "persona-0-q1"


def test_completed_question_resume_rejects_duplicate_participant_completion(
    tmp_path: Path,
) -> None:
    run = DurableQuestionRun.start(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    run.begin_question("persona-0-q0")
    for slot in ("same_model_direct", "serious_comparator", "relaylm_exact_rc"):
        _commit_participant(run, slot)
    run.commit_question(
        question_id="persona-0-q0",
        result={"participants": run.rebuild_participant_results("persona-0-q0")},
    )
    resumed = DurableQuestionRun.resume(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    assert resumed.completed_participant_slots("persona-0-q0") == (
        "same_model_direct",
        "serious_comparator",
        "relaylm_exact_rc",
    )
    line = (tmp_path / "participant-observations.jsonl").read_text().splitlines()[0]
    with (tmp_path / "participant-observations.jsonl").open("a") as handle:
        handle.write(line + "\n")
    with pytest.raises(ExactResumeError, match="duplicate or conflicting"):
        DurableQuestionRun.resume(
            artifact_root=tmp_path,
            identity=identity(),
            questions=questions(),
        )


def test_torn_participant_tail_does_not_claim_completion(tmp_path: Path) -> None:
    run = DurableQuestionRun.start(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    run.begin_question("persona-0-q0")
    _commit_participant(run, "same_model_direct")
    observations = tmp_path / "participant-observations.jsonl"
    with observations.open("ab") as handle:
        handle.write(b'{"event":"torn-tail"')
    resumed = DurableQuestionRun.resume(
        artifact_root=tmp_path,
        identity=identity(),
        questions=questions(),
    )
    assert resumed.partial_tail_detected is True
    assert resumed.completed_participant_slots("persona-0-q0") == (
        "same_model_direct",
    )
