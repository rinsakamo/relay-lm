from __future__ import annotations

import json
from pathlib import Path

import pytest

from relaylm.v2_cognitive_ir_semantic_reconstruction import (
    ARMS,
    MAX_OUTPUT_TOKENS,
    REASONING,
    TEMPERATURE,
    prepare_mechanism_control,
    preregistered_seeds,
)
import relaylm.v2_cognitive_ir_semantic_reconstruction_physical as physical
from relaylm.v2_cognitive_ir_semantic_reconstruction_physical import (
    FrozenConsumerIdentity,
    SemanticReconstructionPhysicalBindingError,
    generate_scientific_canonical_payload,
    generate_synthetic_canonical_payload,
    physical_call_plan,
    run_semantic_reconstruction_campaign,
    validate_physical_adapter_binding,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from tools.v2_cognitive_ir_semantic_reconstruction_llama_cpp import (
    SemanticReconstructionInputCounterPreflight,
    SemanticReconstructionLlamaCppClient,
)
import tools.v2_cognitive_ir_semantic_reconstruction_llama_cpp_transaction as semantic_tx
import tools.v2_cognitive_ir_semantic_reconstruction_llama_cpp_wsl as semantic_wsl
import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_wsl as legacy_wsl


def _runtime_attestation() -> dict[str, object]:
    return {
        "upstream_revision": "c" * 40,
        "build_info": "llama.cpp build test",
        "model_alias": "gemma-test",
        "model_path": "/tmp/model.gguf",
        "model_ftype": "Q4_K_M",
        "artifact_sha256": "d" * 64,
        "chat_template_sha256": "e" * 64,
        "context_limit": 8192,
        "total_slots": 1,
        "context_shift_enabled": False,
    }


def _identity() -> FrozenConsumerIdentity:
    value = physical.freeze_consumer_identity(
        repository_commit="a" * 40,
        repository_tree="b" * 40,
        model="gemma-test",
        runtime_attestation=_runtime_attestation(),
    )
    value.validate()
    return value


def test_physical_binding_freezes_16_32_64_without_materializing_families(
    monkeypatch,
) -> None:
    def forbidden_material(_seed: int) -> dict[str, object]:
        raise AssertionError("binding validation must not instantiate family material")

    monkeypatch.setattr(physical, "_canonical_payload_for_seed", forbidden_material)
    validate_physical_adapter_binding()
    plan = physical_call_plan()
    seeds = preregistered_seeds()

    assert len(seeds) == 16
    assert len(plan) == 32
    assert len(set(plan)) == 32
    assert physical.SCIENTIFIC_INPUT_TOKEN_REQUESTS == 64
    assert all(str(seed) in plan[2 * index] for index, seed in enumerate(seeds))


def test_synthetic_material_is_k3_and_rejects_scientific_seed() -> None:
    payload = generate_synthetic_canonical_payload(90_000_000_000_001)
    assert payload["operation"] == "affine_permutation"
    assert payload["permutation"] == [0, 1, 2, 3]
    assert payload["modulus"] == 10
    offsets = payload["offsets"]
    assert isinstance(offsets, list)
    assert len(offsets) == 4
    assert sum(value != 0 for value in offsets) == 3
    assert all(value in (1, 2, 3) for value in offsets if value != 0)

    control = prepare_mechanism_control(payload)
    assert control.serialized_by_arm[ARMS[0]] != control.serialized_by_arm[ARMS[1]]

    with pytest.raises(SemanticReconstructionPhysicalBindingError):
        generate_synthetic_canonical_payload(preregistered_seeds()[0])


def test_scientific_generator_rejects_before_material_boundary(monkeypatch) -> None:
    def forbidden_material(_seed: int) -> dict[str, object]:
        raise AssertionError("invalid admission reached material generation")

    monkeypatch.setattr(physical, "_canonical_payload_for_seed", forbidden_material)
    seeds = preregistered_seeds()

    with pytest.raises(SemanticReconstructionPhysicalBindingError):
        generate_scientific_canonical_payload(
            index=0,
            seed=seeds[1],
            frozen_identity=_identity(),
        )
    with pytest.raises(SemanticReconstructionPhysicalBindingError):
        generate_scientific_canonical_payload(
            index=0,
            seed=seeds[0],
            frozen_identity=None,  # type: ignore[arg-type]
        )


def test_transaction_freezes_counter_and_runtime_before_material(
    monkeypatch,
) -> None:
    def fake_preflight(*, base_url: str, model: str):
        assert base_url == "http://127.0.0.1:1234/v1"
        assert model == "gemma-test"
        return SemanticReconstructionInputCounterPreflight(
            total_input_tokens=12,
            framing_input_tokens=4,
            request_attempts=2,
            request_completions=2,
        )

    def forbidden_material(_seed: int) -> dict[str, object]:
        raise AssertionError("consumer freeze must not instantiate family material")

    monkeypatch.setattr(
        semantic_tx,
        "preflight_semantic_reconstruction_input_counter",
        fake_preflight,
    )
    monkeypatch.setattr(physical, "_canonical_payload_for_seed", forbidden_material)

    identity, counter = semantic_tx._prepare_consumer_identity(
        repository_commit="a" * 40,
        repository_tree="b" * 40,
        model="gemma-test",
        runtime_attestation=_runtime_attestation(),
        base_url="http://127.0.0.1:1234/v1",
    )
    assert isinstance(identity, FrozenConsumerIdentity)
    assert identity.context_limit == 8192
    assert identity.total_slots == 1
    assert identity.request_seed is None
    assert counter.request_attempts == counter.request_completions == 2


class _CampaignClient:
    def __init__(self, *, fail_on_attempt: int | None = None) -> None:
        self.plan = physical_call_plan()
        self.provider_attempts = 0
        self.provider_completions = 0
        self.input_count_attempts = 0
        self.input_count_completions = 0
        self.fail_on_attempt = fail_on_attempt
        self.truth_by_index: dict[int, dict[str, object]] = {}
        self.messages: list[tuple[dict[str, str], ...]] = []

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        assert question_id == self.plan[self.provider_attempts]
        assert output_kind == "text"
        self.input_count_attempts += 2
        self.input_count_completions += 2
        self.provider_attempts += 1
        if self.fail_on_attempt == self.provider_attempts:
            raise RuntimeError("synthetic provider failure after spend")
        self.provider_completions += 1
        self.messages.append(messages)
        _, index_text, _seed_text, _arm = question_id.split(":")
        truth = self.truth_by_index[int(index_text)]
        return ExperimentCompletion(
            content=json.dumps(truth, sort_keys=True),
            input_tokens=21,
            output_tokens=13,
            response_id=f"fake-{self.provider_attempts}",
        )

    def require_complete_plan(self) -> None:
        assert self.provider_attempts == len(self.plan)
        assert self.provider_completions == len(self.plan)


def _synthetic_factory(client: _CampaignClient):
    def factory(
        index: int,
        _seed: int,
        identity: FrozenConsumerIdentity,
    ) -> dict[str, object]:
        identity.validate()
        truth = generate_synthetic_canonical_payload(90_000_000_100_000 + index)
        client.truth_by_index[index] = truth
        return truth

    return factory


def test_synthetic_campaign_is_exact_32_calls_and_arm_symmetric() -> None:
    client = _CampaignClient()
    result = run_semantic_reconstruction_campaign(
        client,
        frozen_identity=_identity(),
        family_factory=_synthetic_factory(client),
    )

    assert result.completed is True
    assert result.semantic_calls == 32
    assert result.input_token_requests == 64
    assert result.paired == {
        "both_correct": 16,
        "p4_only": 0,
        "p6_only": 0,
        "both_wrong": 0,
    }
    assert result.classification == "NO_ACCESSIBILITY_GAP_DETECTED_AT_THIS_RESOLUTION"
    assert result.statistical_status == "UNDERDETERMINED"
    assert result.architecture_consequence == "NONE"

    for index in range(16):
        p4_messages = client.messages[2 * index]
        p6_messages = client.messages[2 * index + 1]
        assert p4_messages[0] == p6_messages[0]
        assert p4_messages[1]["role"] == p6_messages[1]["role"] == "user"
        assert p4_messages[1]["content"] != p6_messages[1]["content"]


def test_failure_after_scientific_attempt_preserves_partial_v3() -> None:
    client = _CampaignClient(fail_on_attempt=6)
    result = run_semantic_reconstruction_campaign(
        client,
        frozen_identity=_identity(),
        family_factory=_synthetic_factory(client),
    )

    assert result.completed is False
    assert result.classification == "PROTOCOL_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND"
    assert result.statistical_status == "UNDERDETERMINED"
    assert result.architecture_consequence == "NONE"
    assert result.semantic_calls == 6
    assert result.input_token_requests == 12
    assert len(result.cells) == 5
    assert result.paired is None
    assert result.failure == "RuntimeError: synthetic provider failure after spend"


class _FakeResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300

    def json(self) -> object:
        return self._payload


class _FakeHttpClient:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, object]]] = []

    def post(self, url: str, *, headers=None, json=None):
        del headers
        body = dict(json or {})
        self.requests.append((url, body))
        if url.endswith("/input_tokens"):
            messages = body.get("messages")
            assert isinstance(messages, list)
            has_content = any(item.get("content") for item in messages)
            return _FakeResponse({"input_tokens": 12 if has_content else 4})
        return _FakeResponse(
            {
                "id": "fake-completion",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "{}"},
                    }
                ],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 5,
                    "completion_tokens_details": {"reasoning_tokens": 0},
                },
            }
        )


