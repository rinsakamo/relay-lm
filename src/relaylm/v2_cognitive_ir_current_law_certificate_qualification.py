from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from typing import Protocol

from relaylm.v2_cognitive_ir_attack_observability_calibration import (
    ATTACK_OBS_SEEDS,
    D1_PREREGISTERED_SEEDS,
)
from relaylm.v2_cognitive_ir_calibration import CALIBRATION_SEEDS
from relaylm.v2_cognitive_ir_calibration_v2 import CALIBRATION_V2_SEEDS
from relaylm.v2_cognitive_ir_p2_boundedness_qual_v2 import P2_BOUNDEDNESS_QUAL_V2_SEEDS
from relaylm.v2_cognitive_ir_p2_termination_qual import P2_TERMINATION_QUAL_SEEDS
from relaylm.v2_cognitive_ir_s2_selected import S2_SELECTED_SEED
from relaylm.v2_cognitive_ir_s3 import (
    S3_MODULUS,
    S3_SHIFT_INDEX,
    S3_SOURCE_EXAMPLES,
    S3_TARGET_STEPS,
    S3_VECTOR_WIDTH,
)
from relaylm.v2_cognitive_ir_s3_r2 import HISTORICAL_S3_V1_SEEDS, S3_R2_SEEDS
from relaylm.v2_cognitive_ir_s3_r3 import S3_R3_SEEDS
from relaylm.v2_cognitive_ir_s3_r4 import S3_R4_SEEDS
from relaylm.v2_cognitive_ir_s3_r5 import S3_R5_SEEDS
from relaylm.v2_cognitive_ir_shared_floor_calibration import SHARED_FLOOR_SEEDS
from relaylm.v2_cognitive_ir_shared_floor_calibration_v2 import SHARED_FLOOR_V2_SEEDS
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from relaylm.v2_transfer_experiment import PublicExample, TargetStep, TransferFamily, VectorRule


G1_SCHEMA = "relaylm2-cognitive-ir-s3-r6d-g1-certificate-usability-prereg-v1"
G1_LABEL = "relaylm2-cognitive-ir-s3-r6d-g1-current-law-certificate-usability-v1"
G1_CLAIM = "NON_CITABLE_CURRENT_LAW_CERTIFICATE_USABILITY_QUALIFICATION"
G1_CITABLE = False
G1_ARCHITECTURE_CONSEQUENCE = "NONE"
G1_QUALIFIED = "CURRENT_LAW_CERTIFICATE_USABILITY_QUALIFIED"
G1_FAILED = "CURRENT_LAW_CERTIFICATE_USABILITY_FAILED"
G1_INCOMPLETE = "QUALIFICATION_INCOMPLETE"
G1_REGIMES = ("null", "mismatch", "shift")
G1_SEEDS_PER_REGIME = 6
G1_SEMANTIC_CALLS = 18
G1_INPUT_TOKEN_REQUESTS = 36
G1_MIN_CORRECT_PER_REGIME = 5
G1_ACTIVE_COORDINATES = 3
G1_TARGET_EXAMPLE_INDEX = 0
G1_SEEDS: Mapping[str, tuple[int, ...]] = {
    "null": (
        24174405,
        244405335,
        1624350917,
        1271676860,
        256313055,
        866259132,
    ),
    "mismatch": (
        634460086,
        971845400,
        319707397,
        70560149,
        1614596380,
        606339468,
    ),
    "shift": (
        1617515533,
        1748442581,
        712887364,
        275048247,
        251381766,
        1867897343,
    ),
}
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
    2665,
    2666,
    2667,
    2669,
    2670,
    2702,
    2703,
    2710,
    2711,
    2712,
    2713,
}


class CurrentLawCertificateQualificationError(ValueError):
    """The #2712 current-law certificate qualification contract was violated."""


class CurrentLawCertificateClient(Protocol):
    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion: ...

    def require_complete_plan(self) -> None: ...


@dataclass(frozen=True, slots=True)
class CurrentLawCertificate:
    permutation: tuple[int, ...]
    offsets: tuple[int, ...]
    modulus: int
    regime: str
    seed: int
    target_step_index: int
    target_example_index: int


@dataclass(frozen=True, slots=True)
class CurrentLawCertificateSeedResult:
    regime: str
    seed: int
    correct: bool


