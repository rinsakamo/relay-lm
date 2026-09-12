from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import math

from relaylm.v2_cognitive_ir_semantic_reconstruction import (
    ARMS,
    build_reconstruction_messages as _build_reconstruction_messages,
    historical_family_seeds as _historical_family_seeds,
    prepare_mechanism_control as _prepare_mechanism_control,
    preregistered_seeds as _historical_reconstruction_seeds,
    score_reconstruction as _score_reconstruction,
)
from relaylm.v2_cognitive_ir_strict_output_interface_qualification import (
    preregistered_case_seeds as _ifq1_seeds,
    response_format as _ifq1_response_format,
)


PREREGISTRATION_ISSUE = 2768
REPOSITORY_BINDING_ISSUE = 2769
SCIENTIFIC_PARENT_ISSUE = 2211
PREREGISTRATION_LABEL = "relaylm2-cognitive-ir-semantic-reconstruction-strict-v1"

FAMILY_COUNT = 24
SEMANTIC_COMPLETIONS = 48
INPUT_TOKEN_REQUESTS = 96
MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS = 2

CONTEXT_LIMIT = 8192
MAX_OUTPUT_TOKENS = 256
TEMPERATURE = 0.0
REASONING = "none"
REQUEST_SEED = None
PARALLEL_SEMANTIC_SLOTS = 1
STREAM = False
ALPHA = 0.05

PRIMARY_ENDPOINT = "full_payload_exact"
DIAGNOSTIC_ENDPOINTS = ("core_rule_exact", "provenance_exact")
PHYSICAL_EXECUTION_AUTHORIZED = False
ARCHITECTURE_CONSEQUENCE = "NONE"

FORBIDDEN_RESCUE_COUNTS: Mapping[str, int] = {
    "semantic_retry": 0,
    "replay": 0,
    "reseed": 0,
    "fallback": 0,
    "hidden_repair": 0,
    "judge": 0,
}


class StrictSemanticReconstructionBindingError(ValueError):
    """The #2768 E4-SR2 preregistration was violated."""


