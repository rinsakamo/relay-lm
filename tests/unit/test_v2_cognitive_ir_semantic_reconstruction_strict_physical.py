from __future__ import annotations

import json
from pathlib import Path

import pytest

from relaylm.v2_cognitive_ir_semantic_reconstruction import (
    ARMS,
    prepare_mechanism_control,
)
from relaylm.v2_cognitive_ir_semantic_reconstruction_physical import (
    FrozenConsumerIdentity,
    freeze_consumer_identity,
)
from relaylm.v2_cognitive_ir_semantic_reconstruction_strict import (
    ARCHITECTURE_CONSEQUENCE,
    MAX_OUTPUT_TOKENS,
    REASONING,
    STREAM,
    TEMPERATURE,
    build_reconstruction_messages,
    preregistered_seeds,
    response_format,
)
import relaylm.v2_cognitive_ir_semantic_reconstruction_strict_physical as physical
from relaylm.v2_cognitive_ir_semantic_reconstruction_strict_physical import (
    StrictSemanticReconstructionPhysicalBindingError,
    generate_scientific_canonical_payload,
    generate_synthetic_canonical_payload,
    physical_call_plan,
    run_strict_semantic_reconstruction_campaign,
    validate_physical_adapter_binding,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from tools.relay_physical_run import _load_targets
from tools.v2_cognitive_ir_semantic_reconstruction_strict_llama_cpp import (
    StrictOutputInputCounterPreflight,
    StrictSemanticReconstructionLlamaCppClient,
)
import tools.v2_cognitive_ir_semantic_reconstruction_strict_llama_cpp_transaction as strict_tx
import tools.v2_cognitive_ir_semantic_reconstruction_strict_llama_cpp_wsl as strict_wsl
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
    value = freeze_consumer_identity(
        repository_commit="a" * 40,
        repository_tree="b" * 40,
        model="gemma-test",
        runtime_attestation=_runtime_attestation(),
    )
    value.validate()
    return value


def test_physical_binding_freezes_24_48_96_without_materializing_families(
    monkeypatch,
) -> None:
    def forbidden_material(_seed: int) -> dict[str, object]:
        raise AssertionError("binding validation must not instantiate E4-SR2 material")

    monkeypatch.setattr(physical, "_legacy_generate_canonical_payload", forbidden_material)
    validate_physical_adapter_binding()
    seeds = preregistered_seeds()
    plan = physical_call_plan()

    assert len(seeds) == 24
    assert len(set(seeds)) == 24
    assert len(plan) == 48
    assert len(set(plan)) == 48
    assert physical.SCIENTIFIC_INPUT_TOKEN_REQUESTS == 96
    assert STREAM is False
    assert ARCHITECTURE_CONSEQUENCE == "NONE"


def test_synthetic_material_rejects_all_preregistered_e4_sr2_seeds() -> None:
    payload = generate_synthetic_canonical_payload(91_000_000_000_001)
    assert payload["operation"] == "affine_permutation"
    assert sorted(payload["permutation"]) == [0, 1, 2, 3]
    assert payload["modulus"] == 10

    for seed in preregistered_seeds():
        with pytest.raises(StrictSemanticReconstructionPhysicalBindingError):
            generate_synthetic_canonical_payload(seed)


def test_scientific_generator_fails_before_exact_material_on_bad_admission(
    monkeypatch,
) -> None:
    def forbidden_material(_seed: int) -> dict[str, object]:
        raise AssertionError("invalid admission reached exact material generation")

    monkeypatch.setattr(physical, "_legacy_generate_canonical_payload", forbidden_material)
    seeds = preregistered_seeds()

    with pytest.raises(StrictSemanticReconstructionPhysicalBindingError):
        generate_scientific_canonical_payload(
            index=0,
            seed=seeds[1],
            frozen_identity=_identity(),
        )
    with pytest.raises(StrictSemanticReconstructionPhysicalBindingError):
        generate_scientific_canonical_payload(
            index=0,
            seed=seeds[0],
            frozen_identity=None,  # type: ignore[arg-type]
        )


def test_transaction_freezes_structured_counter_before_material(monkeypatch) -> None:
    def fake_preflight(*, base_url: str, model: str):
        assert base_url == "http://127.0.0.1:1234/v1"
        assert model == "gemma-test"
        return StrictOutputInputCounterPreflight(
            total_input_tokens=12,
            framing_input_tokens=4,
            request_attempts=2,
            request_completions=2,
        )

    def forbidden_material(_seed: int) -> dict[str, object]:
        raise AssertionError("consumer freeze must not instantiate E4-SR2 material")

    monkeypatch.setattr(strict_tx, "preflight_strict_output_input_counter", fake_preflight)
    monkeypatch.setattr(physical, "_legacy_generate_canonical_payload", forbidden_material)

    identity, counter = strict_tx._prepare_consumer_identity(
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
        self.seen_output_kinds: list[str] = []

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        assert question_id == self.plan[self.provider_attempts]
        assert output_kind == "strict_semantic_payload"
        self.seen_output_kinds.append(output_kind)
        self.input_count_attempts += 2
        self.input_count_completions += 2
        self.provider_attempts += 1
        if self.fail_on_attempt == self.provider_attempts:
            raise RuntimeError("synthetic provider failure after spend")
        self.provider_completions += 1
        _, index_text, _seed_text, arm = question_id.rsplit(":", 3)
        control = prepare_mechanism_control(self.truth_by_index[int(index_text)])
        assert messages == build_reconstruction_messages(control.serialized_by_arm[arm])
        return ExperimentCompletion(
            content=json.dumps(control.canonical_truth, sort_keys=True),
            input_tokens=21,
            output_tokens=13,
            response_id=f"fake-{self.provider_attempts}",
        )

    def require_complete_plan(self) -> None:
        assert self.provider_attempts == len(self.plan)
        assert self.provider_completions == len(self.plan)
        assert self.input_count_attempts == 2 * self.provider_attempts
        assert self.input_count_completions == self.input_count_attempts


def _synthetic_factory(client: _CampaignClient):
    def factory(
        index: int,
        _seed: int,
        identity: FrozenConsumerIdentity,
    ) -> dict[str, object]:
        identity.validate()
        truth = generate_synthetic_canonical_payload(91_000_001_000_000 + index)
        client.truth_by_index[index] = truth
        return truth

    return factory


def test_synthetic_campaign_is_exact_48_calls_96_counts_and_semantically_paired() -> None:
    client = _CampaignClient()
    result = run_strict_semantic_reconstruction_campaign(
        client,
        frozen_identity=_identity(),
        family_factory=_synthetic_factory(client),
    )

    assert result.completed is True
    assert result.measurement_admitted is True
    assert result.semantic_calls == result.provider_completions == 48
    assert result.input_token_requests == result.input_token_completions == 96
    assert result.semantic_equal_pairs == 24
    assert result.strict_parse_valid == 48
    assert result.classification == "NO_ACCESSIBILITY_GAP_DETECTED_AT_THIS_RESOLUTION"
    assert result.architecture_consequence == "NONE"
    assert result.citable_for_accessibility_claim is True
    assert client.seen_output_kinds == ["strict_semantic_payload"] * 48

    for index in range(24):
        first, second = result.cells[2 * index : 2 * index + 2]
        assert (first.arm, second.arm) == ARMS
        assert first.semantic_digest == second.semantic_digest
        assert first.serialized_representation != second.serialized_representation
        assert first.canonical_truth == second.canonical_truth


def test_failure_after_scientific_attempt_is_terminal_without_rescue() -> None:
    client = _CampaignClient(fail_on_attempt=7)
    result = run_strict_semantic_reconstruction_campaign(
        client,
        frozen_identity=_identity(),
        family_factory=_synthetic_factory(client),
    )

    assert result.completed is False
    assert result.measurement_admitted is False
    assert result.classification == "MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND"
    assert result.semantic_calls == 7
    assert result.provider_completions == 6
    assert result.input_token_requests == result.input_token_completions == 14
    assert len(result.cells) == 6
    assert result.paired is None
    assert result.p_value is None
    assert result.citable_for_accessibility_claim is False
    assert result.failure == "RuntimeError: synthetic provider failure after spend"


class _FakeResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300

    def json(self) -> object:
        return self._payload


class _FakeHttpClient:
    def __init__(self, completion_content: str) -> None:
        self.completion_content = completion_content
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
                        "message": {"content": self.completion_content},
                    }
                ],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 5,
                    "completion_tokens_details": {"reasoning_tokens": 0},
                },
            }
        )

    def close(self) -> None:
        return None


