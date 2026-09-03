from __future__ import annotations

import json
from dataclasses import replace

import pytest

from relaylm.actual_model_vllm_profiler import (
    VLLMKVAllocationDemand,
    VLLMTokenCapacityLaunchClass,
    VLLMTokenCapacityReferenceEvidence,
    VLLMTokenCapacityReferenceEvidenceError,
    load_vllm_token_capacity_reference_evidence,
    write_vllm_token_capacity_reference_evidence,
)


def _launch_class() -> VLLMTokenCapacityLaunchClass:
    return VLLMTokenCapacityLaunchClass(
        target_id="gemma-4-12b-it-qat-w4a16-google-vllm-v1",
        target_artifact_revision="a" * 40,
        target_digest="sha256:" + "b" * 64,
        backend_version="0.26.1rc1.dev549+g70b84f0bc",
        backend_source_revision="c" * 40,
        model_runner="v2",
        gpu_compute_capability_major=8,
        gpu_compute_capability_minor=6,
        gpu_total_memory_bytes=12_884_377_600,
    )


def _demands() -> tuple[VLLMKVAllocationDemand, ...]:
    return (
        VLLMKVAllocationDemand(
            multiplicity=5,
            tokens_per_block=16,
            fixed_blocks_per_request=1,
        ),
        VLLMKVAllocationDemand(
            multiplicity=1,
            tokens_per_block=64,
        ),
    )


def _evidence() -> VLLMTokenCapacityReferenceEvidence:
    return VLLMTokenCapacityReferenceEvidence.from_successful_launch(
        launch_class=_launch_class(),
        startup_free_bytes=11_800_000_000,
        kv_cache_memory_bytes=1_420_000_000,
        kv_cache_capacity_tokens=4_096,
        kv_pool_block_bytes=1_000_000,
        kv_allocation_demands=_demands(),
    )


def test_reference_evidence_round_trips_and_yields_compatible_reference(tmp_path) -> None:
    evidence = _evidence()

    path = write_vllm_token_capacity_reference_evidence(
        evidence=evidence,
        artifact_root=tmp_path,
    )
    loaded = load_vllm_token_capacity_reference_evidence(path)
    reference = loaded.require_compatible_reference(_launch_class())

    assert loaded == evidence
    assert path.name == f"{evidence.evidence_id}.json"
    assert evidence.format_version == 2
    assert reference.non_kv_memory_bytes == 10_380_000_000
    assert reference.kv_cache_memory_bytes == 1_420_000_000
    assert reference.kv_cache_capacity_tokens == 4_096
    assert reference.kv_pool_block_bytes == 1_000_000
    assert reference.kv_allocation_demands == _demands()


def test_reference_evidence_rejects_incompatible_launch_class() -> None:
    evidence = _evidence()
    incompatible = replace(
        _launch_class(),
        gpu_compute_capability_minor=9,
    )

    with pytest.raises(
        VLLMTokenCapacityReferenceEvidenceError,
        match="launch class",
    ):
        evidence.require_compatible_reference(incompatible)


def test_reference_evidence_rejects_impossible_allocation_geometry() -> None:
    with pytest.raises(ValueError, match="allocation geometry"):
        VLLMTokenCapacityReferenceEvidence.from_successful_launch(
            launch_class=_launch_class(),
            startup_free_bytes=11_800_000_000,
            kv_cache_memory_bytes=5_000_000,
            kv_cache_capacity_tokens=4_096,
            kv_pool_block_bytes=1_000_000,
            kv_allocation_demands=_demands(),
        )


def test_reference_evidence_id_is_independent_of_artifact_path(tmp_path) -> None:
    evidence = _evidence()
    first = write_vllm_token_capacity_reference_evidence(
        evidence=evidence,
        artifact_root=tmp_path / "first",
    )
    second = write_vllm_token_capacity_reference_evidence(
        evidence=evidence,
        artifact_root=tmp_path / "different" / "root",
    )

    assert first.name == second.name == f"{evidence.evidence_id}.json"


def test_equivalent_demand_order_and_duplicates_have_one_content_identity() -> None:
    canonical = _evidence()
    reordered = VLLMTokenCapacityReferenceEvidence.from_successful_launch(
        launch_class=_launch_class(),
        startup_free_bytes=11_800_000_000,
        kv_cache_memory_bytes=1_420_000_000,
        kv_cache_capacity_tokens=4_096,
        kv_pool_block_bytes=1_000_000,
        kv_allocation_demands=(
            VLLMKVAllocationDemand(multiplicity=1, tokens_per_block=64),
            VLLMKVAllocationDemand(
                multiplicity=2,
                tokens_per_block=16,
                fixed_blocks_per_request=1,
            ),
            VLLMKVAllocationDemand(
                multiplicity=3,
                tokens_per_block=16,
                fixed_blocks_per_request=1,
            ),
        ),
    )

    assert reordered.reference.kv_allocation_demands == _demands()
    assert reordered.evidence_id == canonical.evidence_id


def test_reference_evidence_rejects_tampered_content_id(tmp_path) -> None:
    evidence = _evidence()
    path = write_vllm_token_capacity_reference_evidence(
        evidence=evidence,
        artifact_root=tmp_path,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["successful_launch"]["kv_cache_capacity_tokens"] = 4_080
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        VLLMTokenCapacityReferenceEvidenceError,
        match="evidence_id",
    ):
        load_vllm_token_capacity_reference_evidence(path)


def test_reference_evidence_rejects_legacy_scalar_format(tmp_path) -> None:
    evidence = _evidence()
    payload = evidence.to_mapping()
    payload["format_version"] = 1
    path = tmp_path / f"{evidence.evidence_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        VLLMTokenCapacityReferenceEvidenceError,
        match="format_version",
    ):
        load_vllm_token_capacity_reference_evidence(path)
