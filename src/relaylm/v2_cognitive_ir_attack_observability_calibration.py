from __future__ import annotations

from collections.abc import Callable, Mapping, Protocol
from dataclasses import dataclass
import hashlib
import json

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


ATTACK_OBS_SCHEMA = "relaylm2-cognitive-ir-s3-r6d-d2-observability-cal-v1"
ATTACK_OBS_LABEL = "relaylm2-cognitive-ir-s3-r6d-attack-observability-cal-v1"
ATTACK_OBS_CLAIM = "NON_CITABLE_ATTACK_OBSERVABILITY_CALIBRATION"
ATTACK_OBS_CITABLE = False
ATTACK_OBS_ARCHITECTURE_CONSEQUENCE = "NONE"
ATTACK_OBS_QUALIFIED = "ATTACK_OBSERVABILITY_QUALIFIED"
NO_OBSERVABLE_ATTACK_TARGET_RANGE = "NO_OBSERVABLE_ATTACK_TARGET_RANGE"
ATTACK_OBS_INCOMPLETE = "CALIBRATION_INCOMPLETE"
ATTACK_OBS_REGIMES = ("null", "mismatch", "shift")
ATTACK_OBS_VISIBILITIES = (1, 2, 3)
ATTACK_OBS_SEEDS_PER_REGIME = 6
ATTACK_OBS_CALLS_PER_CANDIDATE = 18
ATTACK_OBS_INPUT_TOKEN_REQUESTS_PER_CANDIDATE = 36
ATTACK_OBS_MAX_SEMANTIC_CALLS = 54
ATTACK_OBS_MAX_INPUT_TOKEN_REQUESTS = 108
ATTACK_OBS_MIN_CORRECT_PER_REGIME = 5
ATTACK_OBS_ACTIVE_COORDINATES = 3
ATTACK_OBS_SEEDS: Mapping[str, tuple[int, ...]] = {
    "null": (
        1532208095,
        166020602,
        172209029,
        1867232037,
        1895006708,
        1439139994,
    ),
    "mismatch": (
        2112432796,
        565231701,
        115620527,
        1843326401,
        806893815,
        1799740474,
    ),
    "shift": (
        2008905029,
        660234600,
        854173960,
        581940620,
        1890736338,
        1593338407,
    ),
}
D1_PREREGISTERED_SEEDS = (
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
    2665,
    2666,
    2667,
    2669,
    2670,
}


class AttackObservabilityCalibrationError(ValueError):
    """The #2667 treatment-blind observability calibration contract was violated."""


class AttackObservabilityClient(Protocol):
    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion: ...

    def require_complete_plan(self) -> None: ...


@dataclass(frozen=True, slots=True)
class AttackObservabilitySeedResult:
    visibility: int
    regime: str
    seed: int
    correct: bool


@dataclass(frozen=True, slots=True)
class AttackObservabilityCandidateResult:
    visibility: int
    seeds: tuple[AttackObservabilitySeedResult, ...]
    correct_by_regime: Mapping[str, int]
    admitted: bool
    semantic_calls: int = ATTACK_OBS_CALLS_PER_CANDIDATE
    input_token_requests: int = ATTACK_OBS_INPUT_TOKEN_REQUESTS_PER_CANDIDATE


@dataclass(frozen=True, slots=True)
class AttackObservabilityCalibrationResult:
    classification: str
    selected_visibility: int | None
    candidates: tuple[AttackObservabilityCandidateResult, ...]
    semantic_calls: int
    input_token_requests: int
    claim: str = ATTACK_OBS_CLAIM
    citable: bool = ATTACK_OBS_CITABLE
    architecture_consequence: str = ATTACK_OBS_ARCHITECTURE_CONSEQUENCE


def _flatten(values: Mapping[str, tuple[int, ...]]) -> set[int]:
    return {seed for seeds in values.values() for seed in seeds}


