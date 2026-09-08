from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import random
import re
from typing import Mapping, Sequence

from tools import v2_cognitive_work_r2_preregistration as r2_v1
from tools import v2_cognitive_work_r2_structured_preregistration as r2


CLAIM_STATUS = "R4_SHIFT_PREREGISTERED_DESIGN_ONLY"
PREREGISTRATION_VERSION = "relaylm2-cognitive-work-r4-availability-shift-v1"
ROOT_SEED_DOMAIN = "relaylm2-2187-r4-availability-decorrelation-v1"
REGIMES = r2.REGIMES
TASKS_PER_REGIME = 4
TASK_COUNT = len(REGIMES) * TASKS_PER_REGIME
CONTEXT_LIMIT = r2.CONTEXT_LIMIT
BOOTSTRAP_RESAMPLES = r2.BOOTSTRAP_RESAMPLES
EXACT_TEST_ALPHA = r2.EXACT_TEST_ALPHA
MATERIAL_TASK_GAIN = r2.MATERIAL_TASK_GAIN
HEURISTIC_ORACLE_GAP_MAX = r2.HEURISTIC_ORACLE_GAP_MAX
QUALIFIED_TRANSPORT_VERSION = r2.QUALIFIED_TRANSPORT_VERSION

R4PreregistrationError = r2.R2PreregistrationError
PlannedProviderCall = r2.PlannedProviderCall
OperationResult = r2.OperationResult
TaskOperationBank = r2.TaskOperationBank
CounterfactualOutcome = r2.CounterfactualOutcome
OracleDecision = r2.OracleDecision
R2BudgetContract = r2.R2BudgetContract

# Preserve the exact R2-tested policy/message/parser/statistic semantics.
a0_policy = r2.a0_policy
a1_policy = r2.a1_policy
a3_oracle = r2.a3_oracle
counterfactual_outcome = r2.counterfactual_outcome
answer_messages = r2.answer_messages
revision_messages = r2.revision_messages
allocator_messages = r2.allocator_messages
parse_answer = r2.parse_answer
parse_operation = r2.parse_operation
paired_directional_exact_pvalue = r2.paired_directional_exact_pvalue
paired_bootstrap_interval = r2.paired_bootstrap_interval
schema_kind_for_call = r2.schema_kind_for_call
response_format_for_call = r2.response_format_for_call
validate_qualified_transport = r2.validate_qualified_transport

_HEX40 = re.compile(r"^[0-9a-fA-F]{40}$")
_AUX_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


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
    if not _HEX40.fullmatch(merged_pr_commit_sha):
        raise R4PreregistrationError("merged PR commit must be exactly 40 hex characters")
    return _sha256(ROOT_SEED_DOMAIN, merged_pr_commit_sha.lower())


def _rng(root_seed: str, regime: str, index: int) -> random.Random:
    seed = _sha256(root_seed, "r4-auxiliary", regime, index)
    return random.Random(int(seed.split(":", 1)[1], 16))


def _opaque_task_id(root_seed: str, regime: str, index: int) -> str:
    digest = _sha256(root_seed, "r4-task-id", regime, index).split(":", 1)[1]
    return "r4s-" + digest[:16]


def _letters(rng: random.Random, length: int) -> str:
    return "".join(rng.choice(_AUX_ALPHABET) for _ in range(length))


@dataclass(frozen=True)
class R4ShiftTask:
    task_id: str
    public_prompt: str
    expected_answer: str
    retrieval_packet: str
    observation_packet: str
    hidden_regime: str
    retrieval_available: bool = True
    observation_available: bool = True

    def __post_init__(self) -> None:
        if self.hidden_regime not in REGIMES:
            raise R4PreregistrationError("unknown hidden regime")
        if not self.task_id or not self.public_prompt or not self.expected_answer:
            raise R4PreregistrationError("task identity, prompt, and expected answer are required")
        if not self.retrieval_packet or not self.observation_packet:
            raise R4PreregistrationError("R4 shift requires both external packets")
        if not self.retrieval_available or not self.observation_available:
            raise R4PreregistrationError("R4 shift requires both availability cues on every task")
        if self.hidden_regime in self.public_prompt or self.hidden_regime in self.task_id:
            raise R4PreregistrationError("hidden regime leaked into deployable task identity")
        if self.retrieval_packet in self.public_prompt or self.observation_packet in self.public_prompt:
            raise R4PreregistrationError("external packet leaked into public prompt")

    def public_mapping(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "prompt": self.public_prompt,
            "retrieval_available": True,
            "observation_available": True,
        }

    def legal_operations(self) -> tuple[str, ...]:
        return ("ZERO", "THINK", "RETRIEVE", "OBSERVE")

    def packet_for(self, operation: str) -> str | None:
        if operation == "RETRIEVE":
            return self.retrieval_packet
        if operation == "OBSERVE":
            return self.observation_packet
        if operation in {"ZERO", "THINK"}:
            return None
        raise R4PreregistrationError("undeclared operation")


