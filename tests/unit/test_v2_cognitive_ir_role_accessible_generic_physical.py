from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from relaylm.v2_cognitive_ir_actual_model import build_s2_formation_messages
from relaylm.v2_cognitive_ir_experiment import prepare_r0_representation_arms
from relaylm.v2_cognitive_ir_role_accessible_generic import (
    ARCHITECTURE_CONSEQUENCE,
    CONFIRMATORY_CONTRASTS,
    LEGACY_SURFACE,
    MAX_OUTPUT_TOKENS,
    PHYSICAL_EXECUTION_AUTHORIZED,
    ROLE_FUNCTIONAL_SURFACE,
    SURFACES,
    TYPED_SURFACE,
    build_formation_messages,
    preregistered_seeds,
)
import relaylm.v2_cognitive_ir_role_accessible_generic_physical as physical
from relaylm.v2_cognitive_ir_role_accessible_generic_physical import (
    FrozenConsumerIdentity,
    RoleAccessibleGenericPhysicalError,
    freeze_consumer_identity,
    generate_scientific_shared_family,
    generate_synthetic_shared_family,
    physical_call_plan,
    prepare_physical_representations,
    run_role_accessible_generic_campaign,
    validate_physical_adapter_binding,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from tools.v2_cognitive_ir_role_accessible_generic_llama_cpp import (
    RoleAccessibleGenericInputCounterPreflight,
    RoleAccessibleGenericLlamaCppClient,
    preflight_role_accessible_generic_input_counter,
)
import tools.v2_cognitive_ir_role_accessible_generic_llama_cpp as transport
import tools.v2_cognitive_ir_role_accessible_generic_llama_cpp_transaction as tx
import tools.v2_cognitive_ir_role_accessible_generic_llama_cpp_wsl as wsl


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
    identity = freeze_consumer_identity(
        repository_commit="a" * 40,
        repository_tree="b" * 40,
        model="gemma-test",
        runtime_attestation=_runtime_attestation(),
    )
    identity.validate()
    return identity


def test_binding_is_zero_gpu_and_does_not_materialize_official_families(
    monkeypatch,
) -> None:
    def forbidden(_seed: int):
        raise AssertionError("binding validation materialized official E5 material")

    monkeypatch.setattr(physical, "_repository_generate_shared_family", forbidden)
    validate_physical_adapter_binding()
    assert len(preregistered_seeds()) == 24
    assert len(set(preregistered_seeds())) == 24
    assert len(physical_call_plan()) == 96
    assert len(set(physical_call_plan())) == 96
    assert physical.SCIENTIFIC_INPUT_TOKEN_REQUESTS == 192
    assert physical.MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS == 2
    assert MAX_OUTPUT_TOKENS == 1024
    assert PHYSICAL_EXECUTION_AUTHORIZED is False
    assert ARCHITECTURE_CONSEQUENCE == "NONE"


def test_synthetic_paths_reject_all_preregistered_seeds() -> None:
    synthetic = generate_synthetic_shared_family(91_600_000_000_001)
    assert synthetic.regime == "shared"
    assert synthetic.source_rule == synthetic.target_rules[0]
    for seed in preregistered_seeds():
        with pytest.raises(ValueError):
            generate_synthetic_shared_family(seed)


def test_official_material_guard_fails_before_generator(monkeypatch) -> None:
    def forbidden(_seed: int):
        raise AssertionError("bad admission reached exact official generation")

    monkeypatch.setattr(physical, "_repository_generate_shared_family", forbidden)
    seeds = preregistered_seeds()
    with pytest.raises(RoleAccessibleGenericPhysicalError):
        generate_scientific_shared_family(
            index=0,
            seed=seeds[1],
            frozen_identity=_identity(),
        )
    with pytest.raises(RoleAccessibleGenericPhysicalError):
        generate_scientific_shared_family(
            index=0,
            seed=seeds[0],
            frozen_identity=None,  # type: ignore[arg-type]
        )


def test_formation_is_historical_p4_and_contains_no_hidden_rule() -> None:
    family = generate_synthetic_shared_family(91_600_000_000_002)
    messages = build_formation_messages(family)
    assert messages == build_s2_formation_messages("P4_MEMORY_PLUS_STRUCTURE", family)
    packet = json.loads(messages[1]["content"])
    assert set(packet) == {"modulus", "examples"}
    assert "source_rule" not in messages[1]["content"]
    assert "target_rules" not in messages[1]["content"]


def test_model_formed_t_g_l_are_semantically_equal_and_provenance_matched() -> None:
    family = generate_synthetic_shared_family(91_600_000_000_003)
    learned = {
        "permutation": list(family.source_rule.permutation),
        "offsets": list(family.source_rule.offsets),
        "modulus": family.modulus,
    }
    prepared = prepare_physical_representations(
        learned_rule=learned,
        family=family,
    )
    assert set(prepared.serialized_by_surface) == set(SURFACES)
    assert len(set(prepared.serialized_by_surface.values())) == 3
    historical = prepare_r0_representation_arms(family)
    assert prepared.provenance_handles == historical["P0_RAW_HISTORY"].provenance_handles

    typed = json.loads(prepared.serialized_by_surface[TYPED_SURFACE])
    role = json.loads(prepared.serialized_by_surface[ROLE_FUNCTIONAL_SURFACE])
    legacy = json.loads(prepared.serialized_by_surface[LEGACY_SURFACE])
    assert set(typed) == {"memory", "structure"}
    assert set(role) == {"context", "relation"}
    assert set(role["context"]) == {"source_handles"}
    assert set(role["relation"]) == {
        "transform_kind",
        "index_reordering",
        "additive_shifts",
        "modular_divisor",
    }
    assert set(legacy["context"]) == {"refs"}
    assert set(legacy["relation"]) == {"kind", "a", "b", "n"}
    role_keys = json.dumps(sorted(role["context"]) + sorted(role["relation"]))
    assert "memory" not in role_keys.lower()
    assert "structure" not in role_keys.lower()


def test_transaction_counter_preflight_precedes_consumer_freeze_and_material(
    monkeypatch,
) -> None:
    events: list[str] = []

    def fake_preflight(*, base_url: str, model: str):
        assert base_url == "http://127.0.0.1:1234/v1"
        assert model == "gemma-test"
        events.append("preflight")
        return RoleAccessibleGenericInputCounterPreflight(
            total_input_tokens=12,
            framing_input_tokens=4,
            request_attempts=2,
            request_completions=2,
        )

    def forbidden(_seed: int):
        raise AssertionError("consumer freeze materialized official E5 material")

    monkeypatch.setattr(
        tx,
        "preflight_role_accessible_generic_input_counter",
        fake_preflight,
    )
    monkeypatch.setattr(physical, "_repository_generate_shared_family", forbidden)
    identity, counter = tx._prepare_consumer_identity(
        repository_commit="a" * 40,
        repository_tree="b" * 40,
        model="gemma-test",
        runtime_attestation=_runtime_attestation(),
        base_url="http://127.0.0.1:1234/v1",
    )
    events.append("frozen")
    assert events == ["preflight", "frozen"]
    assert identity.max_output_tokens == 1024
    assert counter.request_attempts == counter.request_completions == 2


class _CampaignClient:
    def __init__(
        self,
        *,
        fail_on_attempt: int | None = None,
        wrong_surface: str | None = None,
    ) -> None:
        self.plan = physical_call_plan()
        self.provider_attempts = 0
        self.provider_completions = 0
        self.input_count_attempts = 0
        self.input_count_completions = 0
        self.fail_on_attempt = fail_on_attempt
        self.wrong_surface = wrong_surface
        self.families: dict[int, object] = {}
        self.output_kinds: list[str] = []

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        del messages
        assert question_id == self.plan[self.provider_attempts]
        self.input_count_attempts += 2
        self.input_count_completions += 2
        self.provider_attempts += 1
        self.output_kinds.append(output_kind)
        if self.fail_on_attempt == self.provider_attempts:
            raise RuntimeError("synthetic provider failure after spend")

        _prefix, index_text, _seed_text, label = question_id.split(":")
        family = self.families[int(index_text)]
        if label == "FORM_P4":
            assert output_kind == "rule"
            content = json.dumps(
                {
                    "permutation": list(family.source_rule.permutation),
                    "offsets": list(family.source_rule.offsets),
                    "modulus": family.modulus,
                },
                sort_keys=True,
            )
        else:
            assert output_kind == "vector"
            vector = list(family.expected_output(0))
            if self.wrong_surface == label:
                vector[0] = (vector[0] + 1) % family.modulus
            content = json.dumps(vector)
        self.provider_completions += 1
        return ExperimentCompletion(
            content=content,
            input_tokens=19,
            output_tokens=7,
            response_id=f"fake-{self.provider_attempts}",
        )

    def require_complete_plan(self) -> None:
        assert self.provider_attempts == len(self.plan)
        assert self.provider_completions == len(self.plan)
        assert self.input_count_attempts == 2 * len(self.plan)
        assert self.input_count_completions == self.input_count_attempts


def _synthetic_factory(client: _CampaignClient):
    def factory(index: int, _seed: int, identity: FrozenConsumerIdentity):
        identity.validate()
        family = generate_synthetic_shared_family(91_600_001_000_000 + index)
        client.families[index] = family
        return family

    return factory


def test_synthetic_campaign_is_exact_96_calls_192_counts_and_t_g_l_paired() -> None:
    client = _CampaignClient()
    result = run_role_accessible_generic_campaign(
        client,
        frozen_identity=_identity(),
        family_factory=_synthetic_factory(client),
    )
    assert result.completed is True
    assert result.measurement_admitted is True
    assert result.semantic_calls == result.provider_completions == 96
    assert result.input_token_requests == result.input_token_completions == 192
    assert len(result.formations) == 24
    assert len(result.cells) == 72
    assert result.semantic_equal_families == 24
    assert result.wire_shape_valid == result.semantic_domain_valid == 72
    assert result.surface_exact_totals == {surface: 24 for surface in SURFACES}
    assert result.classification == (
        "NO_DECLARED_TYPED_OR_ROLE_ACCESSIBILITY_GAP_DETECTED_AT_THIS_RESOLUTION"
    )
    assert result.statistical_status == "UNDERDETERMINED"
    assert result.citable_for_downstream_claim is True
    assert set(result.confirmatory or {}) == set(CONFIRMATORY_CONTRASTS)
    assert result.descriptive_typed_vs_legacy is not None
    assert client.output_kinds == ["rule", "vector", "vector", "vector"] * 24
    for index in range(24):
        family = result.cells[3 * index : 3 * index + 3]
        assert tuple(cell.surface for cell in family) == SURFACES
        assert len({cell.semantic_digest for cell in family}) == 1
        assert len({cell.serialized_representation for cell in family}) == 3


def test_valid_but_wrong_vector_is_scientific_outcome_not_transport_failure() -> None:
    client = _CampaignClient(wrong_surface=LEGACY_SURFACE)
    result = run_role_accessible_generic_campaign(
        client,
        frozen_identity=_identity(),
        family_factory=_synthetic_factory(client),
    )
    assert result.completed is True
    assert result.measurement_admitted is True
    assert result.wire_shape_valid == 72
    assert result.surface_exact_totals[LEGACY_SURFACE] == 0
    assert result.surface_exact_totals[TYPED_SURFACE] == 24
    assert result.surface_exact_totals[ROLE_FUNCTIONAL_SURFACE] == 24
    assert result.classification == "ROLE_ACCESSIBILITY_DOWNSTREAM_DIFFERENCE_DETECTED"


def test_failure_after_scientific_spend_terminalizes_without_rescue() -> None:
    client = _CampaignClient(fail_on_attempt=7)
    result = run_role_accessible_generic_campaign(
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
    assert result.confirmatory is None
    assert result.citable_for_downstream_claim is False


def test_completed_panel_classification_set_is_exact() -> None:
    names = CONFIRMATORY_CONTRASTS
    observed = set()
    for h1 in (False, True):
        for h2 in (False, True):
            contrasts = {
                names[0]: SimpleNamespace(holm_reject=h1),
                names[1]: SimpleNamespace(holm_reject=h2),
            }
            observed.add(physical._classification(contrasts)[0])
    assert observed == {
        "TYPED_PACKAGING_DIFFERENCE_DETECTED_AFTER_ROLE_ACCESSIBILITY_CONTROL",
        "ROLE_ACCESSIBILITY_DOWNSTREAM_DIFFERENCE_DETECTED",
        "MULTIPLE_TYPED_AND_ROLE_ACCESSIBILITY_COMPONENTS_DETECTED",
        "NO_DECLARED_TYPED_OR_ROLE_ACCESSIBILITY_GAP_DETECTED_AT_THIS_RESOLUTION",
    }


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload
        self.status_code = 200
        self.is_success = True

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
        schema = body["response_format"]["json_schema"]["name"]
        if schema == "relaylm2_s3_reusable_rule":
            content = json.dumps(
                {
                    "permutation": [0, 1, 2, 3],
                    "offsets": [1, 1, 1, 0],
                    "modulus": 10,
                }
            )
        else:
            content = "[1,2,3,4]"
        return _FakeResponse(
            {
                "id": "fake-completion",
                "choices": [
                    {"finish_reason": "stop", "message": {"content": content}}
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


def test_transport_uses_rule_then_vector_strict_schemas_and_1024_envelope() -> None:
    family = generate_synthetic_shared_family(91_600_000_000_004)
    fake = _FakeHttpClient()
    client = RoleAccessibleGenericLlamaCppClient(
        base_url="http://127.0.0.1:1234/v1",
        model="gemma-test",
        http_client=fake,  # type: ignore[arg-type]
    )
    try:
        formation = client.complete_named(
            physical_call_plan()[0],
            build_formation_messages(family),
            output_kind="rule",
        )
        prepared = prepare_physical_representations(
            learned_rule=json.loads(formation.content),
            family=family,
        )
        client.complete_named(
            physical_call_plan()[1],
            physical.build_target_messages(TYPED_SURFACE, prepared, family),
            output_kind="vector",
        )
    finally:
        client.close()

    generation_requests = [
        body for url, body in fake.requests if url.endswith("/chat/completions")
    ]
    assert len(generation_requests) == 2
    first, second = generation_requests
    assert first["max_tokens"] == second["max_tokens"] == 1024
    assert first["temperature"] == second["temperature"] == 0.0
    assert first["reasoning_effort"] == second["reasoning_effort"] == "none"
    assert first["stream"] is second["stream"] is False
    assert "seed" not in first and "seed" not in second
    assert first["response_format"]["json_schema"]["name"] == (
        "relaylm2_s3_reusable_rule"
    )
    assert second["response_format"]["json_schema"]["name"] == (
        "relaylm2_s3_target_vector"
    )
    assert client.provider_attempts == client.provider_completions == 2
    assert client.input_count_attempts == client.input_count_completions == 4


def test_preflight_performs_exactly_two_non_scientific_counter_requests(
    monkeypatch,
) -> None:
    fake = _FakeHttpClient()
    monkeypatch.setattr(transport.httpx, "Client", lambda **_kwargs: fake)
    result = preflight_role_accessible_generic_input_counter(
        base_url="http://127.0.0.1:1234/v1",
        model="gemma-test",
    )
    assert result.request_attempts == result.request_completions == 2
    assert len(fake.requests) == 2
    assert all(url.endswith("/input_tokens") for url, _body in fake.requests)


def test_wsl_adapter_pins_common_generation_and_registered_target() -> None:
    root = Path(__file__).resolve().parents[2]
    identity = wsl.verify_common_physical_binding(root)
    assert identity["generation_id"] == "relay-common-physical-g2"
    assert identity["aggregate_identity"] == (
        "sha256:bb983011905bdd8b5393c2c3459b691289f5ced9a41561bb8dc7f642fa330b87"
    )
    assert wsl.TARGET_NAME == "v2:role-accessible-generic"
    assert wsl.TARGET_MODULE == (
        "tools.v2_cognitive_ir_role_accessible_generic_llama_cpp_wsl"
    )
    assert wsl.TARGET_REQUIRED_DISTRIBUTIONS == ("httpx",)
