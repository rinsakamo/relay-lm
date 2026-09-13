from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json

from relaylm.v2_cognitive_ir_semantic_role_binding import (
    ARCHITECTURE_CONSEQUENCE as _RB1_ARCHITECTURE_CONSEQUENCE,
    CONFIRMATORY_CONTRASTS as _RB1_CONFIRMATORY_CONTRASTS,
    FAMILY_COUNT as _RB1_FAMILY_COUNT,
    FORBIDDEN_RESCUE_COUNTS as _RB1_FORBIDDEN_RESCUE_COUNTS,
    INPUT_TOKEN_REQUESTS as _RB1_INPUT_TOKEN_REQUESTS,
    MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS as _RB1_PREFLIGHT_REQUESTS,
    OPAQUE_SURFACE as _RB1_OPAQUE_SURFACE,
    PHYSICAL_EXECUTION_AUTHORIZED as _RB1_PHYSICAL_EXECUTION_AUTHORIZED,
    ROLE_EXPLICIT_SURFACE as _RB1_ROLE_EXPLICIT_SURFACE,
    SEMANTIC_COMPLETIONS as _RB1_SEMANTIC_COMPLETIONS,
    PairedTable,
    RoleBindingScore,
    build_reconstruction_messages as _build_reconstruction_messages,
    decode_surface as _decode_rb1_surface,
    exact_two_sided_sign_p as _exact_two_sided_sign_p,
    historical_family_seeds as _rb1_historical_family_seeds,
    holm_bonferroni as _rb1_holm_bonferroni,
    measurement_admitted as _rb1_measurement_admitted,
    paired_accuracy_difference,
    paired_table as _paired_table,
    parse_wire_shape as _parse_wire_shape,
    prepare_synthetic_mechanism_control as _prepare_rb1_synthetic_control,
    preregistered_seeds as _rb1_preregistered_seeds,
    response_format as _response_format,
    score_reconstruction as _score_reconstruction,
)

PREREGISTRATION_ISSUE = 2847
REPOSITORY_BINDING_ISSUE = 2848
SCIENTIFIC_PARENT_ISSUE = 2211
TRIGGERING_PHYSICAL_ISSUE = 2837
PREREGISTRATION_LABEL = "relaylm2-cognitive-ir-semantic-role-lexical-alignment-v1"

FAMILY_COUNT = 24
SURFACES = (
    "NEUTRAL_ROLE_EXACT_LEXEMES",
    "NEUTRAL_ROLE_DESCRIPTIVE_NONLEXICAL",
    "NEUTRAL_OPAQUE_ROLE_ALIASES",
)
EXACT_LEXEME_SURFACE, DESCRIPTIVE_SURFACE, OPAQUE_SURFACE = SURFACES

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
OUTPUT_FIELDS = (
    "operation",
    "permutation",
    "offsets",
    "modulus",
    "provenance_handles",
)
DESCRIPTIVE_CONTEXT_KEY = "source_handles"
DESCRIPTIVE_RELATION_KEYS = (
    "transform_kind",
    "index_reordering",
    "additive_shifts",
    "modular_divisor",
)
CONFIRMATORY_CONTRASTS = (
    "H1_EXACT_LEXEMES_VS_DESCRIPTIVE_NONLEXICAL",
    "H2_DESCRIPTIVE_NONLEXICAL_VS_OPAQUE",
)
DESCRIPTIVE_ONLY_CONTRAST = "E_VS_O_DESCRIPTIVE_ONLY"

FORBIDDEN_RESCUE_COUNTS: Mapping[str, int] = dict(_RB1_FORBIDDEN_RESCUE_COUNTS)
PHYSICAL_EXECUTION_AUTHORIZED = False
ARCHITECTURE_CONSEQUENCE = "NONE"


class SemanticRoleLexicalAlignmentError(ValueError):
    """The #2847 E4-LX1 preregistration was violated."""


