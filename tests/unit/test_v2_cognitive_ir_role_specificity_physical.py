from __future__ import annotations

import json
from pathlib import Path

import pytest

from relaylm.v2_cognitive_ir_semantic_reconstruction_physical import (
    FrozenConsumerIdentity,
    freeze_consumer_identity,
)
from relaylm.v2_cognitive_ir_role_specificity import (
    ARCHITECTURE_CONSEQUENCE,
    CATEGORY_CONTEXT_KEY,
    CATEGORY_RELATION_KEYS,
    CATEGORY_SURFACE,
    CONFIRMATORY_CONTRASTS,
    FUNCTION_SURFACE,
    MAX_OUTPUT_TOKENS,
    OPAQUE_SURFACE,
    REASONING,
    STREAM,
    SURFACES,
    TEMPERATURE,
    build_reconstruction_messages,
    preregistered_seeds,
    response_format,
)
import relaylm.v2_cognitive_ir_role_specificity_physical as physical
from relaylm.v2_cognitive_ir_role_specificity_physical import (
    SemanticRoleSpecificityPhysicalError,
    generate_scientific_canonical_payload,
    generate_synthetic_canonical_payload,
    physical_call_plan,
    prepare_physical_mechanism_control,
    run_semantic_role_specificity_campaign,
    validate_physical_adapter_binding,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from tools.v2_cognitive_ir_role_specificity_llama_cpp import (
    SemanticRoleSpecificityLlamaCppClient,
    StrictOutputInputCounterPreflight,
)
import tools.v2_cognitive_ir_role_specificity_llama_cpp_transaction as tx
import tools.v2_cognitive_ir_role_specificity_llama_cpp_wsl as wsl


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


def test_binding_freezes_24_72_144_without_materializing_families(
    monkeypatch,
) -> None:
    def forbidden_material(_seed: int) -> dict[str, object]:
        raise AssertionError("binding validation must not instantiate E4-RS1 material")

    monkeypatch.setattr(
        physical, "_legacy_generate_canonical_payload", forbidden_material
    )
    validate_physical_adapter_binding()
    assert len(preregistered_seeds()) == 24
    assert len(set(preregistered_seeds())) == 24
    assert len(physical_call_plan()) == 72
    assert len(set(physical_call_plan())) == 72
    assert physical.SCIENTIFIC_INPUT_TOKEN_REQUESTS == 144
    assert STREAM is False
    assert ARCHITECTURE_CONSEQUENCE == "NONE"


def test_synthetic_material_rejects_all_preregistered_e4_rs1_seeds() -> None:
    payload = generate_synthetic_canonical_payload(91_300_000_000_001)
    assert payload["operation"] == "affine_permutation"
    assert sorted(payload["permutation"]) == [0, 1, 2, 3]
    assert payload["modulus"] == 10
    for seed in preregistered_seeds():
        with pytest.raises(SemanticRoleSpecificityPhysicalError):
            generate_synthetic_canonical_payload(seed)


def test_scientific_generator_fails_before_exact_material_on_bad_admission(
    monkeypatch,
) -> None:
    def forbidden_material(_seed: int) -> dict[str, object]:
        raise AssertionError("invalid admission reached exact material generation")

    monkeypatch.setattr(
        physical, "_legacy_generate_canonical_payload", forbidden_material
    )
    seeds = preregistered_seeds()
    with pytest.raises(SemanticRoleSpecificityPhysicalError):
        generate_scientific_canonical_payload(
            index=0,
            seed=seeds[1],
            frozen_identity=_identity(),
        )
    with pytest.raises(SemanticRoleSpecificityPhysicalError):
        generate_scientific_canonical_payload(
            index=0,
            seed=seeds[0],
            frozen_identity=None,  # type: ignore[arg-type]
        )


def test_transaction_freezes_counter_before_material(monkeypatch) -> None:
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
        raise AssertionError("consumer freeze must not instantiate E4-RS1 material")

    monkeypatch.setattr(tx, "preflight_strict_output_input_counter", fake_preflight)
    monkeypatch.setattr(
        physical, "_legacy_generate_canonical_payload", forbidden_material
    )
    identity, counter = tx._prepare_consumer_identity(
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
    def __init__(
        self,
        *,
        fail_on_attempt: int | None = None,
        domain_invalid_question: str | None = None,
    ) -> None:
        self.plan = physical_call_plan()
        self.provider_attempts = 0
        self.provider_completions = 0
        self.input_count_attempts = 0
        self.input_count_completions = 0
        self.fail_on_attempt = fail_on_attempt
        self.domain_invalid_question = domain_invalid_question
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
        assert output_kind == "semantic_role_payload"
        self.seen_output_kinds.append(output_kind)
        self.input_count_attempts += 2
        self.input_count_completions += 2
        self.provider_attempts += 1
        if self.fail_on_attempt == self.provider_attempts:
            raise RuntimeError("synthetic provider failure after spend")
        self.provider_completions += 1
        _, index_text, _seed_text, surface = question_id.rsplit(":", 3)
        control = prepare_physical_mechanism_control(
            self.truth_by_index[int(index_text)]
        )
        assert messages == build_reconstruction_messages(
            control.serialized_by_surface[surface]
        )
        content = dict(control.canonical_truth)
        if question_id == self.domain_invalid_question:
            content["permutation"] = [0, 0, 0, 0]
        return ExperimentCompletion(
            content=json.dumps(content, sort_keys=True),
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
        truth = generate_synthetic_canonical_payload(91_300_001_000_000 + index)
        client.truth_by_index[index] = truth
        return truth

    return factory


def test_synthetic_campaign_is_exact_72_calls_144_counts_and_f_c_o_paired() -> None:
    client = _CampaignClient()
    result = run_semantic_role_specificity_campaign(
        client,
        frozen_identity=_identity(),
        family_factory=_synthetic_factory(client),
    )
    assert result.completed is True
    assert result.measurement_admitted is True
    assert result.semantic_calls == result.provider_completions == 72
    assert result.input_token_requests == result.input_token_completions == 144
    assert result.semantic_equal_families == 24
    assert result.wire_shape_valid == 72
    assert result.semantic_domain_valid == 72
    assert result.classification == (
        "NO_DECLARED_ROLE_SPECIFICITY_GAP_DETECTED_AT_THIS_RESOLUTION"
    )
    assert result.statistical_status == "UNDERDETERMINED"
    assert result.citable_for_accessibility_claim is True
    assert set(result.confirmatory or {}) == set(CONFIRMATORY_CONTRASTS)
    assert result.descriptive_function_vs_opaque is not None
    assert client.seen_output_kinds == ["semantic_role_payload"] * 72

    for index in range(24):
        family = result.cells[3 * index : 3 * index + 3]
        assert tuple(cell.surface for cell in family) == SURFACES
        assert len({cell.semantic_digest for cell in family}) == 1
        assert len({cell.serialized_representation for cell in family}) == 3
        assert family[0].canonical_truth == family[1].canonical_truth
        assert family[1].canonical_truth == family[2].canonical_truth


def test_category_surface_is_role_neutral_and_has_no_model_visible_legend() -> None:
    truth = generate_synthetic_canonical_payload(91_300_000_000_777)
    control = prepare_physical_mechanism_control(truth)
    category = control.serialized_by_surface[CATEGORY_SURFACE]
    assert f'"{CATEGORY_CONTEXT_KEY}"' in category
    for key in CATEGORY_RELATION_KEYS:
        assert f'"{key}"' in category
    for forbidden in (
        '"source_handles"',
        '"transform_kind"',
        '"index_reordering"',
        '"additive_shifts"',
        '"modular_divisor"',
        '"operation"',
        '"permutation"',
        '"offsets"',
        '"modulus"',
        '"provenance_handles"',
    ):
        assert forbidden not in category
    messages = json.dumps(
        build_reconstruction_messages(category),
        sort_keys=True,
    )
    assert "text_value -> operation" not in messages
    assert "integer_list_one -> permutation" not in messages


def test_shape_valid_domain_failure_remains_scientific_outcome() -> None:
    invalid_question = physical_call_plan()[2]
    assert invalid_question.endswith(OPAQUE_SURFACE)
    client = _CampaignClient(domain_invalid_question=invalid_question)
    result = run_semantic_role_specificity_campaign(
        client,
        frozen_identity=_identity(),
        family_factory=_synthetic_factory(client),
    )
    assert result.completed is True
    assert result.measurement_admitted is True
    assert result.wire_shape_valid == 72
    assert result.semantic_domain_valid == 71
    invalid = result.cells[2]
    assert invalid.score.wire_shape_valid is True
    assert invalid.score.semantic_domain_valid is False
    assert invalid.score.failure_reason == "semantic_domain: invalid permutation"
    assert result.confirmatory is not None


def test_failure_after_scientific_attempt_is_terminal_without_rescue() -> None:
    client = _CampaignClient(fail_on_attempt=7)
    result = run_semantic_role_specificity_campaign(
        client,
        frozen_identity=_identity(),
        family_factory=_synthetic_factory(client),
    )
    assert result.completed is False
    assert result.measurement_admitted is False
    assert result.classification == (
        "MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND"
    )
    assert result.semantic_calls == 7
    assert result.provider_completions == 6
    assert result.input_token_requests == result.input_token_completions == 14
    assert len(result.cells) == 6
    assert result.confirmatory is None
    assert result.citable_for_accessibility_claim is False


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


def test_llama_cpp_transport_uses_wire_only_schema_and_frozen_envelope() -> None:
    truth = generate_synthetic_canonical_payload(91_300_000_000_779)
    control = prepare_physical_mechanism_control(truth)
    fake = _FakeHttpClient(json.dumps(control.canonical_truth, sort_keys=True))
    client = SemanticRoleSpecificityLlamaCppClient(
        base_url="http://127.0.0.1:1234/v1",
        model="gemma-test",
        http_client=fake,  # type: ignore[arg-type]
    )
    try:
        completion = client.complete_named(
            physical_call_plan()[0],
            build_reconstruction_messages(
                control.serialized_by_surface[FUNCTION_SURFACE]
            ),
            output_kind="semantic_role_payload",
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
    schema_text = json.dumps(generation["response_format"], sort_keys=True)
    assert "uniqueItems" not in schema_text
    assert '"const"' not in schema_text
    assert '"enum"' not in schema_text
    assert completion.content == json.dumps(control.canonical_truth, sort_keys=True)
    assert client.provider_attempts == client.provider_completions == 1
    assert client.input_count_attempts == client.input_count_completions == 2


def test_wsl_adapter_pins_common_generation_and_target() -> None:
    root = Path(__file__).resolve().parents[2]
    identity = wsl.verify_common_physical_binding(root)
    assert identity["generation_id"] == "relay-common-physical-g2"
    assert identity["aggregate_identity"] == (
        "sha256:bb983011905bdd8b5393c2c3459b691289f5ced9a41561bb8dc7f642fa330b87"
    )
    assert wsl.TARGET_NAME == "v2:semantic-role-specificity"
    assert wsl.TARGET_MODULE == "tools.v2_cognitive_ir_role_specificity_llama_cpp_wsl"
    assert wsl.TARGET_REQUIRED_DISTRIBUTIONS == ("httpx",)
