from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import random
import re
from typing import Literal as TypingLiteral

from relaylm.v2_interventions import (
    InterventionSpec,
    ProjectionPolicy,
    ResourceVector,
    assert_clean_intervention,
    project_scope,
    snapshot_arm,
)
from relaylm.v2_semantics import (
    ObservationInput,
    Proposal,
    SemanticTransactionStore,
    TransactionRequest,
    apply,
    literal,
    semantic_id,
)


RelationRegime = TypingLiteral["shared", "null", "mismatch", "shift"]
TransferDistance = TypingLiteral["near", "compositional", "structural", "shift"]
ArmName = TypingLiteral["T0", "T1", "T2"]

MODULUS = 17
_VECTOR_FAMILIES = ("diagonal", "upper", "lower", "dense", "swap")
_FAMILY_MASKS: dict[str, tuple[int, int, int, int]] = {
    "diagonal": (1, 0, 0, 1),
    "upper": (1, 1, 0, 1),
    "lower": (1, 0, 1, 1),
    "dense": (1, 1, 1, 1),
    "swap": (0, 1, 1, 0),
}


class TransferExperimentError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Example:
    inputs: tuple[int, ...]
    outputs: tuple[int, ...]

    def render(self) -> str:
        left = ",".join(str(value) for value in self.inputs)
        right = ",".join(str(value) for value in self.outputs)
        return f"{left} -> {right}"


@dataclass(frozen=True, slots=True)
class VectorRule:
    family: str
    matrix: tuple[int, int, int, int]
    bias: tuple[int, int]
    iterations: int = 1
    modulus: int = MODULUS

    def __post_init__(self) -> None:
        if self.family not in _FAMILY_MASKS:
            raise ValueError(f"unknown vector family: {self.family}")
        if self.iterations < 1:
            raise ValueError("iterations must be positive")
        mask = _FAMILY_MASKS[self.family]
        for enabled, coefficient in zip(mask, self.matrix, strict=True):
            if bool(coefficient) != bool(enabled):
                raise ValueError("matrix does not match declared family mask")
        if any(not 0 <= value < self.modulus for value in self.bias):
            raise ValueError("bias must be inside modulus")

    def apply_once(self, values: tuple[int, int]) -> tuple[int, int]:
        x0, x1 = values
        a00, a01, a10, a11 = self.matrix
        b0, b1 = self.bias
        return (
            (a00 * x0 + a01 * x1 + b0) % self.modulus,
            (a10 * x0 + a11 * x1 + b1) % self.modulus,
        )

    def evaluate(self, values: tuple[int, int]) -> tuple[int, int]:
        current = values
        for _ in range(self.iterations):
            current = self.apply_once(current)
        return current


@dataclass(frozen=True, slots=True)
class ScalarRule:
    multiplier: int
    bias: int
    modulus: int = MODULUS

    def evaluate(self, values: tuple[int]) -> tuple[int]:
        return ((self.multiplier * values[0] + self.bias) % self.modulus,)


Rule = VectorRule | ScalarRule


@dataclass(frozen=True, slots=True)
class GeneratedTask:
    task_id: str
    rule: Rule
    teaching_examples: tuple[Example, ...]
    probes: tuple[Example, ...]

    @property
    def arity(self) -> int:
        return len(self.probes[0].inputs)


@dataclass(frozen=True, slots=True)
class TransferCase:
    seed: int
    relation: RelationRegime
    distance: TransferDistance
    source_tasks: tuple[GeneratedTask, ...]
    target_task: GeneratedTask
    shifted_rule: VectorRule | None
    shift_after_evidence: int | None
    reusable_structure_text: str

    def __post_init__(self) -> None:
        if self.relation == "shift":
            if self.shifted_rule is None or self.shift_after_evidence is None:
                raise ValueError("shift case requires shifted rule and transition")
        elif self.shifted_rule is not None or self.shift_after_evidence is not None:
            raise ValueError("non-shift case must not carry shift metadata")


