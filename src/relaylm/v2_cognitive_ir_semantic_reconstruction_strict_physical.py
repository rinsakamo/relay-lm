from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import time
from typing import Protocol

from relaylm.v2_cognitive_ir_semantic_reconstruction import (
    ARMS,
    ReconstructionCost,
    prepare_mechanism_control,
)
from relaylm.v2_cognitive_ir_semantic_reconstruction_physical import (
    FrozenConsumerIdentity,
    generate_synthetic_canonical_payload as _legacy_generate_canonical_payload,
)
from relaylm.v2_cognitive_ir_semantic_reconstruction_strict import (
    ARCHITECTURE_CONSEQUENCE,
    CONTEXT_LIMIT,
    FAMILY_COUNT,
    FORBIDDEN_RESCUE_COUNTS,
    INPUT_TOKEN_REQUESTS,
    MAX_OUTPUT_TOKENS,
    PARALLEL_SEMANTIC_SLOTS,
    PHYSICAL_EXECUTION_AUTHORIZED,
    REASONING,
    REQUEST_SEED,
    SEMANTIC_COMPLETIONS,
    STREAM,
    TEMPERATURE,
    PairedTable,
    ReconstructionVerdict,
    StrictReconstructionScore,
    build_reconstruction_messages,
    classify_result,
    measurement_admitted,
    paired_accuracy_difference,
    paired_table,
    preregistered_seeds,
    response_format,
    score_strict_reconstruction,
    semantic_call_plan,
    validate_repository_binding,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion


PHYSICAL_ADAPTER_ISSUE = 2774
INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL = 2
SCIENTIFIC_INPUT_TOKEN_REQUESTS = (
    SEMANTIC_COMPLETIONS * INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL
)
CLAIM = "STRICT_SEMANTIC_RECONSTRUCTION_ACCESSIBILITY_PROBE"


class StrictSemanticReconstructionPhysicalBindingError(ValueError):
    """The #2774 E4-SR2 physical adapter cannot proceed truthfully."""


def generate_synthetic_canonical_payload(seed: int) -> dict[str, object]:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "synthetic seed must be a non-negative integer"
        )
    if seed in set(preregistered_seeds()):
        raise StrictSemanticReconstructionPhysicalBindingError(
            "synthetic helper must not materialize a preregistered E4-SR2 seed"
        )
    return _legacy_generate_canonical_payload(seed)


def generate_scientific_canonical_payload(
    *,
    index: int,
    seed: int,
    frozen_identity: FrozenConsumerIdentity,
) -> dict[str, object]:
    if not isinstance(frozen_identity, FrozenConsumerIdentity):
        raise StrictSemanticReconstructionPhysicalBindingError(
            "scientific E4-SR2 material requires FrozenConsumerIdentity"
        )
    frozen_identity.validate()
    seeds = preregistered_seeds()
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 0 <= index < FAMILY_COUNT
    ):
        raise StrictSemanticReconstructionPhysicalBindingError(
            "scientific E4-SR2 family index must be 0..23"
        )
    if isinstance(seed, bool) or not isinstance(seed, int) or seed != seeds[index]:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "scientific E4-SR2 seed does not match preregistered family index"
        )
    return _legacy_generate_canonical_payload(seed)


def physical_call_plan() -> tuple[str, ...]:
    plan = tuple(
        f"semantic-reconstruction-strict:{index}:{seed}:{arm}"
        for index, seed, arm in semantic_call_plan()
    )
    if len(plan) != SEMANTIC_COMPLETIONS or len(set(plan)) != SEMANTIC_COMPLETIONS:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "E4-SR2 physical semantic call plan drifted"
        )
    return plan


class StrictSemanticReconstructionClient(Protocol):
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

    def require_complete_plan(self) -> None: ...


@dataclass(frozen=True, slots=True)
class StrictReconstructionCell:
    family_index: int
    family_seed: int
    arm: str
    semantic_digest: str
    canonical_truth: Mapping[str, object]
    serialized_representation: str
    raw_completion: str
    score: StrictReconstructionScore
    cost: ReconstructionCost
    response_id: str | None
    finish_reason: str


