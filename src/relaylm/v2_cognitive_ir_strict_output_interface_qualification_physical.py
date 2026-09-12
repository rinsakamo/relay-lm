from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import time
from typing import Protocol

from relaylm.v2_cognitive_ir_semantic_reconstruction_physical import (
    FrozenConsumerIdentity,
)
from relaylm.v2_cognitive_ir_strict_output_interface_qualification import (
    ARCHITECTURE_CONSEQUENCE,
    CASE_COUNT,
    CITABLE_FOR_REPRESENTATION_CLAIM,
    FORBIDDEN_RESCUE_COUNTS,
    INPUT_TOKEN_REQUESTS,
    MAX_OUTPUT_TOKENS,
    PHYSICAL_EXECUTION_AUTHORIZED,
    REASONING,
    REQUEST_SEED,
    SEMANTIC_COMPLETIONS,
    TEMPERATURE,
    InterfaceQualificationScore,
    build_neutral_messages,
    classify_qualification,
    preregistered_case_seeds,
    response_format,
    score_completion,
    validate_reference_payload,
    validate_seed_admission,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion


PHYSICAL_ADAPTER_ISSUE = 2748
MATERIAL_SCHEMA = "relaylm2-cognitive-ir-strict-output-ifq1-material-v1"
CLAIM = "STRICT_OUTPUT_INTERFACE_QUALIFICATION"
INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL = 2


class StrictOutputInterfacePhysicalBindingError(ValueError):
    """The #2748 E4-IFQ1 physical adapter cannot proceed truthfully."""


def _material_digest(seed: int, purpose: str) -> bytes:
    return hashlib.sha256(
        f"{MATERIAL_SCHEMA}|{seed}|{purpose}".encode("utf-8")
    ).digest()


def _reference_payload_for_seed(seed: int) -> dict[str, object]:
    permutation = sorted(
        range(4),
        key=lambda coordinate: (
            _material_digest(seed, f"permutation:{coordinate}"),
            coordinate,
        ),
    )
    ranked = sorted(
        range(4),
        key=lambda coordinate: (
            _material_digest(seed, f"active-rank:{coordinate}"),
            coordinate,
        ),
    )
    active = set(ranked[:3])
    offsets = [
        1 + (_material_digest(seed, f"offset:{coordinate}")[0] % 3)
        if coordinate in active
        else 0
        for coordinate in range(4)
    ]
    provenance_handles = [
        "ifq1_"
        + hashlib.sha256(
            f"{MATERIAL_SCHEMA}|{seed}|provenance|0".encode("utf-8")
        ).hexdigest()[:24]
    ]
    return validate_reference_payload(
        {
            "operation": "affine_permutation",
            "permutation": permutation,
            "offsets": offsets,
            "modulus": 10,
            "provenance_handles": provenance_handles,
        }
    )


def generate_synthetic_reference_payload(seed: int) -> dict[str, object]:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise StrictOutputInterfacePhysicalBindingError(
            "synthetic seed must be a non-negative integer"
        )
    if seed in set(preregistered_case_seeds()):
        raise StrictOutputInterfacePhysicalBindingError(
            "synthetic helper must not materialize a preregistered IFQ1 seed"
        )
    return _reference_payload_for_seed(seed)


def generate_scientific_reference_payload(
    *,
    index: int,
    seed: int,
    frozen_identity: FrozenConsumerIdentity,
) -> dict[str, object]:
    if not isinstance(frozen_identity, FrozenConsumerIdentity):
        raise StrictOutputInterfacePhysicalBindingError(
            "scientific IFQ1 material requires FrozenConsumerIdentity"
        )
    frozen_identity.validate()
    seeds = preregistered_case_seeds()
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 0 <= index < CASE_COUNT
    ):
        raise StrictOutputInterfacePhysicalBindingError(
            "scientific IFQ1 case index must be 0..17"
        )
    if isinstance(seed, bool) or not isinstance(seed, int) or seed != seeds[index]:
        raise StrictOutputInterfacePhysicalBindingError(
            "scientific IFQ1 seed does not match preregistered case index"
        )
    return _reference_payload_for_seed(seed)


def physical_call_plan() -> tuple[str, ...]:
    plan = tuple(
        f"strict-output-interface-qualification:{index}:{seed}"
        for index, seed in enumerate(preregistered_case_seeds())
    )
    if len(plan) != SEMANTIC_COMPLETIONS or len(set(plan)) != SEMANTIC_COMPLETIONS:
        raise StrictOutputInterfacePhysicalBindingError(
            "IFQ1 physical semantic call plan drifted"
        )
    return plan


class StrictOutputInterfaceClient(Protocol):
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
class StrictOutputInterfaceCell:
    case_index: int
    case_seed: int
    visible_reference_payload: Mapping[str, object]
    raw_completion: str
    score: InterfaceQualificationScore
    input_tokens: int
    output_tokens: int
    model_calls: int
    wall_clock_seconds: float
    response_id: str | None
    finish_reason: str


@dataclass(frozen=True, slots=True)
class StrictOutputInterfaceQualificationResult:
    classification: str
    citable_for_representation_claim: bool
    architecture_consequence: str
    cells: tuple[StrictOutputInterfaceCell, ...]
    semantic_calls: int
    input_token_requests: int
    completed: bool
    failure: str | None


PayloadFactory = Callable[[int, int, FrozenConsumerIdentity], Mapping[str, object]]


def _official_payload_factory(
    index: int,
    seed: int,
    identity: FrozenConsumerIdentity,
) -> Mapping[str, object]:
    return generate_scientific_reference_payload(
        index=index,
        seed=seed,
        frozen_identity=identity,
    )