def derive_family_seed(index: int) -> int:
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 0 <= index < FAMILY_COUNT
    ):
        raise StrictSemanticReconstructionBindingError("family index must be 0..23")
    raw = hashlib.sha256(
        f"{PREREGISTRATION_LABEL}|family|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(raw[:8], "big")


def preregistered_seeds() -> tuple[int, ...]:
    return tuple(derive_family_seed(index) for index in range(FAMILY_COUNT))


def historical_family_seeds() -> frozenset[int]:
    return frozenset(
        {
            *_historical_family_seeds(),
            *_historical_reconstruction_seeds(),
            *_ifq1_seeds(),
        }
    )


def validate_seed_admission() -> None:
    seeds = preregistered_seeds()
    if len(seeds) != FAMILY_COUNT or len(set(seeds)) != FAMILY_COUNT:
        raise StrictSemanticReconstructionBindingError(
            "E4-SR2 seeds are not exactly 24 unique values"
        )
    overlap = sorted(set(seeds) & historical_family_seeds())
    if overlap:
        raise StrictSemanticReconstructionBindingError(
            f"E4-SR2 seeds overlap historical #2211 evidence: {overlap}"
        )


def response_format() -> dict[str, object]:
    return _ifq1_response_format()


def build_reconstruction_messages(
    serialized_representation: str,
) -> tuple[dict[str, str], ...]:
    return _build_reconstruction_messages(serialized_representation)


def prepare_synthetic_mechanism_control(
    seed: int,
    canonical_payload: Mapping[str, object],
):
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise StrictSemanticReconstructionBindingError(
            "synthetic seed must be a non-negative integer"
        )
    if seed in set(preregistered_seeds()):
        raise StrictSemanticReconstructionBindingError(
            "synthetic helper cannot materialize a preregistered E4-SR2 seed"
        )
    return _prepare_mechanism_control(canonical_payload)


@dataclass(frozen=True, slots=True)
class StrictReconstructionScore:
    strict_parse_valid: bool
    full_payload_exact: bool
    core_rule_exact: bool
    provenance_exact: bool


def score_strict_reconstruction(
    content: str,
    canonical_truth: Mapping[str, object],
) -> StrictReconstructionScore:
    score = _score_reconstruction(content, canonical_truth)
    return StrictReconstructionScore(
        strict_parse_valid=score.parse_valid,
        full_payload_exact=score.full_payload_exact,
        core_rule_exact=score.core_rule_exact,
        provenance_exact=score.provenance_exact,
    )


def semantic_call_plan() -> tuple[tuple[int, int, str], ...]:
    validate_seed_admission()
    plan = tuple(
        (index, seed, arm)
        for index, seed in enumerate(preregistered_seeds())
        for arm in ARMS
    )
    if len(plan) != SEMANTIC_COMPLETIONS:
        raise StrictSemanticReconstructionBindingError("semantic call ledger drifted")
    return plan


@dataclass(frozen=True, slots=True)
class PairedTable:
    both_correct: int
    p4_only: int
    p6_only: int
    both_wrong: int

    @property
    def discordant(self) -> int:
        return self.p4_only + self.p6_only


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
        raise StrictSemanticReconstructionBindingError(
            "paired table counts must be non-negative integers"
        )
    if sum(values) != FAMILY_COUNT:
        raise StrictSemanticReconstructionBindingError(
            "paired table must contain exactly 24 families"
        )


def paired_table(outcomes: Sequence[tuple[bool, bool]]) -> PairedTable:
    if len(outcomes) != FAMILY_COUNT:
        raise StrictSemanticReconstructionBindingError(
            "paired outcome vector must contain exactly 24 families"
        )
    counts = {
        "both_correct": 0,
        "p4_only": 0,
        "p6_only": 0,
        "both_wrong": 0,
    }
    for p4_correct, p6_correct in outcomes:
        if not isinstance(p4_correct, bool) or not isinstance(p6_correct, bool):
            raise StrictSemanticReconstructionBindingError(
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


def paired_accuracy_difference(table: PairedTable) -> float:
    _validate_paired_table(table)
    return (table.p4_only - table.p6_only) / FAMILY_COUNT


def exact_two_sided_sign_p(table: PairedTable) -> float:
    _validate_paired_table(table)
    discordant = table.discordant
    if discordant == 0:
        return 1.0
    smaller = min(table.p4_only, table.p6_only)
    tail = sum(math.comb(discordant, k) for k in range(smaller + 1))
    return min(1.0, 2.0 * tail / (2**discordant))


def _validate_rescue_counts(rescue_counts: Mapping[str, int]) -> bool:
    return dict(rescue_counts) == dict(FORBIDDEN_RESCUE_COUNTS)


def measurement_admitted(
    *,
    semantic_equal_pairs: int,
    provider_attempts: int,
    provider_completions: int,
    strict_parse_valid: int,
    input_count_attempts: int,
    input_count_completions: int,
    rescue_counts: Mapping[str, int],
    truncation_failures: int,
    identity_checks_passed: bool,
) -> bool:
    values = (
        semantic_equal_pairs,
        provider_attempts,
        provider_completions,
        strict_parse_valid,
        input_count_attempts,
        input_count_completions,
        truncation_failures,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in values
    ):
        raise StrictSemanticReconstructionBindingError(
            "measurement counts must be non-negative integers"
        )
    return (
        semantic_equal_pairs == FAMILY_COUNT
        and provider_attempts == SEMANTIC_COMPLETIONS
        and provider_completions == SEMANTIC_COMPLETIONS
        and strict_parse_valid == SEMANTIC_COMPLETIONS
        and input_count_attempts == INPUT_TOKEN_REQUESTS
        and input_count_completions == INPUT_TOKEN_REQUESTS
        and _validate_rescue_counts(rescue_counts)
        and truncation_failures == 0
        and identity_checks_passed
    )


@dataclass(frozen=True, slots=True)
class ReconstructionVerdict:
    classification: str
    statistical_status: str
    p_value: float | None
    citable_for_accessibility_claim: bool
    architecture_consequence: str = ARCHITECTURE_CONSEQUENCE


def classify_result(
    table: PairedTable | None,
    *,
    pre_execution_valid: bool = True,
    protocol_failure_after_spend: bool = False,
    measurement_passed: bool = True,
) -> ReconstructionVerdict:
    if not pre_execution_valid:
        return ReconstructionVerdict(
            classification="INVALID_BEFORE_PHYSICAL_EXECUTION",
            statistical_status="INVALID",
            p_value=None,
            citable_for_accessibility_claim=False,
        )
    if protocol_failure_after_spend or not measurement_passed:
        return ReconstructionVerdict(
            classification="MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND",
            statistical_status="UNDERDETERMINED",
            p_value=None,
            citable_for_accessibility_claim=False,
        )
    if table is None:
        raise StrictSemanticReconstructionBindingError(
            "valid completed result requires one paired table"
        )

    p_value = exact_two_sided_sign_p(table)
    if p_value < ALPHA:
        return ReconstructionVerdict(
            classification=(
                "CONSUMER_ACCESSIBILITY_DIFFERENCE_DETECTED_WITHIN_DECLARED_SCOPE"
            ),
            statistical_status="SIGNIFICANT_PAIRED_EXACT_TEST",
            p_value=p_value,
            citable_for_accessibility_claim=True,
        )
    return ReconstructionVerdict(
        classification="NO_ACCESSIBILITY_GAP_DETECTED_AT_THIS_RESOLUTION",
        statistical_status="UNDERDETERMINED",
        p_value=p_value,
        citable_for_accessibility_claim=True,
    )


def validate_repository_binding() -> None:
    validate_seed_admission()
    plan = semantic_call_plan()
    if len(plan) != SEMANTIC_COMPLETIONS:
        raise StrictSemanticReconstructionBindingError(
            "repository semantic ledger is inconsistent"
        )
    if response_format() != _ifq1_response_format():
        raise StrictSemanticReconstructionBindingError(
            "strict response format drifted from qualified IFQ1 interface"
        )
    if any(FORBIDDEN_RESCUE_COUNTS.values()):
        raise StrictSemanticReconstructionBindingError("rescue counters must be zero")
    if PHYSICAL_EXECUTION_AUTHORIZED:
        raise StrictSemanticReconstructionBindingError(
            "repository binding must not authorize physical execution"
        )
    if ARCHITECTURE_CONSEQUENCE != "NONE":
        raise StrictSemanticReconstructionBindingError(
            "repository binding cannot mutate architecture"
        )
