from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Protocol

from relaylm.v2_cognitive_ir_actual_model import (
    S2Representation,
    build_s2_target_messages,
    form_s2_representations,
)
from relaylm.v2_cognitive_ir_calibration import CALIBRATION_SEEDS
from relaylm.v2_cognitive_ir_calibration_v2 import CALIBRATION_V2_SEEDS
from relaylm.v2_cognitive_ir_experiment import (
    REPRESENTATION_KINDS,
    decode_semantic_payload,
    neutralize_typed_payload,
    semantic_digest,
)
from relaylm.v2_cognitive_ir_s2_selected import S2_SELECTED_SEED
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from relaylm.v2_transfer_experiment import (
    PublicExample,
    TargetStep,
    TransferFamily,
    VectorRule,
)


S3_PREREGISTRATION_SCHEMA = "relaylm2-cognitive-ir-s3-prereg-v1"
S3_PREREGISTRATION_SHA256 = (
    "2448d147e8bbb1ab17446fbc54e464fa6d8746a18d19fad7f92627a039384c69"
)
S3_LABEL = "relaylm2-cognitive-ir-s3-semantic-invariance-v1"
S3_REGIMES = ("shared", "null", "mismatch", "shift")
S3_SEEDS: Mapping[str, tuple[int, ...]] = {
    "shared": (408671368, 1152794703, 2087212991),
    "null": (292304948, 865761977, 509247258),
    "mismatch": (1201776179, 630460040, 1118062807),
    "shift": (5662972, 445070522, 1853464615),
}
S3_MODULUS = 10
S3_VECTOR_WIDTH = 4
S3_SOURCE_EXAMPLES = 4
S3_TARGET_STEPS = 4
S3_SHIFT_INDEX = 2
S3_EXAMPLES_VISIBLE = 0
S3_SURFACE_VARIANTS = (
    "S1_ROLE_LABEL_NEUTRAL",
    "S2_KEY_RENAME_REORDER",
    "S3_LOSSLESS_LIST_PROSE_SERIALIZATION",
    "S4_PROMPT_PARAPHRASE_FORMAT",
)
S3_SEMANTIC_INTERVENTIONS = (
    "M1_RULE_OFFSET_FLIP",
    "M2_EXCEPTION_CHANGE",
    "M3_SCOPE_CHANGE",
    "M4_RELATION_REPLACE",
)
S3_TYPED_GENERIC_ARMS = (
    "P4_MEMORY_PLUS_STRUCTURE",
    "P6_GENERIC_EQUAL_INFORMATION",
)
S3_SHARD_CALLS: Mapping[str, int] = {
    "shared": 123,
    "null": 123,
    "mismatch": 123,
    "shift": 129,
}
S3_TOTAL_SEMANTIC_CALLS = 498
S3_TOTAL_INPUT_TOKEN_REQUESTS = 996
S3_SURFACE_EFFECT_MAX = 0.15
S3_SEMANTIC_EFFECT_MIN = 0.20
S3_EFFECT_MARGIN_MIN = 0.15
S3_CLAIM = "CITABLE_S3_WITHIN_DECLARED_SCOPE"
S3_INCOMPLETE_CLAIM = "S3_INCOMPLETE"


class S3ExperimentError(ValueError):
    """The frozen #2211 S3 preregistration contract was violated."""


class S3Client(Protocol):
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