@dataclass(frozen=True, slots=True)
class CurrentLawCertificateQualificationResult:
    classification: str
    seeds: tuple[CurrentLawCertificateSeedResult, ...]
    correct_by_regime: Mapping[str, int]
    semantic_calls: int = G1_SEMANTIC_CALLS
    input_token_requests: int = G1_INPUT_TOKEN_REQUESTS
    claim: str = G1_CLAIM
    citable: bool = G1_CITABLE
    architecture_consequence: str = G1_ARCHITECTURE_CONSEQUENCE


def _flatten(values: Mapping[str, tuple[int, ...]]) -> set[int]:
    return {seed for seeds in values.values() for seed in seeds}


def derive_g1_seed(regime: str, index: int) -> int:
    if regime not in G1_REGIMES:
        raise CurrentLawCertificateQualificationError(f"unsupported G1 regime: {regime}")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 6:
        raise CurrentLawCertificateQualificationError("G1 seed index must be 0..5")
    raw = hashlib.sha256(f"{G1_LABEL}|{regime}|seed|{index}".encode("utf-8")).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def validate_g1_preregistration() -> None:
    derived = {
        regime: tuple(derive_g1_seed(regime, index) for index in range(6))
        for regime in G1_REGIMES
    }
    if derived != dict(G1_SEEDS):
        raise CurrentLawCertificateQualificationError(
            "derived G1 seeds drifted from #2712"
        )
    fresh = _flatten(G1_SEEDS)
    if len(fresh) != 18:
        raise CurrentLawCertificateQualificationError("G1 seeds are not unique")
    if fresh & set(D1_PREREGISTERED_SEEDS):
        raise CurrentLawCertificateQualificationError("G1 seeds overlap D1 seeds")
    if fresh & _flatten(ATTACK_OBS_SEEDS):
        raise CurrentLawCertificateQualificationError("G1 seeds overlap old D2 seeds")

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
        *_flatten(S3_R5_SEEDS),
        *SHARED_FLOOR_SEEDS,
        *SHARED_FLOOR_V2_SEEDS,
        *_RELEVANT_ISSUE_IDENTITIES,
    }
    overlap = sorted(fresh & historical)
    if overlap:
        raise CurrentLawCertificateQualificationError(
            f"G1 seeds overlap historical evidence: {overlap}"
        )
    if (
        S3_VECTOR_WIDTH,
        S3_MODULUS,
        S3_SOURCE_EXAMPLES,
        S3_TARGET_STEPS,
        S3_SHIFT_INDEX,
        G1_ACTIVE_COORDINATES,
        G1_TARGET_EXAMPLE_INDEX,
    ) != (4, 10, 4, 4, 2, 3, 0):
        raise CurrentLawCertificateQualificationError("G1 inherited geometry drifted")
    if (G1_SEMANTIC_CALLS, G1_INPUT_TOKEN_REQUESTS) != (18, 36):
        raise CurrentLawCertificateQualificationError("G1 call ledger drifted")


def _digest(regime: str, seed: int, purpose: str) -> bytes:
    return hashlib.sha256(
        f"{G1_LABEL}|{regime}|{seed}|{purpose}".encode("utf-8")
    ).digest()


def _k3_offsets(regime: str, seed: int, role: str) -> tuple[int, ...]:
    ranked = sorted(
        range(S3_VECTOR_WIDTH),
        key=lambda coordinate: (
            _digest(regime, seed, f"{role}:active-rank:{coordinate}"),
            coordinate,
        ),
    )
    active = set(ranked[:G1_ACTIVE_COORDINATES])
    offsets = tuple(
        1 + (_digest(regime, seed, f"{role}:offset-value:{coordinate}")[0] % 3)
        if coordinate in active
        else 0
        for coordinate in range(S3_VECTOR_WIDTH)
    )
    if sum(value != 0 for value in offsets) != G1_ACTIVE_COORDINATES:
        raise AssertionError("G1 K3 active count drifted")
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
    raise CurrentLawCertificateQualificationError(
        "failed to derive distinct G1 target rule"
    )


def _rule(offsets: tuple[int, ...]) -> VectorRule:
    return VectorRule(tuple(range(S3_VECTOR_WIDTH)), offsets, S3_MODULUS)


