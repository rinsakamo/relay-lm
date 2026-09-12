from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math

from relaylm.v2_cognitive_ir_attack_observability_calibration import (
    ATTACK_OBS_SEEDS,
    D1_PREREGISTERED_SEEDS,
)
from relaylm.v2_cognitive_ir_calibration import CALIBRATION_SEEDS
from relaylm.v2_cognitive_ir_calibration_v2 import CALIBRATION_V2_SEEDS
from relaylm.v2_cognitive_ir_current_law_certificate_qualification import G1_SEEDS
from relaylm.v2_cognitive_ir_experiment import (
    decode_semantic_payload,
    neutralize_typed_payload,
    semantic_digest,
)
from relaylm.v2_cognitive_ir_p2_boundedness_qual_v2 import (
    P2_BOUNDEDNESS_QUAL_V2_SEEDS,
)
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
from relaylm.v2_cognitive_ir_s3_r5 import (
    S3_R5_ACTIVE_COORDINATES,
    S3_R5_SELECTED_DIFFICULTY,
    S3_R5_SEEDS,
)
from relaylm.v2_cognitive_ir_shared_floor_calibration import SHARED_FLOOR_SEEDS
from relaylm.v2_cognitive_ir_shared_floor_calibration_v2 import SHARED_FLOOR_V2_SEEDS


PREREGISTRATION_ISSUE = 2709
SCIENTIFIC_PARENT_ISSUE = 2211
PREREGISTRATION_LABEL = "relaylm2-cognitive-ir-semantic-reconstruction-v1"

FAMILY_COUNT = 16
ARMS = ("P4_MEMORY_PLUS_STRUCTURE", "P6_GENERIC_EQUAL_INFORMATION")
SEMANTIC_COMPLETIONS = 32
SCORED_FIELDS = (
    "operation",
    "permutation",
    "offsets",
    "modulus",
    "provenance_handles",
)
PRIMARY_ENDPOINT = "full_payload_exact"
DIAGNOSTIC_ENDPOINTS = (
    "core_rule_exact",
    "provenance_exact",
    "parse_valid",
)
COST_FIELDS = (
    "input_tokens",
    "output_tokens",
    "model_calls",
    "wall_clock_seconds",
    "representation_bytes",
    "representation_tokens",
)

CONTEXT_LIMIT = 8192
MAX_OUTPUT_TOKENS = 256
TEMPERATURE = 0.0
REASONING = "none"
REQUEST_SEED = None
PARALLEL_SEMANTIC_SLOTS = 1
ALPHA = 0.05
ARCHITECTURE_CONSEQUENCE = "NONE"
PHYSICAL_EXECUTION_AUTHORIZED = False

FORBIDDEN_RESCUE_COUNTS: Mapping[str, int] = {
    "semantic_retry": 0,
    "replay": 0,
    "reseed": 0,
    "fallback": 0,
    "hidden_repair_call": 0,
    "judge_call": 0,
}

RECONSTRUCTION_SYSTEM_PROMPT = (
    "Reconstruct the semantic payload represented by the supplied prior material. "
    "Return only one JSON object with exactly these keys: operation, permutation, "
    "offsets, modulus, provenance_handles. Do not add markdown or commentary."
)


class SemanticReconstructionBindingError(ValueError):
    """The #2709 semantic-reconstruction preregistration was violated."""


def _flatten(values: Mapping[str, Sequence[int]]) -> set[int]:
    return {seed for seeds in values.values() for seed in seeds}


def derive_family_seed(index: int) -> int:
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 0 <= index < FAMILY_COUNT
    ):
        raise SemanticReconstructionBindingError("family index must be 0..15")
    raw = hashlib.sha256(
        f"{PREREGISTRATION_LABEL}|family|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(raw[:8], "big")


def preregistered_seeds() -> tuple[int, ...]:
    return tuple(derive_family_seed(index) for index in range(FAMILY_COUNT))


def historical_family_seeds() -> frozenset[int]:
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
        *D1_PREREGISTERED_SEEDS,
        *_flatten(ATTACK_OBS_SEEDS),
        *_flatten(G1_SEEDS),
    }
    return frozenset(historical)


def validate_seed_admission() -> None:
    seeds = preregistered_seeds()
    if len(seeds) != FAMILY_COUNT or len(set(seeds)) != FAMILY_COUNT:
        raise SemanticReconstructionBindingError(
            "semantic-reconstruction seeds are not exactly 16 unique values"
        )
    overlap = sorted(set(seeds) & historical_family_seeds())
    if overlap:
        raise SemanticReconstructionBindingError(
            f"semantic-reconstruction seeds overlap historical evidence: {overlap}"
        )


