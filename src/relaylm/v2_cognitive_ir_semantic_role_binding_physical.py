from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import time
from typing import Protocol

from relaylm.v2_cognitive_ir_semantic_reconstruction import ReconstructionCost
from relaylm.v2_cognitive_ir_semantic_reconstruction_physical import (
    FrozenConsumerIdentity,
)
from relaylm.v2_cognitive_ir_semantic_reconstruction_strict_physical import (
    generate_synthetic_canonical_payload as _legacy_generate_canonical_payload,
)
from relaylm.v2_cognitive_ir_semantic_role_binding import (
    ARCHITECTURE_CONSEQUENCE,
    CONTEXT_LIMIT,
    FAMILY_COUNT,
    FORBIDDEN_RESCUE_COUNTS,
    INPUT_TOKEN_REQUESTS,
    MAX_OUTPUT_TOKENS,
    OPAQUE_SURFACE,
    PARALLEL_SEMANTIC_SLOTS,
    PHYSICAL_EXECUTION_AUTHORIZED,
    REASONING,
    REQUEST_SEED,
    ROLE_EXPLICIT_SURFACE,
    SEMANTIC_COMPLETIONS,
    STREAM,
    SURFACES,
    TEMPERATURE,
    TYPED_SURFACE,
    ConfirmatoryContrast,
    PairedTable,
    RoleBindingMechanismControl,
    RoleBindingScore,
    RoleBindingVerdict,
    build_reconstruction_messages,
    classify_result,
    confirmatory_analysis,
    measurement_admitted,
    paired_table,
    prepare_synthetic_mechanism_control,
    preregistered_seeds,
    response_format,
    score_reconstruction,
    semantic_call_plan,
    validate_repository_binding,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion


PHYSICAL_ADAPTER_ISSUE = 2834
INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL = 2
SCIENTIFIC_INPUT_TOKEN_REQUESTS = (
    SEMANTIC_COMPLETIONS * INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL
)
CLAIM = "SEMANTIC_ROLE_BINDING_ACCESSIBILITY_PROBE"
_CONTROL_SENTINEL_SEED = 91_2834_000_000_001


class SemanticRoleBindingPhysicalError(ValueError):
    """The #2834 E4-RB1 physical adapter cannot proceed truthfully."""


def generate_synthetic_canonical_payload(seed: int) -> dict[str, object]:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise SemanticRoleBindingPhysicalError(
            "synthetic seed must be a non-negative integer"
        )
    if seed in set(preregistered_seeds()):
        raise SemanticRoleBindingPhysicalError(
            "synthetic helper must not materialize a preregistered E4-RB1 seed"
        )
    return _legacy_generate_canonical_payload(seed)


def generate_scientific_canonical_payload(
    *,
    index: int,
    seed: int,
    frozen_identity: FrozenConsumerIdentity,
) -> dict[str, object]:
    if not isinstance(frozen_identity, FrozenConsumerIdentity):
        raise SemanticRoleBindingPhysicalError(
            "scientific E4-RB1 material requires FrozenConsumerIdentity"
        )
    frozen_identity.validate()
    seeds = preregistered_seeds()
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 0 <= index < FAMILY_COUNT
    ):
        raise SemanticRoleBindingPhysicalError(
            "scientific E4-RB1 family index must be 0..23"
        )
    if isinstance(seed, bool) or not isinstance(seed, int) or seed != seeds[index]:
        raise SemanticRoleBindingPhysicalError(
            "scientific E4-RB1 seed does not match preregistered family index"
        )
    return _legacy_generate_canonical_payload(seed)


def prepare_physical_mechanism_control(
    canonical_payload: Mapping[str, object],
) -> RoleBindingMechanismControl:
    """Apply the #2831 T/R/O transforms without exposing an official seed.

    #2831 intentionally exposes a synthetic-only transform helper whose seed is
    used solely as a material-boundary guard.  The physical layer has already
    admitted/frozen the official family before this function is reached, so a
    fixed non-preregistered sentinel reuses the exact authoritative transform
    while never weakening the scientific seed guard.
    """
    if _CONTROL_SENTINEL_SEED in set(preregistered_seeds()):
        raise SemanticRoleBindingPhysicalError(
            "physical transform sentinel collides with E4-RB1 preregistration"
        )
    return prepare_synthetic_mechanism_control(
        _CONTROL_SENTINEL_SEED,
        canonical_payload,
    )


def physical_call_plan() -> tuple[str, ...]:
    plan = tuple(
        f"semantic-role-binding:{index}:{seed}:{surface}"
        for index, seed, surface in semantic_call_plan()
    )
    if len(plan) != SEMANTIC_COMPLETIONS or len(set(plan)) != SEMANTIC_COMPLETIONS:
        raise SemanticRoleBindingPhysicalError(
            "E4-RB1 physical semantic call plan drifted"
        )
    return plan