def _json_text(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _seed_bytes(seed: int, label: str) -> bytes:
    return hashlib.sha256(f"{S3_LABEL}|{seed}|{label}".encode("utf-8")).digest()


def derive_s3_seed(regime: str, index: int) -> int:
    if regime not in S3_REGIMES:
        raise S3ExperimentError(f"unsupported S3 regime: {regime}")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 3:
        raise S3ExperimentError("S3 seed index must be 0..2")
    raw = hashlib.sha256(f"{S3_LABEL}|{regime}|seed|{index}".encode("utf-8")).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def validate_frozen_seeds() -> None:
    derived = {
        regime: tuple(derive_s3_seed(regime, index) for index in range(3))
        for regime in S3_REGIMES
    }
    if derived != dict(S3_SEEDS):
        raise S3ExperimentError("derived S3 seeds drifted from frozen preregistration")
    flattened = tuple(seed for regime in S3_REGIMES for seed in S3_SEEDS[regime])
    if len(set(flattened)) != 12:
        raise S3ExperimentError("S3 seeds are not unique")
    forbidden = {2211, S2_SELECTED_SEED, *CALIBRATION_SEEDS, *CALIBRATION_V2_SEEDS}
    overlap = sorted(set(flattened) & forbidden)
    if overlap:
        raise S3ExperimentError(f"S3 seeds overlap historical evidence: {overlap}")


def _offsets(seed: int, label: str) -> tuple[int, ...]:
    return tuple(1 + (_seed_bytes(seed, f"{label}:offset:{index}")[0] % 3) for index in range(4))


def _distinct_offsets(seed: int, label: str, source: tuple[int, ...]) -> tuple[int, ...]:
    for attempt in range(32):
        candidate = _offsets(seed, f"{label}:{attempt}")
        if candidate != source:
            return candidate
    raise S3ExperimentError("failed to derive distinct identity+offset target rule")


def _rule(offsets: tuple[int, ...]) -> VectorRule:
    return VectorRule(tuple(range(S3_VECTOR_WIDTH)), offsets, S3_MODULUS)


def _bounded_vector(seed: int, label: str, *rules: VectorRule) -> tuple[int, ...]:
    raw = _seed_bytes(seed, label)
    maxima = [S3_MODULUS - 1] * S3_VECTOR_WIDTH
    for rule in rules:
        for output_index, input_index in enumerate(rule.permutation):
            maxima[input_index] = min(
                maxima[input_index],
                rule.modulus - 1 - rule.offsets[output_index],
            )
    return tuple(raw[index] % (maxima[index] + 1) for index in range(S3_VECTOR_WIDTH))


def _examples(seed: int, label: str, rule: VectorRule, *bounds: VectorRule) -> tuple[PublicExample, ...]:
    all_bounds = (rule, *bounds)
    return tuple(
        PublicExample(
            values := _bounded_vector(seed, f"{label}:example:{index}", *all_bounds),
            rule.apply(values),
        )
        for index in range(S3_SOURCE_EXAMPLES)
    )


def _target_step(seed: int, index: int, rule: VectorRule, *bounds: VectorRule) -> TargetStep:
    all_bounds = (rule, *bounds)
    examples = tuple(
        PublicExample(
            values := _bounded_vector(
                seed,
                f"target:{index}:example:{example_index}",
                *all_bounds,
            ),
            rule.apply(values),
        )
        for example_index in range(3)
    )
    query = _bounded_vector(seed, f"target:{index}:query", *all_bounds)
    return TargetStep(examples=examples, query=query)


def generate_s3_family(regime: str, index: int) -> TransferFamily:
    validate_frozen_seeds()
    seed = S3_SEEDS[regime][index]
    source_offsets = _offsets(seed, "source")
    source_rule = _rule(source_offsets)

    if regime == "shared":
        target_rule = source_rule
        target_rules = (target_rule,) * S3_TARGET_STEPS
        shift_index = None
    elif regime == "null":
        target_rule = _rule(_distinct_offsets(seed, "null-target", source_offsets))
        target_rules = (target_rule,) * S3_TARGET_STEPS
        shift_index = None
    elif regime == "mismatch":
        mismatch = list(source_offsets)
        mismatch[0] = (mismatch[0] % 3) + 1
        target_rule = _rule(tuple(mismatch))
        target_rules = (target_rule,) * S3_TARGET_STEPS
        shift_index = None
    elif regime == "shift":
        post_rule = _rule(_distinct_offsets(seed, "shift-target", source_offsets))
        target_rules = (source_rule, source_rule, post_rule, post_rule)
        shift_index = S3_SHIFT_INDEX
    else:
        raise S3ExperimentError(f"unsupported S3 regime: {regime}")

    bounds = tuple(dict.fromkeys(target_rules))
    source_examples = _examples(seed, "source", source_rule, *bounds)
    target_steps = tuple(
        _target_step(seed, step_index, rule, source_rule, *bounds)
        for step_index, rule in enumerate(target_rules)
    )
    family = TransferFamily(
        seed=seed,
        regime=regime,
        modulus=S3_MODULUS,
        source_rule=source_rule,
        target_rules=target_rules,
        source_examples=source_examples,
        target_steps=target_steps,
        shift_index=shift_index,
    )
    _require_no_wrap(family)
    return family


def _require_no_wrap(family: TransferFamily) -> None:
    for example in family.source_examples:
        if any(
            example.input_values[index] + family.source_rule.offsets[index] >= S3_MODULUS
            for index in range(S3_VECTOR_WIDTH)
        ):
            raise S3ExperimentError("S3 source example unexpectedly wraps")
    for step_index, step in enumerate(family.target_steps):
        rule = family.target_rules[step_index]
        values = [item.input_values for item in step.examples] + [step.query]
        if any(
            value[index] + rule.offsets[index] >= S3_MODULUS
            for value in values
            for index in range(S3_VECTOR_WIDTH)
        ):
            raise S3ExperimentError("S3 target example/query unexpectedly wraps")


def primary_step_index(family: TransferFamily) -> int:
    return S3_SHIFT_INDEX if family.regime == "shift" else 0


def pre_shift_anchor_step_index(family: TransferFamily) -> int | None:
    return S3_SHIFT_INDEX - 1 if family.regime == "shift" else None


@dataclass(frozen=True, slots=True)
class S3SurfaceMaterial:
    serialized: str
    canonical_semantics: dict[str, object]
    prompt_variant: str


def _canonical_semantics(representation: S2Representation) -> dict[str, object]:
    if representation.kind not in S3_TYPED_GENERIC_ARMS:
        raise S3ExperimentError("surface/semantic panel requires P4 or P6")
    payload = json.loads(representation.serialized)
    if not isinstance(payload, Mapping):
        raise S3ExperimentError("P4/P6 representation must decode to an object")
    decoded = decode_semantic_payload(representation.kind, payload)
    return dict(decoded)


def _typed_from_semantics(semantics: Mapping[str, object]) -> dict[str, object]:
    return {
        "memory": {"origin_refs": list(semantics["provenance_handles"])},
        "structure": {
            "operation": semantics["operation"],
            "permutation": list(semantics["permutation"]),
            "offsets": list(semantics["offsets"]),
            "modulus": semantics["modulus"],
        },
    }


def _generic_from_semantics(semantics: Mapping[str, object]) -> dict[str, object]:
    return neutralize_typed_payload(_typed_from_semantics(semantics))


def render_s3_surface_variant(
    representation: S2Representation,
    variant: str,
) -> S3SurfaceMaterial:
    if variant not in S3_SURFACE_VARIANTS:
        raise S3ExperimentError(f"unsupported S3 surface variant: {variant}")
    semantics = _canonical_semantics(representation)
    if variant == "S1_ROLE_LABEL_NEUTRAL":
        payload: object = (
            _generic_from_semantics(semantics)
            if representation.kind == "P4_MEMORY_PLUS_STRUCTURE"
            else _typed_from_semantics(semantics)
        )
        decoded = decode_semantic_payload(
            "P6_GENERIC_EQUAL_INFORMATION"
            if representation.kind == "P4_MEMORY_PLUS_STRUCTURE"
            else "P4_MEMORY_PLUS_STRUCTURE",
            payload,
        )
    elif variant == "S2_KEY_RENAME_REORDER":
        payload = {
            "z_rule_alias": {
                "n_alias": semantics["modulus"],
                "b_alias": list(semantics["offsets"]),
                "a_alias": list(semantics["permutation"]),
                "op_alias": semantics["operation"],
            },
            "a_refs_alias": list(semantics["provenance_handles"]),
        }
        decoded = {
            "operation": payload["z_rule_alias"]["op_alias"],
            "permutation": payload["z_rule_alias"]["a_alias"],
            "offsets": payload["z_rule_alias"]["b_alias"],
            "modulus": payload["z_rule_alias"]["n_alias"],
            "provenance_handles": payload["a_refs_alias"],
        }
    elif variant == "S3_LOSSLESS_LIST_PROSE_SERIALIZATION":
        payload = [
            "refs",
            list(semantics["provenance_handles"]),
            "rule",
            [
                semantics["operation"],
                list(semantics["permutation"]),
                list(semantics["offsets"]),
                semantics["modulus"],
            ],
        ]
        decoded = {
            "operation": payload[3][0],
            "permutation": payload[3][1],
            "offsets": payload[3][2],
            "modulus": payload[3][3],
            "provenance_handles": payload[1],
        }
    else:
        payload = json.loads(representation.serialized)
        decoded = semantics

    if _json_text(decoded) != _json_text(semantics):
        raise S3ExperimentError("meaning-preserving surface variant changed semantic payload")
    return S3SurfaceMaterial(
        serialized=_json_text(payload),
        canonical_semantics=semantics,
        prompt_variant=variant,
    )


def _surface_messages(
    representation: S2Representation,
    material: S3SurfaceMaterial,
    family: TransferFamily,
    *,
    step_index: int,
) -> tuple[dict[str, str], ...]:
    task = {
        "instruction": "Infer the vector transformation and return only a JSON integer array.",
        "modulus": family.modulus,
        "examples": [],
        "query": list(family.target_steps[step_index].query),
    }
    system = (
        "Solve the formal vector task. The supplied prior material is fallible derived context. "
        "Use its meaning when useful. Return only one JSON integer array of length 4."
    )
    if material.prompt_variant == "S4_PROMPT_PARAPHRASE_FORMAT":
        system = (
            "Answer the vector query from the earlier derived material when it helps. "
            "Treat that material as fallible and output exactly a JSON array containing four integers."
        )
    return (
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": _json_text(
                {
                    "surface_variant": material.prompt_variant,
                    "prior_context": json.loads(material.serialized),
                    "task": task,
                }
            ),
        },
    )


