from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json

import relaylm.v2_cognitive_ir_s3 as s3_base
from relaylm.v2_cognitive_ir_actual_model import (
    S2Representation,
    _parse_learned_rule as _parse_s2_learned_rule,
    build_s2_formation_messages as _build_s2_formation_messages,
    build_s2_target_messages as _build_s2_target_messages,
)
from relaylm.v2_cognitive_ir_experiment import (
    neutralize_typed_payload,
    semantic_digest as _historical_semantic_digest,
)
from relaylm.v2_cognitive_ir_role_specificity import (
    FUNCTION_CONTEXT_KEY,
    FUNCTION_RELATION_KEYS,
    PairedTable,
    exact_two_sided_sign_p as _exact_two_sided_sign_p,
    historical_family_seeds as _role_historical_family_seeds,
    paired_accuracy_difference,
    paired_table as _paired_table,
    preregistered_seeds as _role_preregistered_seeds,
)
from relaylm.v2_cognitive_ir_role_specificity_physical import (
    INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL as _ESTABLISHED_INPUT_COUNTS_PER_CALL,
)
from relaylm.v2_cognitive_ir_s3_r5 import S3_R5_MAX_OUTPUT_TOKENS
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from relaylm.v2_transfer_experiment import PublicExample, TargetStep, TransferFamily, VectorRule


PREREGISTRATION_ISSUE = 2899
REPOSITORY_BINDING_ISSUE = 2900
SCIENTIFIC_PARENT_ISSUE = 2211
TRIGGERING_PHYSICAL_ISSUE = 2897
PREREGISTRATION_LABEL = "relaylm2-cognitive-ir-role-accessible-generic-v1"

FAMILY_COUNT = 24
SURFACES = (
    "TYPED_MEMORY_STRUCTURE",
    "GENERIC_ROLE_FUNCTIONAL",
    "LEGACY_GENERIC_ROLE_NEUTRAL",
)
TYPED_SURFACE, ROLE_FUNCTIONAL_SURFACE, LEGACY_SURFACE = SURFACES

FORMATION_CALLS = FAMILY_COUNT
DOWNSTREAM_TARGET_CALLS = FAMILY_COUNT * len(SURFACES)
SEMANTIC_PROVIDER_CALLS = FORMATION_CALLS + DOWNSTREAM_TARGET_CALLS
INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL = _ESTABLISHED_INPUT_COUNTS_PER_CALL
SCIENTIFIC_INPUT_TOKEN_REQUESTS = (
    SEMANTIC_PROVIDER_CALLS * INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL
)

CONTEXT_LIMIT = 8192
MAX_OUTPUT_TOKENS = S3_R5_MAX_OUTPUT_TOKENS
TEMPERATURE = 0.0
REASONING = "none"
REQUEST_SEED = None
PARALLEL_SEMANTIC_SLOTS = 1
STREAM = False
ALPHA = 0.05
EXAMPLES_VISIBLE = 0
TARGET_STEP_INDEX = 0

GENERIC_CONTEXT_KEY = FUNCTION_CONTEXT_KEY
GENERIC_RELATION_KEYS = tuple(FUNCTION_RELATION_KEYS)
PRIVILEGED_ONTOLOGY_LABELS = ("memory", "structure", "crystal", "crystallized")

CONFIRMATORY_CONTRASTS = (
    "H1_TYPED_VS_ROLE_FUNCTIONAL_GENERIC",
    "H2_ROLE_FUNCTIONAL_VS_LEGACY_GENERIC",
)
DESCRIPTIVE_ONLY_CONTRAST = "T_VS_L_DESCRIPTIVE_ONLY"

FORBIDDEN_RESCUE_COUNTS: Mapping[str, int] = {
    "semantic_retry": 0,
    "replay": 0,
    "reseed": 0,
    "fallback": 0,
    "hidden_repair": 0,
    "judge": 0,
}
PHYSICAL_EXECUTION_AUTHORIZED = False
ARCHITECTURE_CONSEQUENCE = "NONE"

