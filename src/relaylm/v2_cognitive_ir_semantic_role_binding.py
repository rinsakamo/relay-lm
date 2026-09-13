from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math

from relaylm.v2_cognitive_ir_experiment import (
    decode_semantic_payload,
    semantic_digest,
)
from relaylm.v2_cognitive_ir_semantic_reconstruction import (
    build_reconstruction_messages as _build_reconstruction_messages,
    prepare_mechanism_control as _prepare_mechanism_control,
)
from relaylm.v2_cognitive_ir_semantic_reconstruction_strict import (
    historical_family_seeds as _strict_historical_family_seeds,
    preregistered_seeds as _strict_reconstruction_seeds,
)


PREREGISTRATION_ISSUE = 2830
REPOSITORY_BINDING_ISSUE = 2831
SCIENTIFIC_PARENT_ISSUE = 2211
PREREGISTRATION_LABEL = "relaylm2-cognitive-ir-semantic-role-binding-v1"

FAMILY_COUNT = 24
SURFACES = (
    "TYPED_MEMORY_STRUCTURE",
    "NEUTRAL_ROLE_EXPLICIT",
    "NEUTRAL_OPAQUE_ROLE_ALIASES",
)
TYPED_SURFACE, ROLE_EXPLICIT_SURFACE, OPAQUE_SURFACE = SURFACES

SEMANTIC_COMPLETIONS = 72
INPUT_TOKEN_REQUESTS = 144
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
DIAGNOSTIC_ENDPOINTS = (
    "wire_shape_valid",
    "semantic_domain_valid",
    "core_rule_exact",
    "provenance_exact",
)
SCORED_FIELDS = (
    "operation",
    "permutation",
    "offsets",
    "modulus",
    "provenance_handles",
)
CONFIRMATORY_CONTRASTS = ("H1_ROLE_EXPLICIT_VS_OPAQUE", "H2_TYPED_VS_ROLE_EXPLICIT")
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

_RESPONSE_SCHEMA_NAME = "relaylm2_e4_rb1_semantic_role_binding_v1"
WIRE_SHAPE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "operation": {"type": "string"},
        "permutation": {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 4,
            "maxItems": 4,
        },
        "offsets": {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 4,
            "maxItems": 4,
        },
        "modulus": {"type": "integer"},
        "provenance_handles": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "minItems": 1,
        },
    },
    "required": list(SCORED_FIELDS),
    "additionalProperties": False,
}


class SemanticRoleBindingError(ValueError):
    """The #2830 E4-RB1 preregistration was violated."""