@dataclass(frozen=True, slots=True)
class S3Intervention:
    name: str
    query: tuple[int, ...]
    expected: tuple[int, ...]
    update: dict[str, object]


def semantic_intervention(
    family: TransferFamily,
    name: str,
    *,
    step_index: int,
) -> S3Intervention:
    if name not in S3_SEMANTIC_INTERVENTIONS:
        raise S3ExperimentError(f"unsupported semantic intervention: {name}")
    query = family.target_steps[step_index].query
    base = list(family.target_rules[step_index].apply(query))
    if name == "M1_RULE_OFFSET_FLIP":
        base[0] = (base[0] + 1) % family.modulus
        update = {"kind": "offset_delta", "output_coordinate": 0, "delta": 1}
    elif name == "M2_EXCEPTION_CHANGE":
        base[0] = (base[0] + 1) % family.modulus
        update = {
            "kind": "exact_query_exception",
            "query": list(query),
            "override": list(base),
        }
    elif name == "M3_SCOPE_CHANGE":
        base[1] = (base[1] + 1) % family.modulus
        update = {
            "kind": "scoped_delta",
            "condition": {"input_coordinate": 0, "gte": query[0]},
            "output_coordinate": 1,
            "delta": 1,
        }
    else:
        base[2] = (query[3] + family.target_rules[step_index].offsets[2]) % family.modulus
        update = {
            "kind": "relation_replace",
            "output_coordinate": 2,
            "source_coordinate": 3,
            "offset": family.target_rules[step_index].offsets[2],
        }
    return S3Intervention(name=name, query=query, expected=tuple(base), update=update)