FROZEN_SEEDS = (
    6276403570877362942,
    16646835369191652154,
    17451557426670770666,
    8605551150376748854,
    2797857429699198600,
    17574863390346769892,
    10746221780016842376,
    15296925114053318370,
    12163103898550334673,
    10167777586803268918,
    11540280064376697683,
    7919704239235549867,
    8391268104596340661,
    10686984440448687635,
    9794157743656523271,
    18257526278307268741,
    249688563448603309,
    5827486100102731877,
    7511732198909646689,
    5209041944142095853,
    16411447877057031301,
    1547189760059282007,
    4666269880306296807,
    1785040667075777081,
)

_HISTORICAL_ISSUE_IDENTITIES = frozenset(
    {
        2211,
        2634,
        2635,
        2658,
        2709,
        2722,
        2723,
        2768,
        2769,
        2774,
        2830,
        2831,
        2834,
        2837,
        2847,
        2848,
        2857,
        2871,
        2883,
        2884,
        2889,
        2897,
        2899,
        2900,
    }
)


class RoleAccessibleGenericError(ValueError):
    """The #2899 E5-RA1 preregistration cannot be bound exactly."""


def _json_text(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def derive_family_seed(index: int) -> int:
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < FAMILY_COUNT:
        raise RoleAccessibleGenericError("family index must be 0..23")
    digest = hashlib.sha256(
        f"{PREREGISTRATION_LABEL}|family|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "big")


def preregistered_seeds() -> tuple[int, ...]:
    return tuple(derive_family_seed(index) for index in range(FAMILY_COUNT))


def historical_family_seeds() -> frozenset[int]:
    return frozenset(
        {
            *_role_historical_family_seeds(),
            *_role_preregistered_seeds(),
            *_HISTORICAL_ISSUE_IDENTITIES,
        }
    )


def validate_seed_admission() -> None:
    seeds = preregistered_seeds()
    if seeds != FROZEN_SEEDS:
        raise RoleAccessibleGenericError("derived E5-RA1 seeds drifted from #2899")
    if len(seeds) != FAMILY_COUNT or len(set(seeds)) != FAMILY_COUNT:
        raise RoleAccessibleGenericError("E5-RA1 seeds are not exactly 24 unique values")
    overlap = sorted(set(seeds) & historical_family_seeds())
    if overlap:
        raise RoleAccessibleGenericError(
            f"E5-RA1 seeds overlap historical #2211 evidence: {overlap}"
        )


def _family_digest(seed: int, purpose: str) -> bytes:
    return hashlib.sha256(
        f"{PREREGISTRATION_LABEL}|shared|{seed}|{purpose}".encode("utf-8")
    ).digest()


def _k3_offsets(seed: int) -> tuple[int, ...]:
    ranked = sorted(
        range(s3_base.S3_VECTOR_WIDTH),
        key=lambda coordinate: (
            _family_digest(seed, f"active-rank:{coordinate}"),
            coordinate,
        ),
    )
    active = set(ranked[:3])
    offsets = tuple(
        1 + (_family_digest(seed, f"offset-value:{coordinate}")[0] % 3)
        if coordinate in active
        else 0
        for coordinate in range(s3_base.S3_VECTOR_WIDTH)
    )
    _require_k3_offsets(offsets)
    return offsets


def _require_k3_offsets(offsets: Sequence[int]) -> None:
    if len(tuple(offsets)) != 4:
        raise RoleAccessibleGenericError("K3 rule width drifted")
    active = [value for value in offsets if value != 0]
    if len(active) != 3 or any(value not in (1, 2, 3) for value in active):
        raise RoleAccessibleGenericError(
            "K3 rule must have exactly three active offsets in 1..3"
        )


def _bounded_vector(seed: int, purpose: str, offsets: tuple[int, ...]) -> tuple[int, ...]:
    raw = _family_digest(seed, purpose)
    return tuple(
        raw[coordinate] % (s3_base.S3_MODULUS - offsets[coordinate])
        for coordinate in range(s3_base.S3_VECTOR_WIDTH)
    )


def _generate_shared_family(seed: int) -> TransferFamily:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise RoleAccessibleGenericError("family seed must be a non-negative integer")
    offsets = _k3_offsets(seed)
    rule = VectorRule(tuple(range(4)), offsets, s3_base.S3_MODULUS)
    source_examples = tuple(
        PublicExample(
            values := _bounded_vector(seed, f"source:example:{index}", offsets),
            rule.apply(values),
        )
        for index in range(s3_base.S3_SOURCE_EXAMPLES)
    )
    target_steps = tuple(
        TargetStep(
            examples=tuple(
                PublicExample(
                    values := _bounded_vector(
                        seed,
                        f"target:{step_index}:example:{example_index}",
                        offsets,
                    ),
                    rule.apply(values),
                )
                for example_index in range(3)
            ),
            query=_bounded_vector(seed, f"target:{step_index}:query", offsets),
        )
        for step_index in range(s3_base.S3_TARGET_STEPS)
    )
    family = TransferFamily(
        seed=seed,
        regime="shared",
        modulus=s3_base.S3_MODULUS,
        source_rule=rule,
        target_rules=(rule,) * s3_base.S3_TARGET_STEPS,
        source_examples=source_examples,
        target_steps=target_steps,
        shift_index=None,
    )
    _require_k3_offsets(family.source_rule.offsets)
    if any(target_rule != family.source_rule for target_rule in family.target_rules):
        raise RoleAccessibleGenericError("F_SHARED target rule drifted from source rule")
    vectors = [example.input_values for example in family.source_examples]
    for step in family.target_steps:
        vectors.extend(example.input_values for example in step.examples)
        vectors.append(step.query)
    if any(
        vector[index] + offsets[index] >= family.modulus
        for vector in vectors
        for index in range(4)
    ):
        raise RoleAccessibleGenericError("generated E5-RA1 family unexpectedly wraps")
    return family


def generate_synthetic_shared_family(seed: int) -> TransferFamily:
    validate_seed_admission()
    if seed in set(preregistered_seeds()):
        raise RoleAccessibleGenericError(
            "synthetic helper cannot materialize a preregistered E5-RA1 seed"
        )
    return _generate_shared_family(seed)


def build_formation_messages(family: TransferFamily) -> tuple[dict[str, str], ...]:
    return _build_s2_formation_messages("P4_MEMORY_PLUS_STRUCTURE", family)


def parse_learned_rule_completion(
    completion: ExperimentCompletion,
    *,
    expected_modulus: int,
) -> dict[str, object]:
    return _parse_s2_learned_rule(completion, expected_modulus=expected_modulus)


def _require_integer_vector(value: object, *, label: str) -> list[int]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise RoleAccessibleGenericError(f"{label} must be an integer sequence")
    result = list(value)
    if len(result) != 4 or any(
        isinstance(item, bool) or not isinstance(item, int) for item in result
    ):
        raise RoleAccessibleGenericError(f"{label} must contain exactly four integers")
    return result


def _canonical_truth(
    learned_rule: Mapping[str, object],
    provenance_handles: Sequence[str],
) -> dict[str, object]:
    permutation = _require_integer_vector(
        learned_rule.get("permutation"), label="permutation"
    )
    if sorted(permutation) != [0, 1, 2, 3]:
        raise RoleAccessibleGenericError("permutation must be a bijection")
    offsets = _require_integer_vector(learned_rule.get("offsets"), label="offsets")
    modulus = learned_rule.get("modulus")
    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus <= 1:
        raise RoleAccessibleGenericError("modulus must be an integer greater than one")
    if any(value < 0 or value >= modulus for value in offsets):
        raise RoleAccessibleGenericError("offsets must be inside the modulus")
    handles = list(provenance_handles)
    if not handles or any(
        not isinstance(handle, str) or not handle for handle in handles
    ):
        raise RoleAccessibleGenericError("provenance handles must be non-empty strings")
    return {
        "operation": "affine_permutation",
        "permutation": permutation,
        "offsets": offsets,
        "modulus": modulus,
        "provenance_handles": handles,
    }


def _typed_payload(truth: Mapping[str, object]) -> dict[str, object]:
    return {
        "memory": {"origin_refs": list(truth["provenance_handles"])},
        "structure": {
            "operation": truth["operation"],
            "permutation": list(truth["permutation"]),
            "offsets": list(truth["offsets"]),
            "modulus": truth["modulus"],
        },
    }


def _role_functional_payload(truth: Mapping[str, object]) -> dict[str, object]:
    return {
        "context": {GENERIC_CONTEXT_KEY: list(truth["provenance_handles"])},
        "relation": {
            "transform_kind": truth["operation"],
            "index_reordering": list(truth["permutation"]),
            "additive_shifts": list(truth["offsets"]),
            "modular_divisor": truth["modulus"],
        },
    }


def decode_surface(surface: str, payload: Mapping[str, object]) -> dict[str, object]:
    if surface == TYPED_SURFACE:
        memory = payload.get("memory")
        structure = payload.get("structure")
        if not isinstance(memory, Mapping) or not isinstance(structure, Mapping):
            raise RoleAccessibleGenericError(
                "typed payload must contain memory/structure objects"
            )
        if set(payload) != {"memory", "structure"}:
            raise RoleAccessibleGenericError(
                "typed payload must contain exactly memory/structure"
            )
        if set(memory) != {"origin_refs"} or set(structure) != {
            "operation",
            "permutation",
            "offsets",
            "modulus",
        }:
            raise RoleAccessibleGenericError("typed P4 field vocabulary drifted")
        return {
            "operation": structure["operation"],
            "permutation": list(structure["permutation"]),
            "offsets": list(structure["offsets"]),
            "modulus": structure["modulus"],
            "provenance_handles": list(memory["origin_refs"]),
        }
    if surface == ROLE_FUNCTIONAL_SURFACE:
        context = payload.get("context")
        relation = payload.get("relation")
        if not isinstance(context, Mapping) or not isinstance(relation, Mapping):
            raise RoleAccessibleGenericError(
                "role-functional payload must contain context/relation"
            )
        if set(context) != {GENERIC_CONTEXT_KEY} or set(relation) != set(
            GENERIC_RELATION_KEYS
        ):
            raise RoleAccessibleGenericError("role-functional field vocabulary drifted")
        return {
            "operation": relation["transform_kind"],
            "permutation": list(relation["index_reordering"]),
            "offsets": list(relation["additive_shifts"]),
            "modulus": relation["modular_divisor"],
            "provenance_handles": list(context[GENERIC_CONTEXT_KEY]),
        }
    if surface == LEGACY_SURFACE:
        context = payload.get("context")
        relation = payload.get("relation")
        if not isinstance(context, Mapping) or not isinstance(relation, Mapping):
            raise RoleAccessibleGenericError("legacy payload must contain context/relation")
        if set(context) != {"refs"} or set(relation) != {"kind", "a", "b", "n"}:
            raise RoleAccessibleGenericError("legacy P6 field vocabulary drifted")
        return {
            "operation": relation["kind"],
            "permutation": list(relation["a"]),
            "offsets": list(relation["b"]),
            "modulus": relation["n"],
            "provenance_handles": list(context["refs"]),
        }
    raise RoleAccessibleGenericError(f"unsupported E5-RA1 surface: {surface}")


def _semantic_digest(truth: Mapping[str, object]) -> str:
    return hashlib.sha256(_json_text(truth).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RoleAccessibleRepresentations:
    canonical_truth: Mapping[str, object]
    semantic_digest: str
    serialized_by_surface: Mapping[str, str]
    provenance_handles: tuple[str, ...]


def prepare_synthetic_representations(
    *,
    seed: int,
    learned_rule: Mapping[str, object],
    provenance_handles: Sequence[str],
) -> RoleAccessibleRepresentations:
    validate_seed_admission()
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise RoleAccessibleGenericError("synthetic seed must be a non-negative integer")
    if seed in set(preregistered_seeds()):
        raise RoleAccessibleGenericError(
            "synthetic helper cannot materialize a preregistered E5-RA1 seed"
        )
    truth = _canonical_truth(learned_rule, provenance_handles)
    typed = _typed_payload(truth)
    role_functional = _role_functional_payload(truth)
    legacy = neutralize_typed_payload(typed)
    payloads = {
        TYPED_SURFACE: typed,
        ROLE_FUNCTIONAL_SURFACE: role_functional,
        LEGACY_SURFACE: legacy,
    }
    decoded = {
        surface: decode_surface(surface, payload)
        for surface, payload in payloads.items()
    }
    if any(value != truth for value in decoded.values()):
        raise RoleAccessibleGenericError("T/G/L decoded semantics or provenance differ")
    if _historical_semantic_digest(
        "P4_MEMORY_PLUS_STRUCTURE", typed
    ) != _historical_semantic_digest("P6_GENERIC_EQUAL_INFORMATION", legacy):
        raise RoleAccessibleGenericError("historical P4/P6 semantic digest drifted")
    serialized = {
        surface: _json_text(payload) for surface, payload in payloads.items()
    }
    if len(set(serialized.values())) != len(SURFACES):
        raise RoleAccessibleGenericError("T/G/L literal representations must be distinct")
    lowered_generic_keys = " ".join(
        [GENERIC_CONTEXT_KEY, *GENERIC_RELATION_KEYS]
    ).lower()
    if any(label in lowered_generic_keys for label in PRIVILEGED_ONTOLOGY_LABELS):
        raise RoleAccessibleGenericError(
            "generic role-functional surface leaked ontology labels"
        )
    return RoleAccessibleRepresentations(
        canonical_truth=truth,
        semantic_digest=_semantic_digest(truth),
        serialized_by_surface=serialized,
        provenance_handles=tuple(truth["provenance_handles"]),
    )


def _representation_for_target(
    surface: str,
    prepared: RoleAccessibleRepresentations,
) -> S2Representation:
    if surface not in SURFACES:
        raise RoleAccessibleGenericError(f"unsupported target surface: {surface}")
    return S2Representation(
        kind=surface,
        serialized=prepared.serialized_by_surface[surface],
        provenance_handles=prepared.provenance_handles,
        reconstruction_handles=prepared.provenance_handles,
        formation_completion=None,
        formation_calls=1,
        formation_input_tokens=0,
        formation_output_tokens=0,
    )


def build_target_messages(
    surface: str,
    prepared: RoleAccessibleRepresentations,
    family: TransferFamily,
):
    return _build_s2_target_messages(
        _representation_for_target(surface, prepared),
        family,
        step_index=TARGET_STEP_INDEX,
        examples_visible=EXAMPLES_VISIBLE,
    )


def semantic_call_plan() -> tuple[tuple[int, int, str], ...]:
    validate_seed_admission()
    plan: list[tuple[int, int, str]] = []
    for index, seed in enumerate(preregistered_seeds()):
        plan.append((index, seed, "FORM_P4"))
        plan.extend((index, seed, surface) for surface in SURFACES)
    if len(plan) != SEMANTIC_PROVIDER_CALLS:
        raise RoleAccessibleGenericError("semantic provider call ledger drifted")
    return tuple(plan)


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


def paired_table(outcomes: Sequence[tuple[bool, bool]]) -> PairedTable:
    return _paired_table(outcomes)


def exact_two_sided_sign_p(table: PairedTable) -> float:
    return _exact_two_sided_sign_p(table)


def holm_bonferroni(
    raw_p_values: Mapping[str, float],
) -> dict[str, tuple[float, bool]]:
    if set(raw_p_values) != set(CONFIRMATORY_CONTRASTS):
        raise RoleAccessibleGenericError(
            "Holm correction requires exactly E5-RA1 H1/H2"
        )
    ordered = sorted(raw_p_values.items(), key=lambda item: (item[1], item[0]))
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p_value) in enumerate(ordered):
        if not isinstance(p_value, (int, float)) or not 0.0 <= float(p_value) <= 1.0:
            raise RoleAccessibleGenericError("p-values must lie in [0,1]")
        candidate = min(1.0, (len(ordered) - rank) * float(p_value))
        running = max(running, candidate)
        adjusted[name] = running
    reject: dict[str, bool] = {}
    still_rejecting = True
    for rank, (name, p_value) in enumerate(ordered):
        threshold = ALPHA / (len(ordered) - rank)
        decision = still_rejecting and float(p_value) <= threshold
        reject[name] = decision
        if not decision:
            still_rejecting = False
    return {
        name: (adjusted[name], reject[name]) for name in CONFIRMATORY_CONTRASTS
    }


def confirmatory_analysis(
    *,
    h1_typed_vs_role_functional: Sequence[tuple[bool, bool]],
    h2_role_functional_vs_legacy: Sequence[tuple[bool, bool]],
) -> dict[str, ConfirmatoryContrast]:
    tables = {
        CONFIRMATORY_CONTRASTS[0]: paired_table(h1_typed_vs_role_functional),
        CONFIRMATORY_CONTRASTS[1]: paired_table(h2_role_functional_vs_legacy),
    }
    raw = {
        name: exact_two_sided_sign_p(table) for name, table in tables.items()
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


def descriptive_typed_vs_legacy(
    outcomes: Sequence[tuple[bool, bool]],
) -> PairedTable:
    return paired_table(outcomes)


def validate_repository_binding() -> None:
    validate_seed_admission()
    if tuple(SURFACES) != (
        "TYPED_MEMORY_STRUCTURE",
        "GENERIC_ROLE_FUNCTIONAL",
        "LEGACY_GENERIC_ROLE_NEUTRAL",
    ):
        raise RoleAccessibleGenericError("E5-RA1 surface order drifted")
    if GENERIC_CONTEXT_KEY != "source_handles" or GENERIC_RELATION_KEYS != (
        "transform_kind",
        "index_reordering",
        "additive_shifts",
        "modular_divisor",
    ):
        raise RoleAccessibleGenericError("E5-RA1 role-functional vocabulary drifted")
    if (
        FORMATION_CALLS,
        DOWNSTREAM_TARGET_CALLS,
        SEMANTIC_PROVIDER_CALLS,
        INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL,
        SCIENTIFIC_INPUT_TOKEN_REQUESTS,
    ) != (24, 72, 96, 2, 192):
        raise RoleAccessibleGenericError("E5-RA1 provider/input-count ledger drifted")
    if (
        s3_base.S3_VECTOR_WIDTH,
        s3_base.S3_MODULUS,
        s3_base.S3_SOURCE_EXAMPLES,
        s3_base.S3_TARGET_STEPS,
        EXAMPLES_VISIBLE,
    ) != (4, 10, 4, 4, 0):
        raise RoleAccessibleGenericError("E5-RA1 inherited K3 task geometry drifted")
    if (
        CONTEXT_LIMIT,
        MAX_OUTPUT_TOKENS,
        TEMPERATURE,
        REASONING,
        REQUEST_SEED,
        PARALLEL_SEMANTIC_SLOTS,
        STREAM,
    ) != (8192, 1024, 0.0, "none", None, 1, False):
        raise RoleAccessibleGenericError("E5-RA1 runtime class drifted")
    if any(FORBIDDEN_RESCUE_COUNTS.values()):
        raise RoleAccessibleGenericError("E5-RA1 rescue counters must remain zero")
    if PHYSICAL_EXECUTION_AUTHORIZED or ARCHITECTURE_CONSEQUENCE != "NONE":
        raise RoleAccessibleGenericError("E5-RA1 repository binding exceeded authority")
    plan = semantic_call_plan()
    for family_index in range(FAMILY_COUNT):
        chunk = plan[family_index * 4 : family_index * 4 + 4]
        if tuple(item[2] for item in chunk) != ("FORM_P4", *SURFACES):
            raise RoleAccessibleGenericError("E5-RA1 per-family call order drifted")