@dataclass(frozen=True, slots=True)
class PublicTaskManifest:
    task_id: str
    arity: int
    modulus: int
    teaching_examples: tuple[str, ...]
    probes: tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class PublicCaseManifest:
    source_tasks: tuple[PublicTaskManifest, ...]
    target_task: PublicTaskManifest


@dataclass(frozen=True, slots=True)
class TargetTurn:
    arm: ArmName
    task_id: str
    evidence_count: int
    prompt: str
    prompt_sha256: str
    projected_structure: str | None
    resource_envelope: ResourceVector


@dataclass(frozen=True, slots=True)
class MatchedArmFixture:
    source_snapshot: bytes
    source_structure_id: str
    target_evidence_ids: tuple[str, ...]
    t0_projection: tuple[str, ...]
    t1_projection: tuple[str, ...]
    t2_projection: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ParsedAnswer:
    values: tuple[int, ...]
    valid: bool


_PAIR_RE = re.compile(r"^\s*\[?\s*(-?\d+)\s*,\s*(-?\d+)\s*\]?\s*$")
_SCALAR_RE = re.compile(r"^\s*\[?\s*(-?\d+)\s*\]?\s*$")


def _sha(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _opaque_id(seed: int, role: str, index: int) -> str:
    return _sha(["v2-transfer-task", seed, role, index])[:16]


def _sample_nonzero(rng: random.Random) -> int:
    return rng.randrange(1, MODULUS)


def _sample_vector_rule(
    rng: random.Random,
    family: str,
    *,
    iterations: int = 1,
) -> VectorRule:
    mask = _FAMILY_MASKS[family]
    matrix = tuple(_sample_nonzero(rng) if enabled else 0 for enabled in mask)
    bias = (rng.randrange(MODULUS), rng.randrange(MODULUS))
    return VectorRule(
        family=family,
        matrix=matrix,
        bias=bias,
        iterations=iterations,
    )


def _sample_scalar_rule(rng: random.Random) -> ScalarRule:
    return ScalarRule(_sample_nonzero(rng), rng.randrange(MODULUS))


def _example_for(rule: Rule, values: tuple[int, ...]) -> Example:
    if isinstance(rule, VectorRule):
        if len(values) != 2:
            raise ValueError("vector rule requires arity two")
        output = rule.evaluate((values[0], values[1]))
    else:
        if len(values) != 1:
            raise ValueError("scalar rule requires arity one")
        output = rule.evaluate((values[0],))
    return Example(values, output)


def _sample_inputs(
    rng: random.Random,
    *,
    arity: int,
    count: int,
) -> tuple[tuple[int, ...], ...]:
    population = MODULUS**arity
    if count > population:
        raise ValueError("requested more unique inputs than available")
    seen: set[tuple[int, ...]] = set()
    values: list[tuple[int, ...]] = []
    while len(values) < count:
        candidate = tuple(rng.randrange(MODULUS) for _ in range(arity))
        if candidate not in seen:
            seen.add(candidate)
            values.append(candidate)
    return tuple(values)


def _task_from_rule(
    rng: random.Random,
    *,
    task_id: str,
    rule: Rule,
    teaching_count: int,
    probe_count: int,
) -> GeneratedTask:
    arity = 2 if isinstance(rule, VectorRule) else 1
    inputs = _sample_inputs(
        rng,
        arity=arity,
        count=teaching_count + probe_count,
    )
    teaching = tuple(_example_for(rule, value) for value in inputs[:teaching_count])
    probes = tuple(_example_for(rule, value) for value in inputs[teaching_count:])
    return GeneratedTask(task_id, rule, teaching, probes)


def _family_structure_text(family: str) -> str:
    mask = _FAMILY_MASKS[family]
    dependencies = []
    if mask[0]:
        dependencies.append("output-0 depends on input-0")
    if mask[1]:
        dependencies.append("output-0 depends on input-1")
    if mask[2]:
        dependencies.append("output-1 depends on input-0")
    if mask[3]:
        dependencies.append("output-1 depends on input-1")
    joined = "; ".join(dependencies)
    return (
        "Across the source machines, each output coordinate follows an affine "
        f"transformation modulo {MODULUS}; {joined}. Coefficients and offsets "
        "are machine-specific and must be inferred from that machine's examples."
    )


def _exact_rule_text(rule: VectorRule) -> str:
    a00, a01, a10, a11 = rule.matrix
    b0, b1 = rule.bias
    return (
        f"A source primitive maps (x0,x1) to "
        f"(({a00}*x0+{a01}*x1+{b0}) mod {rule.modulus}, "
        f"({a10}*x0+{a11}*x1+{b1}) mod {rule.modulus})."
    )


def _scalar_structure_text(rule: ScalarRule) -> str:
    return (
        "The source task is scalar: one value x maps to "
        f"({rule.multiplier}*x+{rule.bias}) mod {rule.modulus}."
    )


def generate_transfer_case(
    seed: int,
    *,
    relation: RelationRegime,
    distance: TransferDistance = "structural",
    source_task_count: int = 3,
    teaching_count: int = 8,
    probe_count: int = 8,
) -> TransferCase:
    if relation == "shift":
        distance = "shift"
    if distance == "shift" and relation != "shift":
        raise ValueError("shift distance requires shift relation")
    if source_task_count < 1:
        raise ValueError("source_task_count must be positive")

    rng = random.Random(seed)
    source_tasks: list[GeneratedTask] = []

    if relation == "null":
        scalar_rule = _sample_scalar_rule(rng)
        for index in range(source_task_count):
            rule = _sample_scalar_rule(rng) if index else scalar_rule
            source_tasks.append(
                _task_from_rule(
                    rng,
                    task_id=_opaque_id(seed, "source", index),
                    rule=rule,
                    teaching_count=teaching_count,
                    probe_count=probe_count,
                )
            )
        target_family = rng.choice(_VECTOR_FAMILIES)
        target_rule = _sample_vector_rule(rng, target_family)
        structure_text = _scalar_structure_text(scalar_rule)
    else:
        source_family = rng.choice(_VECTOR_FAMILIES)
        source_rules = [
            _sample_vector_rule(rng, source_family)
            for _ in range(source_task_count)
        ]
        for index, rule in enumerate(source_rules):
            source_tasks.append(
                _task_from_rule(
                    rng,
                    task_id=_opaque_id(seed, "source", index),
                    rule=rule,
                    teaching_count=teaching_count,
                    probe_count=probe_count,
                )
            )

        if relation == "shared" and distance == "near":
            target_rule = source_rules[0]
            structure_text = _exact_rule_text(source_rules[0])
        elif relation == "shared" and distance == "compositional":
            base = source_rules[0]
            target_rule = VectorRule(
                family=base.family,
                matrix=base.matrix,
                bias=base.bias,
                iterations=2,
            )
            structure_text = _exact_rule_text(base)
        elif relation == "shared":
            target_rule = _sample_vector_rule(rng, source_family)
            structure_text = _family_structure_text(source_family)
        else:
            other_families = tuple(
                family for family in _VECTOR_FAMILIES if family != source_family
            )
            target_family = rng.choice(other_families)
            target_rule = _sample_vector_rule(rng, target_family)
            structure_text = _family_structure_text(source_family)

    target_task = _task_from_rule(
        rng,
        task_id=_opaque_id(seed, "target", 0),
        rule=target_rule,
        teaching_count=teaching_count,
        probe_count=probe_count,
    )

    shifted_rule = None
    shift_after = None
    if relation == "shift":
        assert isinstance(target_rule, VectorRule)
        other_families = tuple(
            family for family in _VECTOR_FAMILIES if family != target_rule.family
        )
        shifted_rule = _sample_vector_rule(rng, rng.choice(other_families))
        shift_after = teaching_count // 2
        teaching = list(target_task.teaching_examples)
        for index in range(shift_after, len(teaching)):
            teaching[index] = _example_for(shifted_rule, teaching[index].inputs)
        probes = tuple(
            _example_for(shifted_rule, example.inputs)
            for example in target_task.probes
        )
        target_task = GeneratedTask(
            target_task.task_id,
            target_task.rule,
            tuple(teaching),
            probes,
        )

    return TransferCase(
        seed=seed,
        relation=relation,
        distance=distance,
        source_tasks=tuple(source_tasks),
        target_task=target_task,
        shifted_rule=shifted_rule,
        shift_after_evidence=shift_after,
        reusable_structure_text=structure_text,
    )


def public_task_manifest(task: GeneratedTask) -> PublicTaskManifest:
    return PublicTaskManifest(
        task_id=task.task_id,
        arity=task.arity,
        modulus=MODULUS,
        teaching_examples=tuple(example.render() for example in task.teaching_examples),
        probes=tuple(example.inputs for example in task.probes),
    )


def public_case_manifest(case: TransferCase) -> PublicCaseManifest:
    return PublicCaseManifest(
        source_tasks=tuple(public_task_manifest(task) for task in case.source_tasks),
        target_task=public_task_manifest(case.target_task),
    )


def public_case_digest(case: TransferCase) -> str:
    public = public_case_manifest(case)
    payload = {
        "source_tasks": [
            {
                "task_id": task.task_id,
                "arity": task.arity,
                "modulus": task.modulus,
                "teaching_examples": task.teaching_examples,
                "probes": task.probes,
            }
            for task in public.source_tasks
        ],
        "target_task": {
            "task_id": public.target_task.task_id,
            "arity": public.target_task.arity,
            "modulus": public.target_task.modulus,
            "teaching_examples": public.target_task.teaching_examples,
            "probes": public.target_task.probes,
        },
    }
    return _sha(payload)


def private_case_digest(case: TransferCase) -> str:
    def rule_payload(rule: Rule) -> object:
        if isinstance(rule, ScalarRule):
            return ["scalar", rule.multiplier, rule.bias, rule.modulus]
        return [
            "vector",
            rule.family,
            rule.matrix,
            rule.bias,
            rule.iterations,
            rule.modulus,
        ]

    return _sha(
        {
            "seed": case.seed,
            "relation": case.relation,
            "distance": case.distance,
            "source_rules": [rule_payload(task.rule) for task in case.source_tasks],
            "target_rule": rule_payload(case.target_task.rule),
            "shifted_rule": (
                None if case.shifted_rule is None else rule_payload(case.shifted_rule)
            ),
            "shift_after": case.shift_after_evidence,
        }
    )


def render_target_prompt(
    case: TransferCase,
    *,
    evidence_count: int,
    projected_structure: str | None = None,
) -> str:
    task = case.target_task
    if task.arity != 2:
        raise TransferExperimentError("target task must use pair inputs")
    if not 0 <= evidence_count <= len(task.teaching_examples):
        raise ValueError("invalid evidence_count")

    lines = [
        "A hidden machine maps an input pair to an output pair.",
        f"All arithmetic values are in 0..{MODULUS - 1}.",
        "Infer the current machine from the examples available so far.",
    ]
    if projected_structure is not None:
        lines.extend(
            [
                "Reusable structure learned from earlier tasks:",
                projected_structure,
            ]
        )
    lines.append("Observed examples:")
    if evidence_count:
        lines.extend(
            f"- {example.render()}"
            for example in task.teaching_examples[:evidence_count]
        )
    else:
        lines.append("- none")
    lines.extend(
        [
            "For the query below, return only two integers as `y0,y1`.",
            "Do not explain your reasoning.",
        ]
    )
    return "\n".join(lines)


def build_target_turn(
    case: TransferCase,
    *,
    arm: ArmName,
    evidence_count: int,
    resource_envelope: ResourceVector,
) -> TargetTurn:
    structure = None if arm == "T0" else case.reusable_structure_text
    prompt = render_target_prompt(
        case,
        evidence_count=evidence_count,
        projected_structure=structure,
    )
    return TargetTurn(
        arm=arm,
        task_id=case.target_task.task_id,
        evidence_count=evidence_count,
        prompt=prompt,
        prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        projected_structure=structure,
        resource_envelope=resource_envelope,
    )


def parse_answer(text: str, *, arity: int = 2) -> ParsedAnswer:
    match = _PAIR_RE.match(text) if arity == 2 else _SCALAR_RE.match(text)
    if match is None:
        return ParsedAnswer((), False)
    values = tuple(int(value) % MODULUS for value in match.groups())
    return ParsedAnswer(values, True)


def verify_answer(
    task: GeneratedTask,
    *,
    probe_index: int,
    answer: ParsedAnswer,
    shifted_rule: VectorRule | None = None,
) -> bool:
    if not answer.valid:
        return False
    probe = task.probes[probe_index]
    if shifted_rule is not None:
        expected = shifted_rule.evaluate((probe.inputs[0], probe.inputs[1]))
    else:
        expected = probe.outputs
    return answer.values == expected


def _source_observations(case: TransferCase) -> tuple[ObservationInput, ...]:
    observations: list[ObservationInput] = []
    minute = 0
    for task_index, task in enumerate(case.source_tasks):
        for example_index, example in enumerate(task.teaching_examples):
            observations.append(
                ObservationInput(
                    slot=f"source-{task_index}-{example_index}",
                    time=f"2026-09-04T12:{minute:02d}:00+00:00",
                    source="v2-transfer-generated-source",
                    payload=f"{task.task_id}: {example.render()}",
                )
            )
            minute = (minute + 1) % 60
    return tuple(observations)


def prepare_oracle_source_fixture(case: TransferCase) -> tuple[SemanticTransactionStore, str]:
    """Build an R0-only oracle Structure fixture from source evidence.

    The reusable summary is evaluator-derived and therefore must never be
    presented as learned actual-model evidence. It exists only to prove the
    causal-arm mechanics before a physical source-learning implementation.
    """

    store = SemanticTransactionStore()
    observations = _source_observations(case)
    slots = tuple(observation.slot for observation in observations)
    structure_expr = apply("reusable_structure", literal(case.reusable_structure_text))
    result = store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            observations=observations,
            proposals=(
                Proposal(
                    structure_expr,
                    observed_support_slots=slots,
                ),
            ),
        )
    )
    decision = result.decisions[0]
    if decision.status != "accepted" or decision.semantic_id is None:
        raise TransferExperimentError("oracle source Structure was not accepted")
    return store, decision.semantic_id