def _semantic_messages(
    representation: S2Representation,
    intervention: S3Intervention,
    *,
    updated: bool,
    modulus: int,
) -> tuple[dict[str, str], ...]:
    prior: object = json.loads(representation.serialized)
    if updated:
        prior = {"base": prior, "semantic_update": intervention.update}
    return (
        {
            "role": "system",
            "content": (
                "Solve the vector task using the supplied fallible reusable semantics. "
                "If semantic_update is present it supersedes the corresponding base relation. "
                "Return only one JSON integer array of length 4."
            ),
        },
        {
            "role": "user",
            "content": _json_text(
                {
                    "prior_context": prior,
                    "task": {
                        "modulus": modulus,
                        "examples": [],
                        "query": list(intervention.query),
                    },
                }
            ),
        },
    )


def option_value_oracle(family: TransferFamily) -> int:
    sums = [sum(example.input_values) for example in family.source_examples]
    maximum = max(sums)
    return next(index for index, value in enumerate(sums) if value == maximum)


def _source_records(family: TransferFamily) -> list[dict[str, object]]:
    return [
        {
            "index": index,
            "input": list(example.input_values),
            "output": list(example.output_values),
        }
        for index, example in enumerate(family.source_examples)
    ]


def _option_messages(
    representation: S2Representation,
    family: TransferFamily,
) -> tuple[tuple[dict[str, str], ...], int]:
    packet: dict[str, object] = {
        "prior_context": json.loads(representation.serialized),
        "query": (
            "Return the smallest source-example index whose input vector has the maximum "
            "sum of coordinates. Tie-break by smallest index."
        ),
    }
    retrievals = 0
    if representation.kind in S3_TYPED_GENERIC_ARMS or representation.kind == "P5_STRUCTURE_ONLY_RECONSTRUCTABLE":
        packet["reconstructed_source_records"] = _source_records(family)
        retrievals = len(family.source_examples)
    return (
        (
            {
                "role": "system",
                "content": "Answer the source-history query. Return only JSON {\"index\": integer}.",
            },
            {"role": "user", "content": _json_text(packet)},
        ),
        retrievals,
    )


