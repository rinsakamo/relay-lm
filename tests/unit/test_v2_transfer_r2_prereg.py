from __future__ import annotations

from collections.abc import Mapping

import pytest

from relaylm.v2_transfer_actual_model import StructureHypothesis
from tools.v2_cognitive_work_structured_output_qualification import (
    StructuredOutputCompletion,
)
from tools.v2_transfer_r2_prereg import (
    ALPHA,
    BOOTSTRAP_RESAMPLES,
    CALLS_PER_FAMILY,
    EXAMPLES_VISIBLE_LEVELS,
    FAMILY_COUNT,
    MATERIAL_INTERACTION,
    MODULUS,
    PROVIDER_CALL_COUNT,
    R1_EXCLUDED_SEED,
    REGIMES,
    SEEDS_PER_REGIME,
    R2FamilyOutcome,
    R2PlanStructuredClient,
    R2TransferPreregistrationError,
    analyze_r2,
    call_plan,
    call_plan_digest,
    family_specs,
    generate_families,
    preregistration_digest,
    preregistration_identity,
    source_hypothesis_matches_family,
    transport_identity,
)
from tools.v2_transfer_r1_structured_client import (
    SOURCE_SCHEMA_NAME,
    TARGET_SCHEMA_NAME,
)


COMMIT = "a" * 40
OTHER_COMMIT = "b" * 40


class _FakeStructuredClient:
    def __init__(self) -> None:
        self.response_formats: list[Mapping[str, object]] = []

    def complete(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        response_format: Mapping[str, object],
    ) -> StructuredOutputCompletion:
        assert messages
        self.response_formats.append(response_format)
        schema_name = response_format["json_schema"]["name"]  # type: ignore[index]
        if schema_name == SOURCE_SCHEMA_NAME:
            content = (
                '{"permutation":[0,1,2,3],"offsets":[0,0,0,0],"modulus":10}'
            )
        else:
            assert schema_name == TARGET_SCHEMA_NAME
            content = "[0,0,0,0]"
        return StructuredOutputCompletion(
            content=content,
            input_tokens=1,
            output_tokens=1,
            response_id="fake",
            finish_reason="stop",
        )


def _curve(value: bool) -> tuple[bool, bool, bool, bool]:
    return (value, value, value, value)


def _outcomes(
    *,
    shared_t0: bool,
    shared_t1: bool,
    null_t0: bool,
    null_t1: bool,
    source_correct_count: int = FAMILY_COUNT,
) -> tuple[R2FamilyOutcome, ...]:
    results: list[R2FamilyOutcome] = []
    for spec in family_specs(COMMIT):
        is_shared = spec.regime == "shared"
        results.append(
            R2FamilyOutcome(
                family_index=spec.family_index,
                regime=spec.regime,
                seed=spec.seed,
                source_hypothesis_correct=spec.family_index < source_correct_count,
                t0=_curve(shared_t0 if is_shared else null_t0),
                t1=_curve(shared_t1 if is_shared else null_t1),
                t2=_curve(shared_t1 if is_shared else null_t1),
            )
        )
    return tuple(results)


def test_family_specs_are_fresh_balanced_unique_and_deterministic() -> None:
    specs = family_specs(COMMIT)
    assert len(specs) == FAMILY_COUNT == 16
    assert [spec.regime for spec in specs] == ["shared", "null"] * SEEDS_PER_REGIME
    assert sum(spec.regime == "shared" for spec in specs) == 8
    assert sum(spec.regime == "null" for spec in specs) == 8
    assert len({spec.seed for spec in specs}) == FAMILY_COUNT
    assert R1_EXCLUDED_SEED not in {spec.seed for spec in specs}
    assert specs == family_specs(COMMIT)
    assert {spec.seed for spec in specs} != {
        spec.seed for spec in family_specs(OTHER_COMMIT)
    }


def test_generated_families_match_preregistered_regimes_and_modulus() -> None:
    specs = family_specs(COMMIT)
    families = generate_families(COMMIT)
    assert len(families) == FAMILY_COUNT
    for spec, family in zip(specs, families, strict=True):
        assert family.seed == spec.seed
        assert family.regime == spec.regime
        assert family.modulus == MODULUS
        assert len(family.source_examples) == 4
        assert len(family.target_steps) == 4
        assert all(len(step.examples) == 3 for step in family.target_steps)


def test_call_plan_is_exactly_208_and_covers_full_adaptation_curve() -> None:
    plan = call_plan(COMMIT)
    assert len(plan) == PROVIDER_CALL_COUNT == 208
    assert CALLS_PER_FAMILY == 13
    assert sum(entry.phase == "source-learning" for entry in plan) == 16
    assert sum(entry.phase == "target" and entry.arm == "T0" for entry in plan) == 64
    assert sum(entry.phase == "target" and entry.arm == "T1" for entry in plan) == 64
    assert sum(entry.phase == "target" and entry.arm == "T2" for entry in plan) == 64
    assert tuple(entry.call_index for entry in plan) == tuple(range(PROVIDER_CALL_COUNT))

    for family_index in range(FAMILY_COUNT):
        family_entries = [entry for entry in plan if entry.family_index == family_index]
        assert family_entries[0].phase == "source-learning"
        for arm_index, arm in enumerate(("T0", "T1", "T2")):
            start = 1 + arm_index * len(EXAMPLES_VISIBLE_LEVELS)
            arm_entries = family_entries[start : start + len(EXAMPLES_VISIBLE_LEVELS)]
            assert [entry.arm for entry in arm_entries] == [arm] * 4
            assert [entry.examples_visible for entry in arm_entries] == [0, 1, 2, 3]


