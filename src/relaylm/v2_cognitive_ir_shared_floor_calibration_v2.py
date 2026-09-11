from __future__ import annotations

from collections.abc import Callable
import hashlib
import json

from relaylm.v2_cognitive_ir_actual_model import build_s2_target_messages
from relaylm.v2_cognitive_ir_calibration import CALIBRATION_SEEDS
from relaylm.v2_cognitive_ir_calibration_v2 import CALIBRATION_V2_SEEDS
from relaylm.v2_cognitive_ir_experiment import semantic_digest
from relaylm.v2_cognitive_ir_p2_boundedness_qual_v2 import (
    P2_BOUNDEDNESS_QUAL_V2_SEEDS,
)
from relaylm.v2_cognitive_ir_p2_termination_qual import P2_TERMINATION_QUAL_SEEDS
from relaylm.v2_cognitive_ir_s2_selected import S2_SELECTED_SEED
from relaylm.v2_cognitive_ir_s3_r2 import HISTORICAL_S3_V1_SEEDS, S3_R2_SEEDS
from relaylm.v2_cognitive_ir_s3_r3 import S3_R3_SEEDS
from relaylm.v2_cognitive_ir_s3_r4 import S3_R4_SEEDS, form_s2_representations_r4
from relaylm.v2_cognitive_ir_shared_floor_calibration import (
    NO_SHARED_TARGET_RANGE_FOUND,
    SHARED_FLOOR_ACTIVE_COUNTS,
    SHARED_FLOOR_APPLICATION_MIN_CORRECT,
    SHARED_FLOOR_CALLS_PER_DIFFICULTY,
    SHARED_FLOOR_DIFFICULTIES,
    SHARED_FLOOR_EXAMPLES_VISIBLE,
    SHARED_FLOOR_FORMATION_MIN_CORRECT,
    SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY,
    SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS,
    SHARED_FLOOR_MAX_SEMANTIC_CALLS,
    SHARED_FLOOR_MIN_NON_DEGENERATE_ARMS,
    SHARED_FLOOR_MODULUS,
    SHARED_FLOOR_NEUTRAL_ARMS,
    SHARED_FLOOR_NEUTRAL_MEAN_MAX,
    SHARED_FLOOR_NEUTRAL_MEAN_MIN,
    SHARED_FLOOR_P2_REQUIRED_ADMITTED,
    SHARED_FLOOR_SEEDS,
    SHARED_FLOOR_SEEDS_PER_DIFFICULTY,
    SHARED_FLOOR_SOURCE_EXAMPLES,
    SHARED_FLOOR_TARGET_STEPS,
    SHARED_FLOOR_VECTOR_WIDTH,
    SHARED_TARGET_RANGE_QUALIFIED,
    SharedFloorCalibrationError,
    SharedFloorCalibrationResult,
    SharedFloorCandidateResult,
    SharedFloorClient,
    SharedFloorSeedResult,
    _NamedFormationAdapter,
    _flatten_seed_map,
    _formation_recovers_rule,
    _parse_vector,
    _require_no_wrap,
    _require_rule_identifiable,
    build_explicit_application_messages,
    validate_shared_floor_preregistration,
)
from relaylm.v2_transfer_experiment import PublicExample, TargetStep, TransferFamily, VectorRule


SHARED_FLOOR_V2_LABEL = "relaylm2-cognitive-ir-shared-floor-calibration-v2"
SHARED_FLOOR_V2_SEEDS = (
    1142504739,
    1503134270,
    356394414,
    1625198782,
    1873901982,
    2032603824,
)

# Issue-number identities are part of the collision fence. Historical identities
# already fenced by the v1 module are rechecked indirectly through its validator;
# these are the successor-lane identities introduced after #2601.
SHARED_FLOOR_V2_ISSUE_SEEDS = {
    2610,
    2612,
    2614,
    2619,
    2620,
}