@dataclass(frozen=True, slots=True)
class S3CallRecord:
    question_id: str
    panel: str
    arm: str
    correct: bool | None
    input_tokens: int
    output_tokens: int
    projected_bytes: int
    retrieval_operations: int = 0


@dataclass(slots=True)
class S3WorkLedger:
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    projected_bytes: int = 0
    retrieval_operations: int = 0
    verify_operations: int = 0
    failures: int = 0

    def add(self, record: S3CallRecord) -> None:
        self.model_calls += 1
        self.input_tokens += record.input_tokens
        self.output_tokens += record.output_tokens
        self.projected_bytes += record.projected_bytes
        self.retrieval_operations += record.retrieval_operations
        self.verify_operations += int(record.correct is not None)
        self.failures += int(record.correct is False)

    def as_mapping(self) -> dict[str, int]:
        return {
            "C_build_and_model_calls": self.model_calls,
            "C_model_input_tokens": self.input_tokens,
            "C_model_output_tokens": self.output_tokens,
            "C_project_bytes": self.projected_bytes,
            "C_retrieve_operations": self.retrieval_operations,
            "C_verify_operations": self.verify_operations,
            "C_failure": self.failures,
        }


@dataclass(frozen=True, slots=True)
class S3FamilyResult:
    regime: str
    seed: int
    records: tuple[S3CallRecord, ...]
    p4_p6_semantic_equal: bool
    shared_formation_lineage: bool
    provenance_audit_changed: bool


@dataclass(frozen=True, slots=True)
class S3ShardResult:
    regime: str
    families: tuple[S3FamilyResult, ...]
    semantic_calls: int
    work: dict[str, int]
    surface_perturbation_effect: float
    semantic_intervention_effect: float
    semantic_invariance_gate: bool


def _parse_vector(content: str, *, modulus: int) -> tuple[int, ...] | None:
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return None
    if (
        not isinstance(value, list)
        or len(value) != S3_VECTOR_WIDTH
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
        or any(item < 0 or item >= modulus for item in value)
    ):
        return None
    return tuple(value)


def _parse_index(content: str) -> int | None:
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, Mapping) or set(value) != {"index"}:
        return None
    index = value["index"]
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 4:
        return None
    return index


class _FormationAdapter:
    def __init__(self, client: S3Client, prefix: str) -> None:
        self.client = client
        self.prefix = prefix
        self.index = 0
        self.completions: list[ExperimentCompletion] = []

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        if self.index >= 3:
            raise S3ExperimentError("formation adapter attempted an undeclared fourth call")
        suffix = ("p2", "p3", "p4")[self.index]
        completion = self.client.complete_named(
            f"{self.prefix}:form-{suffix}",
            messages,
            output_kind="rule" if suffix == "p4" else "text",
        )
        self.completions.append(completion)
        self.index += 1
        return completion