def _json_text(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _canonical_truth(payload: Mapping[str, object]) -> dict[str, object]:
    if set(payload) != set(SCORED_FIELDS):
        raise SemanticReconstructionBindingError(
            "semantic payload must contain exactly the five scored fields"
        )
    operation = payload["operation"]
    permutation = payload["permutation"]
    offsets = payload["offsets"]
    modulus = payload["modulus"]
    provenance = payload["provenance_handles"]

    if operation != "affine_permutation":
        raise SemanticReconstructionBindingError("unsupported operation")
    if (
        not isinstance(permutation, (list, tuple))
        or len(permutation) != S3_VECTOR_WIDTH
        or any(
            isinstance(item, bool) or not isinstance(item, int)
            for item in permutation
        )
        or tuple(sorted(permutation)) != tuple(range(S3_VECTOR_WIDTH))
    ):
        raise SemanticReconstructionBindingError("invalid permutation")
    if (
        not isinstance(offsets, (list, tuple))
        or len(offsets) != S3_VECTOR_WIDTH
        or any(
            isinstance(item, bool) or not isinstance(item, int)
            for item in offsets
        )
    ):
        raise SemanticReconstructionBindingError("invalid offsets")
    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus <= 1:
        raise SemanticReconstructionBindingError("invalid modulus")
    if any(value < 0 or value >= modulus for value in offsets):
        raise SemanticReconstructionBindingError("offset outside modulus")
    if (
        not isinstance(provenance, (list, tuple))
        or not provenance
        or any(not isinstance(item, str) or not item for item in provenance)
    ):
        raise SemanticReconstructionBindingError("invalid provenance handles")

    return {
        "operation": operation,
        "permutation": list(permutation),
        "offsets": list(offsets),
        "modulus": modulus,
        "provenance_handles": list(provenance),
    }


@dataclass(frozen=True, slots=True)
class MechanismControl:
    canonical_truth: Mapping[str, object]
    semantic_digest: str
    serialized_by_arm: Mapping[str, str]


def prepare_mechanism_control(
    canonical_payload: Mapping[str, object],
) -> MechanismControl:
    truth = _canonical_truth(canonical_payload)
    typed = {
        "memory": {"origin_refs": truth["provenance_handles"]},
        "structure": {
            "operation": truth["operation"],
            "permutation": truth["permutation"],
            "offsets": truth["offsets"],
            "modulus": truth["modulus"],
        },
    }
    generic = neutralize_typed_payload(typed)

    typed_digest = semantic_digest(ARMS[0], typed)
    generic_digest = semantic_digest(ARMS[1], generic)
    if typed_digest != generic_digest:
        raise SemanticReconstructionBindingError("P4/P6 semantic digests differ")

    typed_truth = decode_semantic_payload(ARMS[0], typed)
    generic_truth = decode_semantic_payload(ARMS[1], generic)
    if typed_truth != truth or generic_truth != truth:
        raise SemanticReconstructionBindingError(
            "P4/P6 decoded semantics differ from canonical truth"
        )

    serialized = {
        ARMS[0]: _json_text(typed),
        ARMS[1]: _json_text(generic),
    }
    if serialized[ARMS[0]] == serialized[ARMS[1]]:
        raise SemanticReconstructionBindingError(
            "P4/P6 mechanism-control surfaces unexpectedly match"
        )
    return MechanismControl(
        canonical_truth=truth,
        semantic_digest=typed_digest,
        serialized_by_arm=serialized,
    )


def build_reconstruction_messages(
    serialized_representation: str,
) -> tuple[dict[str, str], ...]:
    if not isinstance(serialized_representation, str) or not serialized_representation:
        raise SemanticReconstructionBindingError(
            "serialized representation must be a non-empty string"
        )
    return (
        {"role": "system", "content": RECONSTRUCTION_SYSTEM_PROMPT},
        {"role": "user", "content": serialized_representation},
    )


def semantic_call_plan() -> tuple[tuple[int, int, str], ...]:
    validate_seed_admission()
    plan = tuple(
        (index, seed, arm)
        for index, seed in enumerate(preregistered_seeds())
        for arm in ARMS
    )
    if len(plan) != SEMANTIC_COMPLETIONS:
        raise SemanticReconstructionBindingError("semantic call ledger drifted")
    return plan


def _reject_constant(value: str) -> object:
    raise SemanticReconstructionBindingError(f"non-finite JSON constant: {value}")


def _reject_duplicate_object(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SemanticReconstructionBindingError(
                f"duplicate JSON object member: {key}"
            )
        result[key] = value
    return result


def parse_reconstruction(content: str) -> dict[str, object]:
    if not isinstance(content, str) or not content.strip():
        raise SemanticReconstructionBindingError(
            "completion must be one non-empty JSON object"
        )
    try:
        value = json.loads(
            content,
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise SemanticReconstructionBindingError(
            "completion is not one valid JSON value"
        ) from exc
    if not isinstance(value, Mapping):
        raise SemanticReconstructionBindingError(
            "completion must decode to one JSON object"
        )
    return _canonical_truth(value)


@dataclass(frozen=True, slots=True)
class ReconstructionScore:
    parse_valid: bool
    full_payload_exact: bool
    core_rule_exact: bool
    provenance_exact: bool


def score_reconstruction(
    content: str,
    canonical_truth: Mapping[str, object],
) -> ReconstructionScore:
    expected = _canonical_truth(canonical_truth)
    try:
        parsed = parse_reconstruction(content)
    except SemanticReconstructionBindingError:
        return ReconstructionScore(
            parse_valid=False,
            full_payload_exact=False,
            core_rule_exact=False,
            provenance_exact=False,
        )

    core_fields = ("operation", "permutation", "offsets", "modulus")
    core_rule_exact = all(parsed[key] == expected[key] for key in core_fields)
    provenance_exact = (
        parsed["provenance_handles"] == expected["provenance_handles"]
    )
    return ReconstructionScore(
        parse_valid=True,
        full_payload_exact=core_rule_exact and provenance_exact,
        core_rule_exact=core_rule_exact,
        provenance_exact=provenance_exact,
    )


@dataclass(frozen=True, slots=True)
class ReconstructionCost:
    input_tokens: int | None
    output_tokens: int | None
    model_calls: int
    wall_clock_seconds: float | None
    representation_bytes: int
    representation_tokens: int | None

    def validate(self) -> None:
        if self.model_calls != 1:
            raise SemanticReconstructionBindingError(
                "each arm/family cell must spend exactly one model call"
            )
        for label, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
            ("representation_tokens", self.representation_tokens),
        ):
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise SemanticReconstructionBindingError(
                    f"{label} must be a non-negative integer or null"
                )
        if (
            isinstance(self.representation_bytes, bool)
            or not isinstance(self.representation_bytes, int)
            or self.representation_bytes < 0
        ):
            raise SemanticReconstructionBindingError(
                "representation_bytes must be non-negative"
            )
        if self.wall_clock_seconds is not None and (
            isinstance(self.wall_clock_seconds, bool)
            or not isinstance(self.wall_clock_seconds, (int, float))
            or not math.isfinite(float(self.wall_clock_seconds))
            or self.wall_clock_seconds < 0
        ):
            raise SemanticReconstructionBindingError(
                "wall_clock_seconds must be finite, non-negative, or null"
            )


@dataclass(frozen=True, slots=True)
class PairedTable:
    both_correct: int
    p4_only: int
    p6_only: int
    both_wrong: int

    @property
    def discordant(self) -> int:
        return self.p4_only + self.p6_only


def paired_table(outcomes: Sequence[tuple[bool, bool]]) -> PairedTable:
    if len(outcomes) != FAMILY_COUNT:
        raise SemanticReconstructionBindingError(
            "paired outcome vector must contain exactly 16 families"
        )
    counts = {
        "both_correct": 0,
        "p4_only": 0,
        "p6_only": 0,
        "both_wrong": 0,
    }
    for p4_correct, p6_correct in outcomes:
        if not isinstance(p4_correct, bool) or not isinstance(p6_correct, bool):
            raise SemanticReconstructionBindingError(
                "paired outcomes must be booleans"
            )
        if p4_correct and p6_correct:
            counts["both_correct"] += 1
        elif p4_correct:
            counts["p4_only"] += 1
        elif p6_correct:
            counts["p6_only"] += 1
        else:
            counts["both_wrong"] += 1
    return PairedTable(**counts)


def _validate_paired_table(table: PairedTable) -> None:
    values = (
        table.both_correct,
        table.p4_only,
        table.p6_only,
        table.both_wrong,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in values
    ):
        raise SemanticReconstructionBindingError(
            "paired table cells must be non-negative integers"
        )
    if sum(values) != FAMILY_COUNT:
        raise SemanticReconstructionBindingError(
            "paired table must account for exactly 16 families"
        )


def paired_accuracy_difference(table: PairedTable) -> float:
    _validate_paired_table(table)
    return (table.p4_only - table.p6_only) / FAMILY_COUNT


def exact_two_sided_sign_p(table: PairedTable) -> float:
    _validate_paired_table(table)
    discordant = table.discordant
    if discordant == 0:
        return 1.0
    smaller = min(table.p4_only, table.p6_only)
    lower_tail = sum(
        math.comb(discordant, index) for index in range(smaller + 1)
    ) / (2**discordant)
    return min(1.0, 2.0 * lower_tail)


@dataclass(frozen=True, slots=True)
class ReconstructionVerdict:
    classification: str
    statistical_status: str
    p_value: float | None
    architecture_consequence: str = ARCHITECTURE_CONSEQUENCE


def classify_result(
    table: PairedTable | None,
    *,
    pre_execution_valid: bool = True,
    protocol_failure_after_spend: bool = False,
) -> ReconstructionVerdict:
    if not pre_execution_valid:
        return ReconstructionVerdict(
            classification="INVALID_BEFORE_PHYSICAL_EXECUTION",
            statistical_status="INVALID",
            p_value=None,
        )
    if protocol_failure_after_spend:
        return ReconstructionVerdict(
            classification="PROTOCOL_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND",
            statistical_status="UNDERDETERMINED",
            p_value=None,
        )
    if table is None:
        raise SemanticReconstructionBindingError(
            "paired table is required after valid execution"
        )

    p_value = exact_two_sided_sign_p(table)
    if p_value < ALPHA:
        return ReconstructionVerdict(
            classification=(
                "CONSUMER_ACCESSIBILITY_DIFFERENCE_DETECTED_WITHIN_DECLARED_SCOPE"
            ),
            statistical_status="SIGNIFICANT_PAIRED_EXACT_TEST",
            p_value=p_value,
        )
    return ReconstructionVerdict(
        classification="NO_ACCESSIBILITY_GAP_DETECTED_AT_THIS_RESOLUTION",
        statistical_status="UNDERDETERMINED",
        p_value=p_value,
    )


def validate_repository_binding() -> None:
    validate_seed_admission()
    if (PREREGISTRATION_ISSUE, SCIENTIFIC_PARENT_ISSUE) != (2709, 2211):
        raise SemanticReconstructionBindingError("issue lineage drifted")
    if ARMS != (
        "P4_MEMORY_PLUS_STRUCTURE",
        "P6_GENERIC_EQUAL_INFORMATION",
    ):
        raise SemanticReconstructionBindingError("arm contract drifted")
    if FAMILY_COUNT != 16 or SEMANTIC_COMPLETIONS != 32:
        raise SemanticReconstructionBindingError("family/call budget drifted")
    if SCORED_FIELDS != (
        "operation",
        "permutation",
        "offsets",
        "modulus",
        "provenance_handles",
    ):
        raise SemanticReconstructionBindingError("scored fields drifted")
    if (
        CONTEXT_LIMIT,
        MAX_OUTPUT_TOKENS,
        TEMPERATURE,
        REASONING,
        REQUEST_SEED,
        PARALLEL_SEMANTIC_SLOTS,
    ) != (8192, 256, 0.0, "none", None, 1):
        raise SemanticReconstructionBindingError("resource envelope drifted")
    if ALPHA != 0.05:
        raise SemanticReconstructionBindingError("alpha drifted")
    if any(FORBIDDEN_RESCUE_COUNTS.values()):
        raise SemanticReconstructionBindingError(
            "forbidden rescue budget is non-zero"
        )
    if PHYSICAL_EXECUTION_AUTHORIZED:
        raise SemanticReconstructionBindingError(
            "#2709 repository binding must not authorize physical execution"
        )
    if ARCHITECTURE_CONSEQUENCE != "NONE":
        raise SemanticReconstructionBindingError(
            "architecture consequence drifted"
        )
    if (
        S3_R5_SELECTED_DIFFICULTY,
        S3_R5_ACTIVE_COORDINATES,
        S3_VECTOR_WIDTH,
        S3_MODULUS,
        S3_SOURCE_EXAMPLES,
        S3_TARGET_STEPS,
        S3_SHIFT_INDEX,
    ) != ("K3_THREE_ACTIVE", 3, 4, 10, 4, 4, 2):
        raise SemanticReconstructionBindingError(
            "inherited K3 geometry drifted"
        )
    if len(semantic_call_plan()) != SEMANTIC_COMPLETIONS:
        raise SemanticReconstructionBindingError("semantic call plan drifted")
