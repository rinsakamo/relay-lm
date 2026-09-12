from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json

from relaylm.v2_cognitive_ir_semantic_reconstruction import (
    historical_family_seeds as semantic_reconstruction_historical_seeds,
    preregistered_seeds as semantic_reconstruction_seeds,
)


PREREGISTRATION_ISSUE = 2742
REPOSITORY_BINDING_ISSUE = 2744
SCIENTIFIC_PARENT_ISSUE = 2211
PREREGISTRATION_LABEL = (
    "relaylm2-cognitive-ir-semantic-reconstruction-interface-qualification-v1"
)

CASE_COUNT = 18
SEMANTIC_COMPLETIONS = 18
INPUT_TOKEN_REQUESTS = 36
CONTEXT_LIMIT = 8192
MAX_OUTPUT_TOKENS = 256
TEMPERATURE = 0.0
REASONING = "none"
REQUEST_SEED = None
PARALLEL_SEMANTIC_SLOTS = 1
STREAM = False
PHYSICAL_EXECUTION_AUTHORIZED = False
CITABLE_FOR_REPRESENTATION_CLAIM = False
ARCHITECTURE_CONSEQUENCE = "NONE"

STRICT_PARSE_REQUIRED = 18
VISIBLE_COPY_REQUIRED = 17

SCORED_FIELDS = (
    "operation",
    "permutation",
    "offsets",
    "modulus",
    "provenance_handles",
)

FORBIDDEN_RESCUE_COUNTS: Mapping[str, int] = {
    "semantic_retry": 0,
    "replay": 0,
    "reseed": 0,
    "fallback": 0,
    "hidden_repair": 0,
    "judge": 0,
}

_RESPONSE_SCHEMA_NAME = "relaylm2_e4_ifq1_reference_payload_v1"
STRICT_OUTPUT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "operation": {"type": "string"},
        "permutation": {
            "type": "array",
            "items": {"type": "integer", "minimum": 0, "maximum": 3},
            "minItems": 4,
            "maxItems": 4,
            "uniqueItems": True,
        },
        "offsets": {
            "type": "array",
            "items": {"type": "integer", "minimum": 0, "maximum": 9},
            "minItems": 4,
            "maxItems": 4,
        },
        "modulus": {"type": "integer", "minimum": 2},
        "provenance_handles": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "minItems": 1,
        },
    },
    "required": list(SCORED_FIELDS),
    "additionalProperties": False,
}

_NEUTRAL_SYSTEM_PROMPT = (
    "Copy the values from the visible REFERENCE_PAYLOAD into the required output "
    "object. Preserve every visible value exactly. The provider enforces the "
    "response schema. Return no additional content."
)

_FORBIDDEN_MODEL_FACING_MARKERS = (
    "P4_MEMORY_PLUS_STRUCTURE",
    "P6_GENERIC_EQUAL_INFORMATION",
    "MEMORY_PLUS_STRUCTURE",
    "GENERIC_EQUAL_INFORMATION",
    '"memory"',
    '"structure"',
    '"context"',
    '"relation"',
)


class StrictOutputInterfaceQualificationError(ValueError):
    """The #2742 strict-output interface qualification contract was violated."""


def derive_case_seed(index: int) -> int:
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 0 <= index < CASE_COUNT
    ):
        raise StrictOutputInterfaceQualificationError("case index must be 0..17")
    raw = hashlib.sha256(
        f"{PREREGISTRATION_LABEL}|case|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(raw[:8], "big")


def preregistered_case_seeds() -> tuple[int, ...]:
    return tuple(derive_case_seed(index) for index in range(CASE_COUNT))


def historical_case_seeds() -> frozenset[int]:
    return frozenset(
        {
            *semantic_reconstruction_historical_seeds(),
            *semantic_reconstruction_seeds(),
        }
    )


def validate_seed_admission() -> None:
    seeds = preregistered_case_seeds()
    if len(seeds) != CASE_COUNT or len(set(seeds)) != CASE_COUNT:
        raise StrictOutputInterfaceQualificationError(
            "IFQ1 seeds are not exactly 18 unique values"
        )
    overlap = sorted(set(seeds) & historical_case_seeds())
    if overlap:
        raise StrictOutputInterfaceQualificationError(
            f"IFQ1 seeds overlap historical #2211 evidence: {overlap}"
        )


def response_format() -> dict[str, object]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": _RESPONSE_SCHEMA_NAME,
            "strict": True,
            "schema": STRICT_OUTPUT_SCHEMA,
        },
    }


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _validate_integer_sequence(
    value: object,
    *,
    label: str,
    length: int,
) -> list[int]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
        or len(value) != length
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
    ):
        raise StrictOutputInterfaceQualificationError(
            f"{label} must contain exactly {length} integers"
        )
    return list(value)


