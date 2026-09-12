from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib

import relaylm.v2_cognitive_ir_s3 as base
from relaylm.v2_cognitive_ir_attack_observability_calibration import ATTACK_OBS_SEEDS
from relaylm.v2_cognitive_ir_calibration import CALIBRATION_SEEDS
from relaylm.v2_cognitive_ir_calibration_v2 import CALIBRATION_V2_SEEDS
from relaylm.v2_cognitive_ir_p2_boundedness_qual_v2 import P2_BOUNDEDNESS_QUAL_V2_SEEDS
from relaylm.v2_cognitive_ir_p2_termination_qual import P2_TERMINATION_QUAL_SEEDS
from relaylm.v2_cognitive_ir_s2_selected import S2_SELECTED_SEED
from relaylm.v2_cognitive_ir_s3_r2 import HISTORICAL_S3_V1_SEEDS, S3_R2_SEEDS
from relaylm.v2_cognitive_ir_s3_r3 import S3_R3_SEEDS
from relaylm.v2_cognitive_ir_s3_r4 import (
    S3_R4_SEEDS,
    form_s2_representations_r4,
)
from relaylm.v2_cognitive_ir_s3_r5 import (
    S3_R5_SEEDS,
    exact_first_arm_superiority_p,
    paired_outcome_cells,
    validate_s3_r5_preregistration,
    weakly_pareto_dominates,
)
from relaylm.v2_cognitive_ir_shared_floor_calibration import SHARED_FLOOR_SEEDS
from relaylm.v2_cognitive_ir_shared_floor_calibration_v2 import SHARED_FLOOR_V2_SEEDS
from relaylm.v2_transfer_experiment import PublicExample, TargetStep, TransferFamily, VectorRule


D1_SCHEMA = "relaylm2-cognitive-ir-s3-r6d-d1-prereg-v1"
D1_LABEL = "relaylm2-cognitive-ir-s3-r6d-shared-discriminator-v1"
D1_CLAIM = "CITABLE_D1_WITHIN_DECLARED_SCOPE"
D1_INCOMPLETE_CLAIM = "D1_INCOMPLETE"
D1_ARCHITECTURE_CONSEQUENCE = "NONE"
D1_REGIME = "shared"
D1_SELECTED_DIFFICULTY = "K3_THREE_ACTIVE"
D1_ACTIVE_COORDINATES = 3
D1_FAMILY_COUNT = 24
D1_CALLS_PER_FAMILY = 41
D1_TOTAL_SEMANTIC_CALLS = 984
D1_TOTAL_INPUT_TOKEN_REQUESTS = 1968
D1_MAX_OUTPUT_TOKENS = 1024
D1_PREREGISTRATION_SHA256 = (
    "b3709c57d7c421060d3776932442ef1e06ea808be1abfb3833d7992c5cf5f1b4"
)
D1_SEEDS = (
    1079450750,
    2044967339,
    1618439815,
    1703928454,
    2118795471,
    1988710105,
    1975963702,
    270330662,
    924576050,
    288951690,
    1495273968,
    467079912,
    1228436443,
    174115850,
    1230751945,
    1156452390,
    1614943672,
    1835075237,
    89123956,
    136500175,
    404655139,
    2097607365,
    1694929697,
    1175126817,
)

_RELEVANT_ISSUE_IDENTITIES = {
    2211,
    2530,
    2533,
    2538,
    2571,
    2572,
    2577,
    2580,
    2595,
    2596,
    2598,
    2600,
    2601,
    2610,
    2612,
    2614,
    2619,
    2620,
    2628,
    2634,
    2635,
    2651,
    2658,
    2662,
    2665,
    2666,
    2667,
    2669,
    2670,
    2671,
}