def _record(
    records: list[S3CallRecord],
    ledger: S3WorkLedger,
    *,
    question_id: str,
    panel: str,
    arm: str,
    completion: ExperimentCompletion,
    correct: bool | None,
    projected_bytes: int,
    retrieval_operations: int = 0,
) -> None:
    item = S3CallRecord(
        question_id=question_id,
        panel=panel,
        arm=arm,
        correct=correct,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
        projected_bytes=projected_bytes,
        retrieval_operations=retrieval_operations,
    )
    records.append(item)
    ledger.add(item)


def _provenance_audit(representation: S2Representation) -> bool:
    semantics = _canonical_semantics(representation)
    before = tuple(semantics["provenance_handles"])
    after = tuple(f"audit-replacement-{index}" for index, _ in enumerate(before))
    return before != after and len(before) == len(after)


def run_s3_family(client: S3Client, regime: str, index: int) -> S3FamilyResult:
    family = generate_s3_family(regime, index)
    prefix = f"{regime}:{index}:{family.seed}"
    adapter = _FormationAdapter(client, prefix)
    representations = form_s2_representations(adapter, family)
    if adapter.index != 3:
        raise S3ExperimentError("S3 representation formation did not consume exactly three calls")

    p4_payload = json.loads(representations["P4_MEMORY_PLUS_STRUCTURE"].serialized)
    p6_payload = json.loads(representations["P6_GENERIC_EQUAL_INFORMATION"].serialized)
    p4_p6_equal = semantic_digest("P4_MEMORY_PLUS_STRUCTURE", p4_payload) == semantic_digest(
        "P6_GENERIC_EQUAL_INFORMATION", p6_payload
    )
    if not p4_p6_equal:
        raise S3ExperimentError("P4/P6 semantic equality failed before S3 probes")
    shared_lineage = (
        representations["P4_MEMORY_PLUS_STRUCTURE"].formation_completion
        is representations["P5_STRUCTURE_ONLY_RECONSTRUCTABLE"].formation_completion
        is representations["P6_GENERIC_EQUAL_INFORMATION"].formation_completion
    )
    if not shared_lineage:
        raise S3ExperimentError("P4/P5/P6 no longer share one formation completion")

    records: list[S3CallRecord] = []
    ledger = S3WorkLedger()
    for suffix, completion in zip(("p2", "p3", "p4"), adapter.completions, strict=True):
        _record(
            records,
            ledger,
            question_id=f"{prefix}:form-{suffix}",
            panel="formation",
            arm=suffix.upper(),
            completion=completion,
            correct=None,
            projected_bytes=0,
        )

    step_index = primary_step_index(family)
    anchor_index = pre_shift_anchor_step_index(family)
    if anchor_index is not None:
        for arm in S3_TYPED_GENERIC_ARMS:
            rep = representations[arm]
            prompt = build_s2_target_messages(
                rep,
                family,
                step_index=anchor_index,
                examples_visible=S3_EXAMPLES_VISIBLE,
            )
            question_id = f"{prefix}:anchor:{arm}"
            completion = client.complete_named(question_id, prompt.messages, output_kind="vector")
            parsed = _parse_vector(completion.content, modulus=family.modulus)
            correct = parsed == family.expected_output(anchor_index)
            _record(
                records,
                ledger,
                question_id=question_id,
                panel="shift_pre_anchor",
                arm=arm,
                completion=completion,
                correct=correct,
                projected_bytes=rep.serialized_bytes,
            )

    canonical_correctness: dict[str, bool] = {}
    for arm in REPRESENTATION_KINDS:
        rep = representations[arm]
        prompt = build_s2_target_messages(
            rep,
            family,
            step_index=step_index,
            examples_visible=S3_EXAMPLES_VISIBLE,
        )
        question_id = f"{prefix}:canonical:{arm}"
        completion = client.complete_named(question_id, prompt.messages, output_kind="vector")
        parsed = _parse_vector(completion.content, modulus=family.modulus)
        correct = parsed == family.expected_output(step_index)
        canonical_correctness[arm] = correct
        _record(
            records,
            ledger,
            question_id=question_id,
            panel="canonical",
            arm=arm,
            completion=completion,
            correct=correct,
            projected_bytes=rep.serialized_bytes,
        )

    for arm in S3_TYPED_GENERIC_ARMS:
        rep = representations[arm]
        for variant in S3_SURFACE_VARIANTS:
            material = render_s3_surface_variant(rep, variant)
            messages = _surface_messages(rep, material, family, step_index=step_index)
            question_id = f"{prefix}:surface:{arm}:{variant}"
            completion = client.complete_named(question_id, messages, output_kind="vector")
            parsed = _parse_vector(completion.content, modulus=family.modulus)
            correct = parsed == family.expected_output(step_index)
            _record(
                records,
                ledger,
                question_id=question_id,
                panel="surface",
                arm=arm,
                completion=completion,
                correct=correct,
                projected_bytes=len(material.serialized.encode("utf-8")),
            )

    for arm in S3_TYPED_GENERIC_ARMS:
        rep = representations[arm]
        for name in S3_SEMANTIC_INTERVENTIONS:
            intervention = semantic_intervention(family, name, step_index=step_index)
            for updated in (False, True):
                state = "UPDATED_INTERVENED" if updated else "STALE_ORIGINAL"
                question_id = f"{prefix}:semantic:{arm}:{name}:{state}"
                messages = _semantic_messages(
                    rep,
                    intervention,
                    updated=updated,
                    modulus=family.modulus,
                )
                completion = client.complete_named(question_id, messages, output_kind="vector")
                parsed = _parse_vector(completion.content, modulus=family.modulus)
                correct = parsed == intervention.expected
                _record(
                    records,
                    ledger,
                    question_id=question_id,
                    panel=f"semantic:{name}:{state}",
                    arm=arm,
                    completion=completion,
                    correct=correct,
                    projected_bytes=rep.serialized_bytes,
                )

    option_expected = option_value_oracle(family)
    for arm in REPRESENTATION_KINDS:
        rep = representations[arm]
        messages, retrievals = _option_messages(rep, family)
        question_id = f"{prefix}:option:{arm}"
        completion = client.complete_named(question_id, messages, output_kind="index")
        correct = _parse_index(completion.content) == option_expected
        _record(
            records,
            ledger,
            question_id=question_id,
            panel="option_value",
            arm=arm,
            completion=completion,
            correct=correct,
            projected_bytes=rep.serialized_bytes,
            retrieval_operations=retrievals,
        )

    expected_calls = 43 if regime == "shift" else 41
    if len(records) != expected_calls:
        raise S3ExperimentError(
            f"S3 family call ledger drift: expected {expected_calls}, got {len(records)}"
        )
    return S3FamilyResult(
        regime=regime,
        seed=family.seed,
        records=tuple(records),
        p4_p6_semantic_equal=p4_p6_equal,
        shared_formation_lineage=shared_lineage,
        provenance_audit_changed=(
            _provenance_audit(representations["P4_MEMORY_PLUS_STRUCTURE"])
            and _provenance_audit(representations["P6_GENERIC_EQUAL_INFORMATION"])
        ),
    )