def validate_reference_payload(payload: Mapping[str, object]) -> dict[str, object]:
    if set(payload) != set(SCORED_FIELDS):
        raise StrictOutputInterfaceQualificationError(
            "reference payload must contain exactly the five declared fields"
        )

    operation = payload["operation"]
    if operation != "affine_permutation":
        raise StrictOutputInterfaceQualificationError(
            "reference operation must be affine_permutation"
        )

    permutation = _validate_integer_sequence(
        payload["permutation"], label="permutation", length=4
    )
    if sorted(permutation) != [0, 1, 2, 3]:
        raise StrictOutputInterfaceQualificationError(
            "reference permutation must be a permutation of 0..3"
        )

    offsets = _validate_integer_sequence(payload["offsets"], label="offsets", length=4)
    modulus = payload["modulus"]
    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus != 10:
        raise StrictOutputInterfaceQualificationError("reference modulus must be 10")
    if any(item < 0 or item >= modulus for item in offsets):
        raise StrictOutputInterfaceQualificationError(
            "reference offsets must lie inside the modulus"
        )
    if sum(item != 0 for item in offsets) != 3:
        raise StrictOutputInterfaceQualificationError(
            "reference payload must contain exactly three active offsets"
        )

    provenance = payload["provenance_handles"]
    if (
        isinstance(provenance, (str, bytes, bytearray))
        or not isinstance(provenance, Sequence)
        or not provenance
        or any(not isinstance(item, str) or not item for item in provenance)
    ):
        raise StrictOutputInterfaceQualificationError(
            "provenance_handles must be a non-empty sequence of strings"
        )

    return {
        "operation": operation,
        "permutation": permutation,
        "offsets": offsets,
        "modulus": modulus,
        "provenance_handles": list(provenance),
    }


def build_neutral_messages(
    reference_payload: Mapping[str, object],
) -> tuple[dict[str, str], ...]:
    normalized = validate_reference_payload(reference_payload)
    user_content = "REFERENCE_PAYLOAD\n" + _canonical_json(normalized)
    messages = (
        {"role": "system", "content": _NEUTRAL_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    )
    model_facing = "\n".join(message["content"] for message in messages)
    for marker in _FORBIDDEN_MODEL_FACING_MARKERS:
        if marker in model_facing:
            raise StrictOutputInterfaceQualificationError(
                f"neutral request contains forbidden treatment marker: {marker}"
            )
    return messages


def _reject_constant(value: str) -> object:
    raise StrictOutputInterfaceQualificationError(
        f"non-finite JSON constant is forbidden: {value}"
    )


def _reject_duplicate_object(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise StrictOutputInterfaceQualificationError(
                f"duplicate JSON object member: {key}"
            )
        result[key] = value
    return result


def parse_strict_completion(content: str) -> dict[str, object]:
    if not isinstance(content, str) or not content.strip():
        raise StrictOutputInterfaceQualificationError(
            "completion must be one non-empty JSON object"
        )
    try:
        value = json.loads(
            content,
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise StrictOutputInterfaceQualificationError(
            "completion is not one valid JSON value"
        ) from exc
    if not isinstance(value, Mapping):
        raise StrictOutputInterfaceQualificationError(
            "completion must decode to one JSON object"
        )
    return validate_reference_payload(value)


@dataclass(frozen=True, slots=True)
class InterfaceQualificationScore:
    strict_parse_valid: bool
    visible_payload_copy_exact: bool
    failure_reason: str | None


def score_completion(
    content: str,
    visible_reference_payload: Mapping[str, object],
) -> InterfaceQualificationScore:
    expected = validate_reference_payload(visible_reference_payload)
    try:
        parsed = parse_strict_completion(content)
    except StrictOutputInterfaceQualificationError as exc:
        return InterfaceQualificationScore(
            strict_parse_valid=False,
            visible_payload_copy_exact=False,
            failure_reason=str(exc),
        )
    return InterfaceQualificationScore(
        strict_parse_valid=True,
        visible_payload_copy_exact=parsed == expected,
        failure_reason=None if parsed == expected else "visible payload differs",
    )


def _validate_rescue_counts(rescue_counts: Mapping[str, int]) -> bool:
    return dict(rescue_counts) == dict(FORBIDDEN_RESCUE_COUNTS)


def classify_qualification(
    scores: Sequence[InterfaceQualificationScore],
    *,
    provider_attempts: int,
    provider_completions: int,
    input_count_attempts: int,
    input_count_completions: int,
    rescue_counts: Mapping[str, int],
    truncation_failures: int,
    identity_checks_passed: bool,
    pre_wrapper_mechanical_blocked: bool = False,
) -> str:
    if pre_wrapper_mechanical_blocked:
        if any(
            value != 0
            for value in (
                provider_attempts,
                provider_completions,
                input_count_attempts,
                input_count_completions,
            )
        ):
            raise StrictOutputInterfaceQualificationError(
                "pre-wrapper blocked outcome cannot spend scientific requests"
            )
        if scores:
            raise StrictOutputInterfaceQualificationError(
                "pre-wrapper blocked outcome cannot contain scientific scores"
            )
        return "PRE_WRAPPER_MECHANICAL_BLOCKED"

    completed = (
        len(scores) == CASE_COUNT
        and provider_attempts == SEMANTIC_COMPLETIONS
        and provider_completions == SEMANTIC_COMPLETIONS
        and input_count_attempts == INPUT_TOKEN_REQUESTS
        and input_count_completions == INPUT_TOKEN_REQUESTS
    )
    if not completed:
        return "QUALIFICATION_INCOMPLETE"

    parse_valid = sum(score.strict_parse_valid for score in scores)
    copy_exact = sum(score.visible_payload_copy_exact for score in scores)
    qualified = (
        parse_valid == STRICT_PARSE_REQUIRED
        and copy_exact >= VISIBLE_COPY_REQUIRED
        and _validate_rescue_counts(rescue_counts)
        and truncation_failures == 0
        and identity_checks_passed
    )
    return (
        "STRICT_OUTPUT_INTERFACE_QUALIFIED"
        if qualified
        else "STRICT_OUTPUT_INTERFACE_FAILED"
    )
