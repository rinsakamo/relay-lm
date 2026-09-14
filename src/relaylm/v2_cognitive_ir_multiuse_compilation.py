from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math

import relaylm.v2_cognitive_ir_s3 as s3_base
from relaylm.v2_cognitive_ir_actual_model import (
    S2Representation,
    S2TargetPrompt,
    _parse_learned_rule,
    _parse_text_representation,
    _source_records,
    build_s2_formation_messages,
    build_s2_target_messages,
)
from relaylm.v2_cognitive_ir_p2_boundedness_qual_v2 import (
    P2_BOUNDEDNESS_HARD_MAX_CHARACTERS,
    P2_BOUNDEDNESS_HARD_MAX_WORDS,
    P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS,
    P2_BOUNDEDNESS_TARGET_MAX_WORDS,
    P2_BOUNDEDNESS_TARGET_MIN_WORDS,
    build_margin_p2_formation_messages,
)
from relaylm.v2_cognitive_ir_role_accessible_generic import (
    GENERIC_CONTEXT_KEY,
    GENERIC_RELATION_KEYS,
    INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL,
    PRIVILEGED_ONTOLOGY_LABELS,
    historical_family_seeds as _e5_historical_family_seeds,
    preregistered_seeds as _e5_preregistered_seeds,
)
from relaylm.v2_cognitive_ir_s3_r5 import S3_R5_MAX_OUTPUT_TOKENS
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from relaylm.v2_transfer_experiment import (
    PublicExample,
    TargetStep,
    TransferFamily,
    VectorRule,
)

PREREGISTRATION_ISSUE = 2918
REPOSITORY_BINDING_ISSUE = 2919
SCIENTIFIC_PARENT_ISSUE = 2211
TRIGGERING_PHYSICAL_ISSUE = 2914
PREREGISTRATION_LABEL = "relaylm2-cognitive-ir-multiuse-compilation-v1"

FAMILY_COUNT = 24
FUTURE_PROBES_PER_FAMILY = 3
ARMS = (
    "DIRECT_RETRIEVAL",
    "STRONG_ORDINARY_SUMMARY",
    "SEMANTIC_CACHE",
    "GENERIC_ROLE_FUNCTIONAL_REUSABLE_RULE",
)
RETRIEVAL_ARM, SUMMARY_ARM, CACHE_ARM, RULE_ARM = ARMS

FORMATION_PHASES = ("FORM_S", "FORM_C", "FORM_K")
FORMATION_CALLS_PER_FAMILY = len(FORMATION_PHASES)
DOWNSTREAM_CALLS_PER_FAMILY = FUTURE_PROBES_PER_FAMILY * len(ARMS)
SEMANTIC_CALLS_PER_FAMILY = FORMATION_CALLS_PER_FAMILY + DOWNSTREAM_CALLS_PER_FAMILY
FORMATION_CALLS = FAMILY_COUNT * FORMATION_CALLS_PER_FAMILY
DOWNSTREAM_TARGET_CALLS = FAMILY_COUNT * DOWNSTREAM_CALLS_PER_FAMILY
SEMANTIC_PROVIDER_CALLS = FAMILY_COUNT * SEMANTIC_CALLS_PER_FAMILY
SCIENTIFIC_INPUT_TOKEN_REQUESTS = (
    SEMANTIC_PROVIDER_CALLS * INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL
)
MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS = 2

CONTEXT_LIMIT = 8192
MAX_OUTPUT_TOKENS = S3_R5_MAX_OUTPUT_TOKENS
TEMPERATURE = 0.0
REASONING = "none"
REQUEST_SEED = None
PARALLEL_SEMANTIC_SLOTS = 1
STREAM = False
EXAMPLES_VISIBLE = 0
ALPHA = 0.05

CONFIRMATORY_CONTRASTS = (
    "H1_RULE_VS_STRONG_SUMMARY",
    "H2_RULE_VS_SEMANTIC_CACHE",
)
DESCRIPTIVE_ONLY_CONTRASTS = (
    "RULE_VS_DIRECT_RETRIEVAL_DESCRIPTIVE_ONLY",
    "SUMMARY_VS_CACHE_DESCRIPTIVE_ONLY",
)