def derive_family_seed(index: int) -> int:
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 0 <= index < FAMILY_COUNT
    ):
        raise SemanticRoleLexicalAlignmentError("family index must be 0..23")
    digest = hashlib.sha256(
        f"{PREREGISTRATION_LABEL}|family|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "big")


def preregistered_seeds() -> tuple[int, ...]:
    return tuple(derive_family_seed(index) for index in range(FAMILY_COUNT))


def historical_family_seeds() -> frozenset[int]:
    return frozenset(
        {
            *_rb1_historical_family_seeds(),
            *_rb1_preregistered_seeds(),
        }
    )


def validate_seed_admission() -> None:
    seeds = preregistered_seeds()
    if len(seeds) != FAMILY_COUNT or len(set(seeds)) != FAMILY_COUNT:
        raise SemanticRoleLexicalAlignmentError(
            "E4-LX1 seeds are not exactly 24 unique values"
        )
    overlap = sorted(set(seeds) & historical_family_seeds())
    if overlap:
        raise SemanticRoleLexicalAlignmentError(
            f"E4-LX1 seeds overlap historical #2211 evidence: {overlap}"
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
        raise SemanticRoleLexicalAlignmentError(f"{label} must be an object")
    return value


def _descriptive_payload(
    canonical_truth: Mapping[str, object],
) -> dict[str, object]:
    return {
        "context": {
            DESCRIPTIVE_CONTEXT_KEY: list(canonical_truth["provenance_handles"]),
        },
        "relation": {
            "transform_kind": canonical_truth["operation"],
            "index_reordering": list(canonical_truth["permutation"]),
            "additive_shifts": list(canonical_truth["offsets"]),
            "modular_divisor": canonical_truth["modulus"],
        },
    }


def decode_surface(
    surface: str,
    payload: Mapping[str, object],
) -> dict[str, object]:
    if surface == EXACT_LEXEME_SURFACE:
        return _decode_rb1_surface(_RB1_ROLE_EXPLICIT_SURFACE, payload)
    if surface == OPAQUE_SURFACE:
        return _decode_rb1_surface(_RB1_OPAQUE_SURFACE, payload)
    if surface != DESCRIPTIVE_SURFACE:
        raise SemanticRoleLexicalAlignmentError(
            f"unsupported E4-LX1 surface: {surface}"
        )

    if set(payload) != {"context", "relation"}:
        raise SemanticRoleLexicalAlignmentError(
            "descriptive payload must contain exactly context/relation"
        )
    context = _require_mapping(payload["context"], label="context")
    relation = _require_mapping(payload["relation"], label="relation")
    if set(context) != {DESCRIPTIVE_CONTEXT_KEY}:
        raise SemanticRoleLexicalAlignmentError(
            "descriptive context must contain exactly source_handles"
        )
    if set(relation) != set(DESCRIPTIVE_RELATION_KEYS):
        raise SemanticRoleLexicalAlignmentError(
            "descriptive relation has unexpected fields"
        )

    explicit_shadow = {
        "context": {"provenance_handles": context["source_handles"]},
        "relation": {
            "operation": relation["transform_kind"],
            "permutation": relation["index_reordering"],
            "offsets": relation["additive_shifts"],
            "modulus": relation["modular_divisor"],
        },
    }
    return _decode_rb1_surface(_RB1_ROLE_EXPLICIT_SURFACE, explicit_shadow)


@dataclass(frozen=True, slots=True)
class LexicalAlignmentMechanismControl:
    canonical_truth: Mapping[str, object]
    semantic_digest: str
    semantic_digest_by_surface: Mapping[str, str]
    serialized_by_surface: Mapping[str, str]


def prepare_synthetic_mechanism_control(
    seed: int,
    canonical_payload: Mapping[str, object],
) -> LexicalAlignmentMechanismControl:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise SemanticRoleLexicalAlignmentError(
            "synthetic seed must be a non-negative integer"
        )
    if seed in set(preregistered_seeds()):
        raise SemanticRoleLexicalAlignmentError(
            "synthetic helper cannot materialize a preregistered E4-LX1 seed"
        )

    rb1 = _prepare_rb1_synthetic_control(seed, canonical_payload)
    truth = dict(rb1.canonical_truth)
    exact_payload = json.loads(
        rb1.serialized_by_surface[_RB1_ROLE_EXPLICIT_SURFACE]
    )
    opaque_payload = json.loads(
        rb1.serialized_by_surface[_RB1_OPAQUE_SURFACE]
    )
    descriptive_payload = _descriptive_payload(truth)

    payloads = {
        EXACT_LEXEME_SURFACE: exact_payload,
        DESCRIPTIVE_SURFACE: descriptive_payload,
        OPAQUE_SURFACE: opaque_payload,
    }
    decoded = {
        surface: decode_surface(surface, payload)
        for surface, payload in payloads.items()
    }
    if any(value != truth for value in decoded.values()):
        raise SemanticRoleLexicalAlignmentError(
            "E/D/O decoded semantics differ from canonical truth"
        )

    serialized = {
        surface: _json_text(payload)
        for surface, payload in payloads.items()
    }
    if len(set(serialized.values())) != len(SURFACES):
        raise SemanticRoleLexicalAlignmentError(
            "E/D/O literal representation surfaces must be distinct"
        )

    digest_by_surface = {surface: rb1.semantic_digest for surface in SURFACES}
    if len(set(digest_by_surface.values())) != 1:
        raise SemanticRoleLexicalAlignmentError(
            "E/D/O semantic digest equality failed"
        )

    return LexicalAlignmentMechanismControl(
        canonical_truth=truth,
        semantic_digest=rb1.semantic_digest,
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
    """Reuse the prospective E4-RB1 wire-only parser unchanged."""
    return _parse_wire_shape(content)


def score_reconstruction(
    content: str,
    canonical_truth: Mapping[str, object],
) -> RoleBindingScore:
    """Reuse the E4-RB1 wire/domain/canonical scorer unchanged."""
    return _score_reconstruction(content, canonical_truth)


def semantic_call_plan() -> tuple[tuple[int, int, str], ...]:
    validate_seed_admission()
    plan = tuple(
        (index, seed, surface)
        for index, seed in enumerate(preregistered_seeds())
        for surface in SURFACES
    )
    if len(plan) != SEMANTIC_COMPLETIONS:
        raise SemanticRoleLexicalAlignmentError("semantic call ledger drifted")
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
        raise SemanticRoleLexicalAlignmentError(
            "Holm correction requires exactly E4-LX1 H1/H2"
        )
    rb1_h1, rb1_h2 = _RB1_CONFIRMATORY_CONTRASTS
    mapped = _rb1_holm_bonferroni(
        {
            rb1_h1: raw_p_values[CONFIRMATORY_CONTRASTS[0]],
            rb1_h2: raw_p_values[CONFIRMATORY_CONTRASTS[1]],
        }
    )
    return {
        CONFIRMATORY_CONTRASTS[0]: mapped[rb1_h1],
        CONFIRMATORY_CONTRASTS[1]: mapped[rb1_h2],
    }


def confirmatory_analysis(
    *,
    h1_exact_vs_descriptive: Sequence[tuple[bool, bool]],
    h2_descriptive_vs_opaque: Sequence[tuple[bool, bool]],
) -> dict[str, ConfirmatoryContrast]:
    tables = {
        CONFIRMATORY_CONTRASTS[0]: paired_table(h1_exact_vs_descriptive),
        CONFIRMATORY_CONTRASTS[1]: paired_table(h2_descriptive_vs_opaque),
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


def descriptive_exact_vs_opaque(
    outcomes: Sequence[tuple[bool, bool]],
) -> PairedTable:
    """Return descriptive E-vs-O counts only; intentionally no p-value."""
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
    return _rb1_measurement_admitted(
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
class LexicalAlignmentVerdict:
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
) -> LexicalAlignmentVerdict:
    if not pre_execution_valid:
        return LexicalAlignmentVerdict(
            classification="INVALID_BEFORE_PHYSICAL_EXECUTION",
            statistical_status="INVALID",
            citable_for_accessibility_claim=False,
        )
    if protocol_failure_after_spend or not measurement_passed:
        return LexicalAlignmentVerdict(
            classification="MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND",
            statistical_status="UNDERDETERMINED",
            citable_for_accessibility_claim=False,
        )
    if contrasts is None or set(contrasts) != set(CONFIRMATORY_CONTRASTS):
        raise SemanticRoleLexicalAlignmentError(
            "admitted result requires exactly E4-LX1 H1/H2"
        )

    h1 = contrasts[CONFIRMATORY_CONTRASTS[0]].holm_reject
    h2 = contrasts[CONFIRMATORY_CONTRASTS[1]].holm_reject
    if h1 and h2:
        classification = (
            "MULTIPLE_LEXICAL_ROLE_ACCESSIBILITY_DIFFERENCES_DETECTED"
        )
    elif h1:
        classification = "LEXICAL_FORM_ACCESSIBILITY_DIFFERENCE_DETECTED"
    elif h2:
        classification = "ROLE_DESCRIPTION_ACCESSIBILITY_DIFFERENCE_DETECTED"
    else:
        return LexicalAlignmentVerdict(
            classification=(
                "NO_DECLARED_LEXICAL_ROLE_GAP_DETECTED_AT_THIS_RESOLUTION"
            ),
            statistical_status="UNDERDETERMINED",
            citable_for_accessibility_claim=True,
        )
    return LexicalAlignmentVerdict(
        classification=classification,
        statistical_status="SIGNIFICANT_HOLM_CORRECTED_PAIRED_EXACT_TEST",
        citable_for_accessibility_claim=True,
    )


def validate_repository_binding() -> None:
    if (
        FAMILY_COUNT != _RB1_FAMILY_COUNT
        or SEMANTIC_COMPLETIONS != _RB1_SEMANTIC_COMPLETIONS
        or INPUT_TOKEN_REQUESTS != _RB1_INPUT_TOKEN_REQUESTS
        or MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS != _RB1_PREFLIGHT_REQUESTS
    ):
        raise SemanticRoleLexicalAlignmentError(
            "E4-LX1 accounting drifted from E4-RB1-compatible envelope"
        )

    validate_seed_admission()
    if len(semantic_call_plan()) != SEMANTIC_COMPLETIONS:
        raise SemanticRoleLexicalAlignmentError(
            "repository semantic ledger is inconsistent"
        )

    strict_format = response_format()
    if strict_format.get("type") != "json_schema":
        raise SemanticRoleLexicalAlignmentError(
            "E4-LX1 must use native json_schema response format"
        )
    encoded = _json_text(strict_format)
    for forbidden in (
        "uniqueItems",
        '"minimum"',
        '"maximum"',
        '"const"',
        '"enum"',
    ):
        if forbidden in encoded:
            raise SemanticRoleLexicalAlignmentError(
                f"E4-LX1 wire schema contains semantic constraint: {forbidden}"
            )

    if any(FORBIDDEN_RESCUE_COUNTS.values()):
        raise SemanticRoleLexicalAlignmentError("rescue counters must be zero")
    if PHYSICAL_EXECUTION_AUTHORIZED or _RB1_PHYSICAL_EXECUTION_AUTHORIZED:
        raise SemanticRoleLexicalAlignmentError(
            "repository binding must not authorize physical execution"
        )
    if (
        ARCHITECTURE_CONSEQUENCE != "NONE"
        or _RB1_ARCHITECTURE_CONSEQUENCE != "NONE"
    ):
        raise SemanticRoleLexicalAlignmentError(
            "repository binding cannot mutate architecture"
        )