def derive_family_seed(index: int) -> int:
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 0 <= index < FAMILY_COUNT
    ):
        raise SemanticRoleBindingError("family index must be 0..23")
    raw = hashlib.sha256(
        f"{PREREGISTRATION_LABEL}|family|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(raw[:8], "big")


def preregistered_seeds() -> tuple[int, ...]:
    return tuple(derive_family_seed(index) for index in range(FAMILY_COUNT))


def historical_family_seeds() -> frozenset[int]:
    return frozenset(
        {
            *_strict_historical_family_seeds(),
            *_strict_reconstruction_seeds(),
        }
    )


def validate_seed_admission() -> None:
    seeds = preregistered_seeds()
    if len(seeds) != FAMILY_COUNT or len(set(seeds)) != FAMILY_COUNT:
        raise SemanticRoleBindingError(
            "E4-RB1 seeds are not exactly 24 unique values"
        )
    overlap = sorted(set(seeds) & historical_family_seeds())
    if overlap:
        raise SemanticRoleBindingError(
            f"E4-RB1 seeds overlap historical #2211 evidence: {overlap}"
        )


def _json_text(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _require_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SemanticRoleBindingError(f"{label} must be an object")
    return value


def _role_explicit_payload(canonical_truth: Mapping[str, object]) -> dict[str, object]:
    return {
        "context": {
            "provenance_handles": list(canonical_truth["provenance_handles"]),
        },
        "relation": {
            "operation": canonical_truth["operation"],
            "permutation": list(canonical_truth["permutation"]),
            "offsets": list(canonical_truth["offsets"]),
            "modulus": canonical_truth["modulus"],
        },
    }


def decode_surface(surface: str, payload: Mapping[str, object]) -> dict[str, object]:
    if surface == TYPED_SURFACE:
        return decode_semantic_payload("P4_MEMORY_PLUS_STRUCTURE", payload)
    if surface == OPAQUE_SURFACE:
        return decode_semantic_payload("P6_GENERIC_EQUAL_INFORMATION", payload)
    if surface != ROLE_EXPLICIT_SURFACE:
        raise SemanticRoleBindingError(f"unsupported E4-RB1 surface: {surface}")

    if set(payload) != {"context", "relation"}:
        raise SemanticRoleBindingError(
            "role-explicit payload must contain exactly context/relation"
        )
    context = _require_mapping(payload["context"], label="context")
    relation = _require_mapping(payload["relation"], label="relation")
    if set(context) != {"provenance_handles"}:
        raise SemanticRoleBindingError(
            "role-explicit context must contain provenance_handles"
        )
    if set(relation) != {"operation", "permutation", "offsets", "modulus"}:
        raise SemanticRoleBindingError(
            "role-explicit relation has unexpected fields"
        )

    typed_shadow = {
        "memory": {"origin_refs": context["provenance_handles"]},
        "structure": {
            "operation": relation["operation"],
            "permutation": relation["permutation"],
            "offsets": relation["offsets"],
            "modulus": relation["modulus"],
        },
    }
    return decode_semantic_payload("P4_MEMORY_PLUS_STRUCTURE", typed_shadow)


@dataclass(frozen=True, slots=True)
class RoleBindingMechanismControl:
    canonical_truth: Mapping[str, object]
    semantic_digest: str
    serialized_by_surface: Mapping[str, str]


def prepare_synthetic_mechanism_control(
    seed: int,
    canonical_payload: Mapping[str, object],
) -> RoleBindingMechanismControl:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise SemanticRoleBindingError(
            "synthetic seed must be a non-negative integer"
        )
    if seed in set(preregistered_seeds()):
        raise SemanticRoleBindingError(
            "synthetic helper cannot materialize a preregistered E4-RB1 seed"
        )

    historical = _prepare_mechanism_control(canonical_payload)
    truth = dict(historical.canonical_truth)
    typed = json.loads(historical.serialized_by_arm["P4_MEMORY_PLUS_STRUCTURE"])
    opaque = json.loads(historical.serialized_by_arm["P6_GENERIC_EQUAL_INFORMATION"])
    explicit = _role_explicit_payload(truth)

    decoded = {
        TYPED_SURFACE: decode_surface(TYPED_SURFACE, typed),
        ROLE_EXPLICIT_SURFACE: decode_surface(ROLE_EXPLICIT_SURFACE, explicit),
        OPAQUE_SURFACE: decode_surface(OPAQUE_SURFACE, opaque),
    }
    if any(value != truth for value in decoded.values()):
        raise SemanticRoleBindingError(
            "T/R/O decoded semantics differ from canonical truth"
        )

    typed_digest = semantic_digest("P4_MEMORY_PLUS_STRUCTURE", typed)
    opaque_digest = semantic_digest("P6_GENERIC_EQUAL_INFORMATION", opaque)
    if typed_digest != historical.semantic_digest or opaque_digest != typed_digest:
        raise SemanticRoleBindingError("T/O historical semantic digest drifted")

    serialized = {
        TYPED_SURFACE: _json_text(typed),
        ROLE_EXPLICIT_SURFACE: _json_text(explicit),
        OPAQUE_SURFACE: _json_text(opaque),
    }
    if len(set(serialized.values())) != len(SURFACES):
        raise SemanticRoleBindingError(
            "T/R/O literal representation surfaces must be distinct"
        )

    return RoleBindingMechanismControl(
        canonical_truth=truth,
        semantic_digest=typed_digest,
        serialized_by_surface=serialized,
    )


def build_reconstruction_messages(
    serialized_representation: str,
) -> tuple[dict[str, str], ...]:
    return _build_reconstruction_messages(serialized_representation)


def response_format() -> dict[str, object]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": _RESPONSE_SCHEMA_NAME,
            "strict": True,
            "schema": WIRE_SHAPE_SCHEMA,
        },
    }


def semantic_call_plan() -> tuple[tuple[int, int, str], ...]:
    validate_seed_admission()
    plan = tuple(
        (index, seed, surface)
        for index, seed in enumerate(preregistered_seeds())
        for surface in SURFACES
    )
    if len(plan) != SEMANTIC_COMPLETIONS:
        raise SemanticRoleBindingError("semantic call ledger drifted")
    return plan


def _reject_constant(value: str) -> object:
    raise SemanticRoleBindingError(f"non-finite JSON constant: {value}")


def _reject_duplicate_object(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SemanticRoleBindingError(
                f"duplicate JSON object member: {key}"
            )
        result[key] = value
    return result


def _is_integer(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int)


def _integer_vector(value: object, *, label: str) -> list[int]:
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
        or len(value) != 4
        or any(not _is_integer(item) for item in value)
    ):
        raise SemanticRoleBindingError(
            f"{label} must contain exactly four integers"
        )
    return list(value)