_FORMATION_ALIAS = {
    "P2_ORDINARY_SUMMARY": "P2",
    "P3_SEMANTIC_CACHE": "P3",
    "P4_MEMORY_PLUS_STRUCTURE": "P4",
    "P5_STRUCTURE_ONLY_RECONSTRUCTABLE": "P4",
    "P6_GENERIC_EQUAL_INFORMATION": "P4",
}


class D1BindingError(ValueError):
    """The #2666 shared discriminator cannot be bound exactly."""


def _flatten(values: Mapping[str, tuple[int, ...]]) -> set[int]:
    return {seed for seeds in values.values() for seed in seeds}


def derive_d1_seed(index: int) -> int:
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < D1_FAMILY_COUNT:
        raise D1BindingError("D1 seed index must be 0..23")
    raw = hashlib.sha256(
        f"{D1_LABEL}|shared|seed|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def validate_d1_preregistration() -> None:
    validate_s3_r5_preregistration()
    derived = tuple(derive_d1_seed(index) for index in range(D1_FAMILY_COUNT))
    if derived != D1_SEEDS:
        raise D1BindingError("derived D1 seeds drifted from #2666")
    if len(set(D1_SEEDS)) != D1_FAMILY_COUNT:
        raise D1BindingError("D1 seeds are not unique")

    historical = {
        *CALIBRATION_SEEDS,
        *CALIBRATION_V2_SEEDS,
        *_flatten(P2_TERMINATION_QUAL_SEEDS),
        *_flatten(P2_BOUNDEDNESS_QUAL_V2_SEEDS),
        S2_SELECTED_SEED,
        *_flatten(HISTORICAL_S3_V1_SEEDS),
        *_flatten(S3_R2_SEEDS),
        *_flatten(S3_R3_SEEDS),
        *_flatten(S3_R4_SEEDS),
        *_flatten(S3_R5_SEEDS),
        *SHARED_FLOOR_SEEDS,
        *SHARED_FLOOR_V2_SEEDS,
        *_flatten(ATTACK_OBS_SEEDS),
        *_RELEVANT_ISSUE_IDENTITIES,
    }
    overlap = sorted(set(D1_SEEDS) & historical)
    if overlap:
        raise D1BindingError(f"D1 seeds overlap historical authority: {overlap}")

    if (
        D1_REGIME,
        D1_SELECTED_DIFFICULTY,
        D1_ACTIVE_COORDINATES,
        D1_FAMILY_COUNT,
        D1_CALLS_PER_FAMILY,
        D1_TOTAL_SEMANTIC_CALLS,
        D1_TOTAL_INPUT_TOKEN_REQUESTS,
    ) != ("shared", "K3_THREE_ACTIVE", 3, 24, 41, 984, 1968):
        raise D1BindingError("D1 frozen campaign ledger drifted")
    if (
        base.S3_VECTOR_WIDTH,
        base.S3_MODULUS,
        base.S3_SOURCE_EXAMPLES,
        base.S3_TARGET_STEPS,
        base.S3_SHIFT_INDEX,
        base.S3_EXAMPLES_VISIBLE,
    ) != (4, 10, 4, 4, 2, 0):
        raise D1BindingError("D1 inherited task geometry drifted")
    if (
        base.S3_SURFACE_EFFECT_MAX,
        base.S3_SEMANTIC_EFFECT_MIN,
        base.S3_EFFECT_MARGIN_MIN,
    ) != (0.15, 0.20, 0.15):
        raise D1BindingError("D1 semantic-invariance thresholds drifted")
    if D1_MAX_OUTPUT_TOKENS != 1024:
        raise D1BindingError("D1 output ceiling drifted")


def _digest(seed: int, purpose: str) -> bytes:
    return hashlib.sha256(
        f"{D1_LABEL}|shared|{seed}|{purpose}".encode("utf-8")
    ).digest()


def _k3_offsets(seed: int) -> tuple[int, ...]:
    ranked = sorted(
        range(base.S3_VECTOR_WIDTH),
        key=lambda coordinate: (
            _digest(seed, f"source:active-rank:{coordinate}"),
            coordinate,
        ),
    )
    active = set(ranked[:D1_ACTIVE_COORDINATES])
    offsets = tuple(
        1 + (_digest(seed, f"source:offset-value:{coordinate}")[0] % 3)
        if coordinate in active
        else 0
        for coordinate in range(base.S3_VECTOR_WIDTH)
    )
    if sum(value != 0 for value in offsets) != D1_ACTIVE_COORDINATES:
        raise AssertionError("D1 K3 active-count drifted")
    return offsets


def _rule(seed: int) -> VectorRule:
    return VectorRule(
        tuple(range(base.S3_VECTOR_WIDTH)),
        _k3_offsets(seed),
        base.S3_MODULUS,
    )


def _bounded_vector(
    seed: int,
    purpose: str,
    rule: VectorRule,
) -> tuple[int, ...]:
    raw = _digest(seed, purpose)
    maxima = [base.S3_MODULUS - 1] * base.S3_VECTOR_WIDTH
    for output_index, input_index in enumerate(rule.permutation):
        maxima[input_index] = min(
            maxima[input_index],
            rule.modulus - 1 - rule.offsets[output_index],
        )
    return tuple(
        raw[index] % (maxima[index] + 1)
        for index in range(base.S3_VECTOR_WIDTH)
    )


def generate_d1_family(regime: str, index: int) -> TransferFamily:
    if regime != D1_REGIME:
        raise D1BindingError(f"D1 supports shared only, got {regime}")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < D1_FAMILY_COUNT:
        raise D1BindingError("D1 family index must be 0..23")

    seed = D1_SEEDS[index]
    rule = _rule(seed)
    source_examples = tuple(
        PublicExample(
            values := _bounded_vector(seed, f"source:example:{example_index}", rule),
            rule.apply(values),
        )
        for example_index in range(base.S3_SOURCE_EXAMPLES)
    )
    target_steps = tuple(
        TargetStep(
            examples=tuple(
                PublicExample(
                    values := _bounded_vector(
                        seed,
                        f"target:{step_index}:example:{example_index}",
                        rule,
                    ),
                    rule.apply(values),
                )
                for example_index in range(3)
            ),
            query=_bounded_vector(seed, f"target:{step_index}:query", rule),
        )
        for step_index in range(base.S3_TARGET_STEPS)
    )
    family = TransferFamily(
        seed=seed,
        regime=D1_REGIME,
        modulus=base.S3_MODULUS,
        source_rule=rule,
        target_rules=(rule,) * base.S3_TARGET_STEPS,
        source_examples=source_examples,
        target_steps=target_steps,
        shift_index=None,
    )
    _require_no_wrap(family)
    return family


def _require_no_wrap(family: TransferFamily) -> None:
    vectors = [example.input_values for example in family.source_examples]
    for step in family.target_steps:
        vectors.extend(example.input_values for example in step.examples)
        vectors.append(step.query)
    if any(
        vector[input_index] + family.source_rule.offsets[output_index] >= family.modulus
        for vector in vectors
        for output_index, input_index in enumerate(family.source_rule.permutation)
    ):
        raise D1BindingError("D1 generated vector unexpectedly wraps")


def d1_call_plan(regime: str) -> tuple[str, ...]:
    if regime != D1_REGIME:
        raise D1BindingError(f"D1 supports shared only, got {regime}")
    plan: list[str] = []
    for index, seed in enumerate(D1_SEEDS):
        prefix = f"shared:{index}:{seed}"
        plan.extend(f"{prefix}:form-{kind}" for kind in ("p2", "p3", "p4"))
        plan.extend(f"{prefix}:canonical:{arm}" for arm in base.REPRESENTATION_KINDS)
        plan.extend(
            f"{prefix}:surface:{arm}:{variant}"
            for arm in base.S3_TYPED_GENERIC_ARMS
            for variant in base.S3_SURFACE_VARIANTS
        )
        plan.extend(
            f"{prefix}:semantic:{arm}:{name}:{state}"
            for arm in base.S3_TYPED_GENERIC_ARMS
            for name in base.S3_SEMANTIC_INTERVENTIONS
            for state in ("STALE_ORIGINAL", "UPDATED_INTERVENED")
        )
        plan.extend(f"{prefix}:option:{arm}" for arm in base.REPRESENTATION_KINDS)
    if len(plan) != D1_TOTAL_SEMANTIC_CALLS:
        raise AssertionError("D1 call plan length drifted")
    return tuple(plan)


def run_d1_shard(client: base.S3Client, regime: str) -> base.S3ShardResult:
    if regime != D1_REGIME:
        raise D1BindingError(f"D1 supports shared only, got {regime}")
    before_attempts = client.provider_attempts
    before_input = client.input_count_attempts
    families = tuple(
        base.run_s3_family(client, D1_REGIME, index)
        for index in range(D1_FAMILY_COUNT)
    )
    semantic_calls = client.provider_attempts - before_attempts
    input_requests = client.input_count_attempts - before_input
    if semantic_calls != D1_TOTAL_SEMANTIC_CALLS:
        raise D1BindingError(
            f"D1 semantic-call drift: expected {D1_TOTAL_SEMANTIC_CALLS}, got {semantic_calls}"
        )
    if input_requests != D1_TOTAL_INPUT_TOKEN_REQUESTS:
        raise D1BindingError(
            "D1 exact input-token request drift: "
            f"expected {D1_TOTAL_INPUT_TOKEN_REQUESTS}, got {input_requests}"
        )

    ledger = base.S3WorkLedger()
    for family in families:
        for record in family.records:
            ledger.add(record)
        if not family.p4_p6_semantic_equal or not family.shared_formation_lineage:
            raise D1BindingError("D1 family violated semantic/formation lineage")
        if not family.provenance_audit_changed:
            raise D1BindingError("D1 provenance boundary audit failed")

    surface_effect, semantic_effect = base._effect_metrics(families)
    return base.S3ShardResult(
        regime=D1_REGIME,
        families=families,
        semantic_calls=semantic_calls,
        work=ledger.as_mapping(),
        surface_perturbation_effect=surface_effect,
        semantic_intervention_effect=semantic_effect,
        semantic_invariance_gate=base.semantic_invariance_gate(
            surface_effect,
            semantic_effect,
        ),
    )


def _require_complete_d1_shard(shard: base.S3ShardResult) -> None:
    if shard.regime != D1_REGIME or len(shard.families) != D1_FAMILY_COUNT:
        raise D1BindingError("D1 analysis requires one complete 24-family shared shard")
    if shard.semantic_calls != D1_TOTAL_SEMANTIC_CALLS:
        raise D1BindingError("D1 analysis received incomplete semantic-call ledger")
    if any(
        not family.p4_p6_semantic_equal
        or not family.shared_formation_lineage
        or not family.provenance_audit_changed
        for family in shard.families
    ):
        raise D1BindingError("D1 analysis received invalid lineage/semantic family")


def canonical_outcomes(
    shard: base.S3ShardResult,
    arm: str,
) -> tuple[bool, ...]:
    _require_complete_d1_shard(shard)
    if arm not in base.REPRESENTATION_KINDS:
        raise D1BindingError(f"unsupported D1 arm: {arm}")
    outcomes: list[bool] = []
    for family in shard.families:
        matches = [
            record
            for record in family.records
            if record.panel == "canonical" and record.arm == arm
        ]
        if len(matches) != 1 or matches[0].correct is None:
            raise D1BindingError(f"canonical record missing for {arm}")
        outcomes.append(bool(matches[0].correct))
    return tuple(outcomes)


def paired_contrast(
    shard: base.S3ShardResult,
    first_arm: str,
    second_arm: str,
) -> dict[str, int | float]:
    first = canonical_outcomes(shard, first_arm)
    second = canonical_outcomes(shard, second_arm)
    cells = paired_outcome_cells(first, second)
    return {
        **cells,
        "exact_directional_p": exact_first_arm_superiority_p(
            cells["first_only"],
            cells["second_only"],
        ),
    }


def canonical_correct_counts(shard: base.S3ShardResult) -> dict[str, int]:
    return {
        arm: sum(canonical_outcomes(shard, arm))
        for arm in base.REPRESENTATION_KINDS
    }


def canonical_natural_cost_vectors(
    shard: base.S3ShardResult,
) -> dict[str, dict[str, int]]:
    """Counterfactual per-arm formation+canonical Cognitive Work.

    P4/P5/P6 each carry the one shared P4 formation cost because each arm
    requires that learned semantic lineage to exist, while the physical run
    still performs that formation only once per family.
    """

    _require_complete_d1_shard(shard)
    components = (
        "C_build_and_model_calls",
        "C_model_input_tokens",
        "C_model_output_tokens",
        "C_project_bytes",
        "C_retrieve_operations",
    )
    totals = {
        arm: {component: 0 for component in components}
        for arm in base.REPRESENTATION_KINDS
    }
    for family in shard.families:
        for arm in base.REPRESENTATION_KINDS:
            selected: list[base.S3CallRecord] = []
            alias = _FORMATION_ALIAS.get(arm)
            if alias is not None:
                formation = [
                    record
                    for record in family.records
                    if record.panel == "formation" and record.arm == alias
                ]
                if len(formation) != 1:
                    raise D1BindingError(f"formation record missing for {arm}")
                selected.extend(formation)
            canonical = [
                record
                for record in family.records
                if record.panel == "canonical" and record.arm == arm
            ]
            if len(canonical) != 1:
                raise D1BindingError(f"canonical cost record missing for {arm}")
            selected.extend(canonical)
            totals[arm]["C_build_and_model_calls"] += len(selected)
            totals[arm]["C_model_input_tokens"] += sum(
                record.input_tokens for record in selected
            )
            totals[arm]["C_model_output_tokens"] += sum(
                record.output_tokens for record in selected
            )
            totals[arm]["C_project_bytes"] += sum(
                record.projected_bytes for record in selected
            )
            totals[arm]["C_retrieve_operations"] += sum(
                record.retrieval_operations for record in selected
            )
    return totals


def capability_pareto_dominators(
    shard: base.S3ShardResult,
    target_arm: str,
) -> tuple[str, ...]:
    counts = canonical_correct_counts(shard)
    costs = canonical_natural_cost_vectors(shard)
    if target_arm not in counts:
        raise D1BindingError(f"unsupported D1 target arm: {target_arm}")
    return tuple(
        arm
        for arm in base.REPRESENTATION_KINDS
        if arm != target_arm
        and counts[arm] >= counts[target_arm]
        and weakly_pareto_dominates(costs[arm], costs[target_arm])
    )


def option_value_correct_counts(shard: base.S3ShardResult) -> dict[str, int]:
    _require_complete_d1_shard(shard)
    counts = {arm: 0 for arm in base.REPRESENTATION_KINDS}
    for family in shard.families:
        for arm in base.REPRESENTATION_KINDS:
            matches = [
                record
                for record in family.records
                if record.panel == "option_value" and record.arm == arm
            ]
            if len(matches) != 1 or matches[0].correct is None:
                raise D1BindingError(f"option-value record missing for {arm}")
            counts[arm] += int(bool(matches[0].correct))
    return counts


def evaluate_d1(shard: base.S3ShardResult) -> dict[str, object]:
    _require_complete_d1_shard(shard)
    counts = canonical_correct_counts(shard)
    c1 = paired_contrast(
        shard,
        "P4_MEMORY_PLUS_STRUCTURE",
        "P3_SEMANTIC_CACHE",
    )
    c2 = paired_contrast(
        shard,
        "P4_MEMORY_PLUS_STRUCTURE",
        "P6_GENERIC_EQUAL_INFORMATION",
    )
    p3_p2 = paired_contrast(
        shard,
        "P3_SEMANTIC_CACHE",
        "P2_ORDINARY_SUMMARY",
    )
    p3_p1 = paired_contrast(
        shard,
        "P3_SEMANTIC_CACHE",
        "P1_RETRIEVAL_ONLY",
    )
    p4 = counts["P4_MEMORY_PLUS_STRUCTURE"]
    strict_controls = (
        "P0_RAW_HISTORY",
        "P1_RETRIEVAL_ONLY",
        "P2_ORDINARY_SUMMARY",
        "P3_SEMANTIC_CACHE",
        "P6_GENERIC_EQUAL_INFORMATION",
    )
    dedicated_type_earned = (
        shard.semantic_invariance_gate
        and float(c1["exact_directional_p"]) <= 0.05
        and float(c2["exact_directional_p"]) <= 0.05
        and all(p4 > counts[arm] for arm in strict_controls)
        and not capability_pareto_dominators(
            shard,
            "P4_MEMORY_PLUS_STRUCTURE",
        )
    )
    p4_vs_p3_supported = float(c1["exact_directional_p"]) <= 0.05
    semantic_cache_useful = (
        float(p3_p2["exact_directional_p"]) <= 0.05
        and float(p3_p1["exact_directional_p"]) <= 0.05
        and not capability_pareto_dominators(shard, "P3_SEMANTIC_CACHE")
        and not dedicated_type_earned
        and (
            counts["P3_SEMANTIC_CACHE"] >= p4
            or not p4_vs_p3_supported
        )
    )
    return {
        "canonical_correct": counts,
        "p4_gt_p3": c1,
        "p4_gt_p6": c2,
        "p3_gt_p2": p3_p2,
        "p3_gt_p1": p3_p1,
        "semantic_invariance_gate": shard.semantic_invariance_gate,
        "natural_cost": canonical_natural_cost_vectors(shard),
        "option_value_correct": option_value_correct_counts(shard),
        "p4_pareto_dominators": capability_pareto_dominators(
            shard,
            "P4_MEMORY_PLUS_STRUCTURE",
        ),
        "p3_pareto_dominators": capability_pareto_dominators(
            shard,
            "P3_SEMANTIC_CACHE",
        ),
        "dedicated_type_earned": dedicated_type_earned,
        "semantic_cache_useful": semantic_cache_useful,
        "architecture_consequence": D1_ARCHITECTURE_CONSEQUENCE,
    }


def activate_d1_preregistration() -> None:
    """Bind D1 into the existing listener-safe S3 transaction process only."""

    validate_d1_preregistration()
    base.S3_PREREGISTRATION_SCHEMA = D1_SCHEMA
    base.S3_PREREGISTRATION_SHA256 = D1_PREREGISTRATION_SHA256
    base.S3_LABEL = D1_LABEL
    base.S3_REGIMES = (D1_REGIME,)
    base.S3_SEEDS = {D1_REGIME: D1_SEEDS}
    base.S3_SHARD_CALLS = {D1_REGIME: D1_TOTAL_SEMANTIC_CALLS}
    base.S3_TOTAL_SEMANTIC_CALLS = D1_TOTAL_SEMANTIC_CALLS
    base.S3_TOTAL_INPUT_TOKEN_REQUESTS = D1_TOTAL_INPUT_TOKEN_REQUESTS
    base.S3_CLAIM = D1_CLAIM
    base.S3_INCOMPLETE_CLAIM = D1_INCOMPLETE_CLAIM
    base.generate_s3_family = generate_d1_family
    base.form_s2_representations = form_s2_representations_r4
    base.run_s3_shard = run_d1_shard
    base.s3_call_plan = d1_call_plan