def _bounded_vector(
    regime: str,
    seed: int,
    purpose: str,
    *rules: VectorRule,
) -> tuple[int, ...]:
    maxima = [S3_MODULUS - 1] * S3_VECTOR_WIDTH
    for rule in rules:
        for output_index, input_index in enumerate(rule.permutation):
            maxima[input_index] = min(
                maxima[input_index],
                rule.modulus - 1 - rule.offsets[output_index],
            )
    raw = _digest(regime, seed, purpose)
    return tuple(raw[index] % (maxima[index] + 1) for index in range(S3_VECTOR_WIDTH))


def _target_step(
    regime: str,
    seed: int,
    index: int,
    rule: VectorRule,
    *bounds: VectorRule,
) -> TargetStep:
    all_bounds = (rule, *bounds)
    examples = tuple(
        PublicExample(
            values := _bounded_vector(
                regime,
                seed,
                f"target:{index}:example:{example_index}",
                *all_bounds,
            ),
            rule.apply(values),
        )
        for example_index in range(3)
    )
    query = _bounded_vector(regime, seed, f"target:{index}:query", *all_bounds)
    return TargetStep(examples=examples, query=query)


def generate_g1_family(regime: str, index: int) -> TransferFamily:
    validate_g1_preregistration()
    if regime not in G1_REGIMES:
        raise CurrentLawCertificateQualificationError(f"unsupported G1 regime: {regime}")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 6:
        raise CurrentLawCertificateQualificationError("G1 family index must be 0..5")
    seed = G1_SEEDS[regime][index]
    source_offsets = _k3_offsets(regime, seed, "source")
    source_rule = _rule(source_offsets)

    if regime == "null":
        target_rule = _rule(_distinct_k3_offsets(regime, seed, "null-target", source_offsets))
        target_rules = (target_rule,) * S3_TARGET_STEPS
        shift_index = None
    elif regime == "mismatch":
        mismatch = list(source_offsets)
        active = [i for i, value in enumerate(mismatch) if value != 0]
        chosen = active[_digest(regime, seed, "mismatch-coordinate")[0] % len(active)]
        mismatch[chosen] = (mismatch[chosen] % 3) + 1
        target_rule = _rule(tuple(mismatch))
        target_rules = (target_rule,) * S3_TARGET_STEPS
        shift_index = None
    else:
        post_rule = _rule(_distinct_k3_offsets(regime, seed, "shift-target", source_offsets))
        target_rules = (source_rule, source_rule, post_rule, post_rule)
        shift_index = S3_SHIFT_INDEX

    bounds = tuple(dict.fromkeys((source_rule, *target_rules)))
    source_examples = tuple(
        PublicExample(
            values := _bounded_vector(
                regime,
                seed,
                f"source-example:{example_index}",
                *bounds,
            ),
            source_rule.apply(values),
        )
        for example_index in range(S3_SOURCE_EXAMPLES)
    )
    target_steps = tuple(
        _target_step(regime, seed, step_index, rule, *bounds)
        for step_index, rule in enumerate(target_rules)
    )
    family = TransferFamily(
        seed=seed,
        regime=regime,
        modulus=S3_MODULUS,
        source_rule=source_rule,
        target_rules=target_rules,
        source_examples=source_examples,
        target_steps=target_steps,
        shift_index=shift_index,
    )
    _require_no_wrap(family)
    return family


def _require_no_wrap(family: TransferFamily) -> None:
    rules = (family.source_rule, *family.target_rules)
    for example in family.source_examples:
        for rule in rules:
            for output_index, input_index in enumerate(rule.permutation):
                if (
                    example.input_values[input_index] + rule.offsets[output_index]
                    >= rule.modulus
                ):
                    raise CurrentLawCertificateQualificationError(
                        "G1 source example unexpectedly wraps"
                    )
    for step_index, step in enumerate(family.target_steps):
        rule = family.target_rules[step_index]
        for values in [item.input_values for item in step.examples] + [step.query]:
            for output_index, input_index in enumerate(rule.permutation):
                if values[input_index] + rule.offsets[output_index] >= rule.modulus:
                    raise CurrentLawCertificateQualificationError(
                        "G1 target example/query unexpectedly wraps"
                    )


def g1_probe_step_index(regime: str) -> int:
    if regime == "shift":
        return S3_SHIFT_INDEX
    if regime in ("null", "mismatch"):
        return 0
    raise CurrentLawCertificateQualificationError(f"unsupported G1 regime: {regime}")