def _effect_metrics(families: tuple[S3FamilyResult, ...]) -> tuple[float, float]:
    canonical: dict[tuple[int, str], bool] = {}
    surface_pairs: list[float] = []
    semantic_pairs: dict[tuple[int, str, str], dict[str, bool]] = {}
    for family in families:
        for record in family.records:
            key = (family.seed, record.arm)
            if record.panel == "canonical" and record.arm in S3_TYPED_GENERIC_ARMS:
                canonical[key] = bool(record.correct)
        for record in family.records:
            key = (family.seed, record.arm)
            if record.panel == "surface":
                if key not in canonical:
                    raise S3ExperimentError("surface metric lacks canonical pair")
                surface_pairs.append(abs(int(bool(record.correct)) - int(canonical[key])))
            if record.panel.startswith("semantic:"):
                _, name, state = record.panel.split(":", 2)
                semantic_pairs.setdefault((family.seed, record.arm, name), {})[state] = bool(
                    record.correct
                )
    semantic_deltas: list[float] = []
    for states in semantic_pairs.values():
        if set(states) != {"STALE_ORIGINAL", "UPDATED_INTERVENED"}:
            raise S3ExperimentError("semantic metric pair is incomplete")
        semantic_deltas.append(
            float(int(states["UPDATED_INTERVENED"]) - int(states["STALE_ORIGINAL"]))
        )
    if not surface_pairs or not semantic_deltas:
        raise S3ExperimentError("S3 primary effect panels are empty")
    return sum(surface_pairs) / len(surface_pairs), sum(semantic_deltas) / len(semantic_deltas)


