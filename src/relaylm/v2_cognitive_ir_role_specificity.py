from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json

from relaylm.v2_cognitive_ir_semantic_role_binding import (
    PairedTable,
    RoleBindingScore,
    paired_accuracy_difference,
)
from relaylm.v2_cognitive_ir_semantic_role_lexical_alignment import (
    ARCHITECTURE_CONSEQUENCE as _LX1_ARCHITECTURE_CONSEQUENCE,
    CONTEXT_LIMIT as _LX1_CONTEXT_LIMIT,
    DESCRIPTIVE_CONTEXT_KEY as _LX1_FUNCTION_CONTEXT_KEY,
    DESCRIPTIVE_RELATION_KEYS as _LX1_FUNCTION_RELATION_KEYS,
    DESCRIPTIVE_SURFACE as _LX1_FUNCTION_SURFACE,
    FAMILY_COUNT as _LX1_FAMILY_COUNT,
    FORBIDDEN_RESCUE_COUNTS as _LX1_FORBIDDEN_RESCUE_COUNTS,
    INPUT_TOKEN_REQUESTS as _LX1_INPUT_TOKEN_REQUESTS,
    MAX_OUTPUT_TOKENS as _LX1_MAX_OUTPUT_TOKENS,
    MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS as _LX1_PREFLIGHT_REQUESTS,
    OUTPUT_FIELDS as _LX1_OUTPUT_FIELDS,
    PARALLEL_SEMANTIC_SLOTS as _LX1_PARALLEL_SLOTS,
    REASONING as _LX1_REASONING,
    REQUEST_SEED as _LX1_REQUEST_SEED,
    SEMANTIC_COMPLETIONS as _LX1_SEMANTIC_COMPLETIONS,
    STREAM as _LX1_STREAM,
    TEMPERATURE as _LX1_TEMPERATURE,
    build_reconstruction_messages as _build_reconstruction_messages,
    decode_surface as _decode_lx1_surface,
    exact_two_sided_sign_p as _exact_two_sided_sign_p,
    historical_family_seeds as _lx1_historical_family_seeds,
    holm_bonferroni as _lx1_holm_bonferroni,
    measurement_admitted as _lx1_measurement_admitted,
    paired_table as _paired_table,
    parse_wire_shape as _parse_wire_shape,
    preregistered_seeds as _lx1_preregistered_seeds,
    response_format as _response_format,
    score_reconstruction as _score_reconstruction,
)

PREREGISTRATION_ISSUE = 2883
REPOSITORY_BINDING_ISSUE = 2884
SCIENTIFIC_PARENT_ISSUE = 2211
TRIGGERING_PHYSICAL_ISSUE = 2871
PREREGISTRATION_LABEL = "relaylm2-cognitive-ir-role-specificity-v1"

FAMILY_COUNT = 24
SURFACES = (
    "ROLE_FUNCTION_DESCRIPTIVE_NONLEXICAL",
    "CATEGORY_DESCRIPTIVE_ROLE_NEUTRAL",
    "OPAQUE_ROLE_ALIASES",
)
FUNCTION_SURFACE, CATEGORY_SURFACE, OPAQUE_SURFACE = SURFACES

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
    "operation_exact",
    "permutation_exact",
    "offsets_exact",
    "modulus_exact",
    "provenance_exact",
)
OUTPUT_FIELDS = tuple(_LX1_OUTPUT_FIELDS)

FUNCTION_CONTEXT_KEY = "source_handles"
FUNCTION_RELATION_KEYS = (
    "transform_kind",
    "index_reordering",
    "additive_shifts",
    "modular_divisor",
)
CATEGORY_CONTEXT_KEY = "text_list"
CATEGORY_RELATION_KEYS = (
    "text_value",
    "integer_list_one",
    "integer_list_two",
    "integer_value",
)
OPAQUE_CONTEXT_KEY = "q0"
OPAQUE_RELATION_KEYS = ("q1", "q2", "q3", "q4")

CATEGORY_FORBIDDEN_ROLE_TERMS = (
    "permutation",
    "offset",
    "modulus",
    "provenance",
    "source",
    "transform",
    "reorder",
    "shift",
    "add",
    "wrap",
    "base",
)