def test_llama_cpp_transport_uses_exact_native_schema_and_frozen_envelope() -> None:
    truth = generate_synthetic_canonical_payload(91_000_000_000_777)
    control = prepare_mechanism_control(truth)
    fake = _FakeHttpClient(json.dumps(control.canonical_truth, sort_keys=True))
    client = StrictSemanticReconstructionLlamaCppClient(
        base_url="http://127.0.0.1:1234/v1",
        model="gemma-test",
        http_client=fake,  # type: ignore[arg-type]
    )
    try:
        completion = client.complete_named(
            physical_call_plan()[0],
            build_reconstruction_messages(control.serialized_by_arm[ARMS[0]]),
            output_kind="strict_semantic_payload",
        )
    finally:
        client.close()

    generation = fake.requests[-1][1]
    assert generation["max_tokens"] == MAX_OUTPUT_TOKENS == 256
    assert generation["temperature"] == TEMPERATURE == 0.0
    assert generation["reasoning_effort"] == REASONING == "none"
    assert generation["stream"] is STREAM is False
    assert "seed" not in generation
    assert generation["response_format"] == response_format()
    assert completion.content == json.dumps(control.canonical_truth, sort_keys=True)
    assert client.provider_attempts == client.provider_completions == 1
    assert client.input_count_attempts == client.input_count_completions == 2


