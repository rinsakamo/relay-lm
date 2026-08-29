from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tools.external_qualification import (
    ExternalQualificationError,
    run_case,
    stable_run_id,
    validate_manifest,
    validate_release_identity,
    write_evidence,
)


def identity(*, version: str = "system-v1", revision: str = "b" * 40, model: str = "gemma") -> dict[str, object]:
    return {
        "implementation": "synthetic-system",
        "source_revision": revision,
        "version": version,
        "deployment": "local-process",
        "license": "Apache-2.0",
        "physical_model": {"artifact": model, "tokenizer": "tokenizer-v1", "quantization": "Q4"},
        "provider": "openai-compatible",
        "backend": "vllm",
        "runtime": "synthetic-runtime",
        "context_capacity": 8192,
        "decoding": {"temperature": "0"},
        "reasoning": {"effort": "off"},
        "hardware": {"gpu": "RTX 3060", "cpu": "i5-12400", "offload": "none"},
        "retry_policy": "no retry",
        "matched_condition_differences": [],
    }


def participant(slot: str, *, enabled: bool = True, version: str = "system-v1", revision: str = "b" * 40) -> dict[str, object]:
    return {
        "slot": slot,
        "identity": identity(version=version, revision=revision) if enabled else None,
        "omission_reason": None if enabled else "not scientifically meaningful for this benchmark",
    }


def manifest(*, purpose: str = "dry_run", simple_enabled: bool = True) -> dict[str, object]:
    return {
        "format_version": 1,
        "purpose": purpose,
        "harness": {"identity": "rinsakamo/relay-lm", "revision": "a" * 40},
        "adapter": {"identity": "synthetic-adapter", "revision": "c" * 40},
        "participants": [
            participant("same_model_direct"),
            participant("simple_baseline", enabled=simple_enabled),
            participant("serious_comparator"),
            participant("relaylm_exact_rc", version="synthetic-relaylm"),
        ],
        "relaylm_release": None,
        "judge": None,
        "replicate_id": "0",
    }


def case(axis: str, case_id: str) -> dict[str, object]:
    return {
        "case_id": case_id,
        "axis": axis,
        "benchmark": {
            "id": "synthetic-benchmark",
            "repository": "https://example.test/benchmark.git",
            "revision": "benchmark-revision-1",
            "license": "MIT",
        },
        "dataset": {"revision": "dataset-revision-1", "license": "CC-BY-4.0"},
        "adapter_case_ref": f"cases/{case_id}.json",
    }


def observation(score: float = 1.0) -> dict[str, object]:
    return {
        "quality": {"accuracy": score},
        "tokens": {"model_input_tokens": 100, "model_output_tokens": 20, "model_call_count": 2},
        "latency": {"ttft_ms": 12.0, "query_latency_ms": 50.0, "end_to_end_ms": 75.0},
        "resources": {
            "peak_gpu_memory_bytes": 1000,
            "peak_cpu_memory_bytes": 2000,
            "persistent_storage_bytes": 3000,
            "notes": ["synthetic measurement"],
        },
        "known_limitations": ["synthetic dry-run only"],
        "failure": None,
    }


def executors(raw_manifest: dict[str, object]):
    return {
        item["slot"]: (lambda benchmark_case, system_identity: observation())
        for item in raw_manifest["participants"]
        if item["identity"] is not None
    }


def release_identity() -> dict[str, object]:
    return {
        "schema_version": 1,
        "package": "relaylm",
        "version": "1.0.0rc1",
        "release_kind": "rc",
        "tag": "v1.0.0rc1",
        "commit": "d" * 40,
        "artifacts": [
            {"filename": "relaylm-1.0.0rc1-py3-none-any.whl", "sha256": "1" * 64},
            {"filename": "relaylm-1.0.0rc1.tar.gz", "sha256": "2" * 64},
        ],
    }


def test_dry_run_represents_two_distinct_axes_and_separate_measurement_groups() -> None:
    raw_manifest = manifest()
    first = run_case(
        manifest=raw_manifest,
        case=case("conflict_update_temporal_validity", "conflict-1"),
        classification="reproducible_competitive_result",
        executors=executors(raw_manifest),
    )
    second = run_case(
        manifest=raw_manifest,
        case=case("personalization_accurate_retrieval", "persona-1"),
        classification="comparison_condition_mismatch",
        executors=executors(raw_manifest),
    )
    assert first["run_id"] != second["run_id"]
    measured = first["results"][0]["observation"]
    assert first["manifest"]["citable"] is False
    assert measured["quality"] == {"accuracy": 1.0}
    assert measured["tokens"]["model_call_count"] == 2
    assert measured["latency"]["ttft_ms"] == 12.0
    assert measured["resources"]["peak_gpu_memory_bytes"] == 1000


