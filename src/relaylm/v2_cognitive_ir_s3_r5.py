from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import math

import relaylm.v2_cognitive_ir_s3 as base
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
    validate_s3_r4_preregistration,
)
from relaylm.v2_cognitive_ir_shared_floor_calibration import (
    SHARED_FLOOR_SEEDS,
    validate_shared_floor_preregistration,
)
from relaylm.v2_cognitive_ir_shared_floor_calibration_v2 import (
    SHARED_FLOOR_V2_SEEDS,
    validate_shared_floor_v2_preregistration,
)
from relaylm.v2_transfer_experiment import PublicExample, TargetStep, TransferFamily, VectorRule


S3_R5_PREREGISTRATION_SCHEMA = "relaylm2-cognitive-ir-s3-prereg-v5"
S3_R5_LABEL = "relaylm2-cognitive-ir-s3-semantic-invariance-v5-k3"
S3_R5_SELECTED_DIFFICULTY = "K3_THREE_ACTIVE"
S3_R5_ACTIVE_COORDINATES = 3
S3_R5_FAMILIES_PER_REGIME = 6
S3_R5_MAX_OUTPUT_TOKENS = 1024
S3_R5_SEEDS: Mapping[str, tuple[int, ...]] = {
    "shared": (
        745453345,
        1549669517,
        1235625757,
        193010981,
        1451955535,
        1138886096,
    ),
    "null": (
        2038910999,
        558665687,
        1363041899,
        1756158445,
        1783331388,
        2105217087,
    ),
    "mismatch": (
        804612455,
        196630042,
        742511018,
        1859640844,
        767626048,
        668367038,
    ),
    "shift": (
        1182307820,
        1332196726,
        131208839,
        814841957,
        1532205196,
        1600142459,
    ),
}
S3_R5_SHARD_CALLS: Mapping[str, int] = {
    "shared": 246,
    "null": 246,
    "mismatch": 246,
    "shift": 258,
}
S3_R5_TOTAL_SEMANTIC_CALLS = 996
S3_R5_TOTAL_INPUT_TOKEN_REQUESTS = 1992
S3_R5_P2_BUILDER = (
    "relaylm.v2_cognitive_ir_p2_boundedness_qual_v2."
    "build_margin_p2_formation_messages"
)
S3_R5_PREREGISTRATION_SHA256 = (
    "2f2dc45283af1ce2e4c921d483d16ea2908151ae7e55c50378ee92eecda15d65"
)

_HISTORICAL_ISSUE_SEEDS = {
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
}


class S3R5BindingError(ValueError):
    """The #2634 S3-R5 preregistration cannot be bound exactly."""


def _flatten(values: Mapping[str, tuple[int, ...]]) -> set[int]:
    return {seed for seeds in values.values() for seed in seeds}