class SemanticRoleBindingClient(Protocol):
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
class RoleBindingCell:
    family_index: int
    family_seed: int
    surface: str
    semantic_digest: str
    canonical_truth: Mapping[str, object]
    serialized_representation: str
    raw_completion: str
    score: RoleBindingScore
    cost: ReconstructionCost
    response_id: str | None
    finish_reason: str


@dataclass(frozen=True, slots=True)
class SemanticRoleBindingCampaignResult:
    classification: str
    statistical_status: str
    citable_for_accessibility_claim: bool
    architecture_consequence: str
    cells: tuple[RoleBindingCell, ...]
    confirmatory: Mapping[str, ConfirmatoryContrast] | None
    descriptive_typed_vs_opaque: PairedTable | None
    semantic_equal_families: int
    wire_shape_valid: int
    semantic_domain_valid: int
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
    verdict: RoleBindingVerdict,
    cells: list[RoleBindingCell],
    confirmatory: Mapping[str, ConfirmatoryContrast] | None,
    descriptive: PairedTable | None,
    semantic_equal_families: int,
    client: SemanticRoleBindingClient,
    completed: bool,
    admitted: bool,
    failure: str | None,
) -> SemanticRoleBindingCampaignResult:
    return SemanticRoleBindingCampaignResult(
        classification=verdict.classification,
        statistical_status=verdict.statistical_status,
        citable_for_accessibility_claim=verdict.citable_for_accessibility_claim,
        architecture_consequence=verdict.architecture_consequence,
        cells=tuple(cells),
        confirmatory=confirmatory,
        descriptive_typed_vs_opaque=descriptive,
        semantic_equal_families=semantic_equal_families,
        wire_shape_valid=sum(cell.score.wire_shape_valid for cell in cells),
        semantic_domain_valid=sum(
            cell.score.semantic_domain_valid for cell in cells
        ),
        semantic_calls=int(client.provider_attempts),
        provider_completions=int(client.provider_completions),
        input_token_requests=int(client.input_count_attempts),
        input_token_completions=int(client.input_count_completions),
        completed=completed,
        measurement_admitted=admitted,
        failure=failure,
    )