@dataclass(frozen=True, slots=True)
class StrictSemanticReconstructionCampaignResult:
    classification: str
    statistical_status: str
    p_value: float | None
    citable_for_accessibility_claim: bool
    architecture_consequence: str
    cells: tuple[StrictReconstructionCell, ...]
    paired: Mapping[str, int] | None
    paired_accuracy_difference: float | None
    semantic_equal_pairs: int
    strict_parse_valid: int
    semantic_calls: int
    provider_completions: int
    input_token_requests: int
    input_token_completions: int
    completed: bool
    measurement_admitted: bool
    failure: str | None


FamilyFactory = Callable[
    [int, int, FrozenConsumerIdentity],
    Mapping[str, object],
]


def _official_family_factory(
    index: int,
    seed: int,
    identity: FrozenConsumerIdentity,
) -> Mapping[str, object]:
    return generate_scientific_canonical_payload(
        index=index,
        seed=seed,
        frozen_identity=identity,
    )


def _campaign_result(
    *,
    verdict: ReconstructionVerdict,
    cells: list[StrictReconstructionCell],
    table: PairedTable | None,
    semantic_equal_pairs: int,
    client: StrictSemanticReconstructionClient,
    completed: bool,
    admitted: bool,
    failure: str | None,
) -> StrictSemanticReconstructionCampaignResult:
    strict_parse_valid = sum(cell.score.strict_parse_valid for cell in cells)
    return StrictSemanticReconstructionCampaignResult(
        classification=verdict.classification,
        statistical_status=verdict.statistical_status,
        p_value=verdict.p_value,
        citable_for_accessibility_claim=verdict.citable_for_accessibility_claim,
        architecture_consequence=verdict.architecture_consequence,
        cells=tuple(cells),
        paired=(
            {
                "both_correct": table.both_correct,
                "p4_only": table.p4_only,
                "p6_only": table.p6_only,
                "both_wrong": table.both_wrong,
            }
            if table is not None
            else None
        ),
        paired_accuracy_difference=(
            paired_accuracy_difference(table) if table is not None else None
        ),
        semantic_equal_pairs=semantic_equal_pairs,
        strict_parse_valid=strict_parse_valid,
        semantic_calls=int(client.provider_attempts),
        provider_completions=int(client.provider_completions),
        input_token_requests=int(client.input_count_attempts),
        input_token_completions=int(client.input_count_completions),
        completed=completed,
        measurement_admitted=admitted,
        failure=failure,
    )


