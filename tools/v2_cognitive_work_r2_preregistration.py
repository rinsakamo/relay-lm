from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import random
import re
from typing import Mapping, Sequence

from relaylm.v2_interventions import ResourceVector


CLAIM_STATUS = "R2_PREREGISTERED_DESIGN_ONLY"
REGIMES = (
    "EASY_SATURATED",
    "DEPTH_BENEFICIAL",
    "RETRIEVAL_BENEFICIAL",
    "OBSERVATION_BENEFICIAL",
    "UNCERTAINTY_TRAP",
)
OPERATIONS = ("ZERO", "THINK", "RETRIEVE", "OBSERVE")
TASKS_PER_REGIME = 8
TOTAL_TASKS = len(REGIMES) * TASKS_PER_REGIME
CONTEXT_LIMIT = 8192
BOOTSTRAP_RESAMPLES = 10_000
EXACT_TEST_ALPHA = 0.05
MATERIAL_TASK_GAIN = 4
HEURISTIC_ORACLE_GAP_MAX = 2
_HEX40 = re.compile(r"^[0-9a-fA-F]{40}$")
_OPERATION_PRIORITY = {"ZERO": 0, "THINK": 1, "RETRIEVE": 2, "OBSERVE": 3}


class R2PreregistrationError(ValueError):
    """Raised when a frozen R2 preregistration invariant is violated."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(*parts: object) -> str:
    digest = hashlib.sha256()
    for part in parts:
        if isinstance(part, bytes):
            payload = part
        elif isinstance(part, str):
            payload = part.encode("utf-8")
        else:
            payload = _canonical_json(part).encode("utf-8")
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return "sha256:" + digest.hexdigest()


def derive_root_seed(merged_pr_commit_sha: str) -> str:
    """Derive the R2 root seed from an immutable merged-commit identity."""
    if not _HEX40.fullmatch(merged_pr_commit_sha):
        raise R2PreregistrationError("merged PR commit must be exactly 40 hex characters")
    return _sha256("relaylm2-2187-r2", merged_pr_commit_sha.lower())


def _rng(root_seed: str, regime: str, index: int) -> random.Random:
    seed = _sha256(root_seed, regime, index)
    return random.Random(int(seed.split(":", 1)[1], 16))


def _opaque_task_id(root_seed: str, regime: str, index: int) -> str:
    digest = _sha256(root_seed, "task-id", regime, index).split(":", 1)[1]
    return "r2-" + digest[:16]


@dataclass(frozen=True)
class R2Task:
    task_id: str
    public_prompt: str
    expected_answer: str
    retrieval_available: bool
    observation_available: bool
    retrieval_packet: str | None
    observation_packet: str | None
    hidden_regime: str

    def __post_init__(self) -> None:
        if self.hidden_regime not in REGIMES:
            raise R2PreregistrationError("unknown hidden regime")
        if not self.task_id or not self.public_prompt or not self.expected_answer:
            raise R2PreregistrationError("task identity, prompt, and expected answer are required")
        if self.retrieval_available != (self.retrieval_packet is not None):
            raise R2PreregistrationError("retrieval availability must match packet presence")
        if self.observation_available != (self.observation_packet is not None):
            raise R2PreregistrationError("observation availability must match packet presence")
        if self.retrieval_available and self.observation_available:
            raise R2PreregistrationError("a primary R2 task exposes at most one external packet")
        if self.hidden_regime in self.public_prompt or self.hidden_regime in self.task_id:
            raise R2PreregistrationError("hidden regime leaked into deployable task identity")
        for hidden in (self.retrieval_packet, self.observation_packet):
            if hidden is not None and hidden in self.public_prompt:
                raise R2PreregistrationError("external packet leaked into public prompt")

    def public_mapping(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "prompt": self.public_prompt,
            "retrieval_available": self.retrieval_available,
            "observation_available": self.observation_available,
        }

    def legal_operations(self) -> tuple[str, ...]:
        values = ["ZERO", "THINK"]
        if self.retrieval_available:
            values.append("RETRIEVE")
        if self.observation_available:
            values.append("OBSERVE")
        return tuple(values)

    def packet_for(self, operation: str) -> str | None:
        if operation == "RETRIEVE":
            if self.retrieval_packet is None:
                raise R2PreregistrationError("RETRIEVE is unavailable for this task")
            return self.retrieval_packet
        if operation == "OBSERVE":
            if self.observation_packet is None:
                raise R2PreregistrationError("OBSERVE is unavailable for this task")
            return self.observation_packet
        if operation in {"ZERO", "THINK"}:
            return None
        raise R2PreregistrationError("undeclared operation")


def _make_task(root_seed: str, regime: str, index: int) -> R2Task:
    rng = _rng(root_seed, regime, index)
    task_id = _opaque_task_id(root_seed, regime, index)

    if regime == "EASY_SATURATED":
        a = rng.randint(11, 89)
        b = rng.randint(11, 89)
        prompt = f"Return the exact integer result of {a} + {b}."
        expected = str(a + b)
        retrieval = None
        observation = None
    elif regime == "DEPTH_BENEFICIAL":
        a = rng.randint(7, 31)
        b = rng.randint(4, 17)
        c = rng.randint(5, 41)
        modulus = rng.choice((11, 13, 17, 19, 23))
        prompt = (
            "Compute in this exact order: multiply "
            f"{a} by {b}, add {c}, then take the result modulo {modulus}. "
            "Return the exact integer."
        )
        expected = str((a * b + c) % modulus)
        retrieval = None
        observation = None
    elif regime == "RETRIEVAL_BENEFICIAL":
        key = f"K-{rng.randrange(10_000, 99_999)}"
        value = f"V-{rng.randrange(100_000, 999_999)}"
        prompt = (
            f"A frozen lookup table contains the value for key {key}, but the table "
            "is not included in the public prompt. Return the table value when it is "
            "available to you; otherwise return UNKNOWN."
        )
        expected = value
        retrieval = f"Frozen lookup record: key {key} has value {value}."
        observation = None
    elif regime == "OBSERVATION_BENEFICIAL":
        sensor = f"S-{rng.randrange(1000, 9999)}"
        state = rng.choice(("OPEN", "CLOSED", "GREEN", "AMBER"))
        prompt = (
            f"Report the current state of sensor {sensor}. The current reading is not "
            "included in the public prompt. Return the observed state when available; "
            "otherwise return UNKNOWN."
        )
        expected = state
        retrieval = None
        observation = f"Fresh observation: sensor {sensor} currently reports {state}."
    elif regime == "UNCERTAINTY_TRAP":
        card = f"C-{rng.randrange(10_000, 99_999)}"
        prompt = (
            f"A sealed card {card} has a color that is not revealed and no external "
            "packet is available. Do not guess. Return UNKNOWN when the evidence is "
            "insufficient."
        )
        expected = "UNKNOWN"
        retrieval = None
        observation = None
    else:
        raise R2PreregistrationError("unknown regime")

    return R2Task(
        task_id=task_id,
        public_prompt=prompt,
        expected_answer=expected,
        retrieval_available=retrieval is not None,
        observation_available=observation is not None,
        retrieval_packet=retrieval,
        observation_packet=observation,
        hidden_regime=regime,
    )


def generate_tasks(merged_pr_commit_sha: str) -> tuple[R2Task, ...]:
    root_seed = derive_root_seed(merged_pr_commit_sha)
    tasks = tuple(
        _make_task(root_seed, regime, index)
        for regime in REGIMES
        for index in range(TASKS_PER_REGIME)
    )
    if len(tasks) != TOTAL_TASKS or len({task.task_id for task in tasks}) != TOTAL_TASKS:
        raise R2PreregistrationError("R2 generator did not produce 40 unique tasks")
    return tasks


def _strict_json_object(text: str) -> dict[str, object]:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise R2PreregistrationError(f"duplicate JSON member: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(text, object_pairs_hook=reject_duplicates)
    except (json.JSONDecodeError, R2PreregistrationError) as exc:
        raise R2PreregistrationError("model output is not strict JSON") from exc
    if not isinstance(value, dict):
        raise R2PreregistrationError("model output must be a JSON object")
    return value


def parse_answer(text: str) -> str:
    payload = _strict_json_object(text)
    if set(payload) != {"answer"}:
        raise R2PreregistrationError("answer output must contain exactly answer")
    answer = payload["answer"]
    if not isinstance(answer, str) or not answer.strip():
        raise R2PreregistrationError("answer must be a non-empty string")
    return answer.strip()


def parse_operation(text: str, *, task: R2Task) -> str:
    payload = _strict_json_object(text)
    if set(payload) != {"operation"}:
        raise R2PreregistrationError("allocator output must contain exactly operation")
    operation = payload["operation"]
    if not isinstance(operation, str) or operation not in task.legal_operations():
        raise R2PreregistrationError("allocator selected an illegal operation")
    return operation


def answer_messages(task: R2Task) -> tuple[dict[str, str], ...]:
    return (
        {
            "role": "system",
            "content": (
                "Answer the task from the information currently available. "
                'Return strict JSON only as {"answer":"..."}. No other keys or prose.'
            ),
        },
        {"role": "user", "content": _canonical_json(task.public_mapping())},
    )


def allocator_messages(task: R2Task, *, base_answer: str) -> tuple[dict[str, str], ...]:
    legal = {
        "ZERO": "keep the current answer; no extra task-work model call",
        "THINK": "buy one revision call using only already-public information",
    }
    if task.retrieval_available:
        legal["RETRIEVE"] = "reveal the frozen retrieval packet, then buy one revision call"
    if task.observation_available:
        legal["OBSERVE"] = "reveal the frozen observation packet, then buy one revision call"
    packet = {
        **task.public_mapping(),
        "base_answer": base_answer,
        "legal_operations": legal,
    }
    return (
        {
            "role": "system",
            "content": (
                "Choose exactly one next cognitive operation with the best expected value. "
                "Use only the information in this request. Return strict JSON only as "
                '{"operation":"ZERO|THINK|RETRIEVE|OBSERVE"}. No prose.'
            ),
        },
        {"role": "user", "content": _canonical_json(packet)},
    )


def revision_messages(
    task: R2Task,
    *,
    base_answer: str,
    operation: str,
) -> tuple[dict[str, str], ...]:
    if operation == "ZERO":
        raise R2PreregistrationError("ZERO has no revision request")
    if operation not in task.legal_operations():
        raise R2PreregistrationError("operation is not legal for this task")
    packet: dict[str, object] = {
        **task.public_mapping(),
        "previous_answer": base_answer,
    }
    if operation == "THINK":
        instruction = "Reconsider the answer using only the already-public task information."
    elif operation == "RETRIEVE":
        packet["retrieved_information"] = task.packet_for(operation)
        instruction = "Use the newly revealed retrieval information."
    else:
        packet["observed_information"] = task.packet_for(operation)
        instruction = "Use the newly revealed observation."
    return (
        {
            "role": "system",
            "content": (
                instruction
                + ' Return strict JSON only as {"answer":"..."}. No other keys or prose.'
            ),
        },
        {"role": "user", "content": _canonical_json(packet)},
    )


def a0_policy(task: R2Task) -> str:
    del task
    return "THINK"


def a1_policy(task: R2Task) -> str:
    if task.retrieval_available:
        return "RETRIEVE"
    if task.observation_available:
        return "OBSERVE"
    return "ZERO"


@dataclass(frozen=True)
class PlannedProviderCall:
    task_id: str
    role: str
    operation: str | None


def physical_call_plan(tasks: Sequence[R2Task]) -> tuple[PlannedProviderCall, ...]:
    if len(tasks) != TOTAL_TASKS:
        raise R2PreregistrationError("physical call plan requires the exact 40-task suite")
    plan: list[PlannedProviderCall] = []
    for task in tasks:
        plan.append(PlannedProviderCall(task.task_id, "BASE", None))
        plan.append(PlannedProviderCall(task.task_id, "A2_ALLOCATE", None))
        plan.append(PlannedProviderCall(task.task_id, "BANK", "THINK"))
        if task.retrieval_available:
            plan.append(PlannedProviderCall(task.task_id, "BANK", "RETRIEVE"))
        if task.observation_available:
            plan.append(PlannedProviderCall(task.task_id, "BANK", "OBSERVE"))
    return tuple(plan)


@dataclass(frozen=True)
class OperationResult:
    operation: str
    answer: str
    correct: bool
    extra_cost: ResourceVector

    def __post_init__(self) -> None:
        if self.operation not in {"THINK", "RETRIEVE", "OBSERVE"}:
            raise R2PreregistrationError("operation-bank result must be non-ZERO")
        if not self.answer:
            raise R2PreregistrationError("operation-bank answer must be non-empty")
        if self.extra_cost.calls != 1:
            raise R2PreregistrationError("each bank operation result must cost one model call")


@dataclass(frozen=True)
class TaskOperationBank:
    task_id: str
    base_answer: str
    base_correct: bool
    base_cost: ResourceVector
    operation_results: tuple[OperationResult, ...]

    def __post_init__(self) -> None:
        if self.base_cost.calls != 1:
            raise R2PreregistrationError("base completion must cost exactly one model call")
        names = tuple(item.operation for item in self.operation_results)
        if len(names) != len(set(names)):
            raise R2PreregistrationError("duplicate operation-bank result")

    def result_for(self, operation: str) -> OperationResult:
        for item in self.operation_results:
            if item.operation == operation:
                return item
        raise R2PreregistrationError("operation result missing from bank")


@dataclass(frozen=True)
class CounterfactualOutcome:
    task_id: str
    arm_id: str
    operation: str
    answer: str
    correct: bool
    cost: ResourceVector


def counterfactual_outcome(
    task: R2Task,
    bank: TaskOperationBank,
    *,
    arm_id: str,
    operation: str,
    allocator_cost: ResourceVector = ResourceVector(),
) -> CounterfactualOutcome:
    if bank.task_id != task.task_id:
        raise R2PreregistrationError("task/bank identity mismatch")
    if operation not in task.legal_operations():
        raise R2PreregistrationError("arm selected an illegal operation")
    if operation == "ZERO":
        answer = bank.base_answer
        correct = bank.base_correct
        extra = ResourceVector()
    else:
        result = bank.result_for(operation)
        answer = result.answer
        correct = result.correct
        extra = result.extra_cost
    return CounterfactualOutcome(
        task_id=task.task_id,
        arm_id=arm_id,
        operation=operation,
        answer=answer,
        correct=correct,
        cost=bank.base_cost + allocator_cost + extra,
    )


@dataclass(frozen=True)
class OracleDecision:
    operation: str
    correct: bool
    oracle_no_headroom: bool


def _pareto_dominates(left: ResourceVector, right: ResourceVector) -> bool:
    left_values = left.as_tuple()
    right_values = right.as_tuple()
    return all(a <= b for a, b in zip(left_values, right_values, strict=True)) and any(
        a < b for a, b in zip(left_values, right_values, strict=True)
    )


def a3_oracle(task: R2Task, bank: TaskOperationBank) -> OracleDecision:
    candidates: list[tuple[str, bool, ResourceVector]] = [
        ("ZERO", bank.base_correct, ResourceVector())
    ]
    for operation in task.legal_operations():
        if operation == "ZERO":
            continue
        result = bank.result_for(operation)
        candidates.append((operation, result.correct, result.extra_cost))

    correct = [item for item in candidates if item[1]]
    if not correct:
        return OracleDecision(operation="ZERO", correct=False, oracle_no_headroom=True)

    frontier = [
        candidate
        for candidate in correct
        if not any(
            _pareto_dominates(other[2], candidate[2])
            for other in correct
            if other is not candidate
        )
    ]
    chosen = min(frontier, key=lambda item: _OPERATION_PRIORITY[item[0]])
    return OracleDecision(
        operation=chosen[0],
        correct=True,
        oracle_no_headroom=False,
    )


@dataclass(frozen=True)
class R2BudgetContract:
    task_count: int
    bank_provider_call_max: int
    a2_allocator_call_max: int
    physical_provider_call_max: int
    treatment_call_ceiling_per_arm: int
    retrieval_unit_ceiling_per_arm: int
    observation_unit_ceiling_per_arm: int
    context_limit: int
    aggregate_input_token_ceiling: int | None
    aggregate_output_token_ceiling: int | None
    automatic_retry: bool
    semantic_retry: bool


def derive_budget_contract(tasks: Sequence[R2Task]) -> R2BudgetContract:
    if len(tasks) != TOTAL_TASKS:
        raise R2PreregistrationError("budget contract requires the exact 40-task suite")
    plan = physical_call_plan(tasks)
    bank_calls = sum(item.role != "A2_ALLOCATE" for item in plan)
    allocator_calls = sum(item.role == "A2_ALLOCATE" for item in plan)
    return R2BudgetContract(
        task_count=len(tasks),
        bank_provider_call_max=bank_calls,
        a2_allocator_call_max=allocator_calls,
        physical_provider_call_max=len(plan),
        treatment_call_ceiling_per_arm=3 * len(tasks),
        retrieval_unit_ceiling_per_arm=sum(task.retrieval_available for task in tasks),
        observation_unit_ceiling_per_arm=sum(task.observation_available for task in tasks),
        context_limit=CONTEXT_LIMIT,
        aggregate_input_token_ceiling=None,
        aggregate_output_token_ceiling=None,
        automatic_retry=False,
        semantic_retry=False,
    )


def paired_directional_exact_pvalue(
    treatment: Sequence[bool],
    baseline: Sequence[bool],
) -> float:
    if len(treatment) != len(baseline) or not treatment:
        raise R2PreregistrationError("paired vectors must have equal non-zero length")
    wins = sum(a and not b for a, b in zip(treatment, baseline, strict=True))
    losses = sum(b and not a for a, b in zip(treatment, baseline, strict=True))
    discordant = wins + losses
    if discordant == 0:
        return 1.0
    return sum(math.comb(discordant, k) for k in range(wins, discordant + 1)) / (
        2**discordant
    )


def paired_bootstrap_interval(
    treatment: Sequence[bool],
    baseline: Sequence[bool],
    *,
    seed: str,
    resamples: int = BOOTSTRAP_RESAMPLES,
    alpha: float = 0.05,
) -> tuple[float, float]:
    if len(treatment) != len(baseline) or not treatment:
        raise R2PreregistrationError("paired vectors must have equal non-zero length")
    if resamples <= 0 or not 0 < alpha < 1:
        raise R2PreregistrationError("invalid bootstrap contract")
    rng = random.Random(int(_sha256("r2-bootstrap", seed).split(":", 1)[1], 16))
    n = len(treatment)
    deltas: list[float] = []
    for _ in range(resamples):
        total = 0
        for _ in range(n):
            index = rng.randrange(n)
            total += int(treatment[index]) - int(baseline[index])
        deltas.append(total / n)
    deltas.sort()
    low_index = max(0, math.floor((alpha / 2) * resamples))
    high_index = min(resamples - 1, math.ceil((1 - alpha / 2) * resamples) - 1)
    return deltas[low_index], deltas[high_index]


@dataclass(frozen=True)
class R2Interpretation:
    category: str
    counts: Mapping[str, int]
    a2_minus_a0: int
    a2_minus_a1: int
    oracle_headroom_over_fixed: int
    a2_vs_a0_pvalue: float
    a2_vs_a1_pvalue: float


def interpret_r2(
    correctness: Mapping[str, Sequence[bool]],
    *,
    resource_accounting_complete: bool,
    hard_constraint_violations: int,
    protocol_invalid_count: int,
) -> R2Interpretation:
    required = ("A0", "A1", "A2", "A3")
    if set(correctness) != set(required):
        raise R2PreregistrationError("R2 interpretation requires exactly A0/A1/A2/A3")
    vectors = {key: tuple(bool(value) for value in correctness[key]) for key in required}
    if any(len(values) != TOTAL_TASKS for values in vectors.values()):
        raise R2PreregistrationError("each R2 arm must contain exactly 40 task outcomes")
    counts = {key: sum(values) for key, values in vectors.items()}
    if counts["A3"] < max(counts["A0"], counts["A1"], counts["A2"]):
        raise R2PreregistrationError("oracle accuracy cannot be below a deployable arm")

    a2_minus_a0 = counts["A2"] - counts["A0"]
    a2_minus_a1 = counts["A2"] - counts["A1"]
    oracle_headroom = counts["A3"] - counts["A0"]
    p_a0 = paired_directional_exact_pvalue(vectors["A2"], vectors["A0"])
    p_a1 = paired_directional_exact_pvalue(vectors["A2"], vectors["A1"])

    if (
        not resource_accounting_complete
        or hard_constraint_violations
        or protocol_invalid_count
    ):
        category = "INCONCLUSIVE"
    elif oracle_headroom < MATERIAL_TASK_GAIN:
        category = "NO_ORACLE_HEADROOM"
    elif (
        a2_minus_a0 >= MATERIAL_TASK_GAIN
        and a2_minus_a1 >= MATERIAL_TASK_GAIN
        and p_a0 <= EXACT_TEST_ALPHA
        and p_a1 <= EXACT_TEST_ALPHA
    ):
        category = "ADAPTIVE_SIGNAL"
    elif counts["A3"] - counts["A1"] <= HEURISTIC_ORACLE_GAP_MAX:
        category = "HEURISTIC_SUFFICIENT"
    else:
        category = "ALLOCATOR_FAILURE"

    return R2Interpretation(
        category=category,
        counts=counts,
        a2_minus_a0=a2_minus_a0,
        a2_minus_a1=a2_minus_a1,
        oracle_headroom_over_fixed=oracle_headroom,
        a2_vs_a0_pvalue=p_a0,
        a2_vs_a1_pvalue=p_a1,
    )


@dataclass(frozen=True)
class R2Preregistration:
    merged_pr_commit_sha: str
    root_seed: str
    tasks: tuple[R2Task, ...]
    budget: R2BudgetContract

    @property
    def digest(self) -> str:
        task_payload = [
            {
                "task_id": task.task_id,
                "public_prompt": task.public_prompt,
                "expected_answer": task.expected_answer,
                "retrieval_available": task.retrieval_available,
                "observation_available": task.observation_available,
                "retrieval_packet": task.retrieval_packet,
                "observation_packet": task.observation_packet,
                "hidden_regime": task.hidden_regime,
            }
            for task in self.tasks
        ]
        return _sha256(
            "relaylm2-cognitive-work-r2-preregistration",
            self.merged_pr_commit_sha,
            self.root_seed,
            task_payload,
            {
                "operations": OPERATIONS,
                "tasks_per_regime": TASKS_PER_REGIME,
                "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
                "exact_test_alpha": EXACT_TEST_ALPHA,
                "material_task_gain": MATERIAL_TASK_GAIN,
                "heuristic_oracle_gap_max": HEURISTIC_ORACLE_GAP_MAX,
                "budget": self.budget.__dict__,
                "physical_call_plan": [item.__dict__ for item in physical_call_plan(self.tasks)],
                "oracle_tie_break": "pareto-frontier-then-fixed-operation-priority",
            },
        )


def build_preregistration(merged_pr_commit_sha: str) -> R2Preregistration:
    tasks = generate_tasks(merged_pr_commit_sha)
    return R2Preregistration(
        merged_pr_commit_sha=merged_pr_commit_sha.lower(),
        root_seed=derive_root_seed(merged_pr_commit_sha),
        tasks=tasks,
        budget=derive_budget_contract(tasks),
    )