def _auxiliary_packets(
    root_seed: str,
    regime: str,
    index: int,
    *,
    expected_answer: str,
) -> tuple[str, str]:
    rng = _rng(root_seed, regime, index)
    while True:
        aux_key = f"AK-{_letters(rng, 6)}"
        aux_value = f"AV-{_letters(rng, 8)}"
        aux_sensor = f"AS-{_letters(rng, 6)}"
        aux_state = rng.choice(("BLUE", "WHITE", "STEADY", "IDLE"))
        retrieval = f"Frozen auxiliary record: key {aux_key} has value {aux_value}."
        observation = (
            f"Fresh auxiliary observation: sensor {aux_sensor} currently reports {aux_state}."
        )
        if expected_answer not in retrieval and expected_answer not in observation:
            return retrieval, observation


def generate_tasks(merged_pr_commit_sha: str) -> tuple[R4ShiftTask, ...]:
    root_seed = derive_root_seed(merged_pr_commit_sha)
    tasks: list[R4ShiftTask] = []
    for regime in REGIMES:
        for index in range(TASKS_PER_REGIME):
            inherited = r2_v1._make_task(root_seed, regime, index)
            aux_retrieval, aux_observation = _auxiliary_packets(
                root_seed,
                regime,
                index,
                expected_answer=inherited.expected_answer,
            )
            retrieval_packet = inherited.retrieval_packet or aux_retrieval
            observation_packet = inherited.observation_packet or aux_observation
            task = R4ShiftTask(
                task_id=_opaque_task_id(root_seed, regime, index),
                public_prompt=inherited.public_prompt,
                expected_answer=inherited.expected_answer,
                retrieval_packet=retrieval_packet,
                observation_packet=observation_packet,
                hidden_regime=regime,
            )
            tasks.append(task)

    result = tuple(tasks)
    if len(result) != TASK_COUNT or len({task.task_id for task in result}) != TASK_COUNT:
        raise R4PreregistrationError("R4 shift generator did not produce 20 unique tasks")
    counts = {regime: sum(task.hidden_regime == regime for task in result) for regime in REGIMES}
    if any(count != TASKS_PER_REGIME for count in counts.values()):
        raise R4PreregistrationError("R4 shift generator is not balanced across regimes")
    return result


def physical_call_plan(tasks: Sequence[R4ShiftTask]) -> tuple[PlannedProviderCall, ...]:
    if len(tasks) != TASK_COUNT:
        raise R4PreregistrationError("R4 shift call plan requires exactly 20 tasks")
    plan: list[PlannedProviderCall] = []
    for task in tasks:
        if task.legal_operations() != ("ZERO", "THINK", "RETRIEVE", "OBSERVE"):
            raise R4PreregistrationError("R4 task operation surface drifted")
        plan.extend(
            (
                PlannedProviderCall(task.task_id, "BASE", None),
                PlannedProviderCall(task.task_id, "A2_ALLOCATE", None),
                PlannedProviderCall(task.task_id, "BANK", "THINK"),
                PlannedProviderCall(task.task_id, "BANK", "RETRIEVE"),
                PlannedProviderCall(task.task_id, "BANK", "OBSERVE"),
            )
        )
    result = tuple(plan)
    if len(result) != 100:
        raise R4PreregistrationError("R4 shift physical plan must contain exactly 100 calls")
    return result


def derive_budget_contract(tasks: Sequence[R4ShiftTask]) -> R2BudgetContract:
    plan = physical_call_plan(tasks)
    bank_calls = sum(item.role != "A2_ALLOCATE" for item in plan)
    allocator_calls = sum(item.role == "A2_ALLOCATE" for item in plan)
    return R2BudgetContract(
        task_count=len(tasks),
        bank_provider_call_max=bank_calls,
        a2_allocator_call_max=allocator_calls,
        physical_provider_call_max=len(plan),
        treatment_call_ceiling_per_arm=3 * len(tasks),
        retrieval_unit_ceiling_per_arm=len(tasks),
        observation_unit_ceiling_per_arm=len(tasks),
        context_limit=CONTEXT_LIMIT,
        aggregate_input_token_ceiling=None,
        aggregate_output_token_ceiling=None,
        automatic_retry=False,
        semantic_retry=False,
    )


@dataclass(frozen=True)
class R4ShiftInterpretation:
    category: str
    counts: Mapping[str, int]
    oracle_headroom_over_fixed: int
    shift_headroom_over_heuristic: int
    adaptive_minus_heuristic: int
    adaptive_minus_fixed: int
    a2_vs_a1_pvalue: float


def _validated_correctness(
    correctness: Mapping[str, Sequence[bool]],
) -> dict[str, tuple[bool, ...]]:
    expected_arms = {"A0", "A1", "A2", "A3"}
    if set(correctness) != expected_arms:
        raise R4PreregistrationError("R4 interpretation requires A0/A1/A2/A3")
    result: dict[str, tuple[bool, ...]] = {}
    for arm in sorted(expected_arms):
        values = tuple(correctness[arm])
        if len(values) != TASK_COUNT or any(not isinstance(value, bool) for value in values):
            raise R4PreregistrationError(
                "each R4 correctness vector must contain exactly 20 booleans"
            )
        result[arm] = values
    return result