def run_strict_semantic_reconstruction_campaign(
    client: StrictSemanticReconstructionClient,
    *,
    frozen_identity: FrozenConsumerIdentity,
    family_factory: FamilyFactory | None = None,
) -> StrictSemanticReconstructionCampaignResult:
    validate_physical_adapter_binding()
    frozen_identity.validate()
    factory = family_factory or _official_family_factory
    cells: list[StrictReconstructionCell] = []
    paired_outcomes: list[tuple[bool, bool]] = []
    semantic_equal_pairs = 0

    for index, seed in enumerate(preregistered_seeds()):
        canonical = factory(index, seed, frozen_identity)
        control = prepare_mechanism_control(canonical)
        if set(control.serialized_by_arm) != set(ARMS):
            raise StrictSemanticReconstructionPhysicalBindingError(
                "P4/P6 mechanism-control arm set drifted"
            )
        semantic_equal_pairs += 1
        arm_outcomes: list[bool] = []

        for arm in ARMS:
            question_id = f"semantic-reconstruction-strict:{index}:{seed}:{arm}"
            serialized = control.serialized_by_arm[arm]
            started = time.monotonic()
            try:
                completion = client.complete_named(
                    question_id,
                    build_reconstruction_messages(serialized),
                    output_kind="strict_semantic_payload",
                )
            except Exception as exc:
                provider_attempts = int(client.provider_attempts)
                input_count_attempts = int(client.input_count_attempts)
                completed_input_count_attempts = (
                    INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL * len(cells)
                )
                if (
                    provider_attempts <= len(cells)
                    and input_count_attempts <= completed_input_count_attempts
                ):
                    raise
                verdict = classify_result(
                    None,
                    protocol_failure_after_spend=True,
                )
                return _campaign_result(
                    verdict=verdict,
                    cells=cells,
                    table=None,
                    semantic_equal_pairs=semantic_equal_pairs,
                    client=client,
                    completed=False,
                    admitted=False,
                    failure=f"{type(exc).__name__}: {exc}",
                )

            elapsed = time.monotonic() - started
            score = score_strict_reconstruction(
                completion.content,
                control.canonical_truth,
            )
            cost = ReconstructionCost(
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
                model_calls=1,
                wall_clock_seconds=elapsed,
                representation_bytes=len(serialized.encode("utf-8")),
                representation_tokens=None,
            )
            cost.validate()
            cells.append(
                StrictReconstructionCell(
                    family_index=index,
                    family_seed=seed,
                    arm=arm,
                    semantic_digest=control.semantic_digest,
                    canonical_truth=dict(control.canonical_truth),
                    serialized_representation=serialized,
                    raw_completion=completion.content,
                    score=score,
                    cost=cost,
                    response_id=completion.response_id,
                    finish_reason="stop",
                )
            )
            arm_outcomes.append(score.full_payload_exact)

        if len(arm_outcomes) != 2:
            raise AssertionError("E4-SR2 arm ledger drifted")
        paired_outcomes.append((arm_outcomes[0], arm_outcomes[1]))

    client.require_complete_plan()
    if len(cells) != SEMANTIC_COMPLETIONS:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "campaign did not complete exactly 48 semantic cells"
        )

    strict_parse_valid = sum(cell.score.strict_parse_valid for cell in cells)
    admitted = measurement_admitted(
        semantic_equal_pairs=semantic_equal_pairs,
        provider_attempts=client.provider_attempts,
        provider_completions=client.provider_completions,
        strict_parse_valid=strict_parse_valid,
        input_count_attempts=client.input_count_attempts,
        input_count_completions=client.input_count_completions,
        rescue_counts=FORBIDDEN_RESCUE_COUNTS,
        truncation_failures=0,
        identity_checks_passed=True,
    )
    table = paired_table(paired_outcomes)
    verdict = classify_result(table, measurement_passed=admitted)
    return _campaign_result(
        verdict=verdict,
        cells=cells,
        table=table if admitted else None,
        semantic_equal_pairs=semantic_equal_pairs,
        client=client,
        completed=True,
        admitted=admitted,
        failure=None if admitted else "measurement admission failed",
    )


def validate_physical_adapter_binding() -> None:
    validate_repository_binding()
    if PHYSICAL_ADAPTER_ISSUE != 2774:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "E4-SR2 physical adapter owner drifted"
        )
    if FAMILY_COUNT != 24 or SEMANTIC_COMPLETIONS != 48:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "E4-SR2 24-family/48-call contract drifted"
        )
    if INPUT_TOKEN_REQUESTS != 96 or SCIENTIFIC_INPUT_TOKEN_REQUESTS != 96:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "E4-SR2 96-request input-token contract drifted"
        )
    if INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL != 2:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "E4-SR2 per-call input-token accounting drifted"
        )
    if CONTEXT_LIMIT != 8192 or MAX_OUTPUT_TOKENS != 256:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "E4-SR2 context/output envelope drifted"
        )
    if TEMPERATURE != 0.0 or REASONING != "none" or REQUEST_SEED is not None:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "E4-SR2 decoding envelope drifted"
        )
    if STREAM is not False:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "E4-SR2 streaming envelope drifted"
        )
    if PARALLEL_SEMANTIC_SLOTS != 1:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "E4-SR2 semantic parallelism drifted"
        )
    if PHYSICAL_EXECUTION_AUTHORIZED is not False:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "physical adapter must not authorize THIS RUN"
        )
    if ARCHITECTURE_CONSEQUENCE != "NONE":
        raise StrictSemanticReconstructionPhysicalBindingError(
            "E4-SR2 architecture consequence drifted"
        )
    candidate = response_format()
    if candidate.get("type") != "json_schema":
        raise StrictSemanticReconstructionPhysicalBindingError(
            "E4-SR2 native structured-output transport drifted"
        )
    if candidate.get("json_schema", {}).get("strict") is not True:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "E4-SR2 strict JSON-schema transport drifted"
        )
    expected = tuple(
        f"semantic-reconstruction-strict:{index}:{seed}:{arm}"
        for index, seed, arm in semantic_call_plan()
    )
    if physical_call_plan() != expected:
        raise StrictSemanticReconstructionPhysicalBindingError(
            "E4-SR2 physical call plan drifted"
        )