TERMINAL_COMPLETED_CLASSES = (
    "REUSABLE_RULE_ADVANTAGE_OVER_SUMMARY_AND_CACHE_DETECTED",
    "REUSABLE_RULE_ADVANTAGE_OVER_SUMMARY_ONLY_DETECTED",
    "REUSABLE_RULE_ADVANTAGE_OVER_CACHE_ONLY_DETECTED",
    "NO_DECLARED_REUSABLE_RULE_ADVANTAGE_DETECTED_AT_THIS_RESOLUTION",
)
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
    18242921196994509208,
    16456503148984747803,
    2564685835201502214,
    99480840271871327,
    15860683760357431997,
    9104597987360713431,
    1684813114263491166,
    16982997413947470597,
    15028261200121275887,
    3882608319091680307,
    13870060799298746367,
    16919662656960685517,
    2233445219633372550,
    5758242852118234026,
    7791868629730920098,
    13217728925700133977,
    14156915422322261787,
    18152737992888522041,
    17756738490386248485,
    13457927886184389722,
    2540459244506115119,
    12979080967736764596,
    10995171988923688105,
    13268585899915094553,
)

_HISTORICAL_ISSUE_IDENTITIES = frozenset(
    {
        2211,
        2533,
        2634,
        2658,
        2899,
        2900,
        2904,
        2914,
        2918,
        2919,
    }
)