def derive_s3_r5_seed(regime: str, index: int) -> int:
    if regime not in base.S3_REGIMES:
        raise S3R5BindingError(f"unsupported S3-R5 regime: {regime}")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 6:
        raise S3R5BindingError("S3-R5 seed index must be 0..5")
    raw = hashlib.sha256(
        f"{S3_R5_LABEL}|{regime}|seed|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def _spec_payload() -> dict[str, object]:
    return {
        "schema": S3_R5_PREREGISTRATION_SCHEMA,
        "label": S3_R5_LABEL,
        "selected_difficulty": S3_R5_SELECTED_DIFFICULTY,
        "active_coordinates_per_rule": S3_R5_ACTIVE_COORDINATES,
        "families_per_regime": S3_R5_FAMILIES_PER_REGIME,
        "regimes": list(base.S3_REGIMES),
        "seeds": {key: list(value) for key, value in S3_R5_SEEDS.items()},
        "shard_calls": dict(S3_R5_SHARD_CALLS),
        "total_semantic_calls": S3_R5_TOTAL_SEMANTIC_CALLS,
        "total_input_token_requests": S3_R5_TOTAL_INPUT_TOKEN_REQUESTS,
        "surface_effect_max": base.S3_SURFACE_EFFECT_MAX,
        "semantic_effect_min": base.S3_SEMANTIC_EFFECT_MIN,
        "effect_margin_min": base.S3_EFFECT_MARGIN_MIN,
        "max_output_tokens": S3_R5_MAX_OUTPUT_TOKENS,
        "vector_width": base.S3_VECTOR_WIDTH,
        "modulus": base.S3_MODULUS,
        "source_examples": base.S3_SOURCE_EXAMPLES,
        "target_steps": base.S3_TARGET_STEPS,
        "shift_index": base.S3_SHIFT_INDEX,
        "examples_visible": base.S3_EXAMPLES_VISIBLE,
        "p2_builder": S3_R5_P2_BUILDER,
    }


def _spec_sha256() -> str:
    canonical = json.dumps(
        _spec_payload(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_s3_r5_preregistration() -> None:
    # R4 is the historical behavioral baseline. Validate it while base still
    # carries the historical 498-call ledger, but do not re-run that validator
    # after R5 activation has deliberately rebound the ledger to 996 calls.
    if base.S3_PREREGISTRATION_SCHEMA != S3_R5_PREREGISTRATION_SCHEMA:
        validate_s3_r4_preregistration()
    validate_shared_floor_preregistration()
    validate_shared_floor_v2_preregistration()

    if tuple(base.S3_REGIMES) != ("shared", "null", "mismatch", "shift"):
        raise S3R5BindingError("S3-R5 regime order drifted")
    derived = {
        regime: tuple(derive_s3_r5_seed(regime, index) for index in range(6))
        for regime in base.S3_REGIMES
    }
    if derived != dict(S3_R5_SEEDS):
        raise S3R5BindingError("derived S3-R5 seeds drifted from #2634")
    fresh = _flatten(S3_R5_SEEDS)
    if len(fresh) != 24:
        raise S3R5BindingError("S3-R5 seeds are not unique")
    historical = {
        *CALIBRATION_SEEDS,
        *CALIBRATION_V2_SEEDS,
        *P2_TERMINATION_QUAL_SEEDS,
        *P2_BOUNDEDNESS_QUAL_V2_SEEDS,
        S2_SELECTED_SEED,
        *_flatten(HISTORICAL_S3_V1_SEEDS),
        *_flatten(S3_R2_SEEDS),
        *_flatten(S3_R3_SEEDS),
        *_flatten(S3_R4_SEEDS),
        *SHARED_FLOOR_SEEDS,
        *SHARED_FLOOR_V2_SEEDS,
        *_HISTORICAL_ISSUE_SEEDS,
    }
    overlap = sorted(fresh & historical)
    if overlap:
        raise S3R5BindingError(f"S3-R5 seeds overlap historical evidence: {overlap}")
    if S3_R5_SELECTED_DIFFICULTY != "K3_THREE_ACTIVE":
        raise S3R5BindingError("S3-R5 selected difficulty drifted")
    if (S3_R5_ACTIVE_COORDINATES, S3_R5_FAMILIES_PER_REGIME) != (3, 6):
        raise S3R5BindingError("S3-R5 K3/family-count contract drifted")
    if dict(S3_R5_SHARD_CALLS) != {
        "shared": 246,
        "null": 246,
        "mismatch": 246,
        "shift": 258,
    }:
        raise S3R5BindingError("S3-R5 shard call ledger drifted")
    if (S3_R5_TOTAL_SEMANTIC_CALLS, S3_R5_TOTAL_INPUT_TOKEN_REQUESTS) != (996, 1992):
        raise S3R5BindingError("S3-R5 campaign call ledger drifted")
    if (
        base.S3_VECTOR_WIDTH,
        base.S3_MODULUS,
        base.S3_SOURCE_EXAMPLES,
        base.S3_TARGET_STEPS,
        base.S3_SHIFT_INDEX,
        base.S3_EXAMPLES_VISIBLE,
    ) != (4, 10, 4, 4, 2, 0):
        raise S3R5BindingError("S3-R5 inherited task geometry drifted")
    if (
        base.S3_SURFACE_EFFECT_MAX,
        base.S3_SEMANTIC_EFFECT_MIN,
        base.S3_EFFECT_MARGIN_MIN,
    ) != (0.15, 0.20, 0.15):
        raise S3R5BindingError("S3-R5 semantic-invariance thresholds drifted")
    if S3_R5_MAX_OUTPUT_TOKENS != 1024:
        raise S3R5BindingError("S3-R5 output ceiling drifted")
    if _spec_sha256() != S3_R5_PREREGISTRATION_SHA256:
        raise S3R5BindingError("S3-R5 preregistration spec hash drifted")


def _digest(regime: str, seed: int, purpose: str) -> bytes:
    return hashlib.sha256(
        f"{S3_R5_LABEL}|{regime}|{seed}|{purpose}".encode("utf-8")
    ).digest()


def _k3_offsets(regime: str, seed: int, role: str) -> tuple[int, ...]:
    ranked = sorted(
        range(base.S3_VECTOR_WIDTH),
        key=lambda coordinate: (
            _digest(regime, seed, f"{role}:active-rank:{coordinate}"),
            coordinate,
        ),
    )
    active = set(ranked[:S3_R5_ACTIVE_COORDINATES])
    offsets = tuple(
        1 + (_digest(regime, seed, f"{role}:offset-value:{coordinate}")[0] % 3)
        if coordinate in active
        else 0
        for coordinate in range(base.S3_VECTOR_WIDTH)
    )
    _require_k3_offsets(offsets)
    return offsets


def _distinct_k3_offsets(
    regime: str,
    seed: int,
    role: str,
    source: tuple[int, ...],
) -> tuple[int, ...]:
    for attempt in range(32):
        candidate = _k3_offsets(regime, seed, f"{role}:{attempt}")
        if candidate != source:
            return candidate
    raise S3R5BindingError("failed to derive a distinct K3 rule")


def _mismatch_offsets(regime: str, seed: int, source: tuple[int, ...]) -> tuple[int, ...]:
    active = [index for index, value in enumerate(source) if value != 0]
    if len(active) != S3_R5_ACTIVE_COORDINATES:
        raise S3R5BindingError("mismatch source is not K3")
    selected = active[_digest(regime, seed, "mismatch-coordinate")[0] % len(active)]
    changed = list(source)
    changed[selected] = (changed[selected] % 3) + 1
    result = tuple(changed)
    _require_k3_offsets(result)
    if result == source:
        raise AssertionError("mismatch K3 rule did not change")
    return result


def _require_k3_offsets(offsets: tuple[int, ...]) -> None:
    if len(offsets) != base.S3_VECTOR_WIDTH:
        raise S3R5BindingError("K3 rule width drifted")
    active = [value for value in offsets if value != 0]
    if len(active) != S3_R5_ACTIVE_COORDINATES:
        raise S3R5BindingError("K3 rule does not have exactly three active offsets")
    if any(value not in (1, 2, 3) for value in active):
        raise S3R5BindingError("K3 active offset escaped 1..3")


def _rule(offsets: tuple[int, ...]) -> VectorRule:
    _require_k3_offsets(offsets)
    return VectorRule(tuple(range(base.S3_VECTOR_WIDTH)), offsets, base.S3_MODULUS)


def _bounded_vector(
    regime: str,
    seed: int,
    purpose: str,
    *rules: VectorRule,
) -> tuple[int, ...]:
    raw = _digest(regime, seed, purpose)
    maxima = [base.S3_MODULUS - 1] * base.S3_VECTOR_WIDTH
    for rule in rules:
        for output_index, input_index in enumerate(rule.permutation):
            maxima[input_index] = min(
                maxima[input_index],
                rule.modulus - 1 - rule.offsets[output_index],
            )
    return tuple(raw[index] % (maxima[index] + 1) for index in range(base.S3_VECTOR_WIDTH))


def _require_no_wrap(family: TransferFamily) -> None:
    rules = {family.source_rule, *family.target_rules}
    vectors = [example.input_values for example in family.source_examples]
    for step in family.target_steps:
        vectors.extend(example.input_values for example in step.examples)
        vectors.append(step.query)
    if any(
        vector[coordinate] + rule.offsets[coordinate] >= family.modulus
        for vector in vectors
        for rule in rules
        for coordinate in range(base.S3_VECTOR_WIDTH)
    ):
        raise S3R5BindingError("S3-R5 generated vector unexpectedly wraps")


def generate_s3_r5_family(regime: str, index: int) -> TransferFamily:
    validate_s3_r5_preregistration()
    if regime not in base.S3_REGIMES:
        raise S3R5BindingError(f"unsupported S3-R5 regime: {regime}")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 6:
        raise S3R5BindingError("S3-R5 family index must be 0..5")
    seed = S3_R5_SEEDS[regime][index]
    source_rule = _rule(_k3_offsets(regime, seed, "source"))

    if regime == "shared":
        target_rules = (source_rule,) * base.S3_TARGET_STEPS
        shift_index = None
    elif regime == "null":
        target = _rule(_distinct_k3_offsets(regime, seed, "null-target", source_rule.offsets))
        target_rules = (target,) * base.S3_TARGET_STEPS
        shift_index = None
    elif regime == "mismatch":
        target = _rule(_mismatch_offsets(regime, seed, source_rule.offsets))
        target_rules = (target,) * base.S3_TARGET_STEPS
        shift_index = None
    elif regime == "shift":
        post = _rule(_distinct_k3_offsets(regime, seed, "shift-post", source_rule.offsets))
        target_rules = (source_rule, source_rule, post, post)
        shift_index = base.S3_SHIFT_INDEX
    else:
        raise S3R5BindingError(f"unsupported S3-R5 regime: {regime}")

    bounds = tuple(dict.fromkeys((source_rule, *target_rules)))
    source_examples = tuple(
        PublicExample(
            values := _bounded_vector(
                regime,
                seed,
                f"source:example:{example_index}",
                *bounds,
            ),
            source_rule.apply(values),
        )
        for example_index in range(base.S3_SOURCE_EXAMPLES)
    )
    target_steps = tuple(
        TargetStep(
            examples=tuple(
                PublicExample(
                    values := _bounded_vector(
                        regime,
                        seed,
                        f"target:{step_index}:example:{example_index}",
                        *bounds,
                    ),
                    rule.apply(values),
                )
                for example_index in range(3)
            ),
            query=_bounded_vector(
                regime,
                seed,
                f"target:{step_index}:query",
                *bounds,
            ),
        )
        for step_index, rule in enumerate(target_rules)
    )
    family = TransferFamily(
        seed=seed,
        regime=regime,
        modulus=base.S3_MODULUS,
        source_rule=source_rule,
        target_rules=target_rules,
        source_examples=source_examples,
        target_steps=target_steps,
        shift_index=shift_index,
    )
    for rule in {source_rule, *target_rules}:
        _require_k3_offsets(rule.offsets)
    _require_no_wrap(family)
    return family


def s3_r5_call_plan(regime: str) -> tuple[str, ...]:
    if regime not in base.S3_REGIMES:
        raise S3R5BindingError(f"unsupported S3-R5 shard: {regime}")
    plan: list[str] = []
    for index, seed in enumerate(S3_R5_SEEDS[regime]):
        prefix = f"{regime}:{index}:{seed}"
        plan.extend(f"{prefix}:form-{kind}" for kind in ("p2", "p3", "p4"))
        if regime == "shift":
            plan.extend(f"{prefix}:anchor:{arm}" for arm in base.S3_TYPED_GENERIC_ARMS)
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
    if len(plan) != S3_R5_SHARD_CALLS[regime]:
        raise AssertionError("S3-R5 call plan length drifted")
    return tuple(plan)


def run_s3_r5_shard(client: base.S3Client, regime: str) -> base.S3ShardResult:
    if regime not in base.S3_REGIMES:
        raise S3R5BindingError(f"unsupported S3-R5 shard: {regime}")
    before_attempts = client.provider_attempts
    before_input = client.input_count_attempts
    families = tuple(
        base.run_s3_family(client, regime, index)
        for index in range(S3_R5_FAMILIES_PER_REGIME)
    )
    semantic_calls = client.provider_attempts - before_attempts
    input_requests = client.input_count_attempts - before_input
    expected = S3_R5_SHARD_CALLS[regime]
    if semantic_calls != expected:
        raise S3R5BindingError(
            f"S3-R5 shard provider call count drift: expected {expected}, got {semantic_calls}"
        )
    if input_requests != expected * 2:
        raise S3R5BindingError(
            "S3-R5 shard exact input-token request count drift: "
            f"expected {expected * 2}, got {input_requests}"
        )
    ledger = base.S3WorkLedger()
    for family in families:
        for record in family.records:
            ledger.add(record)
        if not family.p4_p6_semantic_equal or not family.shared_formation_lineage:
            raise S3R5BindingError("S3-R5 family violated semantic/formation lineage")
        if not family.provenance_audit_changed:
            raise S3R5BindingError("S3-R5 provenance audit-only lineage check failed")
    surface_effect, semantic_effect = base._effect_metrics(families)
    return base.S3ShardResult(
        regime=regime,
        families=families,
        semantic_calls=semantic_calls,
        work=ledger.as_mapping(),
        surface_perturbation_effect=surface_effect,
        semantic_intervention_effect=semantic_effect,
        semantic_invariance_gate=base.semantic_invariance_gate(surface_effect, semantic_effect),
    )


def paired_outcome_cells(
    first: Sequence[bool],
    second: Sequence[bool],
) -> dict[str, int]:
    if len(first) != len(second):
        raise S3R5BindingError("paired outcome vectors must have equal length")
    cells = {"first_only": 0, "second_only": 0, "both_correct": 0, "both_wrong": 0}
    for left, right in zip(first, second, strict=True):
        if not isinstance(left, bool) or not isinstance(right, bool):
            raise S3R5BindingError("paired outcomes must be booleans")
        if left and not right:
            cells["first_only"] += 1
        elif right and not left:
            cells["second_only"] += 1
        elif left and right:
            cells["both_correct"] += 1
        else:
            cells["both_wrong"] += 1
    return cells


def exact_first_arm_superiority_p(first_only: int, second_only: int) -> float:
    if (
        isinstance(first_only, bool)
        or isinstance(second_only, bool)
        or not isinstance(first_only, int)
        or not isinstance(second_only, int)
        or first_only < 0
        or second_only < 0
    ):
        raise S3R5BindingError("discordant counts must be non-negative integers")
    discordant = first_only + second_only
    if discordant == 0:
        return 1.0
    numerator = sum(math.comb(discordant, k) for k in range(first_only, discordant + 1))
    return numerator / (2**discordant)


def weakly_pareto_dominates(
    first: Mapping[str, int],
    second: Mapping[str, int],
) -> bool:
    if not first or set(first) != set(second):
        raise S3R5BindingError("Pareto vectors must have identical non-empty components")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in (*first.values(), *second.values())
    ):
        raise S3R5BindingError("Pareto cost components must be non-negative integers")
    return all(first[key] <= second[key] for key in first) and any(
        first[key] < second[key] for key in first
    )


def activate_s3_r5_preregistration() -> None:
    """Activate R5 only inside its dedicated campaign process."""

    validate_s3_r5_preregistration()
    base.S3_PREREGISTRATION_SCHEMA = S3_R5_PREREGISTRATION_SCHEMA
    base.S3_PREREGISTRATION_SHA256 = S3_R5_PREREGISTRATION_SHA256
    base.S3_LABEL = S3_R5_LABEL
    base.S3_SEEDS = S3_R5_SEEDS
    base.S3_SHARD_CALLS = S3_R5_SHARD_CALLS
    base.S3_TOTAL_SEMANTIC_CALLS = S3_R5_TOTAL_SEMANTIC_CALLS
    base.S3_TOTAL_INPUT_TOKEN_REQUESTS = S3_R5_TOTAL_INPUT_TOKEN_REQUESTS
    base.generate_s3_family = generate_s3_r5_family
    base.form_s2_representations = form_s2_representations_r4
    base.run_s3_shard = run_s3_r5_shard
    base.validate_frozen_seeds = validate_s3_r5_preregistration