def parse_wire_shape(content: str) -> dict[str, object]:
    if not isinstance(content, str) or not content.strip():
        raise SemanticRoleBindingError(
            "completion must be one non-empty JSON object"
        )
    try:
        value = json.loads(
            content,
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise SemanticRoleBindingError(
            "completion is not one valid JSON value"
        ) from exc

    if not isinstance(value, Mapping):
        raise SemanticRoleBindingError(
            "completion must decode to one JSON object"
        )
    if set(value) != set(SCORED_FIELDS):
        raise SemanticRoleBindingError(
            "completion must contain exactly the five scored fields"
        )

    operation = value["operation"]
    if not isinstance(operation, str):
        raise SemanticRoleBindingError("operation must be a string")
    permutation = _integer_vector(value["permutation"], label="permutation")
    offsets = _integer_vector(value["offsets"], label="offsets")
    modulus = value["modulus"]
    if not _is_integer(modulus):
        raise SemanticRoleBindingError("modulus must be an integer")

    provenance = value["provenance_handles"]
    if (
        isinstance(provenance, (str, bytes, bytearray))
        or not isinstance(provenance, Sequence)
        or not provenance
        or any(not isinstance(item, str) or not item for item in provenance)
    ):
        raise SemanticRoleBindingError(
            "provenance_handles must be a non-empty sequence of non-empty strings"
        )

    return {
        "operation": operation,
        "permutation": permutation,
        "offsets": offsets,
        "modulus": modulus,
        "provenance_handles": list(provenance),
    }


def semantic_domain_failure(
    parsed: Mapping[str, object],
) -> str | None:
    if parsed["operation"] != "affine_permutation":
        return "invalid operation"

    permutation = parsed["permutation"]
    assert isinstance(permutation, list)
    if sorted(permutation) != [0, 1, 2, 3]:
        return "invalid permutation"

    modulus = parsed["modulus"]
    assert _is_integer(modulus)
    if modulus <= 1:
        return "invalid modulus"

    offsets = parsed["offsets"]
    assert isinstance(offsets, list)
    if any(value < 0 or value >= modulus for value in offsets):
        return "offset outside modulus"

    return None


@dataclass(frozen=True, slots=True)
class RoleBindingScore:
    wire_shape_valid: bool
    semantic_domain_valid: bool
    full_payload_exact: bool
    core_rule_exact: bool
    provenance_exact: bool
    failure_reason: str | None


def score_reconstruction(
    content: str,
    canonical_truth: Mapping[str, object],
) -> RoleBindingScore:
    expected = dict(_prepare_mechanism_control(canonical_truth).canonical_truth)
    try:
        parsed = parse_wire_shape(content)
    except SemanticRoleBindingError as exc:
        return RoleBindingScore(
            wire_shape_valid=False,
            semantic_domain_valid=False,
            full_payload_exact=False,
            core_rule_exact=False,
            provenance_exact=False,
            failure_reason=f"wire_shape: {exc}",
        )

    domain_failure = semantic_domain_failure(parsed)
    core_fields = ("operation", "permutation", "offsets", "modulus")
    core_exact = all(parsed[key] == expected[key] for key in core_fields)
    provenance_exact = (
        parsed["provenance_handles"] == expected["provenance_handles"]
    )

    if domain_failure is not None:
        failure_reason = f"semantic_domain: {domain_failure}"
    elif not core_exact:
        mismatch = next(
            key for key in core_fields if parsed[key] != expected[key]
        )
        failure_reason = f"core_mismatch: {mismatch}"
    elif not provenance_exact:
        failure_reason = "provenance_mismatch"
    else:
        failure_reason = None

    return RoleBindingScore(
        wire_shape_valid=True,
        semantic_domain_valid=domain_failure is None,
        full_payload_exact=core_exact and provenance_exact,
        core_rule_exact=core_exact,
        provenance_exact=provenance_exact,
        failure_reason=failure_reason,
    )


@dataclass(frozen=True, slots=True)
class PairedTable:
    both_correct: int
    left_only: int
    right_only: int
    both_wrong: int

    @property
    def discordant(self) -> int:
        return self.left_only + self.right_only


def _validate_paired_table(table: PairedTable) -> None:
    values = (
        table.both_correct,
        table.left_only,
        table.right_only,
        table.both_wrong,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in values
    ):
        raise SemanticRoleBindingError(
            "paired table counts must be non-negative integers"
        )
    if sum(values) != FAMILY_COUNT:
        raise SemanticRoleBindingError(
            "paired table must contain exactly 24 families"
        )


def paired_table(outcomes: Sequence[tuple[bool, bool]]) -> PairedTable:
    if len(outcomes) != FAMILY_COUNT:
        raise SemanticRoleBindingError(
            "paired outcome vector must contain exactly 24 families"
        )
    counts = {
        "both_correct": 0,
        "left_only": 0,
        "right_only": 0,
        "both_wrong": 0,
    }
    for left_correct, right_correct in outcomes:
        if not isinstance(left_correct, bool) or not isinstance(right_correct, bool):
            raise SemanticRoleBindingError(
                "paired outcomes must be booleans"
            )
        if left_correct and right_correct:
            counts["both_correct"] += 1
        elif left_correct:
            counts["left_only"] += 1
        elif right_correct:
            counts["right_only"] += 1
        else:
            counts["both_wrong"] += 1
    return PairedTable(**counts)


def paired_accuracy_difference(table: PairedTable) -> float:
    _validate_paired_table(table)
    return (table.left_only - table.right_only) / FAMILY_COUNT


def exact_two_sided_sign_p(table: PairedTable) -> float:
    _validate_paired_table(table)
    discordant = table.discordant
    if discordant == 0:
        return 1.0
    smaller = min(table.left_only, table.right_only)
    tail = sum(math.comb(discordant, k) for k in range(smaller + 1))
    return min(1.0, 2.0 * tail / (2**discordant))


@dataclass(frozen=True, slots=True)
class ConfirmatoryContrast:
    name: str
    table: PairedTable
    raw_p_value: float
    holm_adjusted_p_value: float
    holm_reject: bool


def _validate_p_value(value: float, *, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or not 0.0 <= float(value) <= 1.0
    ):
        raise SemanticRoleBindingError(f"{label} must be a finite p-value")
    return float(value)


def holm_bonferroni(
    raw_p_values: Mapping[str, float],
) -> dict[str, tuple[float, bool]]:
    if set(raw_p_values) != set(CONFIRMATORY_CONTRASTS):
        raise SemanticRoleBindingError(
            "Holm correction requires exactly the two preregistered contrasts"
        )

    ordered = sorted(
        (
            (_validate_p_value(value, label=name), name)
            for name, value in raw_p_values.items()
        ),
        key=lambda item: (item[0], item[1]),
    )
    m = len(ordered)
    adjusted_by_name: dict[str, float] = {}
    running_adjusted = 0.0
    still_rejecting = True
    reject_by_name: dict[str, bool] = {}

    for rank, (raw_p, name) in enumerate(ordered):
        multiplier = m - rank
        running_adjusted = max(
            running_adjusted,
            min(1.0, raw_p * multiplier),
        )
        adjusted_by_name[name] = running_adjusted

        threshold = ALPHA / multiplier
        reject = still_rejecting and raw_p <= threshold
        reject_by_name[name] = reject
        if not reject:
            still_rejecting = False

    return {
        name: (adjusted_by_name[name], reject_by_name[name])
        for name in CONFIRMATORY_CONTRASTS
    }


def confirmatory_analysis(
    *,
    h1_role_explicit_vs_opaque: Sequence[tuple[bool, bool]],
    h2_typed_vs_role_explicit: Sequence[tuple[bool, bool]],
) -> dict[str, ConfirmatoryContrast]:
    tables = {
        CONFIRMATORY_CONTRASTS[0]: paired_table(
            h1_role_explicit_vs_opaque
        ),
        CONFIRMATORY_CONTRASTS[1]: paired_table(
            h2_typed_vs_role_explicit
        ),
    }
    raw = {
        name: exact_two_sided_sign_p(table)
        for name, table in tables.items()
    }
    holm = holm_bonferroni(raw)
    return {
        name: ConfirmatoryContrast(
            name=name,
            table=tables[name],
            raw_p_value=raw[name],
            holm_adjusted_p_value=holm[name][0],
            holm_reject=holm[name][1],
        )
        for name in CONFIRMATORY_CONTRASTS
    }


def _validate_rescue_counts(rescue_counts: Mapping[str, int]) -> bool:
    return dict(rescue_counts) == dict(FORBIDDEN_RESCUE_COUNTS)


def measurement_admitted(
    *,
    semantic_equal_families: int,
    provider_attempts: int,
    provider_completions: int,
    wire_shape_valid: int,
    input_count_attempts: int,
    input_count_completions: int,
    rescue_counts: Mapping[str, int],
    truncation_failures: int,
    identity_checks_passed: bool,
) -> bool:
    values = (
        semantic_equal_families,
        provider_attempts,
        provider_completions,
        wire_shape_valid,
        input_count_attempts,
        input_count_completions,
        truncation_failures,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in values
    ):
        raise SemanticRoleBindingError(
            "measurement counts must be non-negative integers"
        )
    return (
        semantic_equal_families == FAMILY_COUNT
        and provider_attempts == SEMANTIC_COMPLETIONS
        and provider_completions == SEMANTIC_COMPLETIONS
        and wire_shape_valid == SEMANTIC_COMPLETIONS
        and input_count_attempts == INPUT_TOKEN_REQUESTS
        and input_count_completions == INPUT_TOKEN_REQUESTS
        and _validate_rescue_counts(rescue_counts)
        and truncation_failures == 0
        and identity_checks_passed
    )


@dataclass(frozen=True, slots=True)
class RoleBindingVerdict:
    classification: str
    statistical_status: str
    citable_for_accessibility_claim: bool
    architecture_consequence: str = ARCHITECTURE_CONSEQUENCE


def classify_result(
    contrasts: Mapping[str, ConfirmatoryContrast] | None,
    *,
    pre_execution_valid: bool = True,
    protocol_failure_after_spend: bool = False,
    measurement_passed: bool = True,
) -> RoleBindingVerdict:
    if not pre_execution_valid:
        return RoleBindingVerdict(
            classification="INVALID_BEFORE_PHYSICAL_EXECUTION",
            statistical_status="INVALID",
            citable_for_accessibility_claim=False,
        )
    if protocol_failure_after_spend or not measurement_passed:
        return RoleBindingVerdict(
            classification="MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND",
            statistical_status="UNDERDETERMINED",
            citable_for_accessibility_claim=False,
        )
    if contrasts is None or set(contrasts) != set(CONFIRMATORY_CONTRASTS):
        raise SemanticRoleBindingError(
            "admitted result requires exactly H1 and H2 confirmatory contrasts"
        )

    h1 = contrasts[CONFIRMATORY_CONTRASTS[0]].holm_reject
    h2 = contrasts[CONFIRMATORY_CONTRASTS[1]].holm_reject
    if h1 and h2:
        classification = "MULTIPLE_SURFACE_ACCESSIBILITY_DIFFERENCES_DETECTED"
    elif h1:
        classification = "ROLE_BINDING_ACCESSIBILITY_DIFFERENCE_DETECTED"
    elif h2:
        classification = "TYPED_WRAPPER_ACCESSIBILITY_DIFFERENCE_DETECTED"
    else:
        return RoleBindingVerdict(
            classification="NO_DECLARED_SURFACE_GAP_DETECTED_AT_THIS_RESOLUTION",
            statistical_status="UNDERDETERMINED",
            citable_for_accessibility_claim=True,
        )
    return RoleBindingVerdict(
        classification=classification,
        statistical_status="SIGNIFICANT_HOLM_CORRECTED_PAIRED_EXACT_TEST",
        citable_for_accessibility_claim=True,
    )


def validate_repository_binding() -> None:
    validate_seed_admission()
    plan = semantic_call_plan()
    if len(plan) != SEMANTIC_COMPLETIONS:
        raise SemanticRoleBindingError(
            "repository semantic ledger is inconsistent"
        )
    schema = response_format()
    if schema["type"] != "json_schema":
        raise SemanticRoleBindingError(
            "E4-RB1 must use native json_schema response format"
        )
    json_schema = schema["json_schema"]
    if not isinstance(json_schema, Mapping) or json_schema.get("strict") is not True:
        raise SemanticRoleBindingError(
            "E4-RB1 response format must remain strict"
        )
    encoded = _json_text(schema)
    for forbidden in ("uniqueItems", '"minimum"', '"maximum"', '"const"', '"enum"'):
        if forbidden in encoded:
            raise SemanticRoleBindingError(
                f"E4-RB1 wire schema contains semantic answer constraint: {forbidden}"
            )
    if any(FORBIDDEN_RESCUE_COUNTS.values()):
        raise SemanticRoleBindingError("rescue counters must be zero")
    if PHYSICAL_EXECUTION_AUTHORIZED:
        raise SemanticRoleBindingError(
            "repository binding must not authorize physical execution"
        )
    if ARCHITECTURE_CONSEQUENCE != "NONE":
        raise SemanticRoleBindingError(
            "repository binding cannot mutate architecture"
        )