class MultiuseCompilationError(ValueError):
    """The #2918 E6-CE1 preregistration cannot be bound exactly."""


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
        raise MultiuseCompilationError("family index must be 0..23")
    digest = hashlib.sha256(
        f"{PREREGISTRATION_LABEL}|family|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "big")


def preregistered_seeds() -> tuple[int, ...]:
    return tuple(derive_family_seed(index) for index in range(FAMILY_COUNT))


def historical_family_seeds() -> frozenset[int]:
    return frozenset(
        {
            *_e5_historical_family_seeds(),
            *_e5_preregistered_seeds(),
            *_HISTORICAL_ISSUE_IDENTITIES,
        }
    )


def validate_seed_admission() -> None:
    seeds = preregistered_seeds()
    if seeds != FROZEN_SEEDS:
        raise MultiuseCompilationError("derived E6-CE1 seeds drifted from #2918")
    if len(seeds) != FAMILY_COUNT or len(set(seeds)) != FAMILY_COUNT:
        raise MultiuseCompilationError("E6-CE1 seeds are not exactly 24 unique values")
    overlap = sorted(set(seeds) & historical_family_seeds())
    if overlap:
        raise MultiuseCompilationError(
            f"E6-CE1 seeds overlap historical #2211 evidence: {overlap}"
        )


def _family_digest(family_index: int, seed: int, purpose: str) -> bytes:
    return hashlib.sha256(
        f"{PREREGISTRATION_LABEL}|{family_index}|{seed}|{purpose}".encode("utf-8")
    ).digest()


def _require_k3_offsets(offsets: Sequence[int]) -> tuple[int, ...]:
    result = tuple(offsets)
    if len(result) != 4:
        raise MultiuseCompilationError("K3 rule width drifted")
    active = [value for value in result if value != 0]
    if len(active) != 3 or any(value not in (1, 2, 3) for value in active):
        raise MultiuseCompilationError(
            "K3 rule must have exactly three active offsets in 1..3"
        )
    return result


def _k3_offsets(family_index: int, seed: int) -> tuple[int, ...]:
    ranked = sorted(
        range(s3_base.S3_VECTOR_WIDTH),
        key=lambda coordinate: (
            _family_digest(family_index, seed, f"active-rank:{coordinate}"),
            coordinate,
        ),
    )
    active = set(ranked[:3])
    offsets = tuple(
        1
        + (
            _family_digest(
                family_index,
                seed,
                f"offset-value:{coordinate}",
            )[0]
            % 3
        )
        if coordinate in active
        else 0
        for coordinate in range(s3_base.S3_VECTOR_WIDTH)
    )
    return _require_k3_offsets(offsets)


def _bounded_vector(
    family_index: int,
    seed: int,
    purpose: str,
    offsets: tuple[int, ...],
) -> tuple[int, ...]:
    raw = _family_digest(family_index, seed, purpose)
    return tuple(
        raw[coordinate] % (s3_base.S3_MODULUS - offsets[coordinate])
        for coordinate in range(s3_base.S3_VECTOR_WIDTH)
    )


def _distinct_probe_query(
    family_index: int,
    seed: int,
    probe_index: int,
    offsets: tuple[int, ...],
    previous: Sequence[tuple[int, ...]],
) -> tuple[int, ...]:
    if not 0 <= probe_index < FUTURE_PROBES_PER_FAMILY:
        raise MultiuseCompilationError("probe index must be 0..2")
    seen = set(previous)
    for attempt in range(64):
        query = _bounded_vector(
            family_index,
            seed,
            f"probe:{probe_index}:query:{attempt}",
            offsets,
        )
        if query not in seen:
            return query
    raise MultiuseCompilationError("failed to derive three distinct held-out queries")


def _generate_shared_family(family_index: int, seed: int) -> TransferFamily:
    if (
        isinstance(family_index, bool)
        or not isinstance(family_index, int)
        or not 0 <= family_index < FAMILY_COUNT
    ):
        raise MultiuseCompilationError("family index must be 0..23")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise MultiuseCompilationError("family seed must be a non-negative integer")

    offsets = _k3_offsets(family_index, seed)
    rule = VectorRule(tuple(range(4)), offsets, s3_base.S3_MODULUS)
    source_examples = tuple(
        PublicExample(
            values := _bounded_vector(
                family_index,
                seed,
                f"source:example:{example_index}",
                offsets,
            ),
            rule.apply(values),
        )
        for example_index in range(s3_base.S3_SOURCE_EXAMPLES)
    )

    target_steps: list[TargetStep] = []
    previous_queries: list[tuple[int, ...]] = []
    for probe_index in range(FUTURE_PROBES_PER_FAMILY):
        examples = tuple(
            PublicExample(
                values := _bounded_vector(
                    family_index,
                    seed,
                    f"probe:{probe_index}:example:{example_index}",
                    offsets,
                ),
                rule.apply(values),
            )
            for example_index in range(3)
        )
        query = _distinct_probe_query(
            family_index,
            seed,
            probe_index,
            offsets,
            previous_queries,
        )
        previous_queries.append(query)
        target_steps.append(TargetStep(examples=examples, query=query))

    family = TransferFamily(
        seed=seed,
        regime="shared",
        modulus=s3_base.S3_MODULUS,
        source_rule=rule,
        target_rules=(rule,) * FUTURE_PROBES_PER_FAMILY,
        source_examples=source_examples,
        target_steps=tuple(target_steps),
        shift_index=None,
    )
    _require_family_geometry(family)
    return family


def _require_family_geometry(family: TransferFamily) -> None:
    if family.regime != "shared":
        raise MultiuseCompilationError("E6-CE1 requires F_SHARED")
    if family.modulus != 10:
        raise MultiuseCompilationError("E6-CE1 modulus drifted")
    if len(family.source_examples) != 4:
        raise MultiuseCompilationError("E6-CE1 source-example count drifted")
    if len(family.target_steps) != FUTURE_PROBES_PER_FAMILY:
        raise MultiuseCompilationError("E6-CE1 future-probe count drifted")
    if family.shift_index is not None:
        raise MultiuseCompilationError("E6-CE1 F_SHARED cannot carry a shift index")
    if family.source_rule.permutation != tuple(range(4)):
        raise MultiuseCompilationError("E6-CE1 permutation must remain identity")
    offsets = _require_k3_offsets(family.source_rule.offsets)
    if family.target_rules != (family.source_rule,) * FUTURE_PROBES_PER_FAMILY:
        raise MultiuseCompilationError("future probes drifted from the source rule")

    queries = tuple(step.query for step in family.target_steps)
    if len(set(queries)) != FUTURE_PROBES_PER_FAMILY:
        raise MultiuseCompilationError("future probe queries are not pairwise distinct")

    vectors = [example.input_values for example in family.source_examples]
    for step in family.target_steps:
        vectors.extend(example.input_values for example in step.examples)
        vectors.append(step.query)
    if any(
        vector[index] + offsets[index] >= family.modulus
        for vector in vectors
        for index in range(4)
    ):
        raise MultiuseCompilationError("generated E6-CE1 family unexpectedly wraps")


def generate_synthetic_shared_family(
    family_index: int,
    seed: int,
) -> TransferFamily:
    validate_seed_admission()
    if seed in set(preregistered_seeds()):
        raise MultiuseCompilationError(
            "synthetic helper cannot materialize a preregistered E6-CE1 seed"
        )
    return _generate_shared_family(family_index, seed)


def build_summary_formation_messages(
    family: TransferFamily,
) -> tuple[dict[str, str], ...]:
    return build_margin_p2_formation_messages(family)


def build_cache_formation_messages(
    family: TransferFamily,
) -> tuple[dict[str, str], ...]:
    return build_s2_formation_messages("P3_SEMANTIC_CACHE", family)


def build_rule_formation_messages(
    family: TransferFamily,
) -> tuple[dict[str, str], ...]:
    return build_s2_formation_messages("P4_MEMORY_PLUS_STRUCTURE", family)


def formation_message_bundle(
    family: TransferFamily,
) -> Mapping[str, tuple[dict[str, str], ...]]:
    bundle = {
        SUMMARY_ARM: build_summary_formation_messages(family),
        CACHE_ARM: build_cache_formation_messages(family),
        RULE_ARM: build_rule_formation_messages(family),
    }
    user_messages = {messages[1]["content"] for messages in bundle.values()}
    if len(user_messages) != 1:
        raise MultiuseCompilationError(
            "S/C/K formation arms do not share one exact public source packet"
        )
    user_packet = json.loads(next(iter(user_messages)))
    if set(user_packet) != {"modulus", "examples"} or "query" in user_packet:
        raise MultiuseCompilationError("formation packet leaked future target material")
    return bundle


def parse_summary_completion(completion: ExperimentCompletion) -> str:
    return _parse_text_representation(completion, key="summary")


def parse_cache_completion(completion: ExperimentCompletion) -> str:
    return _parse_text_representation(completion, key="gist")


def parse_rule_completion(
    completion: ExperimentCompletion,
    *,
    expected_modulus: int,
) -> dict[str, object]:
    return _parse_learned_rule(completion, expected_modulus=expected_modulus)


def _provenance_handles(family: TransferFamily) -> tuple[str, ...]:
    records = _source_records(family)
    handles = tuple(str(record["ref"]) for record in records)
    if len(handles) != len(family.source_examples) or not handles:
        raise MultiuseCompilationError("public-source provenance identity drifted")
    return handles


def _direct_retrieval_serialized(family: TransferFamily) -> str:
    return _json_text({"records": list(_source_records(family))})


def _require_rule_payload(
    learned_rule: Mapping[str, object],
    provenance_handles: Sequence[str],
) -> dict[str, object]:
    permutation = learned_rule.get("permutation")
    offsets = learned_rule.get("offsets")
    modulus = learned_rule.get("modulus")
    if (
        not isinstance(permutation, list)
        or len(permutation) != 4
        or any(isinstance(value, bool) or not isinstance(value, int) for value in permutation)
        or sorted(permutation) != [0, 1, 2, 3]
    ):
        raise MultiuseCompilationError("learned permutation is invalid")
    if (
        not isinstance(offsets, list)
        or len(offsets) != 4
        or any(isinstance(value, bool) or not isinstance(value, int) for value in offsets)
    ):
        raise MultiuseCompilationError("learned offsets are invalid")
    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus <= 1:
        raise MultiuseCompilationError("learned modulus is invalid")
    if any(value < 0 or value >= modulus for value in offsets):
        raise MultiuseCompilationError("learned offsets escape modulus")
    handles = tuple(provenance_handles)
    if not handles or any(not isinstance(handle, str) or not handle for handle in handles):
        raise MultiuseCompilationError("provenance handles are invalid")
    return {
        "context": {GENERIC_CONTEXT_KEY: list(handles)},
        "relation": {
            "transform_kind": "affine_permutation",
            "index_reordering": list(permutation),
            "additive_shifts": list(offsets),
            "modular_divisor": modulus,
        },
    }


def _representation(
    *,
    kind: str,
    serialized: str,
    provenance_handles: tuple[str, ...],
    completion: ExperimentCompletion | None,
    formation_calls: int,
) -> S2Representation:
    return S2Representation(
        kind=kind,
        serialized=serialized,
        provenance_handles=provenance_handles,
        reconstruction_handles=provenance_handles,
        formation_completion=completion,
        formation_calls=formation_calls,
        formation_input_tokens=0 if completion is None else completion.input_tokens,
        formation_output_tokens=0 if completion is None else completion.output_tokens,
    )


@dataclass(frozen=True, slots=True)
class MultiuseRepresentations:
    by_arm: Mapping[str, S2Representation]
    provenance_handles: tuple[str, ...]
    rule_payload_digest: str

    def for_arm(self, arm: str) -> S2Representation:
        if arm not in ARMS:
            raise MultiuseCompilationError(f"unsupported E6-CE1 arm: {arm}")
        return self.by_arm[arm]


def prepare_representations(
    family: TransferFamily,
    *,
    summary_completion: ExperimentCompletion,
    cache_completion: ExperimentCompletion,
    rule_completion: ExperimentCompletion,
) -> MultiuseRepresentations:
    _require_family_geometry(family)
    provenance = _provenance_handles(family)
    summary_serialized = parse_summary_completion(summary_completion)
    cache_serialized = parse_cache_completion(cache_completion)
    learned_rule = parse_rule_completion(
        rule_completion,
        expected_modulus=family.modulus,
    )
    rule_payload = _require_rule_payload(learned_rule, provenance)
    lowered_keys = " ".join((GENERIC_CONTEXT_KEY, *GENERIC_RELATION_KEYS)).lower()
    if any(label in lowered_keys for label in PRIVILEGED_ONTOLOGY_LABELS):
        raise MultiuseCompilationError("K role-functional vocabulary leaked ontology labels")

    by_arm = {
        RETRIEVAL_ARM: _representation(
            kind=RETRIEVAL_ARM,
            serialized=_direct_retrieval_serialized(family),
            provenance_handles=provenance,
            completion=None,
            formation_calls=0,
        ),
        SUMMARY_ARM: _representation(
            kind=SUMMARY_ARM,
            serialized=summary_serialized,
            provenance_handles=provenance,
            completion=summary_completion,
            formation_calls=1,
        ),
        CACHE_ARM: _representation(
            kind=CACHE_ARM,
            serialized=cache_serialized,
            provenance_handles=provenance,
            completion=cache_completion,
            formation_calls=1,
        ),
        RULE_ARM: _representation(
            kind=RULE_ARM,
            serialized=_json_text(rule_payload),
            provenance_handles=provenance,
            completion=rule_completion,
            formation_calls=1,
        ),
    }
    if tuple(by_arm) != ARMS:
        raise MultiuseCompilationError("E6-CE1 arm order drifted")
    if len({representation.provenance_handles for representation in by_arm.values()}) != 1:
        raise MultiuseCompilationError("E6-CE1 arms do not share provenance identity")

    return MultiuseRepresentations(
        by_arm=by_arm,
        provenance_handles=provenance,
        rule_payload_digest=hashlib.sha256(
            _json_text(rule_payload).encode("utf-8")
        ).hexdigest(),
    )


def build_target_messages(
    arm: str,
    prepared: MultiuseRepresentations,
    family: TransferFamily,
    *,
    probe_index: int,
) -> S2TargetPrompt:
    if not 0 <= probe_index < FUTURE_PROBES_PER_FAMILY:
        raise MultiuseCompilationError("probe index must be 0..2")
    return build_s2_target_messages(
        prepared.for_arm(arm),
        family,
        step_index=probe_index,
        examples_visible=EXAMPLES_VISIBLE,
    )


def semantic_call_plan() -> tuple[tuple[int, int, str], ...]:
    validate_seed_admission()
    plan: list[tuple[int, int, str]] = []
    for family_index, seed in enumerate(preregistered_seeds()):
        plan.extend((family_index, seed, phase) for phase in FORMATION_PHASES)
        for probe_index in range(FUTURE_PROBES_PER_FAMILY):
            plan.extend(
                (family_index, seed, f"PROBE_{probe_index}_{arm}")
                for arm in ARMS
            )
    if len(plan) != SEMANTIC_PROVIDER_CALLS:
        raise MultiuseCompilationError("E6-CE1 semantic-call ledger drifted")
    return tuple(plan)


def future_success_count(outcomes: Sequence[bool]) -> int:
    if len(outcomes) != FUTURE_PROBES_PER_FAMILY:
        raise MultiuseCompilationError("each family/arm must have exactly three outcomes")
    if any(not isinstance(value, bool) for value in outcomes):
        raise MultiuseCompilationError("future-probe outcomes must be booleans")
    return sum(outcomes)


@dataclass(frozen=True, slots=True)
class FamilySignTable:
    left_higher: int
    right_higher: int
    tied: int
    differences: tuple[int, ...]

    @property
    def non_tied(self) -> int:
        return self.left_higher + self.right_higher


def family_sign_table(
    left_scores: Sequence[int],
    right_scores: Sequence[int],
) -> FamilySignTable:
    if len(left_scores) != FAMILY_COUNT or len(right_scores) != FAMILY_COUNT:
        raise MultiuseCompilationError("confirmatory analysis requires exactly 24 families")
    differences: list[int] = []
    left_higher = 0
    right_higher = 0
    tied = 0
    for left, right in zip(left_scores, right_scores, strict=True):
        if (
            isinstance(left, bool)
            or isinstance(right, bool)
            or not isinstance(left, int)
            or not isinstance(right, int)
            or not 0 <= left <= FUTURE_PROBES_PER_FAMILY
            or not 0 <= right <= FUTURE_PROBES_PER_FAMILY
        ):
            raise MultiuseCompilationError("family scores must be integers in 0..3")
        difference = left - right
        differences.append(difference)
        if difference > 0:
            left_higher += 1
        elif difference < 0:
            right_higher += 1
        else:
            tied += 1
    return FamilySignTable(
        left_higher=left_higher,
        right_higher=right_higher,
        tied=tied,
        differences=tuple(differences),
    )


def exact_one_sided_sign_p(table: FamilySignTable) -> float:
    non_tied = table.non_tied
    if non_tied == 0:
        return 1.0
    numerator = sum(
        math.comb(non_tied, wins)
        for wins in range(table.left_higher, non_tied + 1)
    )
    return numerator / (2**non_tied)


def holm_bonferroni(
    raw_p_values: Mapping[str, float],
) -> dict[str, tuple[float, bool]]:
    if set(raw_p_values) != set(CONFIRMATORY_CONTRASTS):
        raise MultiuseCompilationError("Holm correction requires exactly E6-CE1 H1/H2")
    ordered = sorted(raw_p_values.items(), key=lambda item: (float(item[1]), item[0]))
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p_value) in enumerate(ordered):
        if (
            isinstance(p_value, bool)
            or not isinstance(p_value, (int, float))
            or not 0.0 <= float(p_value) <= 1.0
        ):
            raise MultiuseCompilationError("p-values must lie in [0,1]")
        candidate = min(1.0, (len(ordered) - rank) * float(p_value))
        running = max(running, candidate)
        adjusted[name] = running

    rejecting = True
    rejected: dict[str, bool] = {}
    for rank, (name, p_value) in enumerate(ordered):
        threshold = ALPHA / (len(ordered) - rank)
        decision = rejecting and float(p_value) <= threshold
        rejected[name] = decision
        if not decision:
            rejecting = False
    return {
        name: (adjusted[name], rejected[name])
        for name in CONFIRMATORY_CONTRASTS
    }


