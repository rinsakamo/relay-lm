from __future__ import annotations

from copy import deepcopy

import pytest

from tools.external_qualification_readiness import (
    ExternalQualificationReadinessError,
    assess_launch_readiness,
    validate_launch_readiness,
)


def _axis(
    axis_id: str,
    axis_family: str,
    benchmark_id: str,
    adapter_id: str,
) -> dict[str, object]:
    return {
        "axis_id": axis_id,
        "axis_family": axis_family,
        "benchmark_id": benchmark_id,
        "adapter_id": adapter_id,
    }


def _pre_rc_plan() -> dict[str, object]:
    return {
        "format_version": 1,
        "phase": "pre_rc_readiness",
        "axes": [
            _axis(
                "memconflict",
                "conflict_temporal_validity",
                "memconflict",
                "relaylm-memconflict",
            ),
            _axis(
                "longmemeval-update",
                "update_belief_revision",
                "longmemeval",
                "relaylm-longmemeval",
            ),
        ],
        "comparator": {
            "implementation": "hindsight",
            "repository": "https://github.com/vectorize-io/hindsight",
            "source_revision": None,
            "version": None,
            "license": None,
        },
        "physical_carriage": {
            "target": "v1:external-qualification",
            "backend": "llama.cpp",
            "resource_key": "llama-cpp:local-gpu",
            "registered": False,
        },
        "release_cases": [],
        "retry_policy": "no_semantic_retry_or_fallback",
        "resume_policy": "exact_infrastructure_resume_only",
    }


def _release_identity(
    *,
    version: str = "1.0.0rc1",
    commit: str = "d" * 40,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "package": "relaylm",
        "version": version,
        "release_kind": "rc",
        "tag": f"v{version}",
        "commit": commit,
        "artifacts": [
            {
                "filename": f"relaylm-{version}-py3-none-any.whl",
                "sha256": "1" * 64,
            },
            {
                "filename": f"relaylm-{version}.tar.gz",
                "sha256": "2" * 64,
            },
        ],
    }


def _identity(
    implementation: str,
    *,
    revision: str,
    version: str,
    license_name: str,
) -> dict[str, object]:
    return {
        "implementation": implementation,
        "source_revision": revision,
        "version": version,
        "deployment": "local-process",
        "license": license_name,
        "physical_model": {
            "artifact": "gemma-4-12b-q4",
            "tokenizer": "gemma-4",
            "quantization": "Q4_K_M",
        },
        "provider": "openai-compatible",
        "backend": "llama.cpp",
        "runtime": "llama-server",
        "context_capacity": 8192,
        "decoding": {"temperature": 0},
        "reasoning": {"effort": "none"},
        "hardware": {"gpu": "RTX 3060", "cpu": "i5-12400"},
        "retry_policy": "no retry",
        "matched_condition_differences": [],
    }


def _manifest(adapter_id: str) -> dict[str, object]:
    release = _release_identity()
    return {
        "format_version": 1,
        "purpose": "release_qualification",
        "harness": {
            "identity": "rinsakamo/relay-lm",
            "revision": "a" * 40,
        },
        "adapter": {"identity": adapter_id, "revision": "b" * 40},
        "participants": [
            {
                "slot": "same_model_direct",
                "identity": _identity(
                    "same-model-direct",
                    revision="e" * 40,
                    version="direct-v1",
                    license_name="MIT",
                ),
                "omission_reason": None,
            },
            {
                "slot": "simple_baseline",
                "identity": None,
                "omission_reason": "not scientifically meaningful for this slice",
            },
            {
                "slot": "serious_comparator",
                "identity": _identity(
                    "hindsight",
                    revision="c" * 40,
                    version="0.9.0",
                    license_name="MIT",
                ),
                "omission_reason": None,
            },
            {
                "slot": "relaylm_exact_rc",
                "identity": _identity(
                    "relaylm",
                    revision=str(release["commit"]),
                    version=str(release["version"]),
                    license_name="Apache-2.0",
                ),
                "omission_reason": None,
            },
        ],
        "relaylm_release": release,
        "judge": {
            "identity": "benchmark-native-judge@exact-revision",
            "policy": "same judge policy across enabled participants",
        },
        "replicate_id": "0",
    }


def _case(axis_family: str, benchmark_id: str, case_id: str) -> dict[str, object]:
    return {
        "case_id": case_id,
        "axis": axis_family,
        "benchmark": {
            "id": benchmark_id,
            "repository": f"https://example.test/{benchmark_id}.git",
            "revision": "f" * 40,
            "license": "MIT",
        },
        "dataset": {"revision": "dataset-revision", "license": "observed-license"},
        "adapter_case_ref": f"cases/{case_id}",
    }