def _result(
    *,
    classification: str,
    cells: list[StrictOutputInterfaceCell],
    client: StrictOutputInterfaceClient,
    completed: bool,
    failure: str | None,
) -> StrictOutputInterfaceQualificationResult:
    return StrictOutputInterfaceQualificationResult(
        classification=classification,
        citable_for_representation_claim=CITABLE_FOR_REPRESENTATION_CLAIM,
        architecture_consequence=ARCHITECTURE_CONSEQUENCE,
        cells=tuple(cells),
        semantic_calls=int(client.provider_attempts),
        input_token_requests=int(client.input_count_attempts),
        completed=completed,
        failure=failure,
    )


def run_strict_output_interface_qualification(
    client: StrictOutputInterfaceClient,
    *,
    frozen_identity: FrozenConsumerIdentity,
    payload_factory: PayloadFactory | None = None,
) -> StrictOutputInterfaceQualificationResult:
    validate_physical_adapter_binding()
    frozen_identity.validate()
    factory = payload_factory or _official_payload_factory
    cells: list[StrictOutputInterfaceCell] = []

    for index, seed in enumerate(preregistered_case_seeds()):
        reference = validate_reference_payload(factory(index, seed, frozen_identity))
        question_id = f"strict-output-interface-qualification:{index}:{seed}"
        started = time.monotonic()
        try:
            completion = client.complete_named(
                question_id,
                build_neutral_messages(reference),
                output_kind="strict_reference_payload",
            )
        except Exception as exc:
            if client.provider_attempts <= len(cells):
                raise
            classification = classify_qualification(
                [cell.score for cell in cells],
                provider_attempts=client.provider_attempts,
                provider_completions=client.provider_completions,
                input_count_attempts=client.input_count_attempts,
                input_count_completions=client.input_count_completions,
                rescue_counts=FORBIDDEN_RESCUE_COUNTS,
                truncation_failures=0,
                identity_checks_passed=True,
            )
            return _result(
                classification=classification,
                cells=cells,
                client=client,
                completed=False,
                failure=f"{type(exc).__name__}: {exc}",
            )
        elapsed = time.monotonic() - started
        score = score_completion(completion.content, reference)
        cells.append(
            StrictOutputInterfaceCell(
                case_index=index,
                case_seed=seed,
                visible_reference_payload=dict(reference),
                raw_completion=completion.content,
                score=score,
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
                model_calls=1,
                wall_clock_seconds=elapsed,
                response_id=completion.response_id,
                finish_reason="stop",
            )
        )

    client.require_complete_plan()
    classification = classify_qualification(
        [cell.score for cell in cells],
        provider_attempts=client.provider_attempts,
        provider_completions=client.provider_completions,
        input_count_attempts=client.input_count_attempts,
        input_count_completions=client.input_count_completions,
        rescue_counts=FORBIDDEN_RESCUE_COUNTS,
        truncation_failures=0,
        identity_checks_passed=True,
    )
    return _result(
        classification=classification,
        cells=cells,
        client=client,
        completed=True,
        failure=None,
    )


def validate_physical_adapter_binding() -> None:
    validate_seed_admission()
    if PHYSICAL_ADAPTER_ISSUE != 2748:
        raise StrictOutputInterfacePhysicalBindingError(
            "IFQ1 physical adapter owner drifted"
        )
    if CASE_COUNT != 18 or SEMANTIC_COMPLETIONS != 18:
        raise StrictOutputInterfacePhysicalBindingError(
            "IFQ1 18-case semantic contract drifted"
        )
    if INPUT_TOKEN_REQUESTS != 36:
        raise StrictOutputInterfacePhysicalBindingError(
            "IFQ1 36-request input-token contract drifted"
        )
    if INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL * SEMANTIC_COMPLETIONS != 36:
        raise StrictOutputInterfacePhysicalBindingError(
            "IFQ1 input-token accounting ratio drifted"
        )
    if MAX_OUTPUT_TOKENS != 256 or TEMPERATURE != 0.0:
        raise StrictOutputInterfacePhysicalBindingError(
            "IFQ1 decoding envelope drifted"
        )
    if REASONING != "none" or REQUEST_SEED is not None:
        raise StrictOutputInterfacePhysicalBindingError(
            "IFQ1 reasoning/seed envelope drifted"
        )
    if PHYSICAL_EXECUTION_AUTHORIZED is not False:
        raise StrictOutputInterfacePhysicalBindingError(
            "repository binding must not authorize THIS RUN"
        )
    if CITABLE_FOR_REPRESENTATION_CLAIM is not False:
        raise StrictOutputInterfacePhysicalBindingError(
            "IFQ1 must remain non-citable for representation claims"
        )
    if ARCHITECTURE_CONSEQUENCE != "NONE":
        raise StrictOutputInterfacePhysicalBindingError(
            "IFQ1 architecture consequence drifted"
        )
    candidate = response_format()
    if candidate.get("type") != "json_schema":
        raise StrictOutputInterfacePhysicalBindingError(
            "IFQ1 native structured-output transport drifted"
        )
    if candidate.get("json_schema", {}).get("strict") is not True:
        raise StrictOutputInterfacePhysicalBindingError(
            "IFQ1 strict JSON-schema transport drifted"
        )
    if len(physical_call_plan()) != 18:
        raise StrictOutputInterfacePhysicalBindingError(
            "IFQ1 physical call plan must contain exactly 18 calls"
        )