def run_semantic_role_binding_campaign(
    client: SemanticRoleBindingClient,
    *,
    frozen_identity: FrozenConsumerIdentity,
    family_factory: FamilyFactory | None = None,
) -> SemanticRoleBindingCampaignResult:
    validate_physical_adapter_binding()
    frozen_identity.validate()
    factory = family_factory or _official_family_factory
    cells: list[RoleBindingCell] = []
    h1_outcomes: list[tuple[bool, bool]] = []
    h2_outcomes: list[tuple[bool, bool]] = []
    typed_vs_opaque: list[tuple[bool, bool]] = []
    semantic_equal_families = 0

    for index, seed in enumerate(preregistered_seeds()):
        canonical = factory(index, seed, frozen_identity)
        control = prepare_physical_mechanism_control(canonical)
        if set(control.serialized_by_surface) != set(SURFACES):
            raise SemanticRoleBindingPhysicalError(
                "T/R/O mechanism-control surface set drifted"
            )
        semantic_equal_families += 1
        outcomes: dict[str, bool] = {}

        for surface in SURFACES:
            question_id = f"semantic-role-binding:{index}:{seed}:{surface}"
            serialized = control.serialized_by_surface[surface]
            started = time.monotonic()
            try:
                completion = client.complete_named(
                    question_id,
                    build_reconstruction_messages(serialized),
                    output_kind="semantic_role_payload",
                )
            except Exception as exc:
                provider_attempts = int(client.provider_attempts)
                input_count_attempts = int(client.input_count_attempts)
                completed_input_attempts = (
                    INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL * len(cells)
                )
                if (
                    provider_attempts <= len(cells)
                    and input_count_attempts <= completed_input_attempts
                ):
                    raise
                verdict = classify_result(
                    None,
                    protocol_failure_after_spend=True,
                )
                return _campaign_result(
                    verdict=verdict,
                    cells=cells,
                    confirmatory=None,
                    descriptive=None,
                    semantic_equal_families=semantic_equal_families,
                    client=client,
                    completed=False,
                    admitted=False,
                    failure=f"{type(exc).__name__}: {exc}",
                )

            elapsed = time.monotonic() - started
            score = score_reconstruction(
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
                RoleBindingCell(
                    family_index=index,
                    family_seed=seed,
                    surface=surface,
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
            outcomes[surface] = score.full_payload_exact

        if set(outcomes) != set(SURFACES):
            raise AssertionError("E4-RB1 surface outcome ledger drifted")
        h1_outcomes.append(
            (outcomes[ROLE_EXPLICIT_SURFACE], outcomes[OPAQUE_SURFACE])
        )
        h2_outcomes.append(
            (outcomes[TYPED_SURFACE], outcomes[ROLE_EXPLICIT_SURFACE])
        )
        typed_vs_opaque.append(
            (outcomes[TYPED_SURFACE], outcomes[OPAQUE_SURFACE])
        )

    client.require_complete_plan()
    if len(cells) != SEMANTIC_COMPLETIONS:
        raise SemanticRoleBindingPhysicalError(
            "campaign did not complete exactly 72 semantic cells"
        )

    wire_shape_valid = sum(cell.score.wire_shape_valid for cell in cells)
    admitted = measurement_admitted(
        semantic_equal_families=semantic_equal_families,
        provider_attempts=client.provider_attempts,
        provider_completions=client.provider_completions,
        wire_shape_valid=wire_shape_valid,
        input_count_attempts=client.input_count_attempts,
        input_count_completions=client.input_count_completions,
        rescue_counts=FORBIDDEN_RESCUE_COUNTS,
        truncation_failures=0,
        identity_checks_passed=True,
    )

    if not admitted:
        verdict = classify_result(None, measurement_passed=False)
        return _campaign_result(
            verdict=verdict,
            cells=cells,
            confirmatory=None,
            descriptive=None,
            semantic_equal_families=semantic_equal_families,
            client=client,
            completed=True,
            admitted=False,
            failure="measurement admission failed",
        )

    contrasts = confirmatory_analysis(
        h1_role_explicit_vs_opaque=h1_outcomes,
        h2_typed_vs_role_explicit=h2_outcomes,
    )
    descriptive = paired_table(typed_vs_opaque)
    verdict = classify_result(contrasts, measurement_passed=True)
    return _campaign_result(
        verdict=verdict,
        cells=cells,
        confirmatory=contrasts,
        descriptive=descriptive,
        semantic_equal_families=semantic_equal_families,
        client=client,
        completed=True,
        admitted=True,
        failure=None,
    )


def validate_physical_adapter_binding() -> None:
    validate_repository_binding()
    if PHYSICAL_ADAPTER_ISSUE != 2834:
        raise SemanticRoleBindingPhysicalError(
            "E4-RB1 physical adapter owner drifted"
        )
    if FAMILY_COUNT != 24 or SEMANTIC_COMPLETIONS != 72:
        raise SemanticRoleBindingPhysicalError(
            "E4-RB1 24-family/72-call contract drifted"
        )
    if INPUT_TOKEN_REQUESTS != 144 or SCIENTIFIC_INPUT_TOKEN_REQUESTS != 144:
        raise SemanticRoleBindingPhysicalError(
            "E4-RB1 144-request input-token contract drifted"
        )
    if INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL != 2:
        raise SemanticRoleBindingPhysicalError(
            "E4-RB1 per-call input-token accounting drifted"
        )
    if CONTEXT_LIMIT != 8192 or MAX_OUTPUT_TOKENS != 256:
        raise SemanticRoleBindingPhysicalError(
            "E4-RB1 context/output envelope drifted"
        )
    if TEMPERATURE != 0.0 or REASONING != "none" or REQUEST_SEED is not None:
        raise SemanticRoleBindingPhysicalError(
            "E4-RB1 decoding envelope drifted"
        )
    if STREAM is not False or PARALLEL_SEMANTIC_SLOTS != 1:
        raise SemanticRoleBindingPhysicalError(
            "E4-RB1 stream/parallelism envelope drifted"
        )
    if PHYSICAL_EXECUTION_AUTHORIZED is not False:
        raise SemanticRoleBindingPhysicalError(
            "physical adapter must not authorize THIS RUN"
        )
    if ARCHITECTURE_CONSEQUENCE != "NONE":
        raise SemanticRoleBindingPhysicalError(
            "E4-RB1 architecture consequence drifted"
        )
    candidate = response_format()
    if candidate.get("type") != "json_schema":
        raise SemanticRoleBindingPhysicalError(
            "E4-RB1 native structured-output transport drifted"
        )
    json_schema = candidate.get("json_schema")
    if not isinstance(json_schema, Mapping) or json_schema.get("strict") is not True:
        raise SemanticRoleBindingPhysicalError(
            "E4-RB1 strict JSON-schema transport drifted"
        )
    expected = tuple(
        f"semantic-role-binding:{index}:{seed}:{surface}"
        for index, seed, surface in semantic_call_plan()
    )
    if physical_call_plan() != expected:
        raise SemanticRoleBindingPhysicalError(
            "E4-RB1 physical call plan drifted"
        )
