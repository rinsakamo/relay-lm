from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import tools.v1_external_qualification_campaign_proof as campaign_proof
from test_v1_external_qualification_llama_cpp_campaign import _strict_descriptor_mapping
from tools.external_qualification import LiveLaunchAdmissionAttestation
from tools.v1_external_qualification_campaign_proof import (
    CampaignProofError,
    prepare_static_proof,
    verify_zero_semantic_rehearsal,
)
from tools.v1_external_qualification_llama_cpp_campaign import (
    CampaignCarriageError,
    CampaignDescriptor,
    HINDSIGHT_FAIL_ON_EXTRACTION_ERRORS,
    HINDSIGHT_RETAIN_MAX_COMPLETION_TOKENS,
)


def _write_source(tmp_path: Path, *, implementation: str = "Hindsight") -> tuple[Path, str]:
    raw = _strict_descriptor_mapping(tmp_path)
    freeze = raw["execution_freeze"]
    assert isinstance(freeze, dict)
    comparator = freeze["comparator"]
    assert isinstance(comparator, dict)
    comparator["implementation"] = implementation

    axes = raw["axes"]
    assert isinstance(axes, list)
    for axis in axes:
        assert isinstance(axis, dict)
        manifest = axis["manifest"]
        assert isinstance(manifest, dict)
        participants = manifest["participants"]
        assert isinstance(participants, list)
        serious = next(
            participant
            for participant in participants
            if isinstance(participant, dict)
            and participant.get("slot") == "serious_comparator"
        )
        identity = serious["identity"]
        assert isinstance(identity, dict)
        identity["implementation"] = implementation

    path = tmp_path / "preserved-source.json"
    path.write_text(json.dumps(raw, sort_keys=True) + "\n", encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _write_source_with_axis_case_mismatch(
    tmp_path: Path,
    *,
    substantive: bool = False,
) -> tuple[Path, str]:
    source, _ = _write_source(tmp_path)
    raw = json.loads(source.read_text(encoding="utf-8"))

    axes = raw["axes"]
    freeze = raw["execution_freeze"]
    assert isinstance(axes, list)
    assert isinstance(freeze, dict)
    release_cases = freeze["release_cases"]
    assert isinstance(release_cases, list)

    axis = axes[0]
    assert isinstance(axis, dict)
    axis_id = axis["axis_id"]
    assert isinstance(axis_id, str)
    release = next(
        item
        for item in release_cases
        if isinstance(item, dict) and item.get("axis_id") == axis_id
    )
    assert isinstance(release, dict)
    frozen_case = release["case"]
    assert isinstance(frozen_case, dict)
    release["case"] = copy.deepcopy(frozen_case)

    axis_case = axis["case"]
    assert isinstance(axis_case, dict)
    if substantive:
        benchmark = axis_case["benchmark"]
        assert isinstance(benchmark, dict)
        benchmark["revision"] = "e" * 40
    else:
        axis_case["adapter_case_ref"] = str(axis_case["adapter_case_ref"]) + "-historical"

    source.write_text(json.dumps(raw, sort_keys=True) + "\n", encoding="utf-8")
    return source, hashlib.sha256(source.read_bytes()).hexdigest()


def _write_source_with_material_mismatch(
    tmp_path: Path,
    *,
    mismatch: str,
) -> tuple[Path, str, Path]:
    source, _ = _write_source(tmp_path)
    raw = json.loads(source.read_text(encoding="utf-8"))

    axes = raw["axes"]
    freeze = raw["execution_freeze"]
    assert isinstance(axes, list)
    assert isinstance(freeze, dict)
    release_cases = freeze["release_cases"]
    assert isinstance(release_cases, list)

    axis = axes[0]
    assert isinstance(axis, dict)
    axis_id = axis["axis_id"]
    assert isinstance(axis_id, str)
    release = next(
        item
        for item in release_cases
        if isinstance(item, dict) and item.get("axis_id") == axis_id
    )
    assert isinstance(release, dict)

    axis_case = axis["case"]
    release_case = release["case"]
    assert isinstance(axis_case, dict)
    assert isinstance(release_case, dict)
    release["case"] = copy.deepcopy(release_case)
    axis_case["adapter_case_ref"] = str(axis_case["adapter_case_ref"]) + "-historical"

    axis_material = axis["benchmark_material"]
    release_material = release["benchmark_material"]
    assert isinstance(axis_material, dict)
    assert isinstance(release_material, dict)
    release["benchmark_material"] = copy.deepcopy(release_material)
    release_material = release["benchmark_material"]
    assert isinstance(release_material, dict)

    material_path = Path(str(axis_material["path"]))
    assert material_path.is_file()

    if mismatch == "dependent":
        axis_material["case_fingerprint"] = "sha256:" + "1" * 64
        axis_material["question_fingerprints"] = [
            "sha256:" + "2" * 64
            for _ in axis_material["question_fingerprints"]
        ]
    elif mismatch == "path":
        release_material["path"] = str(material_path.with_name("other-material.json"))
    elif mismatch == "sha":
        release_material["sha256"] = "3" * 64
    elif mismatch == "bytes":
        material_path.write_bytes(material_path.read_bytes() + b"\n")
    else:
        raise AssertionError(f"unsupported mismatch {mismatch!r}")

    source.write_text(json.dumps(raw, sort_keys=True) + "\n", encoding="utf-8")
    return source, hashlib.sha256(source.read_bytes()).hexdigest(), material_path


def _prepare(tmp_path: Path) -> tuple[dict[str, object], Path, Path, str]:
    source, source_sha = _write_source(tmp_path)
    plan_path = tmp_path / "fresh-plan.json"
    owner_id = "owner-proof-harness"
    receipt = prepare_static_proof(
        repo_root=tmp_path,
        source_path=source,
        source_sha256=source_sha,
        plan_path=plan_path,
        owner_root=tmp_path / owner_id,
        owner_id=owner_id,
        repository_head="a" * 40,
        repository_tree="b" * 40,
    )
    return receipt, source, plan_path, owner_id


def test_prepare_static_proof_rederives_hindsight_retain_bound_from_repository(
    tmp_path: Path,
) -> None:
    source, _source_sha = _write_source(tmp_path)
    raw = json.loads(source.read_text(encoding="utf-8"))
    raw["hindsight_lifecycle"]["retain_max_completion_tokens"] = 8191
    raw["hindsight_lifecycle"]["fail_on_extraction_errors"] = False
    source.write_text(json.dumps(raw, sort_keys=True) + "\n", encoding="utf-8")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    owner_id = "owner-2994-proof-retain-bound"
    plan_path = tmp_path / "fresh-retain-bound-plan.json"

    receipt = prepare_static_proof(
        repo_root=tmp_path,
        source_path=source,
        source_sha256=source_sha,
        plan_path=plan_path,
        owner_root=tmp_path / owner_id,
        owner_id=owner_id,
        repository_head="a" * 40,
        repository_tree="b" * 40,
    )

    assert receipt["status"] == "FRESH_OWNER_STATIC_PROOF_PASS"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert (
        plan["hindsight_lifecycle"]["retain_max_completion_tokens"]
        == HINDSIGHT_RETAIN_MAX_COMPLETION_TOKENS
    )
    assert (
        plan["hindsight_lifecycle"]["fail_on_extraction_errors"]
        is HINDSIGHT_FAIL_ON_EXTRACTION_ERRORS
    )


def test_prepare_static_proof_can_materialize_history_in_one_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, source_sha = _write_source(tmp_path)
    owner_id = "owner-proof-one-shot-history"
    plan_path = tmp_path / "fresh-one-shot-plan.json"
    memconflict_source = tmp_path / "Step4_4.jsonl"
    longmemeval_source = tmp_path / "longmemeval_s_cleaned.json"
    memconflict_source.write_text("synthetic-memconflict", encoding="utf-8")
    longmemeval_source.write_text("synthetic-longmemeval", encoding="utf-8")
    calls: list[dict[str, object]] = []

    def fake_materialize(
        *,
        axes,
        memconflict_source,
        longmemeval_source,
        output_root,
    ):
        calls.append(
            {
                "axes": copy.deepcopy(list(axes)),
                "memconflict_source": memconflict_source,
                "longmemeval_source": longmemeval_source,
                "output_root": output_root,
            }
        )
        return (
            copy.deepcopy(list(axes)),
            {
                "status": "HISTORY_MATERIAL_PREPARED",
                "semantic_generation_count": 0,
                "benchmark_question_execution_count": 0,
                "axes": [
                    {"axis_id": "axis-a"},
                    {"axis_id": "axis-b"},
                ],
            },
        )

    monkeypatch.setattr(
        campaign_proof,
        "materialize_bounded_history_axes",
        fake_materialize,
    )

    receipt = prepare_static_proof(
        repo_root=tmp_path,
        source_path=source,
        source_sha256=source_sha,
        plan_path=plan_path,
        owner_root=tmp_path / owner_id,
        owner_id=owner_id,
        repository_head="a" * 40,
        repository_tree="b" * 40,
        memconflict_source=memconflict_source,
        longmemeval_source=longmemeval_source,
    )

    assert receipt["status"] == "FRESH_OWNER_STATIC_PROOF_PASS"
    history_receipt = receipt["history_materialization"]
    assert isinstance(history_receipt, dict)
    assert history_receipt["status"] == "HISTORY_MATERIAL_PREPARED"
    assert history_receipt["semantic_generation_count"] == 0
    assert history_receipt["benchmark_question_execution_count"] == 0
    assert len(calls) == 1
    assert calls[0]["memconflict_source"] == memconflict_source
    assert calls[0]["longmemeval_source"] == longmemeval_source
    assert calls[0]["output_root"] == (
        plan_path.parent / f"{plan_path.stem}-history"
    )
    CampaignDescriptor.from_mapping(
        json.loads(plan_path.read_text(encoding="utf-8"))
    )


def test_prepare_static_proof_requires_benchmark_sources_as_a_pair(
    tmp_path: Path,
) -> None:
    source, source_sha = _write_source(tmp_path)
    owner_id = "owner-proof-incomplete-history-input"

    with pytest.raises(
        CampaignProofError,
        match="MemConflict and LongMemEval sources must be supplied together",
    ):
        prepare_static_proof(
            repo_root=tmp_path,
            source_path=source,
            source_sha256=source_sha,
            plan_path=tmp_path / "should-not-exist-history-plan.json",
            owner_root=tmp_path / owner_id,
            owner_id=owner_id,
            repository_head="a" * 40,
            repository_tree="b" * 40,
            memconflict_source=tmp_path / "only-memconflict.jsonl",
        )


def test_prepare_static_proof_canonicalizes_historical_hindsight(tmp_path: Path) -> None:
    receipt, _, plan_path, owner_id = _prepare(tmp_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    assert receipt["status"] == "FRESH_OWNER_STATIC_PROOF_PASS"
    assert receipt["source_comparator_implementation"] == "Hindsight"
    assert receipt["prepared_comparator_implementation"] == "hindsight"
    assert receipt["stale_lifecycle_substitution"] == "REJECTED"
    assert receipt["mutually_stale_owner_identity"] == "REJECTED"
    assert receipt["SCIENTIFIC_SPEND"] == "UNSPENT"

    assert plan["owner_id"] == owner_id
    assert plan["execution_freeze"]["comparator"]["implementation"] == "hindsight"
    for axis in plan["axes"]:
        serious = next(
            participant
            for participant in axis["manifest"]["participants"]
            if participant["slot"] == "serious_comparator"
        )
        assert serious["identity"]["implementation"] == "hindsight"

    admitted = CampaignDescriptor.from_mapping(plan)
    assert admitted.fingerprint == receipt["campaign_fingerprint"]


def test_prepare_static_proof_derives_release_case_from_axis_and_ignores_stale_duplicate(
    tmp_path: Path,
) -> None:
    source, source_sha = _write_source_with_axis_case_mismatch(tmp_path)
    owner_id = "owner-proof-derived-release-case"
    plan_path = tmp_path / "fresh-derived-release-case.json"

    receipt = prepare_static_proof(
        repo_root=tmp_path,
        source_path=source,
        source_sha256=source_sha,
        plan_path=plan_path,
        owner_root=tmp_path / owner_id,
        owner_id=owner_id,
        repository_head="a" * 40,
        repository_tree="b" * 40,
    )

    assert receipt["status"] == "FRESH_OWNER_STATIC_PROOF_PASS"
    compatibility = receipt["preserved_case_compatibility"]
    assert isinstance(compatibility, dict)
    assert compatibility["status"] == "NOT_REQUIRED"

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    prepared_axis = plan["axes"][0]
    release = next(
        item
        for item in plan["execution_freeze"]["release_cases"]
        if item["axis_id"] == prepared_axis["axis_id"]
    )
    assert prepared_axis["case"] == release["case"]
    assert prepared_axis["benchmark_material"] == release["benchmark_material"]
    CampaignDescriptor.from_mapping(plan)


@pytest.mark.parametrize("mismatch", ("dependent", "path", "sha"))
def test_prepare_static_proof_ignores_stale_release_material_duplicate(
    tmp_path: Path,
    mismatch: str,
) -> None:
    source, source_sha, _ = _write_source_with_material_mismatch(
        tmp_path,
        mismatch=mismatch,
    )
    owner_id = f"owner-proof-derived-material-{mismatch}"
    plan_path = tmp_path / f"fresh-derived-material-{mismatch}.json"

    receipt = prepare_static_proof(
        repo_root=tmp_path,
        source_path=source,
        source_sha256=source_sha,
        plan_path=plan_path,
        owner_root=tmp_path / owner_id,
        owner_id=owner_id,
        repository_head="a" * 40,
        repository_tree="b" * 40,
    )
    assert receipt["status"] == "FRESH_OWNER_STATIC_PROOF_PASS"

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    prepared_axis = plan["axes"][0]
    release = next(
        item
        for item in plan["execution_freeze"]["release_cases"]
        if item["axis_id"] == prepared_axis["axis_id"]
    )
    assert prepared_axis["benchmark_material"] == release["benchmark_material"]
    CampaignDescriptor.from_mapping(plan)


def test_prepare_static_proof_still_rejects_material_byte_drift(
    tmp_path: Path,
) -> None:
    source, source_sha, _ = _write_source_with_material_mismatch(
        tmp_path,
        mismatch="bytes",
    )
    owner_id = "owner-proof-material-bytes-reject"

    with pytest.raises(CampaignCarriageError, match="content drifted"):
        prepare_static_proof(
            repo_root=tmp_path,
            source_path=source,
            source_sha256=source_sha,
            plan_path=tmp_path / "should-not-exist-material-bytes.json",
            owner_root=tmp_path / owner_id,
            owner_id=owner_id,
            repository_head="a" * 40,
            repository_tree="b" * 40,
        )


def test_prepare_static_proof_rejects_unknown_hindsight_spelling(tmp_path: Path) -> None:
    source, source_sha = _write_source(tmp_path, implementation="HINDSIGHT")
    owner_id = "owner-proof-reject"

    with pytest.raises(CampaignProofError, match="not recognized Hindsight"):
        prepare_static_proof(
            repo_root=tmp_path,
            source_path=source,
            source_sha256=source_sha,
            plan_path=tmp_path / "should-not-exist.json",
            owner_root=tmp_path / owner_id,
            owner_id=owner_id,
            repository_head="a" * 40,
            repository_tree="b" * 40,
        )


def _runtime_identity(plan: dict[str, object], owner_id: str) -> dict[str, object]:
    lifecycle = plan["hindsight_lifecycle"]
    assert isinstance(lifecycle, dict)
    keys = (
        "deployment_id",
        "source_revision",
        "source_tree",
        "dependency_fingerprint",
        "llm_model",
        "llm_base_url",
        "retain_max_completion_tokens",
        "fail_on_extraction_errors",
        "embeddings_provider",
        "reranker_provider",
        "embeddings_onnx_model_sha256",
        "embeddings_onnx_tokenizer_tree_sha256",
        "package_wheel_sha256",
        "embeddings_onnx_model_path",
        "embeddings_onnx_tokenizer_path",
    )
    result = {key: copy.deepcopy(lifecycle[key]) for key in keys}
    result["version"] = str(lifecycle["runtime_version"]).lstrip("v")
    result["database_profile"] = owner_id
    return result


def _physical_bundle(
    tmp_path: Path,
    *,
    plan_path: Path,
    owner_id: str,
    bad_counter: bool = False,
) -> tuple[Path, Path]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    lifecycle = plan["hindsight_lifecycle"]
    assert isinstance(lifecycle, dict)

    runtime_identity_path = tmp_path / "runtime-identity.json"
    runtime_identity_path.write_text(
        json.dumps(_runtime_identity(plan, owner_id), sort_keys=True) + "\n",
        encoding="utf-8",
    )

    queue_path = tmp_path / "queue.json"
    queue_path.write_text(
        json.dumps(
            {
                "state": "CHILD_EXITED",
                "child_exit_code": 0,
                "lease_state": "RELEASED",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    counters = {
        "semantic_generation_count": 0,
        "benchmark_question_count": 0,
        "answer_model_generation_count": 0,
        "judge_call_count": 0,
        "scientific_durable_run_completion_count": 0,
    }
    if bad_counter:
        counters["judge_call_count"] = 1

    axes = plan["axes"]
    assert isinstance(axes, list) and axes
    first_axis = axes[0]
    assert isinstance(first_axis, dict)
    identity = first_axis["identity"]
    assert isinstance(identity, dict)
    live_mapping = identity["launch_admission"]
    assert isinstance(live_mapping, dict)
    live_attestation = LiveLaunchAdmissionAttestation.from_mapping(live_mapping)

    result = {
        "target": "v1:external-qualification-campaign",
        "status": "PRE_CALL_BARRIER_REACHED",
        "pre_call_barrier_reached": True,
        "SCIENTIFIC_SPEND": "UNSPENT",
        "llama_server_launch_count": 1,
        "exact_rc_adapter_launch_count": 0,
        "exact_rc_adapter_query_count": 0,
        "counters": counters,
        "campaign_fingerprint": CampaignDescriptor.from_mapping(plan).fingerprint,
        "cleanup": {
            "all_owned_processes_terminated": True,
            "external_processes_touched": 0,
            "errors": [],
        },
        "observed_execution": {
            "authority": "OBSERVED_EXECUTION",
            "live_launch_attestation": live_attestation.to_mapping(),
            "live_launch_attestation_fingerprint": live_attestation.fingerprint,
            "hindsight_runtime_identity_path": str(runtime_identity_path),
            "artifact_root": str(plan["artifact_root"]),
            "spend_ledger_path": str(plan["spend_ledger_path"]),
            "axis_evidence_paths": {
                str(axis["axis_id"]): None
                for axis in axes
                if isinstance(axis, dict)
            },
        },
        "hindsight_cleanup": {
            "started": True,
            "start_count": 1,
            "health_count": 1,
            "semantic_operation_count": 0,
            "cleanup_count": 1,
            "deployment_id": lifecycle["deployment_id"],
            "all_owned_processes_terminated": True,
            "external_processes_touched": 0,
            "errors": [],
            "runtime_identity_path": str(runtime_identity_path),
        },
        "exact_rc_cleanup": {
            "removed": True,
            "errors": [],
            "adapter": None,
        },
    }
    stdout_path = tmp_path / "stdout.log"
    stdout_path.write_text(
        "non-json diagnostic line\n" + json.dumps(result, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return queue_path, stdout_path


def test_verify_zero_semantic_rehearsal_accepts_clean_bundle(tmp_path: Path) -> None:
    _, source, plan_path, owner_id = _prepare(tmp_path)
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    queue_path, stdout_path = _physical_bundle(
        tmp_path,
        plan_path=plan_path,
        owner_id=owner_id,
    )

    receipt = verify_zero_semantic_rehearsal(
        plan_path=plan_path,
        queue_path=queue_path,
        stdout_path=stdout_path,
        owner_id=owner_id,
        source_path=source,
        source_sha256=source_sha,
        check_ports=False,
    )

    assert receipt["status"] == "ZERO_SEMANTIC_PHYSICAL_PROOF_PASS"
    assert receipt["scientific_spend"] == "UNSPENT"
    assert receipt["queue_state"] == "CHILD_EXITED"
    assert receipt["lease_state"] == "RELEASED"
    assert receipt["descriptor_sha256"] == hashlib.sha256(plan_path.read_bytes()).hexdigest()
    assert receipt["observed_live_launch_fingerprint"]


def test_verify_zero_semantic_rehearsal_rejects_nonzero_counter(tmp_path: Path) -> None:
    _, _, plan_path, owner_id = _prepare(tmp_path)
    queue_path, stdout_path = _physical_bundle(
        tmp_path,
        plan_path=plan_path,
        owner_id=owner_id,
        bad_counter=True,
    )

    with pytest.raises(CampaignProofError, match="counters were not all zero"):
        verify_zero_semantic_rehearsal(
            plan_path=plan_path,
            queue_path=queue_path,
            stdout_path=stdout_path,
            owner_id=owner_id,
            check_ports=False,
        )