def derive_shared_floor_v2_seed(index: int) -> int:
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 6:
        raise SharedFloorCalibrationError("shared-floor-v2 seed index must be 0..5")
    raw = hashlib.sha256(
        f"{SHARED_FLOOR_V2_LABEL}|seed|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def validate_shared_floor_v2_preregistration() -> None:
    # Keep all historical v1 invariants live and fail closed if they drift.
    validate_shared_floor_preregistration()

    derived = tuple(derive_shared_floor_v2_seed(index) for index in range(6))
    if derived != SHARED_FLOOR_V2_SEEDS:
        raise SharedFloorCalibrationError(
            "derived shared-floor-v2 seeds drifted from #2619"
        )
    if len(set(SHARED_FLOOR_V2_SEEDS)) != len(SHARED_FLOOR_V2_SEEDS):
        raise SharedFloorCalibrationError("shared-floor-v2 seeds are not unique")

    historical = {
        *CALIBRATION_SEEDS,
        *CALIBRATION_V2_SEEDS,
        *P2_TERMINATION_QUAL_SEEDS,
        *P2_BOUNDEDNESS_QUAL_V2_SEEDS,
        S2_SELECTED_SEED,
        *_flatten_seed_map(HISTORICAL_S3_V1_SEEDS),
        *_flatten_seed_map(S3_R2_SEEDS),
        *_flatten_seed_map(S3_R3_SEEDS),
        *_flatten_seed_map(S3_R4_SEEDS),
        *SHARED_FLOOR_SEEDS,
        *SHARED_FLOOR_V2_ISSUE_SEEDS,
    }
    overlap = sorted(set(SHARED_FLOOR_V2_SEEDS) & historical)
    if overlap:
        raise SharedFloorCalibrationError(
            f"shared-floor-v2 seeds overlap historical evidence: {overlap}"
        )

    if SHARED_FLOOR_DIFFICULTIES != (
        "K4_CURRENT_CLASS",
        "K3_THREE_ACTIVE",
        "K2_TWO_ACTIVE",
        "K1_ONE_ACTIVE",
    ):
        raise SharedFloorCalibrationError("shared-floor-v2 difficulty order drifted")
    if (
        SHARED_FLOOR_CALLS_PER_DIFFICULTY,
        SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY,
        SHARED_FLOOR_MAX_SEMANTIC_CALLS,
        SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS,
    ) != (54, 108, 216, 432):
        raise SharedFloorCalibrationError("shared-floor-v2 call ledger drifted")


def _v2_seed_digest(seed: int, purpose: str) -> bytes:
    return hashlib.sha256(
        f"{SHARED_FLOOR_V2_LABEL}|{seed}|{purpose}".encode("utf-8")
    ).digest()


def _v2_active_order(seed: int) -> tuple[int, ...]:
    return tuple(
        sorted(
            range(SHARED_FLOOR_VECTOR_WIDTH),
            key=lambda coordinate: (
                _v2_seed_digest(seed, f"active-rank:{coordinate}"),
                coordinate,
            ),
        )
    )


def _v2_nonzero_value(seed: int, coordinate: int) -> int:
    return 1 + (_v2_seed_digest(seed, f"offset-value:{coordinate}")[0] % 3)


def shared_floor_v2_offsets(difficulty: str, seed: int) -> tuple[int, ...]:
    if difficulty not in SHARED_FLOOR_ACTIVE_COUNTS:
        raise SharedFloorCalibrationError(
            f"unsupported shared-floor-v2 difficulty: {difficulty}"
        )
    active_count = SHARED_FLOOR_ACTIVE_COUNTS[difficulty]
    active = set(_v2_active_order(seed)[:active_count])
    offsets = tuple(
        _v2_nonzero_value(seed, coordinate) if coordinate in active else 0
        for coordinate in range(SHARED_FLOOR_VECTOR_WIDTH)
    )
    if sum(value != 0 for value in offsets) != active_count:
        raise AssertionError("shared-floor-v2 active offset count drifted")
    return offsets


def _v2_bounded_input(seed: int, purpose: str) -> tuple[int, ...]:
    raw = _v2_seed_digest(seed, purpose)
    return tuple(raw[index] % 7 for index in range(SHARED_FLOOR_VECTOR_WIDTH))


def generate_shared_floor_v2_family(difficulty: str, index: int) -> TransferFamily:
    validate_shared_floor_v2_preregistration()
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 6:
        raise SharedFloorCalibrationError("shared-floor-v2 family index must be 0..5")
    seed = SHARED_FLOOR_V2_SEEDS[index]
    offsets = shared_floor_v2_offsets(difficulty, seed)
    rule = VectorRule(
        tuple(range(SHARED_FLOOR_VECTOR_WIDTH)),
        offsets,
        SHARED_FLOOR_MODULUS,
    )
    source_examples = tuple(
        PublicExample(
            values := _v2_bounded_input(seed, f"source-example:{example_index}"),
            rule.apply(values),
        )
        for example_index in range(SHARED_FLOOR_SOURCE_EXAMPLES)
    )
    target_steps = tuple(
        TargetStep(
            examples=tuple(
                PublicExample(
                    values := _v2_bounded_input(
                        seed,
                        f"target:{step_index}:example:{example_index}",
                    ),
                    rule.apply(values),
                )
                for example_index in range(3)
            ),
            query=_v2_bounded_input(seed, f"target:{step_index}:query"),
        )
        for step_index in range(SHARED_FLOOR_TARGET_STEPS)
    )
    family = TransferFamily(
        seed=seed,
        regime="shared",
        modulus=SHARED_FLOOR_MODULUS,
        source_rule=rule,
        target_rules=(rule,) * SHARED_FLOOR_TARGET_STEPS,
        source_examples=source_examples,
        target_steps=target_steps,
        shift_index=None,
    )
    _require_rule_identifiable(rule, source_examples)
    _require_no_wrap(family)
    return family


def run_shared_floor_v2_seed(
    client: SharedFloorClient,
    difficulty: str,
    index: int,
) -> SharedFloorSeedResult:
    family = generate_shared_floor_v2_family(difficulty, index)
    prefix = f"{difficulty}:{index}:{family.seed}"

    explicit_completion = client.complete_named(
        f"{prefix}:a0-explicit",
        build_explicit_application_messages(family),
        output_kind="vector",
    )
    application_correct = (
        _parse_vector(explicit_completion, family=family)
        == family.expected_output(0)
    )

    adapter = _NamedFormationAdapter(client, prefix)
    representations = form_s2_representations_r4(adapter, family)
    if adapter.index != 3:
        raise SharedFloorCalibrationError(
            "shared-floor-v2 formation did not consume exactly three calls"
        )

    p4 = representations["P4_MEMORY_PLUS_STRUCTURE"]
    p5 = representations["P5_STRUCTURE_ONLY_RECONSTRUCTABLE"]
    p6 = representations["P6_GENERIC_EQUAL_INFORMATION"]
    if (
        p4.formation_completion is not p5.formation_completion
        or p4.formation_completion is not p6.formation_completion
    ):
        raise SharedFloorCalibrationError(
            "P4/P5/P6 no longer share one formation completion"
        )
    p4_payload = json.loads(p4.serialized)
    p6_payload = json.loads(p6.serialized)
    p4_p6_equal = semantic_digest(
        "P4_MEMORY_PLUS_STRUCTURE",
        p4_payload,
    ) == semantic_digest(
        "P6_GENERIC_EQUAL_INFORMATION",
        p6_payload,
    )
    if not p4_p6_equal:
        raise SharedFloorCalibrationError(
            "P4/P6 semantic equality failed during shared-floor-v2 calibration"
        )

    neutral_correct: dict[str, bool] = {}
    for arm in SHARED_FLOOR_NEUTRAL_ARMS:
        representation = representations[arm]
        prompt = build_s2_target_messages(
            representation,
            family,
            step_index=0,
            examples_visible=SHARED_FLOOR_EXAMPLES_VISIBLE,
        )
        completion = client.complete_named(
            f"{prefix}:canonical:{arm}",
            prompt.messages,
            output_kind="vector",
        )
        neutral_correct[arm] = (
            _parse_vector(completion, family=family)
            == family.expected_output(0)
        )

    return SharedFloorSeedResult(
        difficulty=difficulty,
        seed=family.seed,
        application_correct=application_correct,
        formation_correct=_formation_recovers_rule(p4, family),
        neutral_correct=neutral_correct,
        p4_p6_semantic_equal=p4_p6_equal,
        shared_formation_lineage=True,
    )


def summarize_shared_floor_v2_candidate(
    difficulty: str,
    seeds: tuple[SharedFloorSeedResult, ...],
    *,
    semantic_calls: int = SHARED_FLOOR_CALLS_PER_DIFFICULTY,
    input_token_requests: int = SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY,
    p2_hard_admitted: int = SHARED_FLOOR_P2_REQUIRED_ADMITTED,
) -> SharedFloorCandidateResult:
    if difficulty not in SHARED_FLOOR_ACTIVE_COUNTS:
        raise SharedFloorCalibrationError(
            f"unsupported shared-floor-v2 difficulty: {difficulty}"
        )
    if len(seeds) != SHARED_FLOOR_SEEDS_PER_DIFFICULTY:
        raise SharedFloorCalibrationError(
            "shared-floor-v2 candidate summary requires exactly six paired seeds"
        )
    if tuple(result.seed for result in seeds) != SHARED_FLOOR_V2_SEEDS:
        raise SharedFloorCalibrationError(
            "shared-floor-v2 candidate seed order drifted"
        )
    if any(result.difficulty != difficulty for result in seeds):
        raise SharedFloorCalibrationError("shared-floor-v2 difficulty labels drifted")
    if any(
        not result.p4_p6_semantic_equal or not result.shared_formation_lineage
        for result in seeds
    ):
        raise SharedFloorCalibrationError(
            "shared-floor-v2 candidate violated shared semantics/lineage"
        )

    application_correct = sum(result.application_correct for result in seeds)
    formation_correct = sum(result.formation_correct for result in seeds)
    neutral_correct = {
        arm: sum(result.neutral_correct[arm] for result in seeds)
        for arm in SHARED_FLOOR_NEUTRAL_ARMS
    }
    neutral_control_mean = sum(neutral_correct.values()) / (
        len(SHARED_FLOOR_NEUTRAL_ARMS) * SHARED_FLOOR_SEEDS_PER_DIFFICULTY
    )
    non_degenerate = sum(
        1
        for correct in neutral_correct.values()
        if 1 <= correct <= SHARED_FLOOR_SEEDS_PER_DIFFICULTY - 1
    )
    admitted = (
        application_correct >= SHARED_FLOOR_APPLICATION_MIN_CORRECT
        and formation_correct >= SHARED_FLOOR_FORMATION_MIN_CORRECT
        and p2_hard_admitted >= SHARED_FLOOR_P2_REQUIRED_ADMITTED
        and SHARED_FLOOR_NEUTRAL_MEAN_MIN
        <= neutral_control_mean
        <= SHARED_FLOOR_NEUTRAL_MEAN_MAX
        and non_degenerate >= SHARED_FLOOR_MIN_NON_DEGENERATE_ARMS
    )
    return SharedFloorCandidateResult(
        difficulty=difficulty,
        seeds=seeds,
        semantic_calls=semantic_calls,
        input_token_requests=input_token_requests,
        application_correct=application_correct,
        formation_correct=formation_correct,
        p2_hard_admitted=p2_hard_admitted,
        neutral_correct=neutral_correct,
        neutral_control_mean=neutral_control_mean,
        neutral_non_degenerate_arm_count=non_degenerate,
        admitted=admitted,
    )


def shared_floor_v2_call_plan(difficulty: str) -> tuple[str, ...]:
    if difficulty not in SHARED_FLOOR_ACTIVE_COUNTS:
        raise SharedFloorCalibrationError(
            f"unsupported shared-floor-v2 difficulty: {difficulty}"
        )
    plan: list[str] = []
    for index, seed in enumerate(SHARED_FLOOR_V2_SEEDS):
        prefix = f"{difficulty}:{index}:{seed}"
        plan.append(f"{prefix}:a0-explicit")
        plan.extend(f"{prefix}:form-{suffix}" for suffix in ("p2", "p3", "p4"))
        plan.extend(
            f"{prefix}:canonical:{arm}" for arm in SHARED_FLOOR_NEUTRAL_ARMS
        )
    if len(plan) != SHARED_FLOOR_CALLS_PER_DIFFICULTY:
        raise AssertionError("shared-floor-v2 call plan length drifted")
    if any(
        ":canonical:P4_MEMORY_PLUS_STRUCTURE" in question
        or ":canonical:P5_STRUCTURE_ONLY_RECONSTRUCTABLE" in question
        for question in plan
    ):
        raise AssertionError("P4/P5 target outcome leaked into v2 calibration")
    return tuple(plan)


def run_shared_floor_v2_candidate(
    client: SharedFloorClient,
    difficulty: str,
) -> SharedFloorCandidateResult:
    before_provider = client.provider_attempts
    before_input = client.input_count_attempts
    seeds = tuple(
        run_shared_floor_v2_seed(client, difficulty, index)
        for index in range(SHARED_FLOOR_SEEDS_PER_DIFFICULTY)
    )
    semantic_calls = client.provider_attempts - before_provider
    input_requests = client.input_count_attempts - before_input
    if semantic_calls != SHARED_FLOOR_CALLS_PER_DIFFICULTY:
        raise SharedFloorCalibrationError(
            "shared-floor-v2 candidate semantic-call count drifted"
        )
    if input_requests != SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY:
        raise SharedFloorCalibrationError(
            "shared-floor-v2 candidate input-token request count drifted"
        )
    return summarize_shared_floor_v2_candidate(
        difficulty,
        seeds,
        semantic_calls=semantic_calls,
        input_token_requests=input_requests,
    )


def run_shared_floor_v2_calibration(
    client_factory: Callable[[str, tuple[str, ...]], SharedFloorClient],
) -> SharedFloorCalibrationResult:
    validate_shared_floor_v2_preregistration()
    candidates: list[SharedFloorCandidateResult] = []
    semantic_calls = 0
    input_token_requests = 0

    for difficulty in SHARED_FLOOR_DIFFICULTIES:
        client = client_factory(difficulty, shared_floor_v2_call_plan(difficulty))
        candidate = run_shared_floor_v2_candidate(client, difficulty)
        if hasattr(client, "require_complete_plan"):
            client.require_complete_plan()  # type: ignore[attr-defined]
        candidates.append(candidate)
        semantic_calls += candidate.semantic_calls
        input_token_requests += candidate.input_token_requests
        if candidate.admitted:
            return SharedFloorCalibrationResult(
                classification=SHARED_TARGET_RANGE_QUALIFIED,
                selected_difficulty=difficulty,
                candidates=tuple(candidates),
                semantic_calls=semantic_calls,
                input_token_requests=input_token_requests,
            )

    if semantic_calls != SHARED_FLOOR_MAX_SEMANTIC_CALLS:
        raise SharedFloorCalibrationError(
            "fully exhausted shared-floor-v2 semantic-call total drifted"
        )
    if input_token_requests != SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS:
        raise SharedFloorCalibrationError(
            "fully exhausted shared-floor-v2 input-token total drifted"
        )
    return SharedFloorCalibrationResult(
        classification=NO_SHARED_TARGET_RANGE_FOUND,
        selected_difficulty=None,
        candidates=tuple(candidates),
        semantic_calls=semantic_calls,
        input_token_requests=input_token_requests,
    )