def _clone(store: SemanticTransactionStore) -> SemanticTransactionStore:
    return SemanticTransactionStore.from_snapshot(store.canonical_snapshot())


def ingest_target_evidence(
    store: SemanticTransactionStore,
    case: TransferCase,
    *,
    evidence_count: int,
) -> tuple[str, ...]:
    if not 0 <= evidence_count <= len(case.target_task.teaching_examples):
        raise ValueError("invalid evidence_count")
    observations = tuple(
        ObservationInput(
            slot=f"target-{index}",
            time=f"2026-09-04T13:{index:02d}:00+00:00",
            source="v2-transfer-generated-target",
            payload=f"{case.target_task.task_id}: {example.render()}",
        )
        for index, example in enumerate(
            case.target_task.teaching_examples[:evidence_count]
        )
    )
    if not observations:
        return ()
    result = store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            observations=observations,
        )
    )
    return result.observation_records


def build_matched_arm_fixture(
    case: TransferCase,
    *,
    evidence_count: int,
) -> MatchedArmFixture:
    source_store, structure_id = prepare_oracle_source_fixture(case)
    t0 = _clone(source_store)
    t1 = _clone(source_store)
    t2 = _clone(source_store)

    evidence_t0 = ingest_target_evidence(t0, case, evidence_count=evidence_count)
    evidence_t1 = ingest_target_evidence(t1, case, evidence_count=evidence_count)
    evidence_t2 = ingest_target_evidence(t2, case, evidence_count=evidence_count)
    if evidence_t0 != evidence_t1 or evidence_t1 != evidence_t2:
        raise TransferExperimentError("matched arms produced different Evidence ids")
    if t0.canonical_snapshot() != t1.canonical_snapshot():
        raise TransferExperimentError("T0/T1 canonical state diverged before projection")
    if t1.canonical_snapshot() != t2.canonical_snapshot():
        raise TransferExperimentError("T1/T2 canonical state diverged before projection")

    t0_policy = ProjectionPolicy(
        cross_task_roots=(structure_id,),
        allow_cross_task=False,
        evidence_packet_ids=evidence_t0,
    )
    t1_policy = ProjectionPolicy(
        cross_task_roots=(structure_id,),
        allow_cross_task=True,
        evidence_packet_ids=evidence_t1,
    )
    t2_policy = ProjectionPolicy(
        cross_task_roots=(structure_id,),
        allow_cross_task=True,
        evidence_packet_ids=evidence_t2,
    )
    t0_projection = project_scope(t0, t0_policy)
    t1_projection = project_scope(t1, t1_policy)
    t2_projection = project_scope(t2, t2_policy)

    assert_clean_intervention(
        snapshot_arm(
            t0,
            projection_policy=t0_policy,
            projection_result=t0_projection,
            policy_id="transfer",
        ),
        snapshot_arm(
            t1,
            projection_policy=t1_policy,
            projection_result=t1_projection,
            policy_id="transfer",
        ),
        spec=InterventionSpec(
            "T0-vs-T1-transfer",
            frozenset({"allow_cross_task", "projected_roots"}),
            frozenset({"allow_cross_task", "projected_roots"}),
        ),
    )
    assert_clean_intervention(
        snapshot_arm(
            t1,
            projection_policy=t1_policy,
            projection_result=t1_projection,
            policy_id="transfer",
        ),
        snapshot_arm(
            t2,
            projection_policy=t2_policy,
            projection_result=t2_projection,
            policy_id="transfer",
        ),
        spec=InterventionSpec("T1-vs-T2-pre-revision", frozenset()),
    )

    return MatchedArmFixture(
        source_snapshot=source_store.canonical_snapshot(),
        source_structure_id=structure_id,
        target_evidence_ids=evidence_t0,
        t0_projection=t0_projection.projected_roots,
        t1_projection=t1_projection.projected_roots,
        t2_projection=t2_projection.projected_roots,
    )


