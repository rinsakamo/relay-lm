from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from relaylm.budget_enforcement import TokenCountMode
from relaylm.providers.openai_compatible_budget import SerializedInputCounterIdentity


def _capacity_module():
    return importlib.import_module("relaylm.actual_model_vllm_capacity")


def _counter_identity() -> SerializedInputCounterIdentity:
    return SerializedInputCounterIdentity(
        capability="vllm.serving-tokenizer.serialized-input.v1",
        implementation="vllm-tokenize-endpoint-counter",
        version="1",
        mode=TokenCountMode.EXACT,
        tokenizer_identity="hf-snapshot-tokenizer:sha256:" + "1" * 64,
        parameters=(
            ("backend", "vllm"),
            ("backend_version", "0.27.1"),
            ("chat_template_identity", "hf-snapshot-chat-template:sha256:" + "2" * 64),
            ("context_limit", 2048),
            ("framing_method", "same-message-shape-empty-content-v1"),
            ("renderer_method", "chat-completion-effective-template-kwargs-v1"),
            ("request_model", "gemma-4-12B-it-qat-w4a16"),
            ("target_id", "gemma-4-12b-it-qat-w4a16-vllm-v1"),
        ),
    )


def _evidence():
    capacity = _capacity_module()
    return capacity.VLLMRuntimeCapacityEvidence(
        relaylm_commit="a" * 40,
        target_id="gemma-4-12b-it-qat-w4a16-vllm-v1",
        target_revision="sha256:" + "b" * 64,
        tokenizer_identity="hf-snapshot-tokenizer:sha256:" + "1" * 64,
        chat_template_identity="hf-snapshot-chat-template:sha256:" + "2" * 64,
        backend_version="0.27.1",
        request_model="gemma-4-12B-it-qat-w4a16",
        observed_max_model_len=2048,
        counter_identity=_counter_identity(),
        footprints=(
            capacity.VLLMCapacityFootprintObservation(
                topology="two_pass",
                pass_id="pass1",
                scenario_id="response-persona-correction-v1",
                turn_index=1,
                total_input_tokens=1180,
                required_input_framing_tokens=96,
                count_mode=TokenCountMode.EXACT,
            ),
            capacity.VLLMCapacityFootprintObservation(
                topology="two_pass",
                pass_id="pass2",
                scenario_id="response-persona-correction-v1",
                turn_index=1,
                total_input_tokens=1310,
                required_input_framing_tokens=104,
                count_mode=TokenCountMode.EXACT,
            ),
        ),
        failed_capacity=capacity.VLLMCapacityFailureObservation(
            configured_max_model_len=1024,
            observed_input_tokens=1324,
            http_status=400,
            failure_kind="input_context_overflow",
        ),
    )


def test_capacity_evidence_is_content_addressed_and_contains_no_semantic_payload() -> None:
    evidence = _evidence()

    assert evidence.evidence_id.startswith("amcap-")
    assert evidence.maximum_observed_input_tokens == 1310
    mapping = evidence.to_mapping()
    assert mapping["evidence_id"] == evidence.evidence_id
    assert set(mapping) == {
        "format_version",
        "evidence_id",
        "relaylm_commit",
        "target_id",
        "target_revision",
        "tokenizer_identity",
        "chat_template_identity",
        "backend_version",
        "request_model",
        "observed_max_model_len",
        "counter_identity",
        "footprints",
        "failed_capacity",
    }
    for footprint in mapping["footprints"]:
        assert set(footprint) == {
            "topology",
            "pass_id",
            "scenario_id",
            "turn_index",
            "total_input_tokens",
            "required_input_framing_tokens",
            "count_mode",
        }
    serialized_keys = json.dumps(sorted(mapping), sort_keys=True).casefold()
    assert "prompt" not in serialized_keys
    assert "message" not in serialized_keys
    assert "content" not in serialized_keys


def test_capacity_evidence_writer_is_immutable_and_loader_recomputes_identity(
    tmp_path: Path,
) -> None:
    capacity = _capacity_module()
    evidence = _evidence()

    path = capacity.write_vllm_runtime_capacity_evidence(
        evidence=evidence,
        artifact_root=tmp_path,
    )
    assert path.name == f"{evidence.evidence_id}.json"
    assert capacity.write_vllm_runtime_capacity_evidence(
        evidence=evidence,
        artifact_root=tmp_path,
    ) == path

    loaded = capacity.load_vllm_runtime_capacity_evidence(path)
    assert loaded == evidence

    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["relaylm_commit"] = "c" * 40
    path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(capacity.VLLMRuntimeCapacityEvidenceError, match="evidence_id"):
        capacity.load_vllm_runtime_capacity_evidence(path)


def test_capacity_evidence_path_requires_exact_content_addressed_id(
    tmp_path: Path,
) -> None:
    capacity = _capacity_module()
    evidence = _evidence()

    path = capacity.capacity_evidence_path(
        artifact_root=tmp_path,
        evidence_id=evidence.evidence_id,
    )
    assert path == tmp_path / f"{evidence.evidence_id}.json"

    for invalid in (
        "amcap-missing-evidence",
        "amcap-" + "A" * 64,
        "amcap-" + "a" * 63,
        "other-" + "a" * 64,
    ):
        with pytest.raises(
            capacity.VLLMRuntimeCapacityEvidenceError,
            match="content-addressed",
        ):
            capacity.capacity_evidence_path(
                artifact_root=tmp_path,
                evidence_id=invalid,
            )


def test_capacity_evidence_rejects_non_resolving_window() -> None:
    capacity = _capacity_module()
    evidence = _evidence()

    with pytest.raises(capacity.VLLMRuntimeCapacityEvidenceError, match="serialized-input"):
        capacity.validate_capacity_window(
            evidence=evidence,
            capacity_evidence_id=evidence.evidence_id,
            effective_context_window=1310,
        )

    capacity.validate_capacity_window(
        evidence=evidence,
        capacity_evidence_id=evidence.evidence_id,
        effective_context_window=1311,
    )

    with pytest.raises(capacity.VLLMRuntimeCapacityEvidenceError, match="runtime capacity"):
        capacity.validate_capacity_window(
            evidence=evidence,
            capacity_evidence_id=evidence.evidence_id,
            effective_context_window=2049,
        )