def interpret_r4_shift(
    correctness: Mapping[str, Sequence[bool]],
    *,
    resource_accounting_complete: bool,
    hard_constraint_violations: int,
    protocol_invalid_count: int,
) -> R4ShiftInterpretation:
    values = _validated_correctness(correctness)
    counts = {arm: sum(items) for arm, items in values.items()}
    oracle_headroom_fixed = counts["A3"] - counts["A0"]
    shift_headroom = counts["A3"] - counts["A1"]
    adaptive_delta = counts["A2"] - counts["A1"]
    adaptive_minus_fixed = counts["A2"] - counts["A0"]
    p_a1 = paired_directional_exact_pvalue(values["A2"], values["A1"])

    if (
        not resource_accounting_complete
        or hard_constraint_violations != 0
        or protocol_invalid_count != 0
    ):
        category = "INCONCLUSIVE"
    elif shift_headroom <= HEURISTIC_ORACLE_GAP_MAX:
        category = "HEURISTIC_TRANSFER_SUFFICIENT"
    elif shift_headroom < MATERIAL_TASK_GAIN:
        category = "NO_MATERIAL_SHIFT_HEADROOM"
    elif counts["A0"] - counts["A2"] >= MATERIAL_TASK_GAIN:
        category = "SIMPLE_FIXED_BASELINE_SUFFICIENT"
    elif adaptive_delta >= MATERIAL_TASK_GAIN and p_a1 <= EXACT_TEST_ALPHA:
        category = "ADAPTIVE_TRANSFER_SIGNAL"
    else:
        category = "SHIFT_HEADROOM_UNCAPTURED"

    return R4ShiftInterpretation(
        category=category,
        counts=counts,
        oracle_headroom_over_fixed=oracle_headroom_fixed,
        shift_headroom_over_heuristic=shift_headroom,
        adaptive_minus_heuristic=adaptive_delta,
        adaptive_minus_fixed=adaptive_minus_fixed,
        a2_vs_a1_pvalue=p_a1,
    )


@dataclass(frozen=True)
class R4ShiftPreregistration:
    merged_pr_commit_sha: str
    root_seed: str
    tasks: tuple[R4ShiftTask, ...]
    budget: R2BudgetContract

    @property
    def digest(self) -> str:
        plan = physical_call_plan(self.tasks)
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
            PREREGISTRATION_VERSION,
            self.merged_pr_commit_sha,
            self.root_seed,
            task_payload,
            {
                "regimes": REGIMES,
                "tasks_per_regime": TASKS_PER_REGIME,
                "task_count": TASK_COUNT,
                "shift": "all-operations-publicly-available-usefulness-remains-regime-dependent",
                "distractor_semantics": "deterministic-task-scoped-auxiliary-record-and-observation",
                "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
                "exact_test_alpha": EXACT_TEST_ALPHA,
                "material_task_gain": MATERIAL_TASK_GAIN,
                "heuristic_oracle_gap_max": HEURISTIC_ORACLE_GAP_MAX,
                "budget": self.budget.__dict__,
                "physical_call_plan": [item.__dict__ for item in plan],
                "root_seed_domain": ROOT_SEED_DOMAIN,
                "semantic_predecessor": r2.CLAIM_STATUS,
                "policy_identity": {
                    "a0": "inherited-r2-fixed-think",
                    "a1": "inherited-r2-retrieval-first-unchanged",
                    "a2": "inherited-r2-model-allocator-unchanged",
                    "a3": "inherited-r2-evaluator-oracle-unchanged",
                },
                "transport": {
                    "qualification_version": QUALIFIED_TRANSPORT_VERSION,
                    "answer_schema_digest": r2.EXPECTED_ANSWER_SCHEMA_DIGEST,
                    "operation_schema_digest": r2.EXPECTED_OPERATION_SCHEMA_DIGEST,
                    "answer_response_format_digest": r2.EXPECTED_ANSWER_RESPONSE_FORMAT_DIGEST,
                    "operation_response_format_digest": r2.EXPECTED_OPERATION_RESPONSE_FORMAT_DIGEST,
                    "per_call_schema_kind": [schema_kind_for_call(item) for item in plan],
                },
                "interpretation_order": (
                    "INCONCLUSIVE",
                    "HEURISTIC_TRANSFER_SUFFICIENT",
                    "NO_MATERIAL_SHIFT_HEADROOM",
                    "SIMPLE_FIXED_BASELINE_SUFFICIENT",
                    "ADAPTIVE_TRANSFER_SIGNAL",
                    "SHIFT_HEADROOM_UNCAPTURED",
                ),
            },
        )


def build_preregistration(merged_pr_commit_sha: str) -> R4ShiftPreregistration:
    validate_qualified_transport()
    tasks = generate_tasks(merged_pr_commit_sha)
    return R4ShiftPreregistration(
        merged_pr_commit_sha=merged_pr_commit_sha.lower(),
        root_seed=derive_root_seed(merged_pr_commit_sha),
        tasks=tasks,
        budget=derive_budget_contract(tasks),
    )
