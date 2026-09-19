from __future__ import annotations

import copy
from pathlib import Path

import pytest

from test_v1_external_qualification_llama_cpp_campaign import _strict_descriptor_mapping
from tools.v1_external_qualification_campaign_prepare import (
    prepare_scientific_owner_descriptor,
)
from tools.v1_external_qualification_llama_cpp_campaign import (
    CampaignCarriageError,
    CampaignDescriptor,
    HINDSIGHT_RETAIN_MAX_COMPLETION_TOKENS,
    HindsightLifecycleSpec,
    _campaign_contract,
    _hindsight_operational_fingerprint,
    _hindsight_owner_deployment_id,
)


def _inputs(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    stale = _strict_descriptor_mapping(tmp_path)
    lifecycle = copy.deepcopy(stale["hindsight_lifecycle"])
    assert isinstance(lifecycle, dict)
    lifecycle.pop("deployment_id")
    lifecycle.pop("database_profile")
    lifecycle.pop("retain_max_completion_tokens")
    return stale, lifecycle


def _authority(head: str = "9", tree: str = "8") -> dict[str, object]:
    return {
        "status": "CURRENT_AUTHORITY_CONFIRMED",
        "branch": "v1",
        "repository_head": head * 40,
        "repository_tree": tree * 40,
    }


def _prepare(
    tmp_path: Path,
    *,
    owner_id: str,
    stale: dict[str, object],
    lifecycle: dict[str, object],
):
    return prepare_scientific_owner_descriptor(
        owner_id=owner_id,
        owner_root=tmp_path / owner_id,
        execution_freeze=stale["execution_freeze"],
        axes=stale["axes"],
        llama_cpp=stale["llama_cpp"],
        relaylm_exact_rc=stale["relaylm_exact_rc"],
        hindsight_lifecycle_base=lifecycle,
        authority=_authority(),
    )


def test_prepare_derives_fresh_owner_identity_and_admits(tmp_path: Path) -> None:
    stale, lifecycle_base = _inputs(tmp_path)
    stale_owner = stale["owner_id"]
    assert isinstance(stale_owner, str)
    stale_lifecycle = stale["hindsight_lifecycle"]
    assert isinstance(stale_lifecycle, dict)
    stale_deployment = stale_lifecycle["deployment_id"]

    owner_id = "owner-2965-physical-proof"
    prepared = _prepare(
        tmp_path,
        owner_id=owner_id,
        stale=stale,
        lifecycle=lifecycle_base,
    )
    raw = prepared.to_mapping()
    admitted = CampaignDescriptor.from_mapping(raw)

    lifecycle = raw["hindsight_lifecycle"]
    health = raw["hindsight_health"]
    assert isinstance(lifecycle, dict)
    assert isinstance(health, dict)
    assert lifecycle["deployment_id"] == _hindsight_owner_deployment_id(owner_id)
    assert lifecycle["deployment_id"] != stale_deployment
    assert lifecycle["database_profile"] == owner_id
    assert lifecycle["database_profile"] != stale_owner
    assert (
        lifecycle["retain_max_completion_tokens"]
        == HINDSIGHT_RETAIN_MAX_COMPLETION_TOKENS
    )
    assert health["source_revision"] == lifecycle["source_revision"]
    assert health["version"] == lifecycle["runtime_version"]
    deployment = health["deployment"]
    assert isinstance(deployment, dict)
    assert deployment["deployment_id"] == lifecycle["deployment_id"]
    assert deployment["dependency_fingerprint"] == lifecycle["dependency_fingerprint"]
    assert admitted.owner_id == owner_id
    assert admitted.fingerprint == prepared.campaign_fingerprint
    assert prepared.descriptor_sha256
    assert not (tmp_path / owner_id).exists()


def test_prepare_rewrites_comparator_freeze_contract_and_authority(tmp_path: Path) -> None:
    stale, lifecycle_base = _inputs(tmp_path)
    owner_id = "owner-2965-contract-proof"
    prepared = _prepare(
        tmp_path,
        owner_id=owner_id,
        stale=stale,
        lifecycle=lifecycle_base,
    )
    raw = prepared.to_mapping()
    lifecycle = HindsightLifecycleSpec.from_mapping(raw["hindsight_lifecycle"])
    expected_deployment = _hindsight_operational_fingerprint(owner_id, lifecycle)

    axes = raw["axes"]
    assert isinstance(axes, list)
    execution_freeze = raw["execution_freeze"]
    assert isinstance(execution_freeze, dict)
    release_cases = execution_freeze["release_cases"]
    assert isinstance(release_cases, list)
    releases = {
        release["axis_id"]: release
        for release in release_cases
        if isinstance(release, dict)
    }
    admitted = CampaignDescriptor.from_mapping(raw)
    for axis in axes:
        assert isinstance(axis, dict)
        manifest = axis["manifest"]
        assert isinstance(manifest, dict)
        participants = manifest["participants"]
        assert isinstance(participants, list)
        comparator = next(
            item
            for item in participants
            if isinstance(item, dict) and item.get("slot") == "serious_comparator"
        )
        comparator_identity = comparator["identity"]
        assert isinstance(comparator_identity, dict)
        assert comparator_identity["deployment"] == expected_deployment
        identity = axis["identity"]
        assert isinstance(identity, dict)
        assert identity["authority"] == _authority()
        parsed_axis = next(
            candidate
            for candidate in admitted.axes
            if candidate.axis_id == axis["axis_id"]
        )
        assert identity["campaign_contract"] == _campaign_contract(parsed_axis)
        release = releases[axis["axis_id"]]
        assert release["manifest"] == axis["manifest"]
        assert release["case"] == axis["case"]
        assert release["benchmark_material"] == axis["benchmark_material"]
        assert release["history_material"] == axis["history_material"]


def test_prepare_accepts_preserved_hindsight_spelling_and_canonicalizes(
    tmp_path: Path,
) -> None:
    stale, lifecycle_base = _inputs(tmp_path)
    axes = stale["axes"]
    assert isinstance(axes, list)
    for axis in axes:
        assert isinstance(axis, dict)
        manifest = axis["manifest"]
        assert isinstance(manifest, dict)
        participants = manifest["participants"]
        assert isinstance(participants, list)
        comparator = next(
            item
            for item in participants
            if isinstance(item, dict) and item.get("slot") == "serious_comparator"
        )
        identity = comparator["identity"]
        assert isinstance(identity, dict)
        identity["implementation"] = "Hindsight"

    execution_freeze = stale["execution_freeze"]
    assert isinstance(execution_freeze, dict)
    freeze_comparator = execution_freeze["comparator"]
    assert isinstance(freeze_comparator, dict)
    freeze_comparator["implementation"] = "Hindsight"

    prepared = _prepare(
        tmp_path,
        owner_id="owner-2965-preserved-source-spelling",
        stale=stale,
        lifecycle=lifecycle_base,
    )
    raw = prepared.to_mapping()
    CampaignDescriptor.from_mapping(raw)

    prepared_axes = raw["axes"]
    assert isinstance(prepared_axes, list)
    for axis in prepared_axes:
        assert isinstance(axis, dict)
        manifest = axis["manifest"]
        assert isinstance(manifest, dict)
        participants = manifest["participants"]
        assert isinstance(participants, list)
        comparator = next(
            item
            for item in participants
            if isinstance(item, dict) and item.get("slot") == "serious_comparator"
        )
        identity = comparator["identity"]
        assert isinstance(identity, dict)
        assert identity["implementation"] == "hindsight"

    prepared_freeze = raw["execution_freeze"]
    assert isinstance(prepared_freeze, dict)
    prepared_comparator = prepared_freeze["comparator"]
    assert isinstance(prepared_comparator, dict)
    assert prepared_comparator["implementation"] == "hindsight"


def test_prepare_rejects_unknown_hindsight_template_spelling(tmp_path: Path) -> None:
    stale, lifecycle_base = _inputs(tmp_path)
    axes = stale["axes"]
    assert isinstance(axes, list)
    first_axis = axes[0]
    assert isinstance(first_axis, dict)
    manifest = first_axis["manifest"]
    assert isinstance(manifest, dict)
    participants = manifest["participants"]
    assert isinstance(participants, list)
    comparator = next(
        item
        for item in participants
        if isinstance(item, dict) and item.get("slot") == "serious_comparator"
    )
    identity = comparator["identity"]
    assert isinstance(identity, dict)
    identity["implementation"] = "HINDSIGHT"

    with pytest.raises(CampaignCarriageError, match="serious comparator must be Hindsight"):
        _prepare(
            tmp_path,
            owner_id="owner-2965-reject-unknown-spelling",
            stale=stale,
            lifecycle=lifecycle_base,
        )


def test_prepare_forbids_owner_local_lifecycle_carry_over(tmp_path: Path) -> None:
    stale, lifecycle_base = _inputs(tmp_path)
    stale_lifecycle = stale["hindsight_lifecycle"]
    assert isinstance(stale_lifecycle, dict)
    lifecycle_base["deployment_id"] = stale_lifecycle["deployment_id"]
    lifecycle_base["database_profile"] = stale_lifecycle["database_profile"]

    with pytest.raises(CampaignCarriageError, match="must omit owner-local fields"):
        _prepare(
            tmp_path,
            owner_id="owner-2965-reject-stale",
            stale=stale,
            lifecycle=lifecycle_base,
        )


def test_prepare_forbids_caller_owned_hindsight_retain_bound(tmp_path: Path) -> None:
    stale, lifecycle_base = _inputs(tmp_path)
    lifecycle_base["retain_max_completion_tokens"] = 8191

    with pytest.raises(CampaignCarriageError, match="must omit owner-local fields"):
        _prepare(
            tmp_path,
            owner_id="owner-2994-reject-retain-bound",
            stale=stale,
            lifecycle=lifecycle_base,
        )


def test_prepare_derives_owner_local_artifact_and_spend_roots(tmp_path: Path) -> None:
    stale, lifecycle_base = _inputs(tmp_path)
    owner_id = "owner-2965-roots-proof"
    prepared = _prepare(
        tmp_path,
        owner_id=owner_id,
        stale=stale,
        lifecycle=lifecycle_base,
    )
    raw = prepared.to_mapping()
    owner_root = tmp_path / owner_id
    assert raw["artifact_root"] == str(owner_root / "campaign-artifacts")
    assert raw["spend_ledger_path"] == str(owner_root / "scientific-spend.json")
    assert not owner_root.exists()

    wrong_root = tmp_path / "some-other-owner"
    with pytest.raises(CampaignCarriageError, match="leaf must equal owner_id"):
        prepare_scientific_owner_descriptor(
            owner_id=owner_id,
            owner_root=wrong_root,
            execution_freeze=stale["execution_freeze"],
            axes=stale["axes"],
            llama_cpp=stale["llama_cpp"],
            relaylm_exact_rc=stale["relaylm_exact_rc"],
            hindsight_lifecycle_base=lifecycle_base,
            authority=_authority(),
        )


def test_prepare_owner_change_changes_descriptor_and_campaign_fingerprint(tmp_path: Path) -> None:
    stale, lifecycle_base = _inputs(tmp_path)
    first = _prepare(
        tmp_path,
        owner_id="owner-2965-fingerprint-a",
        stale=stale,
        lifecycle=lifecycle_base,
    )
    second = _prepare(
        tmp_path,
        owner_id="owner-2965-fingerprint-b",
        stale=stale,
        lifecycle=lifecycle_base,
    )

    assert first.descriptor_sha256 != second.descriptor_sha256
    assert first.campaign_fingerprint != second.campaign_fingerprint


def test_prepare_is_zero_semantic_and_leaves_spend_unspent(tmp_path: Path) -> None:
    stale, lifecycle_base = _inputs(tmp_path)
    owner_id = "owner-2965-zero-semantic"
    prepared = _prepare(
        tmp_path,
        owner_id=owner_id,
        stale=stale,
        lifecycle=lifecycle_base,
    )
    raw = prepared.to_mapping()
    health = raw["hindsight_health"]
    assert isinstance(health, dict)
    assert health["semantic_operations_called"] == []
    assert health["semantic_generation_count"] == 0
    assert health["benchmark_question_count"] == 0
    assert health["answer_model_generation_count"] == 0
    assert health["judge_call_count"] == 0
    assert not Path(raw["spend_ledger_path"]).exists()
    assert not Path(raw["artifact_root"]).exists()