def test_plan_aware_transport_uses_source_then_target_schema_and_rejects_call_209() -> None:
    fake = _FakeStructuredClient()
    client = R2PlanStructuredClient(
        preregistration_commit=COMMIT,
        structured_client=fake,
    )
    messages = ({"role": "user", "content": "fixture"},)
    plan = call_plan(COMMIT)
    for entry in plan:
        assert client.next_plan_entry == entry
        completion = client.complete(messages)
        assert completion.input_tokens == 1
        assert completion.output_tokens == 1
    assert client.call_count == PROVIDER_CALL_COUNT
    assert client.next_plan_entry is None
    assert len(fake.response_formats) == PROVIDER_CALL_COUNT
    assert sum(
        item["json_schema"]["name"] == SOURCE_SCHEMA_NAME  # type: ignore[index]
        for item in fake.response_formats
    ) == 16
    assert sum(
        item["json_schema"]["name"] == TARGET_SCHEMA_NAME  # type: ignore[index]
        for item in fake.response_formats
    ) == 192
    with pytest.raises(R2TransferPreregistrationError):
        client.complete(messages)


def test_source_hypothesis_match_is_exact_not_merely_well_formed() -> None:
    family = generate_families(COMMIT)[0]
    exact = StructureHypothesis(
        family.source_rule.permutation,
        family.source_rule.offsets,
        family.source_rule.modulus,
    )
    wrong_offsets = list(family.source_rule.offsets)
    wrong_offsets[0] = (wrong_offsets[0] + 1) % family.modulus
    wrong = StructureHypothesis(
        family.source_rule.permutation,
        tuple(wrong_offsets),
        family.source_rule.modulus,
    )
    assert source_hypothesis_matches_family(exact, family) is True
    assert source_hypothesis_matches_family(wrong, family) is False


def test_transfer_signal_requires_shared_minus_null_interaction() -> None:
    analysis = analyze_r2(
        _outcomes(
            shared_t0=False,
            shared_t1=True,
            null_t0=False,
            null_t1=False,
        ),
        preregistration_commit=COMMIT,
    )
    assert analysis.shared_gain == 1.0
    assert analysis.null_gain == 0.0
    assert analysis.interaction == 1.0
    assert analysis.exact_p_value <= ALPHA
    assert analysis.bootstrap_interval == (1.0, 1.0)
    assert analysis.category == "TRANSFER_SIGNAL"


def test_generic_context_effect_does_not_count_as_transfer() -> None:
    analysis = analyze_r2(
        _outcomes(
            shared_t0=False,
            shared_t1=True,
            null_t0=False,
            null_t1=True,
        ),
        preregistration_commit=COMMIT,
    )
    assert analysis.shared_gain == 1.0
    assert analysis.null_gain == 1.0
    assert analysis.interaction == 0.0
    assert analysis.category == "GENERIC_CONTEXT_EFFECT"


def test_source_learning_failure_precedes_transfer_interpretation() -> None:
    analysis = analyze_r2(
        _outcomes(
            shared_t0=False,
            shared_t1=True,
            null_t0=False,
            null_t1=False,
            source_correct_count=7,
        ),
        preregistration_commit=COMMIT,
    )
    assert analysis.source_correct_rate == 7 / 16
    assert analysis.category == "NO_SOURCE_LEARNING"


def test_incomplete_campaign_is_inconclusive_even_with_apparent_signal() -> None:
    analysis = analyze_r2(
        _outcomes(
            shared_t0=False,
            shared_t1=True,
            null_t0=False,
            null_t1=False,
        ),
        preregistration_commit=COMMIT,
        complete=False,
    )
    assert analysis.category == "INCONCLUSIVE"


def test_preregistration_identity_freezes_statistics_transport_and_plan() -> None:
    identity = preregistration_identity(COMMIT)
    assert identity["version"] == "relaylm2-transfer-r2-shared-null-v1"
    assert identity["provider_call_count"] == PROVIDER_CALL_COUNT
    assert identity["call_plan_digest"] == call_plan_digest(COMMIT)
    assert identity["transport"] == transport_identity(COMMIT)
    statistics = identity["statistics"]
    assert statistics["alpha"] == ALPHA  # type: ignore[index]
    assert statistics["bootstrap_resamples"] == BOOTSTRAP_RESAMPLES  # type: ignore[index]
    assert statistics["material_interaction"] == MATERIAL_INTERACTION  # type: ignore[index]
    assert preregistration_digest(COMMIT) == preregistration_digest(COMMIT)
    assert preregistration_digest(COMMIT) != preregistration_digest(OTHER_COMMIT)


def test_invalid_commit_is_rejected() -> None:
    with pytest.raises(R2TransferPreregistrationError):
        family_specs("not-a-commit")
