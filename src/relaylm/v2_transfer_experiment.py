from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from relaylm.v2_interventions import (
    ArmSnapshot,
    InterventionSpec,
    ProjectionPolicy,
    ProjectionResult,
    ResourceVector,
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


REGIMES = ("shared", "null", "mismatch", "shift")
_VECTOR_WIDTH = 4
_DEFAULT_MODULUS = 10
_TARGET_STEPS = 4
_EXAMPLES_PER_STEP = 3
_SOURCE_EXAMPLES = 4


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _seed_bytes(seed: int, label: str) -> bytes:
    if type(seed) is not int:
        raise TypeError("seed must be an int")
    if not label:
        raise ValueError("seed label must not be empty")
    return hashlib.sha256(
        f"relaylm2-transfer-r0|{seed}|{label}".encode("utf-8")
    ).digest()


def _vector(seed: int, label: str, *, modulus: int) -> tuple[int, ...]:
    raw = _seed_bytes(seed, label)
    return tuple(raw[index] % modulus for index in range(_VECTOR_WIDTH))


@dataclass(frozen=True, slots=True)
class VectorRule:
    permutation: tuple[int, ...]
    offsets: tuple[int, ...]
    modulus: int = _DEFAULT_MODULUS

    def __post_init__(self) -> None:
        if self.modulus <= 1:
            raise ValueError("modulus must be greater than one")
        if len(self.permutation) != _VECTOR_WIDTH:
            raise ValueError("permutation has the wrong width")
        if tuple(sorted(self.permutation)) != tuple(range(_VECTOR_WIDTH)):
            raise ValueError("permutation must be a bijection")
        if len(self.offsets) != _VECTOR_WIDTH:
            raise ValueError("offset vector has the wrong width")
        if any(type(value) is not int for value in self.offsets):
            raise TypeError("offsets must be integers")
        if any(value < 0 or value >= self.modulus for value in self.offsets):
            raise ValueError("offsets must be inside the modulus")

    def apply(self, values: tuple[int, ...]) -> tuple[int, ...]:
        if len(values) != _VECTOR_WIDTH:
            raise ValueError("input vector has the wrong width")
        if any(type(value) is not int for value in values):
            raise TypeError("input values must be integers")
        return tuple(
            (values[self.permutation[index]] + self.offsets[index]) % self.modulus
            for index in range(_VECTOR_WIDTH)
        )

    def fingerprint(self) -> str:
        return _digest(
            [
                "vector-rule",
                list(self.permutation),
                list(self.offsets),
                self.modulus,
            ]
        )


@dataclass(frozen=True, slots=True)
class PublicExample:
    input_values: tuple[int, ...]
    output_values: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class TargetStep:
    examples: tuple[PublicExample, ...]
    query: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class VerificationResult:
    correct: bool
    parsed_output: tuple[int, ...] | None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class TransferFamily:
    seed: int
    regime: str
    modulus: int
    source_rule: VectorRule
    target_rules: tuple[VectorRule, ...]
    source_examples: tuple[PublicExample, ...]
    target_steps: tuple[TargetStep, ...]
    shift_index: int | None

    def __post_init__(self) -> None:
        if self.regime not in REGIMES:
            raise ValueError(f"unsupported transfer regime: {self.regime}")
        if len(self.target_rules) != len(self.target_steps):
            raise ValueError("each target step requires one hidden target rule")
        if self.regime == "shift":
            if self.shift_index is None:
                raise ValueError("shift regime requires a shift index")
            if not 0 < self.shift_index < len(self.target_steps):
                raise ValueError("shift index must be inside the target trajectory")
        elif self.shift_index is not None:
            raise ValueError("only shift regime may carry a shift index")

    def model_packet(self, step_index: int) -> bytes:
        step = self.target_steps[step_index]
        return _json_bytes(
            {
                "instruction": (
                    "Infer the transformation from the examples. "
                    "Return only a JSON integer array."
                ),
                "examples": [
                    {
                        "input": list(example.input_values),
                        "output": list(example.output_values),
                    }
                    for example in step.examples
                ],
                "query": list(step.query),
            }
        )

    @property
    def public_target_digest(self) -> str:
        return _digest(
            [
                "target-public-sequence",
                [
                    json.loads(self.model_packet(index))
                    for index in range(len(self.target_steps))
                ],
            ]
        )

    def expected_output(self, step_index: int) -> tuple[int, ...]:
        return self.target_rules[step_index].apply(self.target_steps[step_index].query)

    def verify_response(self, step_index: int, response: str) -> VerificationResult:
        try:
            decoded = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return VerificationResult(False, None, "invalid_json")

        if (
            not isinstance(decoded, list)
            or len(decoded) != _VECTOR_WIDTH
            or any(type(value) is not int for value in decoded)
        ):
            return VerificationResult(False, None, "invalid_shape")
        parsed = tuple(decoded)
        if any(value < 0 or value >= self.modulus for value in parsed):
            return VerificationResult(False, parsed, "out_of_range")
        return VerificationResult(
            parsed == self.expected_output(step_index),
            parsed,
            None,
        )

    def feedback_observation(self, step_index: int) -> ObservationInput:
        step = self.target_steps[step_index]
        payload = _json_bytes(
            {
                "input": list(step.query),
                "observed_output": list(self.expected_output(step_index)),
            }
        ).decode("utf-8")
        return ObservationInput(
            slot=f"target-feedback-{step_index}",
            time=f"2026-09-04T00:00:{step_index:02d}+00:00",
            source="synthetic-transfer-environment",
            payload=payload,
        )

    @property
    def evidence_schedule_digest(self) -> str:
        return _digest(
            [
                "target-evidence-schedule",
                [
                    {
                        "slot": observation.slot,
                        "time": observation.time,
                        "source": observation.source,
                        "payload": observation.payload,
                    }
                    for observation in (
                        self.feedback_observation(index)
                        for index in range(len(self.target_steps))
                    )
                ],
            ]
        )


@dataclass(slots=True)
class R0Arm:
    arm_id: str
    store: SemanticTransactionStore
    projection_policy: ProjectionPolicy
    projection: ProjectionResult
    source_structure_id: str
    target_local_id: str
    task_digest: str
    evidence_schedule_digest: str


@dataclass(slots=True)
class R0ArmSet:
    t0: R0Arm
    t1: R0Arm
    t2: R0Arm


def _rule_from_seed(seed: int, label: str, *, modulus: int) -> VectorRule:
    order = sorted(
        range(_VECTOR_WIDTH),
        key=lambda index: _seed_bytes(seed, f"{label}:perm:{index}"),
    )
    offsets = tuple(
        _seed_bytes(seed, f"{label}:offset:{index}")[0] % modulus
        for index in range(_VECTOR_WIDTH)
    )
    return VectorRule(tuple(order), offsets, modulus)


def _distinct_rule(
    seed: int,
    label: str,
    *,
    source: VectorRule,
    modulus: int,
) -> VectorRule:
    for attempt in range(16):
        candidate = _rule_from_seed(seed, f"{label}:{attempt}", modulus=modulus)
        if candidate != source:
            return candidate
    raise RuntimeError("failed to derive a distinct deterministic rule")


def _mismatch_rule(source: VectorRule) -> VectorRule:
    offsets = list(source.offsets)
    offsets[0] = (offsets[0] + 1) % source.modulus
    return VectorRule(source.permutation, tuple(offsets), source.modulus)


def _examples_for_rule(
    seed: int,
    label: str,
    *,
    rule: VectorRule,
    count: int,
) -> tuple[PublicExample, ...]:
    examples: list[PublicExample] = []
    for index in range(count):
        input_values = _vector(
            seed,
            f"{label}:example:{index}",
            modulus=rule.modulus,
        )
        examples.append(PublicExample(input_values, rule.apply(input_values)))
    return tuple(examples)


def generate_transfer_family(
    *,
    seed: int,
    regime: str,
    modulus: int = _DEFAULT_MODULUS,
) -> TransferFamily:
    if regime not in REGIMES:
        raise ValueError(f"unsupported transfer regime: {regime}")
    if modulus <= 1:
        raise ValueError("modulus must be greater than one")

    source_rule = _rule_from_seed(seed, "source", modulus=modulus)
    shift_index: int | None = None

    if regime == "shared":
        target_rule = source_rule
        target_rules = (target_rule,) * _TARGET_STEPS
    elif regime == "null":
        target_rule = _distinct_rule(
            seed,
            "null-target",
            source=source_rule,
            modulus=modulus,
        )
        target_rules = (target_rule,) * _TARGET_STEPS
    elif regime == "mismatch":
        target_rule = _mismatch_rule(source_rule)
        target_rules = (target_rule,) * _TARGET_STEPS
    else:
        shift_index = _TARGET_STEPS // 2
        shifted_rule = _distinct_rule(
            seed,
            "shift-target",
            source=source_rule,
            modulus=modulus,
        )
        target_rules = (
            (source_rule,) * shift_index
            + (shifted_rule,) * (_TARGET_STEPS - shift_index)
        )

    source_examples = _examples_for_rule(
        seed,
        "source",
        rule=source_rule,
        count=_SOURCE_EXAMPLES,
    )
    target_steps: list[TargetStep] = []
    for step_index, target_rule in enumerate(target_rules):
        examples = _examples_for_rule(
            seed,
            f"target:{step_index}",
            rule=target_rule,
            count=_EXAMPLES_PER_STEP,
        )
        query = _vector(
            seed,
            f"target:{step_index}:query",
            modulus=modulus,
        )
        target_steps.append(TargetStep(examples, query))

    return TransferFamily(
        seed=seed,
        regime=regime,
        modulus=modulus,
        source_rule=source_rule,
        target_rules=target_rules,
        source_examples=source_examples,
        target_steps=tuple(target_steps),
        shift_index=shift_index,
    )


def _clone_store(store: SemanticTransactionStore) -> SemanticTransactionStore:
    return SemanticTransactionStore.from_snapshot(store.canonical_snapshot())


def _make_r0_arm(
    *,
    arm_id: str,
    base: SemanticTransactionStore,
    allow_cross_task: bool,
    source_structure_id: str,
    target_local_id: str,
    family: TransferFamily,
) -> R0Arm:
    store = _clone_store(base)
    policy = ProjectionPolicy(
        local_roots=(target_local_id,),
        cross_task_roots=(source_structure_id,),
        allow_cross_task=allow_cross_task,
    )
    projection = project_scope(store, policy)
    return R0Arm(
        arm_id=arm_id,
        store=store,
        projection_policy=policy,
        projection=projection,
        source_structure_id=source_structure_id,
        target_local_id=target_local_id,
        task_digest=family.public_target_digest,
        evidence_schedule_digest=family.evidence_schedule_digest,
    )


def prepare_r0_arms(family: TransferFamily) -> R0ArmSet:
    base = SemanticTransactionStore()

    target_local = apply(
        "r0_target_task",
        literal(family.public_target_digest),
    )
    source_structure = apply(
        "r0_oracle_source_structure",
        literal(family.source_rule.fingerprint()),
    )
    result = base.transact(
        TransactionRequest(
            base_generation=base.current_generation,
            proposals=(Proposal(target_local), Proposal(source_structure)),
        )
    )
    if any(decision.status != "accepted" for decision in result.decisions):
        raise RuntimeError("R0 fixture failed to establish canonical starting roots")

    target_local_id = semantic_id(target_local)
    source_structure_id = semantic_id(source_structure)
    return R0ArmSet(
        t0=_make_r0_arm(
            arm_id="T0",
            base=base,
            allow_cross_task=False,
            source_structure_id=source_structure_id,
            target_local_id=target_local_id,
            family=family,
        ),
        t1=_make_r0_arm(
            arm_id="T1",
            base=base,
            allow_cross_task=True,
            source_structure_id=source_structure_id,
            target_local_id=target_local_id,
            family=family,
        ),
        t2=_make_r0_arm(
            arm_id="T2",
            base=base,
            allow_cross_task=True,
            source_structure_id=source_structure_id,
            target_local_id=target_local_id,
            family=family,
        ),
    )


def r0_transfer_spec() -> InterventionSpec:
    return InterventionSpec(
        "transfer-r0-projection-eligibility",
        frozenset({"allow_cross_task", "projected_roots"}),
        frozenset({"allow_cross_task", "projected_roots"}),
    )


def snapshot_r0_arm(
    arm: R0Arm,
    *,
    resource_total: ResourceVector = ResourceVector(),
) -> ArmSnapshot:
    return snapshot_arm(
        arm.store,
        projection_policy=arm.projection_policy,
        projection_result=arm.projection,
        policy_id="transfer-r0",
        resource_total=resource_total,
    )