CONFIRMATORY_CONTRASTS = (
    "H1_FUNCTION_SPECIFIC_VS_CATEGORY_NEUTRAL",
    "H2_CATEGORY_NEUTRAL_VS_OPAQUE",
)
DESCRIPTIVE_ONLY_CONTRAST = "F_VS_O_DESCRIPTIVE_ONLY"

FORBIDDEN_RESCUE_COUNTS: Mapping[str, int] = dict(_LX1_FORBIDDEN_RESCUE_COUNTS)
PHYSICAL_EXECUTION_AUTHORIZED = False
ARCHITECTURE_CONSEQUENCE = "NONE"


class RoleSpecificityError(ValueError):
    """The #2883 E4-RS1 preregistration was violated."""


def derive_family_seed(index: int) -> int:
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 0 <= index < FAMILY_COUNT
    ):
        raise RoleSpecificityError("family index must be 0..23")
    digest = hashlib.sha256(
        f"{PREREGISTRATION_LABEL}|family|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "big")


def preregistered_seeds() -> tuple[int, ...]:
    return tuple(derive_family_seed(index) for index in range(FAMILY_COUNT))


def historical_family_seeds() -> frozenset[int]:
    return frozenset(
        {
            *_lx1_historical_family_seeds(),
            *_lx1_preregistered_seeds(),
        }
    )


def validate_seed_admission() -> None:
    seeds = preregistered_seeds()
    if len(seeds) != FAMILY_COUNT or len(set(seeds)) != FAMILY_COUNT:
        raise RoleSpecificityError("E4-RS1 seeds are not exactly 24 unique values")
    overlap = sorted(set(seeds) & historical_family_seeds())
    if overlap:
        raise RoleSpecificityError(
            f"E4-RS1 seeds overlap historical #2211 evidence: {overlap}"
        )


def _json_text(value: object) -> str:
    # Preserve insertion order: #2883 holds semantic-slot order fixed by arm.
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def _require_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RoleSpecificityError(f"{label} must be an object")
    return value


def _function_payload(canonical_truth: Mapping[str, object]) -> dict[str, object]:
    return {
        "context": {
            FUNCTION_CONTEXT_KEY: list(canonical_truth["provenance_handles"]),
        },
        "relation": {
            "transform_kind": canonical_truth["operation"],
            "index_reordering": list(canonical_truth["permutation"]),
            "additive_shifts": list(canonical_truth["offsets"]),
            "modular_divisor": canonical_truth["modulus"],
        },
    }


def _category_payload(canonical_truth: Mapping[str, object]) -> dict[str, object]:
    return {
        "context": {
            CATEGORY_CONTEXT_KEY: list(canonical_truth["provenance_handles"]),
        },
        "relation": {
            "text_value": canonical_truth["operation"],
            "integer_list_one": list(canonical_truth["permutation"]),
            "integer_list_two": list(canonical_truth["offsets"]),
            "integer_value": canonical_truth["modulus"],
        },
    }


def _opaque_payload(canonical_truth: Mapping[str, object]) -> dict[str, object]:
    return {
        "context": {
            OPAQUE_CONTEXT_KEY: list(canonical_truth["provenance_handles"]),
        },
        "relation": {
            "q1": canonical_truth["operation"],
            "q2": list(canonical_truth["permutation"]),
            "q3": list(canonical_truth["offsets"]),
            "q4": canonical_truth["modulus"],
        },
    }


def _function_shadow(
    *,
    provenance_handles: object,
    operation: object,
    permutation: object,
    offsets: object,
    modulus: object,
) -> dict[str, object]:
    return {
        "context": {FUNCTION_CONTEXT_KEY: provenance_handles},
        "relation": {
            "transform_kind": operation,
            "index_reordering": permutation,
            "additive_shifts": offsets,
            "modular_divisor": modulus,
        },
    }


def decode_surface(
    surface: str,
    payload: Mapping[str, object],
) -> dict[str, object]:
    if surface == FUNCTION_SURFACE:
        return _decode_lx1_surface(_LX1_FUNCTION_SURFACE, payload)

    if set(payload) != {"context", "relation"}:
        raise RoleSpecificityError("surface payload must contain exactly context/relation")
    context = _require_mapping(payload["context"], label="context")
    relation = _require_mapping(payload["relation"], label="relation")

    if surface == CATEGORY_SURFACE:
        if tuple(context) != (CATEGORY_CONTEXT_KEY,):
            raise RoleSpecificityError(
                "category context must contain exactly text_list"
            )
        if tuple(relation) != CATEGORY_RELATION_KEYS:
            raise RoleSpecificityError(
                "category relation must preserve frozen semantic-slot order"
            )
        shadow = _function_shadow(
            provenance_handles=context[CATEGORY_CONTEXT_KEY],
            operation=relation["text_value"],
            permutation=relation["integer_list_one"],
            offsets=relation["integer_list_two"],
            modulus=relation["integer_value"],
        )
        return _decode_lx1_surface(_LX1_FUNCTION_SURFACE, shadow)

    if surface == OPAQUE_SURFACE:
        if tuple(context) != (OPAQUE_CONTEXT_KEY,):
            raise RoleSpecificityError("opaque context must contain exactly q0")
        if tuple(relation) != OPAQUE_RELATION_KEYS:
            raise RoleSpecificityError(
                "opaque relation must preserve frozen semantic-slot order"
            )
        shadow = _function_shadow(
            provenance_handles=context[OPAQUE_CONTEXT_KEY],
            operation=relation["q1"],
            permutation=relation["q2"],
            offsets=relation["q3"],
            modulus=relation["q4"],
        )
        return _decode_lx1_surface(_LX1_FUNCTION_SURFACE, shadow)

    raise RoleSpecificityError(f"unsupported E4-RS1 surface: {surface}")


@dataclass(frozen=True, slots=True)
class RoleSpecificityMechanismControl:
    canonical_truth: Mapping[str, object]
    semantic_digest: str
    semantic_digest_by_surface: Mapping[str, str]
    serialized_by_surface: Mapping[str, str]


def prepare_synthetic_mechanism_control(
    seed: int,
    canonical_payload: Mapping[str, object],
) -> RoleSpecificityMechanismControl:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise RoleSpecificityError("synthetic seed must be a non-negative integer")
    if seed in set(preregistered_seeds()):
        raise RoleSpecificityError(
            "synthetic helper cannot materialize a preregistered E4-RS1 seed"
        )

    # E4-RS1 binds only representation surfaces. The caller supplies a synthetic
    # canonical payload; official future families remain absent from this module.
    truth = {
        "operation": canonical_payload["operation"],
        "permutation": list(canonical_payload["permutation"]),
        "offsets": list(canonical_payload["offsets"]),
        "modulus": canonical_payload["modulus"],
        "provenance_handles": list(canonical_payload["provenance_handles"]),
    }

    function_payload = _function_payload(truth)
    category_payload = _category_payload(truth)
    opaque_payload = _opaque_payload(truth)
    payloads = {
        FUNCTION_SURFACE: function_payload,
        CATEGORY_SURFACE: category_payload,
        OPAQUE_SURFACE: opaque_payload,
    }

    decoded = {
        surface: decode_surface(surface, payload)
        for surface, payload in payloads.items()
    }
    canonical_truth = decoded[FUNCTION_SURFACE]
    if any(value != canonical_truth for value in decoded.values()):
        raise RoleSpecificityError(
            "F/C/O decoded semantics differ from canonical truth"
        )

    # Reuse E4-LX1's canonical semantic serialization through the successfully
    # decoded F surface. The digest is evaluator-only and never model-visible.
    semantic_digest = hashlib.sha256(
        json.dumps(
            canonical_truth,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    digest_by_surface = {surface: semantic_digest for surface in SURFACES}

    serialized = {
        surface: _json_text(payload)
        for surface, payload in payloads.items()
    }
    if len(set(serialized.values())) != len(SURFACES):
        raise RoleSpecificityError(
            "F/C/O literal representation surfaces must be distinct"
        )

    return RoleSpecificityMechanismControl(
        canonical_truth=canonical_truth,
        semantic_digest=semantic_digest,
        semantic_digest_by_surface=digest_by_surface,
        serialized_by_surface=serialized,
    )


def build_reconstruction_messages(
    serialized_representation: str,
) -> tuple[dict[str, str], ...]:
    return _build_reconstruction_messages(serialized_representation)


def response_format() -> dict[str, object]:
    return _response_format()


def parse_wire_shape(content: str) -> dict[str, object]:
    return _parse_wire_shape(content)


def score_reconstruction(
    content: str,
    canonical_truth: Mapping[str, object],
) -> RoleBindingScore:
    return _score_reconstruction(content, canonical_truth)


def semantic_call_plan() -> tuple[tuple[int, int, str], ...]:
    validate_seed_admission()
    plan = tuple(
        (index, seed, surface)
        for index, seed in enumerate(preregistered_seeds())
        for surface in SURFACES
    )
    if len(plan) != SEMANTIC_COMPLETIONS:
        raise RoleSpecificityError("semantic call ledger drifted")
    return plan


@dataclass(frozen=True, slots=True)
class ConfirmatoryContrast:
    name: str
    table: PairedTable
    raw_p_value: float
    holm_adjusted_p_value: float
    holm_reject: bool

    @property
    def paired_accuracy_difference(self) -> float:
        return paired_accuracy_difference(self.table)


def exact_two_sided_sign_p(table: PairedTable) -> float:
    return _exact_two_sided_sign_p(table)


def paired_table(outcomes: Sequence[tuple[bool, bool]]) -> PairedTable:
    return _paired_table(outcomes)


def holm_bonferroni(
    raw_p_values: Mapping[str, float],
) -> dict[str, tuple[float, bool]]:
    if set(raw_p_values) != set(CONFIRMATORY_CONTRASTS):
        raise RoleSpecificityError(
            "Holm correction requires exactly E4-RS1 H1/H2"
        )
    lx1_h1 = "H1_EXACT_LEXEMES_VS_DESCRIPTIVE_NONLEXICAL"
    lx1_h2 = "H2_DESCRIPTIVE_NONLEXICAL_VS_OPAQUE"
    mapped = _lx1_holm_bonferroni(
        {
            lx1_h1: raw_p_values[CONFIRMATORY_CONTRASTS[0]],
            lx1_h2: raw_p_values[CONFIRMATORY_CONTRASTS[1]],
        }
    )
    return {
        CONFIRMATORY_CONTRASTS[0]: mapped[lx1_h1],
        CONFIRMATORY_CONTRASTS[1]: mapped[lx1_h2],
    }


def confirmatory_analysis(
    *,
    h1_function_vs_category: Sequence[tuple[bool, bool]],
    h2_category_vs_opaque: Sequence[tuple[bool, bool]],
) -> dict[str, ConfirmatoryContrast]:
    tables = {
        CONFIRMATORY_CONTRASTS[0]: paired_table(h1_function_vs_category),
        CONFIRMATORY_CONTRASTS[1]: paired_table(h2_category_vs_opaque),
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


def descriptive_function_vs_opaque(
    outcomes: Sequence[tuple[bool, bool]],
) -> PairedTable:
    return paired_table(outcomes)


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
    return _lx1_measurement_admitted(
        semantic_equal_families=semantic_equal_families,
        provider_attempts=provider_attempts,
        provider_completions=provider_completions,
        wire_shape_valid=wire_shape_valid,
        input_count_attempts=input_count_attempts,
        input_count_completions=input_count_completions,
        rescue_counts=rescue_counts,
        truncation_failures=truncation_failures,
        identity_checks_passed=identity_checks_passed,
    )


@dataclass(frozen=True, slots=True)
class RoleSpecificityVerdict:
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
) -> RoleSpecificityVerdict:
    if not pre_execution_valid:
        return RoleSpecificityVerdict(
            classification="INVALID_BEFORE_PHYSICAL_EXECUTION",
            statistical_status="INVALID",
            citable_for_accessibility_claim=False,
        )
    if protocol_failure_after_spend or not measurement_passed:
        return RoleSpecificityVerdict(
            classification="MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND",
            statistical_status="UNDERDETERMINED",
            citable_for_accessibility_claim=False,
        )
    if contrasts is None or set(contrasts) != set(CONFIRMATORY_CONTRASTS):
        raise RoleSpecificityError(
            "admitted result requires exactly E4-RS1 H1/H2 contrasts"
        )

    h1 = contrasts[CONFIRMATORY_CONTRASTS[0]].holm_reject
    h2 = contrasts[CONFIRMATORY_CONTRASTS[1]].holm_reject
    if h1 and h2:
        classification = "MULTIPLE_ROLE_ACCESSIBILITY_COMPONENTS_DETECTED"
    elif h1:
        classification = "ROLE_FUNCTION_SPECIFICITY_DIFFERENCE_DETECTED"
    elif h2:
        classification = "GENERIC_LEXICAL_TRANSPARENCY_DIFFERENCE_DETECTED"
    else:
        return RoleSpecificityVerdict(
            classification="NO_DECLARED_ROLE_SPECIFICITY_GAP_DETECTED_AT_THIS_RESOLUTION",
            statistical_status="UNDERDETERMINED",
            citable_for_accessibility_claim=True,
        )
    return RoleSpecificityVerdict(
        classification=classification,
        statistical_status="SIGNIFICANT_HOLM_CORRECTED_PAIRED_EXACT_TEST",
        citable_for_accessibility_claim=True,
    )


def validate_repository_binding() -> None:
    if (
        FAMILY_COUNT != _LX1_FAMILY_COUNT
        or SEMANTIC_COMPLETIONS != _LX1_SEMANTIC_COMPLETIONS
        or INPUT_TOKEN_REQUESTS != _LX1_INPUT_TOKEN_REQUESTS
        or MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS != _LX1_PREFLIGHT_REQUESTS
        or CONTEXT_LIMIT != _LX1_CONTEXT_LIMIT
        or MAX_OUTPUT_TOKENS != _LX1_MAX_OUTPUT_TOKENS
        or TEMPERATURE != _LX1_TEMPERATURE
        or REASONING != _LX1_REASONING
        or REQUEST_SEED != _LX1_REQUEST_SEED
        or PARALLEL_SEMANTIC_SLOTS != _LX1_PARALLEL_SLOTS
        or STREAM != _LX1_STREAM
    ):
        raise RoleSpecificityError("E4-RS1 resource envelope drifted from E4-LX1")

    if (
        FUNCTION_CONTEXT_KEY != _LX1_FUNCTION_CONTEXT_KEY
        or FUNCTION_RELATION_KEYS != tuple(_LX1_FUNCTION_RELATION_KEYS)
    ):
        raise RoleSpecificityError(
            "F surface drifted from the successful E4-LX1 descriptive vocabulary"
        )

    if ARCHITECTURE_CONSEQUENCE != _LX1_ARCHITECTURE_CONSEQUENCE:
        raise RoleSpecificityError("architecture consequence drifted")

    all_keys = (
        FUNCTION_CONTEXT_KEY,
        *FUNCTION_RELATION_KEYS,
        CATEGORY_CONTEXT_KEY,
        *CATEGORY_RELATION_KEYS,
        OPAQUE_CONTEXT_KEY,
        *OPAQUE_RELATION_KEYS,
    )
    if set(all_keys) & set(OUTPUT_FIELDS):
        raise RoleSpecificityError("input surface reuses a required output field key")

    for key in (CATEGORY_CONTEXT_KEY, *CATEGORY_RELATION_KEYS):
        lowered = key.lower()
        for term in CATEGORY_FORBIDDEN_ROLE_TERMS:
            if term in lowered:
                raise RoleSpecificityError(
                    f"category key leaks role-functional term {term}: {key}"
                )

    if any(FORBIDDEN_RESCUE_COUNTS.values()):
        raise RoleSpecificityError("zero-rescue contract drifted")
    if PHYSICAL_EXECUTION_AUTHORIZED:
        raise RoleSpecificityError("repository binding cannot authorize execution")

    validate_seed_admission()
    semantic_call_plan()


validate_repository_binding()