@dataclass(frozen=True, slots=True)
class ConfirmatoryContrast:
    name: str
    table: FamilySignTable
    raw_p_value: float
    holm_adjusted_p_value: float
    holm_reject: bool


def confirmatory_analysis(
    *,
    rule_scores: Sequence[int],
    summary_scores: Sequence[int],
    cache_scores: Sequence[int],
) -> dict[str, ConfirmatoryContrast]:
    tables = {
        CONFIRMATORY_CONTRASTS[0]: family_sign_table(rule_scores, summary_scores),
        CONFIRMATORY_CONTRASTS[1]: family_sign_table(rule_scores, cache_scores),
    }
    raw = {name: exact_one_sided_sign_p(table) for name, table in tables.items()}
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


def descriptive_family_comparison(
    left_scores: Sequence[int],
    right_scores: Sequence[int],
) -> FamilySignTable:
    return family_sign_table(left_scores, right_scores)


def classify_completed_panel(
    analysis: Mapping[str, ConfirmatoryContrast],
) -> str:
    if set(analysis) != set(CONFIRMATORY_CONTRASTS):
        raise MultiuseCompilationError("completed-panel analysis must contain exactly H1/H2")
    h1 = analysis[CONFIRMATORY_CONTRASTS[0]].holm_reject
    h2 = analysis[CONFIRMATORY_CONTRASTS[1]].holm_reject
    if h1 and h2:
        return TERMINAL_COMPLETED_CLASSES[0]
    if h1:
        return TERMINAL_COMPLETED_CLASSES[1]
    if h2:
        return TERMINAL_COMPLETED_CLASSES[2]
    return TERMINAL_COMPLETED_CLASSES[3]


