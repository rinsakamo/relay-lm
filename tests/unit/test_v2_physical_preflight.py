from __future__ import annotations

from copy import deepcopy

import pytest

from tools.external_qualification import (
    FROZEN_EXPERIMENT_IDENTITY_FIELDS,
    LIVE_LAUNCH_ADMISSION_FIELDS,
)
from tools.v2_physical_preflight import (
    CONTROLLER_MAX_ESTABLISHMENT_CYCLES,
    PREFLIGHT_VERSION,
    PhysicalControllerPreflightError,
    validate_frozen_identity_controller_setup,
)


MATERIAL_FIELDS = (
    "model",
    "artifact",
    "tokenizer",
    "template",
    "backend",
    "runtime",
    "decoding",
    "reasoning",
    "structured_output",
    "context_capacity",
    "hardware",
    "launch_admission",
)


def _launch() -> dict[str, object]:
    return {
        "backend": "fake-backend",
        "runtime": "fake-runtime",
        "model_runner": "fake-runner",
        "effective_gpu_reservation": 0.9,
        "admitted_context": 8192,
        "capacity_evidence": {"kind": "bounded-test", "tokens": 8192},
        "launch_evidence_reference": "local://launch",
        "runtime_ownership_evidence_reference": "local://runtime-owner",
    }


def _identity() -> dict[str, object]:
    identity = {
        "repository": {"commit": "test-commit", "tree": "test-tree", "clean_required": True},
        "candidate": "test-candidate",
        "prompt_core": "test-prompt",
        "benchmark": {"id": "test-benchmark"},
        "dataset": {"id": "test-dataset"},
        "harness": "test-harness",
        "adapter": "test-adapter",
        "model": {"id": "test-model"},
        "artifact": {"sha256": "artifact"},
        "tokenizer": {"sha256": "tokenizer"},
        "template": {"sha256": "template"},
        "backend": "fake-backend",
        "runtime": "fake-runtime",
        "decoding": {"temperature": "omitted"},
        "reasoning": {"mode": "provider-default"},
        "structured_output": {"mechanism": "json-schema"},
        "context_capacity": 8192,
        "capacity_evidence": {"kind": "bounded-test", "tokens": 8192},
        "hardware": {"gpu": "fake-gpu"},
        "execution_order": ["one"],
        "retry_policy": {"automatic_retry": False, "semantic_retry": False},
        "authority": {"status": "CURRENT"},
        "launch_admission": _launch(),
    }
    assert set(identity) == set(FROZEN_EXPERIMENT_IDENTITY_FIELDS)
    assert set(identity["launch_admission"]) == set(LIVE_LAUNCH_ADMISSION_FIELDS)
    return identity


def _binding(identity: dict[str, object]) -> dict[str, object]:
    return deepcopy({name: identity[name] for name in MATERIAL_FIELDS})


def test_controller_preflight_accepts_complete_identity_and_equal_fresh_bindings() -> None:
    identity = _identity()
    binding = _binding(identity)

    result = validate_frozen_identity_controller_setup(
        identity=identity,
        material_binding_fields=MATERIAL_FIELDS,
        observed_binding_a=deepcopy(binding),
        observed_binding_b=deepcopy(binding),
    )

    assert result.version == PREFLIGHT_VERSION
    assert result.identity_snapshot == identity
    assert result.material_binding == binding
    assert CONTROLLER_MAX_ESTABLISHMENT_CYCLES == 3


def test_controller_preflight_rejects_missing_capacity_evidence_before_host() -> None:
    identity = _identity()
    del identity["capacity_evidence"]
    binding = _binding(_identity())

    with pytest.raises(PhysicalControllerPreflightError, match="field set mismatch"):
        validate_frozen_identity_controller_setup(
            identity=identity,
            material_binding_fields=MATERIAL_FIELDS,
            observed_binding_a=binding,
            observed_binding_b=binding,
        )


def test_controller_preflight_rejects_capacity_evidence_mirror_drift() -> None:
    identity = _identity()
    identity["launch_admission"]["capacity_evidence"] = {"kind": "different"}  # type: ignore[index]
    binding = _binding(identity)

    with pytest.raises(PhysicalControllerPreflightError, match="capacity_evidence"):
        validate_frozen_identity_controller_setup(
            identity=identity,
            material_binding_fields=MATERIAL_FIELDS,
            observed_binding_a=binding,
            observed_binding_b=binding,
        )


def test_controller_preflight_rejects_binding_drift() -> None:
    identity = _identity()
    binding_a = _binding(identity)
    binding_b = _binding(identity)
    binding_b["runtime"] = "drifted-runtime"

    with pytest.raises(PhysicalControllerPreflightError, match="binding B"):
        validate_frozen_identity_controller_setup(
            identity=identity,
            material_binding_fields=MATERIAL_FIELDS,
            observed_binding_a=binding_a,
            observed_binding_b=binding_b,
        )


def test_controller_preflight_snapshots_caller_owned_identity() -> None:
    identity = _identity()
    binding = _binding(identity)
    result = validate_frozen_identity_controller_setup(
        identity=identity,
        material_binding_fields=MATERIAL_FIELDS,
        observed_binding_a=binding,
        observed_binding_b=binding,
    )

    identity["runtime"] = "mutated-after-validation"
    assert result.identity_snapshot["runtime"] == "fake-runtime"