def derive_attack_obs_seed(regime: str, index: int) -> int:
    if regime not in ATTACK_OBS_REGIMES:
        raise AttackObservabilityCalibrationError(f"unsupported attack regime: {regime}")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 6:
        raise AttackObservabilityCalibrationError("attack seed index must be 0..5")
    raw = hashlib.sha256(
        f"{ATTACK_OBS_LABEL}|{regime}|seed|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def validate_attack_observability_preregistration() -> None:
    derived = {
        regime: tuple(derive_attack_obs_seed(regime, index) for index in range(6))
        for regime in ATTACK_OBS_REGIMES
    }
    if derived != dict(ATTACK_OBS_SEEDS):
        raise AttackObservabilityCalibrationError(
            "derived attack-observability seeds drifted from #2667"
        )
    fresh = _flatten(ATTACK_OBS_SEEDS)
    if len(fresh) != 18:
        raise AttackObservabilityCalibrationError("attack-observability seeds are not unique")
    if fresh & set(D1_PREREGISTERED_SEEDS):
        raise AttackObservabilityCalibrationError("D2 seeds overlap D1 preregistered seeds")

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
        raise AttackObservabilityCalibrationError(
            f"attack-observability seeds overlap historical evidence: {overlap}"
        )
    if ATTACK_OBS_VISIBILITIES != (1, 2, 3):
        raise AttackObservabilityCalibrationError("visibility order drifted")
    if (
        ATTACK_OBS_CALLS_PER_CANDIDATE,
        ATTACK_OBS_INPUT_TOKEN_REQUESTS_PER_CANDIDATE,
        ATTACK_OBS_MAX_SEMANTIC_CALLS,
        ATTACK_OBS_MAX_INPUT_TOKEN_REQUESTS,
    ) != (18, 36, 54, 108):
        raise AttackObservabilityCalibrationError("attack-observability call ledger drifted")
    if (
        S3_VECTOR_WIDTH,
        S3_MODULUS,
        S3_SOURCE_EXAMPLES,
        S3_TARGET_STEPS,
        S3_SHIFT_INDEX,
        ATTACK_OBS_ACTIVE_COORDINATES,
    ) != (4, 10, 4, 4, 2, 3):
        raise AttackObservabilityCalibrationError("inherited K3 geometry drifted")


def _digest(regime: str, seed: int, purpose: str) -> bytes:
    return hashlib.sha256(
        f"{ATTACK_OBS_LABEL}|{regime}|{seed}|{purpose}".encode("utf-8")
    ).digest()


def _k3_offsets(regime: str, seed: int, role: str) -> tuple[int, ...]:
    ranked = sorted(
        range(S3_VECTOR_WIDTH),
        key=lambda coordinate: (
            _digest(regime, seed, f"{role}:active-rank:{coordinate}"),
            coordinate,
        ),
    )
    active = set(ranked[:ATTACK_OBS_ACTIVE_COORDINATES])
    offsets = tuple(
        1 + (_digest(regime, seed, f"{role}:offset-value:{coordinate}")[0] % 3)
        if coordinate in active
        else 0
        for coordinate in range(S3_VECTOR_WIDTH)
    )
    if sum(value != 0 for value in offsets) != ATTACK_OBS_ACTIVE_COORDINATES:
        raise AssertionError("attack-observability K3 active count drifted")
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
    raise AttackObservabilityCalibrationError("failed to derive distinct K3 target rule")


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


def generate_attack_observability_family(regime: str, index: int) -> TransferFamily:
    validate_attack_observability_preregistration()
    if regime not in ATTACK_OBS_REGIMES:
        raise AttackObservabilityCalibrationError(f"unsupported attack regime: {regime}")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 6:
        raise AttackObservabilityCalibrationError("attack family index must be 0..5")
    seed = ATTACK_OBS_SEEDS[regime][index]
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
                if example.input_values[input_index] + rule.offsets[output_index] >= rule.modulus:
                    raise AttackObservabilityCalibrationError("source example unexpectedly wraps")
    for step_index, step in enumerate(family.target_steps):
        rule = family.target_rules[step_index]
        for values in [item.input_values for item in step.examples] + [step.query]:
            for output_index, input_index in enumerate(rule.permutation):
                if values[input_index] + rule.offsets[output_index] >= rule.modulus:
                    raise AttackObservabilityCalibrationError("target example/query unexpectedly wraps")


def attack_probe_step_index(regime: str) -> int:
    if regime == "shift":
        return S3_SHIFT_INDEX
    if regime in ("null", "mismatch"):
        return 0
    raise AttackObservabilityCalibrationError(f"unsupported attack regime: {regime}")


def build_attack_target_only_messages(
    family: TransferFamily,
    visibility: int,
) -> tuple[dict[str, str], ...]:
    if visibility not in ATTACK_OBS_VISIBILITIES:
        raise AttackObservabilityCalibrationError(f"unsupported visibility: {visibility}")
    step_index = attack_probe_step_index(family.regime)
    step = family.target_steps[step_index]
    payload = {
        "instruction": "Infer the current vector transformation and return only a JSON integer array.",
        "modulus": family.modulus,
        "examples": [
            {
                "input": list(example.input_values),
                "output": list(example.output_values),
            }
            for example in step.examples[:visibility]
        ],
        "query": list(step.query),
    }
    return (
        {
            "role": "system",
            "content": (
                "Solve the formal vector task from the visible target examples only. "
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


def _parse_vector(completion: ExperimentCompletion, *, family: TransferFamily) -> tuple[int, ...]:
    try:
        value = json.loads(completion.content)
    except json.JSONDecodeError as exc:
        raise AttackObservabilityCalibrationError("target-only completion is not JSON") from exc
    if (
        not isinstance(value, list)
        or len(value) != S3_VECTOR_WIDTH
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
        or any(not 0 <= item < family.modulus for item in value)
    ):
        raise AttackObservabilityCalibrationError("target-only completion is not a valid vector")
    return tuple(value)


def attack_observability_call_plan(visibility: int) -> tuple[str, ...]:
    if visibility not in ATTACK_OBS_VISIBILITIES:
        raise AttackObservabilityCalibrationError(f"unsupported visibility: {visibility}")
    plan = tuple(
        f"E{visibility}:{regime}:{index}:{seed}:target-only"
        for regime in ATTACK_OBS_REGIMES
        for index, seed in enumerate(ATTACK_OBS_SEEDS[regime])
    )
    if len(plan) != ATTACK_OBS_CALLS_PER_CANDIDATE:
        raise AssertionError("attack-observability call plan length drifted")
    return plan


def run_attack_observability_candidate(
    client: AttackObservabilityClient,
    visibility: int,
) -> AttackObservabilityCandidateResult:
    plan = attack_observability_call_plan(visibility)
    results: list[AttackObservabilitySeedResult] = []
    for question_id in plan:
        _, regime, index_text, seed_text, suffix = question_id.split(":")
        if suffix != "target-only":
            raise AssertionError("attack-observability call-plan suffix drifted")
        index = int(index_text)
        seed = int(seed_text)
        family = generate_attack_observability_family(regime, index)
        if family.seed != seed:
            raise AssertionError("attack-observability seed binding drifted")
        completion = client.complete_named(
            question_id,
            build_attack_target_only_messages(family, visibility),
            output_kind="vector",
        )
        expected = family.expected_output(attack_probe_step_index(regime))
        results.append(
            AttackObservabilitySeedResult(
                visibility=visibility,
                regime=regime,
                seed=seed,
                correct=_parse_vector(completion, family=family) == expected,
            )
        )
    client.require_complete_plan()
    correct_by_regime = {
        regime: sum(result.correct for result in results if result.regime == regime)
        for regime in ATTACK_OBS_REGIMES
    }
    admitted = all(
        correct_by_regime[regime] >= ATTACK_OBS_MIN_CORRECT_PER_REGIME
        for regime in ATTACK_OBS_REGIMES
    )
    return AttackObservabilityCandidateResult(
        visibility=visibility,
        seeds=tuple(results),
        correct_by_regime=correct_by_regime,
        admitted=admitted,
    )


def run_attack_observability_calibration(
    client_factory: Callable[[int, tuple[str, ...]], AttackObservabilityClient],
) -> AttackObservabilityCalibrationResult:
    validate_attack_observability_preregistration()
    candidates: list[AttackObservabilityCandidateResult] = []
    for visibility in ATTACK_OBS_VISIBILITIES:
        client = client_factory(visibility, attack_observability_call_plan(visibility))
        candidate = run_attack_observability_candidate(client, visibility)
        candidates.append(candidate)
        if candidate.admitted:
            return AttackObservabilityCalibrationResult(
                classification=ATTACK_OBS_QUALIFIED,
                selected_visibility=visibility,
                candidates=tuple(candidates),
                semantic_calls=len(candidates) * ATTACK_OBS_CALLS_PER_CANDIDATE,
                input_token_requests=(
                    len(candidates) * ATTACK_OBS_INPUT_TOKEN_REQUESTS_PER_CANDIDATE
                ),
            )
    return AttackObservabilityCalibrationResult(
        classification=NO_OBSERVABLE_ATTACK_TARGET_RANGE,
        selected_visibility=None,
        candidates=tuple(candidates),
        semantic_calls=ATTACK_OBS_MAX_SEMANTIC_CALLS,
        input_token_requests=ATTACK_OBS_MAX_INPUT_TOKEN_REQUESTS,
    )