def semantic_invariance_gate(surface_effect: float, semantic_effect: float) -> bool:
    return (
        semantic_effect >= S3_SEMANTIC_EFFECT_MIN
        and surface_effect <= S3_SURFACE_EFFECT_MAX
        and semantic_effect - surface_effect >= S3_EFFECT_MARGIN_MIN
    )


def run_s3_shard(client: S3Client, regime: str) -> S3ShardResult:
    if regime not in S3_REGIMES:
        raise S3ExperimentError(f"unsupported S3 shard: {regime}")
    before_attempts = client.provider_attempts
    before_input = client.input_count_attempts
    families = tuple(run_s3_family(client, regime, index) for index in range(3))
    semantic_calls = client.provider_attempts - before_attempts
    input_requests = client.input_count_attempts - before_input
    expected = S3_SHARD_CALLS[regime]
    if semantic_calls != expected:
        raise S3ExperimentError(
            f"S3 shard provider call count drift: expected {expected}, got {semantic_calls}"
        )
    if input_requests != expected * 2:
        raise S3ExperimentError(
            f"S3 shard exact input-token count drift: expected {expected * 2}, got {input_requests}"
        )
    ledger = S3WorkLedger()
    for family in families:
        for record in family.records:
            ledger.add(record)
        if not family.p4_p6_semantic_equal or not family.shared_formation_lineage:
            raise S3ExperimentError("S3 family violated semantic/formation lineage")
        if not family.provenance_audit_changed:
            raise S3ExperimentError("S3 provenance audit-only intervention did not change lineage identity")
    surface_effect, semantic_effect = _effect_metrics(families)
    return S3ShardResult(
        regime=regime,
        families=families,
        semantic_calls=semantic_calls,
        work=ledger.as_mapping(),
        surface_perturbation_effect=surface_effect,
        semantic_intervention_effect=semantic_effect,
        semantic_invariance_gate=semantic_invariance_gate(surface_effect, semantic_effect),
    )


def s3_call_plan(regime: str) -> tuple[str, ...]:
    if regime not in S3_REGIMES:
        raise S3ExperimentError(f"unsupported S3 shard: {regime}")
    plan: list[str] = []
    for index, seed in enumerate(S3_SEEDS[regime]):
        prefix = f"{regime}:{index}:{seed}"
        plan.extend(f"{prefix}:form-{kind}" for kind in ("p2", "p3", "p4"))
        if regime == "shift":
            plan.extend(f"{prefix}:anchor:{arm}" for arm in S3_TYPED_GENERIC_ARMS)
        plan.extend(f"{prefix}:canonical:{arm}" for arm in REPRESENTATION_KINDS)
        plan.extend(
            f"{prefix}:surface:{arm}:{variant}"
            for arm in S3_TYPED_GENERIC_ARMS
            for variant in S3_SURFACE_VARIANTS
        )
        plan.extend(
            f"{prefix}:semantic:{arm}:{name}:{state}"
            for arm in S3_TYPED_GENERIC_ARMS
            for name in S3_SEMANTIC_INTERVENTIONS
            for state in ("STALE_ORIGINAL", "UPDATED_INTERVENED")
        )
        plan.extend(f"{prefix}:option:{arm}" for arm in REPRESENTATION_KINDS)
    if len(plan) != S3_SHARD_CALLS[regime]:
        raise AssertionError("frozen S3 call plan length drifted")
    return tuple(plan)


def s3_campaign_plan() -> tuple[str, ...]:
    plan = tuple(question for regime in S3_REGIMES for question in s3_call_plan(regime))
    if len(plan) != S3_TOTAL_SEMANTIC_CALLS:
        raise AssertionError("frozen S3 campaign call count drifted")
    return plan