@dataclass(frozen=True, slots=True)
class Horizon3Work:
    formation_calls: int
    formation_input_tokens: int
    formation_output_tokens: int
    formation_wall_seconds: float
    retained_bytes: int
    projected_bytes_by_probe: tuple[int, int, int]
    target_calls: int
    target_input_tokens: int
    target_output_tokens: int
    target_wall_seconds: float

    def __post_init__(self) -> None:
        integer_fields = (
            self.formation_calls,
            self.formation_input_tokens,
            self.formation_output_tokens,
            self.retained_bytes,
            *self.projected_bytes_by_probe,
            self.target_calls,
            self.target_input_tokens,
            self.target_output_tokens,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in integer_fields
        ):
            raise MultiuseCompilationError("observable work integer components must be >= 0")
        if (
            isinstance(self.formation_wall_seconds, bool)
            or isinstance(self.target_wall_seconds, bool)
            or not isinstance(self.formation_wall_seconds, (int, float))
            or not isinstance(self.target_wall_seconds, (int, float))
            or self.formation_wall_seconds < 0
            or self.target_wall_seconds < 0
        ):
            raise MultiuseCompilationError("observable work wall times must be >= 0")

    def as_mapping(self) -> dict[str, object]:
        components: dict[str, object] = {
            "C_build": {
                "formation_calls": self.formation_calls,
                "formation_input_tokens": self.formation_input_tokens,
                "formation_output_tokens": self.formation_output_tokens,
                "formation_wall_seconds": float(self.formation_wall_seconds),
            },
            "C_store": {"retained_bytes": self.retained_bytes},
            "C_project": {
                "projected_bytes_by_probe": list(self.projected_bytes_by_probe),
            },
            "C_model": {
                "target_calls": self.target_calls,
                "target_input_tokens": self.target_input_tokens,
                "target_output_tokens": self.target_output_tokens,
                "target_wall_seconds": float(self.target_wall_seconds),
            },
        }
        return {
            **components,
            "C_total_horizon3": {
                "component_names": list(components),
                "scalarized": False,
            },
        }