def test_wsl_adapter_pins_current_common_generation_and_routes_transaction(
    monkeypatch,
) -> None:
    root = Path(__file__).resolve().parents[2]
    identity = strict_wsl.verify_common_physical_binding(root)
    assert identity["generation_id"] == "relay-common-physical-g2"
    assert identity["aggregate_identity"] == (
        "sha256:bb983011905bdd8b5393c2c3459b691289f5ced9a41561bb8dc7f642fa330b87"
    )

    observed: list[tuple[str, str]] = []
    monkeypatch.setattr(strict_wsl, "verify_common_physical_binding", lambda: identity)

    def fake_main(argv):
        del argv
        observed.append((legacy_wsl.INNER_TRANSACTION_MODULE, legacy_wsl.WALL_TIME_SCHEMA))
        return 19

    monkeypatch.setattr(legacy_wsl, "main", fake_main)
    assert strict_wsl.main(["--repo-root", "."]) == 19
    assert observed == [
        (
            "tools.v2_cognitive_ir_semantic_reconstruction_strict_llama_cpp_transaction",
            "relaylm2-cognitive-ir-semantic-reconstruction-strict-wsl-wall-time-v1",
        )
    ]
    assert legacy_wsl.INNER_TRANSACTION_MODULE == (
        "tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction"
    )


def test_common_physical_target_routes_only_through_wsl_transaction() -> None:
    root = Path(__file__).resolve().parents[2]
    registry = json.loads(
        (root / ".ai" / "physical" / "llama_cpp_targets.json").read_text(
            encoding="utf-8"
        )
    )
    target = registry["targets"]["v2:semantic-reconstruction-strict"]
    assert target["branch"] == "v2"
    assert target["module"] == (
        "tools.v2_cognitive_ir_semantic_reconstruction_strict_llama_cpp_wsl"
    )
    assert target["required_distributions"] == ["httpx"]
    loaded = _load_targets(root)["v2:semantic-reconstruction-strict"]
    assert loaded.module == target["module"]
    assert loaded.required_distributions == ("httpx",)


def test_architecture_boundary_remains_frozen() -> None:
    assert ARCHITECTURE_CONSEQUENCE == "NONE"