def test_llama_cpp_transport_is_plain_text_and_frozen() -> None:
    fake = _FakeHttpClient()
    client = SemanticReconstructionLlamaCppClient(
        base_url="http://127.0.0.1:1234/v1",
        model="gemma-test",
        http_client=fake,  # type: ignore[arg-type]
    )
    try:
        client.complete_named(
            physical_call_plan()[0],
            (
                {"role": "system", "content": "system"},
                {"role": "user", "content": "representation"},
            ),
            output_kind="text",
        )
    finally:
        client.close()

    generation = fake.requests[-1][1]
    assert generation["max_tokens"] == MAX_OUTPUT_TOKENS == 256
    assert generation["temperature"] == TEMPERATURE == 0.0
    assert generation["reasoning_effort"] == REASONING == "none"
    assert generation["stream"] is False
    assert "seed" not in generation
    assert "response_format" not in generation
    assert client.provider_attempts == client.provider_completions == 1
    assert client.input_count_attempts == client.input_count_completions == 2


def test_wsl_adapter_routes_through_semantic_transaction_and_restores(
    monkeypatch,
) -> None:
    observed: list[tuple[str, str]] = []

    def fake_main(argv):
        del argv
        observed.append((legacy_wsl.INNER_TRANSACTION_MODULE, legacy_wsl.WALL_TIME_SCHEMA))
        return 19

    monkeypatch.setattr(legacy_wsl, "main", fake_main)
    assert semantic_wsl.main(["--repo-root", "."]) == 19
    assert observed == [
        (
            "tools.v2_cognitive_ir_semantic_reconstruction_llama_cpp_transaction",
            "relaylm2-cognitive-ir-semantic-reconstruction-wsl-wall-time-v1",
        )
    ]
    assert legacy_wsl.INNER_TRANSACTION_MODULE == (
        "tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction"
    )


def test_common_physical_target_routes_through_wsl_transaction() -> None:
    root = Path(__file__).resolve().parents[2]
    registry = json.loads(
        (root / ".ai" / "physical" / "llama_cpp_targets.json").read_text(
            encoding="utf-8"
        )
    )
    target = registry["targets"]["v2:semantic-reconstruction"]
    assert target["branch"] == "v2"
    assert target["module"] == (
        "tools.v2_cognitive_ir_semantic_reconstruction_llama_cpp_wsl"
    )
    assert target["required_distributions"] == ["httpx"]