def derive_current_law_certificate(family: TransferFamily) -> CurrentLawCertificate:
    step_index = g1_probe_step_index(family.regime)
    example = family.target_steps[step_index].examples[G1_TARGET_EXAMPLE_INDEX]
    offsets = tuple(
        (output_value - input_value) % family.modulus
        for input_value, output_value in zip(
            example.input_values,
            example.output_values,
            strict=True,
        )
    )
    certificate = CurrentLawCertificate(
        permutation=tuple(range(S3_VECTOR_WIDTH)),
        offsets=offsets,
        modulus=family.modulus,
        regime=family.regime,
        seed=family.seed,
        target_step_index=step_index,
        target_example_index=G1_TARGET_EXAMPLE_INDEX,
    )
    reconstructed = VectorRule(
        certificate.permutation,
        certificate.offsets,
        certificate.modulus,
    )
    if reconstructed != family.target_rules[step_index]:
        raise CurrentLawCertificateQualificationError(
            "G1 certificate does not reconstruct current target rule"
        )
    return certificate


def build_g1_messages(family: TransferFamily) -> tuple[dict[str, str], ...]:
    certificate = derive_current_law_certificate(family)
    step = family.target_steps[certificate.target_step_index]
    payload = {
        "instruction": (
            "Apply the explicit current vector transformation to the query and "
            "return only a JSON integer array."
        ),
        "current_law_certificate": {
            "modulus": certificate.modulus,
            "offsets": list(certificate.offsets),
            "permutation": list(certificate.permutation),
        },
        "query": list(step.query),
    }
    return (
        {
            "role": "system",
            "content": (
                "Use only the explicit current-law certificate and query. "
                "Return exactly one JSON integer array of length 4."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ),
        },
    )


def _parse_vector(
    completion: ExperimentCompletion,
    *,
    family: TransferFamily,
) -> tuple[int, ...]:
    try:
        value = json.loads(completion.content)
    except json.JSONDecodeError as exc:
        raise CurrentLawCertificateQualificationError(
            "G1 completion is not JSON"
        ) from exc
    if (
        not isinstance(value, list)
        or len(value) != S3_VECTOR_WIDTH
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
        or any(not 0 <= item < family.modulus for item in value)
    ):
        raise CurrentLawCertificateQualificationError(
            "G1 completion is not a valid vector"
        )
    return tuple(value)


def g1_call_plan() -> tuple[str, ...]:
    plan = tuple(
        f"G1:{regime}:{index}:{seed}:certificate-only"
        for regime in G1_REGIMES
        for index, seed in enumerate(G1_SEEDS[regime])
    )
    if len(plan) != G1_SEMANTIC_CALLS:
        raise AssertionError("G1 call plan length drifted")
    return plan


def run_current_law_certificate_qualification(
    client: CurrentLawCertificateClient,
) -> CurrentLawCertificateQualificationResult:
    validate_g1_preregistration()
    plan = g1_call_plan()
    results: list[CurrentLawCertificateSeedResult] = []
    for question_id in plan:
        prefix, regime, index_text, seed_text, suffix = question_id.split(":")
        if prefix != "G1" or suffix != "certificate-only":
            raise AssertionError("G1 call-plan binding drifted")
        index = int(index_text)
        seed = int(seed_text)
        family = generate_g1_family(regime, index)
        if family.seed != seed:
            raise AssertionError("G1 seed binding drifted")
        completion = client.complete_named(
            question_id,
            build_g1_messages(family),
            output_kind="vector",
        )
        expected = family.expected_output(g1_probe_step_index(regime))
        results.append(
            CurrentLawCertificateSeedResult(
                regime=regime,
                seed=seed,
                correct=_parse_vector(completion, family=family) == expected,
            )
        )
    client.require_complete_plan()
    correct_by_regime = {
        regime: sum(result.correct for result in results if result.regime == regime)
        for regime in G1_REGIMES
    }
    qualified = all(
        correct_by_regime[regime] >= G1_MIN_CORRECT_PER_REGIME
        for regime in G1_REGIMES
    )
    return CurrentLawCertificateQualificationResult(
        classification=G1_QUALIFIED if qualified else G1_FAILED,
        seeds=tuple(results),
        correct_by_regime=correct_by_regime,
    )