def assert_case_relation(case: TransferCase) -> None:
    target_rule = case.target_task.rule
    if not isinstance(target_rule, VectorRule):
        raise TransferExperimentError("target rule must be vector-valued")

    if case.relation == "null":
        if not all(isinstance(task.rule, ScalarRule) for task in case.source_tasks):
            raise TransferExperimentError("null source must be structurally unrelated scalar tasks")
        return

    source_rules = tuple(task.rule for task in case.source_tasks)
    if not all(isinstance(rule, VectorRule) for rule in source_rules):
        raise TransferExperimentError("vector relation requires vector source tasks")
    source_families = {rule.family for rule in source_rules if isinstance(rule, VectorRule)}
    if len(source_families) != 1:
        raise TransferExperimentError("source family is not stable")
    source_family = next(iter(source_families))

    if case.relation == "shared" and target_rule.family != source_family:
        raise TransferExperimentError("shared target does not preserve source family")
    if case.relation == "mismatch" and target_rule.family == source_family:
        raise TransferExperimentError("mismatch target accidentally preserved source family")
    if case.relation == "shift":
        if target_rule.family != source_family:
            raise TransferExperimentError("shift pre-rule must preserve source family")
        if case.shifted_rule is None or case.shifted_rule.family == source_family:
            raise TransferExperimentError("shift post-rule must invalidate source family")


def assert_public_manifest_separation(case: TransferCase) -> None:
    public_json = json.dumps(
        public_case_manifest(case),
        default=lambda value: value.__dict__,
        sort_keys=True,
    )
    forbidden = {
        case.relation,
        case.distance,
        "diagonal",
        "upper",
        "lower",
        "dense",
        "swap",
        "matrix",
        "bias",
        "shift_after",
    }
    leaked = tuple(sorted(token for token in forbidden if token in public_json))
    if leaked:
        raise TransferExperimentError(f"hidden metadata leaked into public manifest: {leaked}")


def transfer_resource_envelope() -> ResourceVector:
    return ResourceVector(
        calls=64,
        input_tokens=32768,
        output_tokens=8192,
        latency_units=10**9,
        observation_units=64,
        retrieval_units=64,
        memory_units=32768,
    )