def validate_repository_binding() -> None:
    validate_seed_admission()
    if tuple(ARMS) != (
        "DIRECT_RETRIEVAL",
        "STRONG_ORDINARY_SUMMARY",
        "SEMANTIC_CACHE",
        "GENERIC_ROLE_FUNCTIONAL_REUSABLE_RULE",
    ):
        raise MultiuseCompilationError("E6-CE1 arm order drifted")
    if tuple(FORMATION_PHASES) != ("FORM_S", "FORM_C", "FORM_K"):
        raise MultiuseCompilationError("E6-CE1 formation order drifted")
    if (
        FAMILY_COUNT,
        FUTURE_PROBES_PER_FAMILY,
        FORMATION_CALLS,
        DOWNSTREAM_TARGET_CALLS,
        SEMANTIC_PROVIDER_CALLS,
        INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL,
        SCIENTIFIC_INPUT_TOKEN_REQUESTS,
        MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS,
    ) != (24, 3, 72, 288, 360, 2, 720, 2):
        raise MultiuseCompilationError("E6-CE1 provider/input-count ledger drifted")
    if (
        s3_base.S3_VECTOR_WIDTH,
        s3_base.S3_MODULUS,
        s3_base.S3_SOURCE_EXAMPLES,
        EXAMPLES_VISIBLE,
    ) != (4, 10, 4, 0):
        raise MultiuseCompilationError("E6-CE1 inherited task geometry drifted")
    if (
        P2_BOUNDEDNESS_TARGET_MIN_WORDS,
        P2_BOUNDEDNESS_TARGET_MAX_WORDS,
        P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS,
        P2_BOUNDEDNESS_HARD_MAX_WORDS,
        P2_BOUNDEDNESS_HARD_MAX_CHARACTERS,
    ) != (60, 80, 550, 120, 800):
        raise MultiuseCompilationError("qualified strong-summary contract drifted")
    if GENERIC_CONTEXT_KEY != "source_handles" or tuple(GENERIC_RELATION_KEYS) != (
        "transform_kind",
        "index_reordering",
        "additive_shifts",
        "modular_divisor",
    ):
        raise MultiuseCompilationError("E5 role-functional vocabulary drifted")
    if (
        CONTEXT_LIMIT,
        MAX_OUTPUT_TOKENS,
        TEMPERATURE,
        REASONING,
        REQUEST_SEED,
        PARALLEL_SEMANTIC_SLOTS,
        STREAM,
    ) != (8192, 1024, 0.0, "none", None, 1, False):
        raise MultiuseCompilationError("E6-CE1 runtime class drifted")
    if tuple(CONFIRMATORY_CONTRASTS) != (
        "H1_RULE_VS_STRONG_SUMMARY",
        "H2_RULE_VS_SEMANTIC_CACHE",
    ):
        raise MultiuseCompilationError("E6-CE1 confirmatory contrasts drifted")
    if any(FORBIDDEN_RESCUE_COUNTS.values()):
        raise MultiuseCompilationError("E6-CE1 rescue counters must remain zero")
    if PHYSICAL_EXECUTION_AUTHORIZED or ARCHITECTURE_CONSEQUENCE != "NONE":
        raise MultiuseCompilationError("E6-CE1 repository binding exceeded authority")

    plan = semantic_call_plan()
    for family_index in range(FAMILY_COUNT):
        start = family_index * SEMANTIC_CALLS_PER_FAMILY
        chunk = plan[start : start + SEMANTIC_CALLS_PER_FAMILY]
        expected = (
            "FORM_S",
            "FORM_C",
            "FORM_K",
            "PROBE_0_DIRECT_RETRIEVAL",
            "PROBE_0_STRONG_ORDINARY_SUMMARY",
            "PROBE_0_SEMANTIC_CACHE",
            "PROBE_0_GENERIC_ROLE_FUNCTIONAL_REUSABLE_RULE",
            "PROBE_1_DIRECT_RETRIEVAL",
            "PROBE_1_STRONG_ORDINARY_SUMMARY",
            "PROBE_1_SEMANTIC_CACHE",
            "PROBE_1_GENERIC_ROLE_FUNCTIONAL_REUSABLE_RULE",
            "PROBE_2_DIRECT_RETRIEVAL",
            "PROBE_2_STRONG_ORDINARY_SUMMARY",
            "PROBE_2_SEMANTIC_CACHE",
            "PROBE_2_GENERIC_ROLE_FUNCTIONAL_REUSABLE_RULE",
        )
        if tuple(item[2] for item in chunk) != expected:
            raise MultiuseCompilationError("E6-CE1 per-family call order drifted")
        if len({item[0] for item in chunk}) != 1 or len({item[1] for item in chunk}) != 1:
            raise MultiuseCompilationError("E6-CE1 family identity drifted inside call plan")
