from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
from typing import Protocol

from relaylm.v2_cognitive_ir_actual_model import (
    S2Representation,
    build_s2_target_messages,
)
from relaylm.v2_cognitive_ir_calibration import CALIBRATION_SEEDS
from relaylm.v2_cognitive_ir_calibration_v2 import CALIBRATION_V2_SEEDS
from relaylm.v2_cognitive_ir_experiment import decode_semantic_payload, semantic_digest
from relaylm.v2_cognitive_ir_p2_boundedness_qual_v2 import (
    P2_BOUNDEDNESS_QUAL_V2_SEEDS,
)
from relaylm.v2_cognitive_ir_p2_termination_qual import P2_TERMINATION_QUAL_SEEDS
from relaylm.v2_cognitive_ir_s2_selected import S2_SELECTED_SEED
from relaylm.v2_cognitive_ir_s3_r2 import HISTORICAL_S3_V1_SEEDS, S3_R2_SEEDS
from relaylm.v2_cognitive_ir_s3_r3 import S3_R3_SEEDS
from relaylm.v2_cognitive_ir_s3_r4 import (
    S3_R4_PREREGISTRATION_SHA256,
    S3_R4_SEEDS,
    form_s2_representations_r4,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from relaylm.v2_transfer_experiment import (
    PublicExample,
    TargetStep,
    TransferFamily,
    VectorRule,
)


SHARED_FLOOR_LABEL = "relaylm2-cognitive-ir-shared-floor-calibration-v1"
SHARED_FLOOR_CLAIM = "NON_CITABLE_SHARED_TARGET_RANGE_CALIBRATION"
SHARED_FLOOR_CITABLE = False
SHARED_FLOOR_ARCHITECTURE_CONSEQUENCE = "NONE"

SHARED_FLOOR_SEEDS = (
    824131651,
    727517075,
    1455229498,
    691488953,
    1485742517,
    411743139,
)
SHARED_FLOOR_DIFFICULTIES = (
    "K4_CURRENT_CLASS",
    "K3_THREE_ACTIVE",
    "K2_TWO_ACTIVE",
    "K1_ONE_ACTIVE",
)
SHARED_FLOOR_ACTIVE_COUNTS: Mapping[str, int] = {
    "K4_CURRENT_CLASS": 4,
    "K3_THREE_ACTIVE": 3,
    "K2_TWO_ACTIVE": 2,
    "K1_ONE_ACTIVE": 1,
}
SHARED_FLOOR_NEUTRAL_ARMS = (
    "P0_RAW_HISTORY",
    "P1_RETRIEVAL_ONLY",
    "P2_ORDINARY_SUMMARY",
    "P3_SEMANTIC_CACHE",
    "P6_GENERIC_EQUAL_INFORMATION",
)

SHARED_FLOOR_VECTOR_WIDTH = 4
SHARED_FLOOR_MODULUS = 10
SHARED_FLOOR_SOURCE_EXAMPLES = 4
SHARED_FLOOR_TARGET_STEPS = 4
SHARED_FLOOR_EXAMPLES_VISIBLE = 0

SHARED_FLOOR_CALLS_PER_SEED = 9
SHARED_FLOOR_SEEDS_PER_DIFFICULTY = 6
SHARED_FLOOR_CALLS_PER_DIFFICULTY = 54
SHARED_FLOOR_MAX_SEMANTIC_CALLS = 216
SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_CALL = 2
SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY = 108
SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS = 432

SHARED_FLOOR_APPLICATION_MIN_CORRECT = 6
SHARED_FLOOR_FORMATION_MIN_CORRECT = 3
SHARED_FLOOR_P2_REQUIRED_ADMITTED = 6
SHARED_FLOOR_NEUTRAL_MEAN_MIN = 0.20
SHARED_FLOOR_NEUTRAL_MEAN_MAX = 0.80
SHARED_FLOOR_MIN_NON_DEGENERATE_ARMS = 2

SHARED_TARGET_RANGE_QUALIFIED = "SHARED_TARGET_RANGE_QUALIFIED"
NO_SHARED_TARGET_RANGE_FOUND = "NO_SHARED_TARGET_RANGE_FOUND"
CALIBRATION_INCOMPLETE = "CALIBRATION_INCOMPLETE"

# Issue identities are part of the seed-collision fence because prior RelayLM
# calibration lanes have historically reserved issue-number seeds as well.
_HISTORICAL_ISSUE_SEEDS = {
    2211,
    2461,
    2491,
    2498,
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
}


class SharedFloorCalibrationError(ValueError):
    """The frozen #2600 shared-floor calibration contract was violated."""


class SharedFloorClient(Protocol):
    provider_attempts: int
    provider_completions: int
    input_count_attempts: int
    input_count_completions: int

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion: ...


def _json_text(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def derive_shared_floor_seed(index: int) -> int:
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 6:
        raise SharedFloorCalibrationError("shared-floor seed index must be 0..5")
    raw = hashlib.sha256(
        f"{SHARED_FLOOR_LABEL}|seed|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def _flatten_seed_map(values: Mapping[str, tuple[int, ...]]) -> set[int]:
    return {seed for seeds in values.values() for seed in seeds}


def validate_shared_floor_preregistration() -> None:
    derived = tuple(derive_shared_floor_seed(index) for index in range(6))
    if derived != SHARED_FLOOR_SEEDS:
        raise SharedFloorCalibrationError(
            "derived shared-floor seeds drifted from #2600"
        )
    if len(set(SHARED_FLOOR_SEEDS)) != len(SHARED_FLOOR_SEEDS):
        raise SharedFloorCalibrationError("shared-floor seeds are not unique")

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
        *_HISTORICAL_ISSUE_SEEDS,
    }
    overlap = sorted(set(SHARED_FLOOR_SEEDS) & historical)
    if overlap:
        raise SharedFloorCalibrationError(
            f"shared-floor seeds overlap historical evidence: {overlap}"
        )

    if tuple(SHARED_FLOOR_DIFFICULTIES) != (
        "K4_CURRENT_CLASS",
        "K3_THREE_ACTIVE",
        "K2_TWO_ACTIVE",
        "K1_ONE_ACTIVE",
    ):
        raise SharedFloorCalibrationError("shared-floor difficulty order drifted")
    if (
        SHARED_FLOOR_CALLS_PER_SEED,
        SHARED_FLOOR_CALLS_PER_DIFFICULTY,
        SHARED_FLOOR_MAX_SEMANTIC_CALLS,
    ) != (9, 54, 216):
        raise SharedFloorCalibrationError("shared-floor semantic-call ledger drifted")
    if (
        SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_CALL,
        SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY,
        SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS,
    ) != (2, 108, 432):
        raise SharedFloorCalibrationError(
            "shared-floor exact input-token request ledger drifted"
        )
    if (
        SHARED_FLOOR_VECTOR_WIDTH,
        SHARED_FLOOR_MODULUS,
        SHARED_FLOOR_SOURCE_EXAMPLES,
        SHARED_FLOOR_TARGET_STEPS,
        SHARED_FLOOR_EXAMPLES_VISIBLE,
    ) != (4, 10, 4, 4, 0):
        raise SharedFloorCalibrationError("shared-floor task geometry drifted")
    if S3_R4_PREREGISTRATION_SHA256 != (
        "deb10b356f1cfe4fd18275b790f1a5bcb5972b1b841e874c26a8827ffd20dae4"
    ):
        raise SharedFloorCalibrationError("historical S3-R4 identity drifted")


def _seed_digest(seed: int, label: str) -> bytes:
    return hashlib.sha256(
        f"{SHARED_FLOOR_LABEL}|{seed}|{label}".encode("utf-8")
    ).digest()


def _active_order(seed: int) -> tuple[int, ...]:
    ranked = sorted(
        range(SHARED_FLOOR_VECTOR_WIDTH),
        key=lambda coordinate: (
            _seed_digest(seed, f"active-rank:{coordinate}"),
            coordinate,
        ),
    )
    return tuple(ranked)


def _nonzero_value(seed: int, coordinate: int) -> int:
    return 1 + (_seed_digest(seed, f"offset-value:{coordinate}")[0] % 3)


def shared_floor_offsets(difficulty: str, seed: int) -> tuple[int, ...]:
    if difficulty not in SHARED_FLOOR_ACTIVE_COUNTS:
        raise SharedFloorCalibrationError(
            f"unsupported shared-floor difficulty: {difficulty}"
        )
    active_count = SHARED_FLOOR_ACTIVE_COUNTS[difficulty]
    active = set(_active_order(seed)[:active_count])
    offsets = tuple(
        _nonzero_value(seed, coordinate) if coordinate in active else 0
        for coordinate in range(SHARED_FLOOR_VECTOR_WIDTH)
    )
    if sum(value != 0 for value in offsets) != active_count:
        raise AssertionError("shared-floor active offset count drifted")
    return offsets


def _bounded_input(seed: int, label: str) -> tuple[int, ...]:
    raw = _seed_digest(seed, label)
    # 0..6 leaves at least three units of no-wrap headroom under every K level.
    return tuple(raw[index] % 7 for index in range(SHARED_FLOOR_VECTOR_WIDTH))


def _require_rule_identifiable(
    rule: VectorRule,
    examples: tuple[PublicExample, ...],
) -> None:
    if not examples:
        raise SharedFloorCalibrationError("shared-floor source examples are empty")
    inferred: list[int] = []
    first = examples[0]
    for coordinate in range(SHARED_FLOOR_VECTOR_WIDTH):
        delta = first.output_values[coordinate] - first.input_values[coordinate]
        if delta < 0:
            raise SharedFloorCalibrationError(
                "shared-floor source example unexpectedly wrapped"
            )
        inferred.append(delta)
    if tuple(inferred) != rule.offsets:
        raise SharedFloorCalibrationError(
            "shared-floor source examples do not identify the exact rule"
        )
    for example in examples:
        if rule.apply(example.input_values) != example.output_values:
            raise SharedFloorCalibrationError(
                "shared-floor source example disagrees with generated rule"
            )


def _require_no_wrap(family: TransferFamily) -> None:
    rule = family.source_rule
    vectors = [example.input_values for example in family.source_examples]
    for step in family.target_steps:
        vectors.extend(example.input_values for example in step.examples)
        vectors.append(step.query)
    if any(
        vector[coordinate] + rule.offsets[coordinate] >= family.modulus
        for vector in vectors
        for coordinate in range(SHARED_FLOOR_VECTOR_WIDTH)
    ):
        raise SharedFloorCalibrationError(
            "shared-floor source/target vector unexpectedly wraps"
        )


def generate_shared_floor_family(difficulty: str, index: int) -> TransferFamily:
    validate_shared_floor_preregistration()
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 6:
        raise SharedFloorCalibrationError("shared-floor family index must be 0..5")
    seed = SHARED_FLOOR_SEEDS[index]
    offsets = shared_floor_offsets(difficulty, seed)
    rule = VectorRule(
        tuple(range(SHARED_FLOOR_VECTOR_WIDTH)),
        offsets,
        SHARED_FLOOR_MODULUS,
    )
    source_examples = tuple(
        PublicExample(
            values := _bounded_input(seed, f"source-example:{example_index}"),
            rule.apply(values),
        )
        for example_index in range(SHARED_FLOOR_SOURCE_EXAMPLES)
    )
    target_steps = tuple(
        TargetStep(
            examples=tuple(
                PublicExample(
                    values := _bounded_input(
                        seed,
                        f"target:{step_index}:example:{example_index}",
                    ),
                    rule.apply(values),
                )
                for example_index in range(3)
            ),
            query=_bounded_input(seed, f"target:{step_index}:query"),
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


def build_explicit_application_messages(
    family: TransferFamily,
) -> tuple[dict[str, str], ...]:
    return (
        {
            "role": "system",
            "content": (
                "Apply the supplied exact vector rule to the query. "
                "Return only one JSON integer array of length 4."
            ),
        },
        {
            "role": "user",
            "content": _json_text(
                {
                    "explicit_rule": {
                        "permutation": list(family.source_rule.permutation),
                        "offsets": list(family.source_rule.offsets),
                        "modulus": family.source_rule.modulus,
                    },
                    "query": list(family.target_steps[0].query),
                }
            ),
        },
    )


class _NamedFormationAdapter:
    def __init__(self, client: SharedFloorClient, prefix: str) -> None:
        self.client = client
        self.prefix = prefix
        self.index = 0

    def complete(
        self,
        messages: tuple[dict[str, str], ...],
    ) -> ExperimentCompletion:
        if self.index >= 3:
            raise SharedFloorCalibrationError(
                "shared-floor formation attempted an undeclared fourth call"
            )
        suffix = ("p2", "p3", "p4")[self.index]
        completion = self.client.complete_named(
            f"{self.prefix}:form-{suffix}",
            messages,
            output_kind="rule" if suffix == "p4" else "text",
        )
        self.index += 1
        return completion


def _parse_vector(
    completion: ExperimentCompletion,
    *,
    family: TransferFamily,
) -> tuple[int, ...] | None:
    try:
        value = json.loads(completion.content)
    except (json.JSONDecodeError, TypeError):
        return None
    if (
        not isinstance(value, list)
        or len(value) != SHARED_FLOOR_VECTOR_WIDTH
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
        or any(item < 0 or item >= family.modulus for item in value)
    ):
        return None
    return tuple(value)


def _formation_recovers_rule(
    representation: S2Representation,
    family: TransferFamily,
) -> bool:
    try:
        payload = json.loads(representation.serialized)
        if not isinstance(payload, Mapping):
            return False
        semantics = decode_semantic_payload(
            "P4_MEMORY_PLUS_STRUCTURE",
            payload,
        )
        return (
            tuple(semantics["permutation"]) == family.source_rule.permutation
            and tuple(semantics["offsets"]) == family.source_rule.offsets
            and semantics["modulus"] == family.modulus
        )
    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ):
        return False


@dataclass(frozen=True, slots=True)
class SharedFloorSeedResult:
    difficulty: str
    seed: int
    application_correct: bool
    formation_correct: bool
    neutral_correct: dict[str, bool]
    p4_p6_semantic_equal: bool
    shared_formation_lineage: bool


@dataclass(frozen=True, slots=True)
class SharedFloorCandidateResult:
    difficulty: str
    seeds: tuple[SharedFloorSeedResult, ...]
    semantic_calls: int
    input_token_requests: int
    application_correct: int
    formation_correct: int
    p2_hard_admitted: int
    neutral_correct: dict[str, int]
    neutral_control_mean: float
    neutral_non_degenerate_arm_count: int
    admitted: bool


@dataclass(frozen=True, slots=True)
class SharedFloorCalibrationResult:
    classification: str
    selected_difficulty: str | None
    candidates: tuple[SharedFloorCandidateResult, ...]
    semantic_calls: int
    input_token_requests: int
    claim: str = SHARED_FLOOR_CLAIM
    citable: bool = SHARED_FLOOR_CITABLE
    architecture_consequence: str = SHARED_FLOOR_ARCHITECTURE_CONSEQUENCE


def run_shared_floor_seed(
    client: SharedFloorClient,
    difficulty: str,
    index: int,
) -> SharedFloorSeedResult:
    family = generate_shared_floor_family(difficulty, index)
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
            "shared-floor formation did not consume exactly three calls"
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
            "P4/P6 semantic equality failed during shared-floor calibration"
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


def summarize_shared_floor_candidate(
    difficulty: str,
    seeds: tuple[SharedFloorSeedResult, ...],
    *,
    semantic_calls: int = SHARED_FLOOR_CALLS_PER_DIFFICULTY,
    input_token_requests: int = SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY,
    p2_hard_admitted: int = SHARED_FLOOR_P2_REQUIRED_ADMITTED,
) -> SharedFloorCandidateResult:
    if difficulty not in SHARED_FLOOR_ACTIVE_COUNTS:
        raise SharedFloorCalibrationError(
            f"unsupported shared-floor difficulty: {difficulty}"
        )
    if len(seeds) != SHARED_FLOOR_SEEDS_PER_DIFFICULTY:
        raise SharedFloorCalibrationError(
            "candidate summary requires exactly six paired seeds"
        )
    if tuple(result.seed for result in seeds) != SHARED_FLOOR_SEEDS:
        raise SharedFloorCalibrationError(
            "candidate seed order drifted from frozen calibration"
        )
    if any(result.difficulty != difficulty for result in seeds):
        raise SharedFloorCalibrationError("candidate difficulty labels drifted")
    if any(
        not result.p4_p6_semantic_equal or not result.shared_formation_lineage
        for result in seeds
    ):
        raise SharedFloorCalibrationError(
            "candidate violated shared semantics/formation lineage"
        )

    application_correct = sum(result.application_correct for result in seeds)
    formation_correct = sum(result.formation_correct for result in seeds)
    neutral_correct = {
        arm: sum(result.neutral_correct[arm] for result in seeds)
        for arm in SHARED_FLOOR_NEUTRAL_ARMS
    }
    total_neutral_correct = sum(neutral_correct.values())
    neutral_control_mean = total_neutral_correct / (
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


def shared_floor_call_plan(difficulty: str) -> tuple[str, ...]:
    if difficulty not in SHARED_FLOOR_ACTIVE_COUNTS:
        raise SharedFloorCalibrationError(
            f"unsupported shared-floor difficulty: {difficulty}"
        )
    plan: list[str] = []
    for index, seed in enumerate(SHARED_FLOOR_SEEDS):
        prefix = f"{difficulty}:{index}:{seed}"
        plan.append(f"{prefix}:a0-explicit")
        plan.extend(f"{prefix}:form-{suffix}" for suffix in ("p2", "p3", "p4"))
        plan.extend(
            f"{prefix}:canonical:{arm}" for arm in SHARED_FLOOR_NEUTRAL_ARMS
        )
    if len(plan) != SHARED_FLOOR_CALLS_PER_DIFFICULTY:
        raise AssertionError("shared-floor call plan length drifted")
    if any(
        ":canonical:P4_MEMORY_PLUS_STRUCTURE" in question
        or ":canonical:P5_STRUCTURE_ONLY_RECONSTRUCTABLE" in question
        for question in plan
    ):
        raise AssertionError("P4/P5 target outcome leaked into calibration call plan")
    return tuple(plan)


def run_shared_floor_candidate(
    client: SharedFloorClient,
    difficulty: str,
) -> SharedFloorCandidateResult:
    before_provider = client.provider_attempts
    before_input = client.input_count_attempts
    seeds = tuple(
        run_shared_floor_seed(client, difficulty, index)
        for index in range(SHARED_FLOOR_SEEDS_PER_DIFFICULTY)
    )
    semantic_calls = client.provider_attempts - before_provider
    input_requests = client.input_count_attempts - before_input
    if semantic_calls != SHARED_FLOOR_CALLS_PER_DIFFICULTY:
        raise SharedFloorCalibrationError(
            "candidate semantic-call count drifted: "
            f"expected {SHARED_FLOOR_CALLS_PER_DIFFICULTY}, got {semantic_calls}"
        )
    if input_requests != SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY:
        raise SharedFloorCalibrationError(
            "candidate input-token request count drifted: "
            f"expected {SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY}, "
            f"got {input_requests}"
        )
    return summarize_shared_floor_candidate(
        difficulty,
        seeds,
        semantic_calls=semantic_calls,
        input_token_requests=input_requests,
    )


def run_shared_floor_calibration(
    client_factory: Callable[[str, tuple[str, ...]], SharedFloorClient],
) -> SharedFloorCalibrationResult:
    validate_shared_floor_preregistration()
    candidates: list[SharedFloorCandidateResult] = []
    semantic_calls = 0
    input_token_requests = 0

    for difficulty in SHARED_FLOOR_DIFFICULTIES:
        client = client_factory(difficulty, shared_floor_call_plan(difficulty))
        candidate = run_shared_floor_candidate(client, difficulty)
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
            "fully exhausted calibration semantic-call total drifted"
        )
    if input_token_requests != SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS:
        raise SharedFloorCalibrationError(
            "fully exhausted calibration input-token request total drifted"
        )
    return SharedFloorCalibrationResult(
        classification=NO_SHARED_TARGET_RANGE_FOUND,
        selected_difficulty=None,
        candidates=tuple(candidates),
        semantic_calls=semantic_calls,
        input_token_requests=input_token_requests,
    )