def test_simple_baseline_can_be_omitted_with_reason() -> None:
    raw_manifest = manifest(simple_enabled=False)
    evidence = run_case(
        manifest=raw_manifest,
        case=case("conflict_update_temporal_validity", "conflict-1"),
        classification="reproducible_competitive_result",
        executors=executors(raw_manifest),
    )
    assert evidence["results"][1]["observation"] is None
    assert "not scientifically meaningful" in evidence["results"][1]["omission_reason"]


def test_release_qualification_is_blocked_until_exact_release_identity_exists() -> None:
    raw = manifest(purpose="release_qualification")
    with pytest.raises(ExternalQualificationError, match="blocked until exact #1447"):
        validate_manifest(raw)


def test_exact_release_identity_binds_relaylm_slot_and_same_model_baseline() -> None:
    raw = manifest(purpose="release_qualification", simple_enabled=False)
    raw["relaylm_release"] = release_identity()
    raw["judge"] = {"identity": "judge@revision", "policy": "benchmark-native deterministic judge"}
    raw["participants"][3] = participant("relaylm_exact_rc", version="1.0.0rc1", revision="d" * 40)
    normalized = validate_manifest(raw)
    assert normalized["citable"] is True
    assert normalized["relaylm_release"]["commit"] == "d" * 40

    mismatched = deepcopy(raw)
    mismatched["participants"][0]["identity"]["physical_model"]["artifact"] = "different-model"
    with pytest.raises(ExternalQualificationError, match="same_model_direct must match"):
        validate_manifest(mismatched)


def test_prequalification_smoke_cannot_carry_citable_release_identity() -> None:
    raw = manifest(purpose="prequalification_smoke")
    raw["relaylm_release"] = release_identity()
    with pytest.raises(ExternalQualificationError, match="must not carry"):
        validate_manifest(raw)


@pytest.mark.parametrize(
    "classification",
    [
        "reproducible_competitive_result",
        "specialist_deferred_capability_loss",
        "generalizable_core_defect_candidate",
        "benchmark_adapter_mismatch",
        "non_reproducible_workload",
        "resource_impracticality",
        "comparison_condition_mismatch",
    ],
)
def test_all_release_reconciliation_classifications_are_serializable(classification: str) -> None:
    raw_manifest = manifest()
    evidence = run_case(
        manifest=raw_manifest,
        case=case("conflict_update_temporal_validity", classification),
        classification=classification,
        executors=executors(raw_manifest),
    )
    assert evidence["classification"] == classification


def test_failure_detail_preserves_partial_measurements() -> None:
    raw_manifest = manifest()
    failed = observation()
    failed["quality"] = {}
    failed["tokens"] = {"model_input_tokens": 512, "model_output_tokens": 0, "model_call_count": 1}
    failed["failure"] = "provider_timeout_after_first_call"
    run = run_case(
        manifest=raw_manifest,
        case=case("conflict_update_temporal_validity", "failed-1"),
        classification="non_reproducible_workload",
        executors={slot: (lambda benchmark_case, system_identity, result=failed: result) for slot in ("same_model_direct", "simple_baseline", "serious_comparator", "relaylm_exact_rc")},
    )
    result = run["results"][0]["observation"]
    assert result["failure"] == "provider_timeout_after_first_call"
    assert result["tokens"]["model_call_count"] == 1


def test_release_manifest_reuse_rejects_development_identity() -> None:
    raw = release_identity()
    raw["version"] = "1.0.0.dev0"
    raw["release_kind"] = "dev"
    raw["tag"] = None
    with pytest.raises(ExternalQualificationError, match="requires an rc or final"):
        validate_release_identity(raw)


def test_stable_run_id_and_immutable_write_are_deterministic(tmp_path: Path) -> None:
    raw_manifest = manifest()
    raw_case = case("conflict_update_temporal_validity", "conflict-1")
    evidence = run_case(
        manifest=raw_manifest,
        case=raw_case,
        classification="reproducible_competitive_result",
        executors=executors(raw_manifest),
    )
    assert evidence["run_id"] == stable_run_id(manifest=raw_manifest, case=raw_case)
    first = write_evidence(evidence=evidence, artifact_root=tmp_path)
    assert write_evidence(evidence=evidence, artifact_root=tmp_path) == first
    assert json.loads(first.read_text())["run_id"] == evidence["run_id"]

    changed = deepcopy(evidence)
    changed["classification"] = "resource_impracticality"
    first.write_text(json.dumps(changed, sort_keys=True, indent=2) + "\n")
    with pytest.raises(ExternalQualificationError, match="different evidence"):
        write_evidence(evidence=evidence, artifact_root=tmp_path)
