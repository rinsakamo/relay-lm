from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from test_v1_external_qualification_llama_cpp_campaign import _strict_descriptor_mapping
from tools.v1_external_qualification_campaign_proof import (
    CampaignProofError,
    prepare_static_proof,
    verify_zero_semantic_rehearsal,
)
from tools.v1_external_qualification_llama_cpp_campaign import CampaignDescriptor


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

    result = {
        "target": "v1:external-qualification-campaign",
        "status": "PRE_CALL_BARRIER_REACHED",
        "pre_call_barrier_reached": True,
        "SCIENTIFIC_SPEND": "UNSPENT",
        "llama_server_launch_count": 1,
        "exact_rc_server_launch_count": 0,
        "counters": counters,
        "campaign_fingerprint": CampaignDescriptor.from_mapping(plan).fingerprint,
        "cleanup": {
            "all_owned_processes_terminated": True,
            "external_processes_touched": 0,
            "errors": [],
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
            "server": None,
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