def _frozen_plan() -> dict[str, object]:
    raw = _pre_rc_plan()
    raw["phase"] = "execution_freeze"
    raw["comparator"] = {
        "implementation": "hindsight",
        "repository": "https://github.com/vectorize-io/hindsight",
        "source_revision": "c" * 40,
        "version": "0.9.0",
        "license": "MIT",
    }
    raw["physical_carriage"] = {
        "target": "v1:external-qualification",
        "backend": "llama.cpp",
        "resource_key": "llama-cpp:local-gpu",
        "registered": True,
    }
    raw["release_cases"] = [
        {
            "axis_id": "memconflict",
            "case": _case(
                "conflict_temporal_validity",
                "memconflict",
                "conflict-1",
            ),
            "manifest": _manifest("relaylm-memconflict"),
        },
        {
            "axis_id": "longmemeval-update",
            "case": _case(
                "update_belief_revision",
                "longmemeval",
                "update-1",
            ),
            "manifest": _manifest("relaylm-longmemeval"),
        },
    ]
    return raw


def test_pre_rc_plan_is_ready_without_claiming_citable_execution() -> None:
    result = validate_launch_readiness(_pre_rc_plan())
    assert result["status"] == "READY_EXCEPT_EXACT_RC"
    assert result["relaylm_release"] is None
    assert result["physical_carriage"]["registered"] is False
    assert result["fingerprint"].startswith("sha256:")


def test_one_axis_and_duplicate_axis_families_fail_closed() -> None:
    one_axis = _pre_rc_plan()
    one_axis["axes"] = one_axis["axes"][:1]
    blocked = assess_launch_readiness(one_axis)
    assert blocked["status"] == "BLOCKED"
    assert "at least two" in blocked["reason"]

    duplicate = _pre_rc_plan()
    duplicate["axes"][1]["axis_family"] = duplicate["axes"][0]["axis_family"]
    with pytest.raises(
        ExternalQualificationReadinessError,
        match="distinct axis_family",
    ):
        validate_launch_readiness(duplicate)


def test_pre_rc_plan_cannot_smuggle_release_cases() -> None:
    raw = _pre_rc_plan()
    raw["release_cases"] = [{"not": "citable"}]
    with pytest.raises(
        ExternalQualificationReadinessError,
        match="must not carry citable release cases",
    ):
        validate_launch_readiness(raw)


def test_execution_freeze_requires_registered_carriage_and_exact_comparator() -> None:
    raw = _frozen_plan()
    raw["physical_carriage"]["registered"] = False
    assert assess_launch_readiness(raw)["status"] == "BLOCKED"

    raw = _frozen_plan()
    raw["comparator"]["source_revision"] = None
    blocked = assess_launch_readiness(raw)
    assert blocked["status"] == "BLOCKED"
    assert "exact comparator source_revision" in blocked["reason"]


def test_execution_freeze_reuses_exact_release_and_manifest_contracts() -> None:
    result = validate_launch_readiness(_frozen_plan())
    assert result["status"] == "EXECUTION_FROZEN"
    assert result["relaylm_release"]["commit"] == "d" * 40
    assert [item["axis_id"] for item in result["release_cases"]] == [
        "memconflict",
        "longmemeval-update",
    ]


def test_execution_freeze_rejects_comparator_or_adapter_drift() -> None:
    comparator_drift = _frozen_plan()
    comparator_drift["release_cases"][1]["manifest"]["participants"][2]["identity"][
        "source_revision"
    ] = "9" * 40
    with pytest.raises(
        ExternalQualificationReadinessError,
        match="comparator source_revision does not match plan",
    ):
        validate_launch_readiness(comparator_drift)

    adapter_drift = _frozen_plan()
    adapter_drift["release_cases"][1]["manifest"]["adapter"]["identity"] = "wrong-adapter"
    with pytest.raises(
        ExternalQualificationReadinessError,
        match="adapter does not match plan",
    ):
        validate_launch_readiness(adapter_drift)


def test_execution_freeze_rejects_mixed_release_candidates() -> None:
    raw = _frozen_plan()
    second = raw["release_cases"][1]["manifest"]
    second_release = _release_identity(version="1.0.0rc2", commit="8" * 40)
    second["relaylm_release"] = second_release
    relay_identity = second["participants"][3]["identity"]
    relay_identity["source_revision"] = second_release["commit"]
    relay_identity["version"] = second_release["version"]

    with pytest.raises(
        ExternalQualificationReadinessError,
        match="same exact RelayLM release",
    ):
        validate_launch_readiness(raw)


def test_pre_rc_fingerprint_is_deterministic() -> None:
    first = validate_launch_readiness(_pre_rc_plan())
    second = validate_launch_readiness(deepcopy(_pre_rc_plan()))
    assert first["fingerprint"] == second["fingerprint"]
