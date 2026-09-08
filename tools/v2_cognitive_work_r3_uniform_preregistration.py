from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Mapping, Sequence

from tools import v2_cognitive_work_r2_preregistration as r2_v1
from tools import v2_cognitive_work_r2_structured_preregistration as r2


CLAIM_STATUS = "R3_UNIFORM_PREREGISTERED_DESIGN_ONLY"
PREREGISTRATION_VERSION = "relaylm2-cognitive-work-r3-uniform-v1"
ROOT_SEED_DOMAIN = "relaylm2-2187-r3-uniform-retrieval-v1"
UNIFORM_REGIME = "RETRIEVAL_BENEFICIAL"
TASK_COUNT = 16
CONTEXT_LIMIT = r2.CONTEXT_LIMIT
BOOTSTRAP_RESAMPLES = r2.BOOTSTRAP_RESAMPLES
EXACT_TEST_ALPHA = r2.EXACT_TEST_ALPHA
MATERIAL_TASK_GAIN = r2.MATERIAL_TASK_GAIN
HEURISTIC_ORACLE_GAP_MAX = r2.HEURISTIC_ORACLE_GAP_MAX
QUALIFIED_TRANSPORT_VERSION = r2.QUALIFIED_TRANSPORT_VERSION

R3PreregistrationError = r2.R2PreregistrationError
R2Task = r2.R2Task
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
        raise R3PreregistrationError("merged PR commit must be exactly 40 hex characters")
    return _sha256(ROOT_SEED_DOMAIN, merged_pr_commit_sha.lower())


def _opaque_task_id(root_seed: str, index: int) -> str:
    digest = _sha256(root_seed, "r3-task-id", UNIFORM_REGIME, index).split(":", 1)[1]
    return "r3u-" + digest[:16]


def generate_tasks(merged_pr_commit_sha: str) -> tuple[R2Task, ...]:
    root_seed = derive_root_seed(merged_pr_commit_sha)
    tasks: list[R2Task] = []
    for index in range(TASK_COUNT):
        inherited = r2_v1._make_task(root_seed, UNIFORM_REGIME, index)
        task = R2Task(
            task_id=_opaque_task_id(root_seed, index),
            public_prompt=inherited.public_prompt,
            expected_answer=inherited.expected_answer,
            retrieval_available=inherited.retrieval_available,
            observation_available=inherited.observation_available,
            retrieval_packet=inherited.retrieval_packet,
            observation_packet=inherited.observation_packet,
            hidden_regime=inherited.hidden_regime,
        )
        if not task.retrieval_available or task.observation_available:
            raise R3PreregistrationError(
                "R3 uniform task must expose retrieval and must not expose observation"
            )
        tasks.append(task)
    result = tuple(tasks)
    if len(result) != TASK_COUNT or len({task.task_id for task in result}) != TASK_COUNT:
        raise R3PreregistrationError("R3 uniform generator did not produce 16 unique tasks")
    return result


def physical_call_plan(tasks: Sequence[R2Task]) -> tuple[PlannedProviderCall, ...]:
    if len(tasks) != TASK_COUNT:
        raise R3PreregistrationError("R3 uniform call plan requires exactly 16 tasks")
    plan: list[PlannedProviderCall] = []
    for task in tasks:
        if task.hidden_regime != UNIFORM_REGIME:
            raise R3PreregistrationError("R3 uniform suite contains a non-retrieval regime")
        if not task.retrieval_available or task.observation_available:
            raise R3PreregistrationError("R3 uniform task operation surface drifted")
        plan.extend(
            (
                PlannedProviderCall(task.task_id, "BASE", None),
                PlannedProviderCall(task.task_id, "A2_ALLOCATE", None),
                PlannedProviderCall(task.task_id, "BANK", "THINK"),
                PlannedProviderCall(task.task_id, "BANK", "RETRIEVE"),
            )
        )
    result = tuple(plan)
    if len(result) != 64:
        raise R3PreregistrationError("R3 uniform physical plan must contain exactly 64 calls")
    return result


def derive_budget_contract(tasks: Sequence[R2Task]) -> R2BudgetContract:
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
        observation_unit_ceiling_per_arm=0,
        context_limit=CONTEXT_LIMIT,
        aggregate_input_token_ceiling=None,
        aggregate_output_token_ceiling=None,
        automatic_retry=False,
        semantic_retry=False,
    )


@dataclass(frozen=True)
class R3UniformInterpretation:
    category: str
    counts: Mapping[str, int]
    oracle_headroom_over_fixed: int
    heuristic_oracle_gap: int
    adaptive_minus_heuristic: int
    a2_vs_a1_pvalue: float


def _validated_correctness(
    correctness: Mapping[str, Sequence[bool]],
) -> dict[str, tuple[bool, ...]]:
    expected_arms = {"A0", "A1", "A2", "A3"}
    if set(correctness) != expected_arms:
        raise R3PreregistrationError("R3 interpretation requires A0/A1/A2/A3")
    result: dict[str, tuple[bool, ...]] = {}
    for arm in sorted(expected_arms):
        values = tuple(correctness[arm])
        if len(values) != TASK_COUNT or any(not isinstance(value, bool) for value in values):
            raise R3PreregistrationError(
                "each R3 correctness vector must contain exactly 16 booleans"
            )
        result[arm] = values
    return result


def interpret_r3_uniform(
    correctness: Mapping[str, Sequence[bool]],
    *,
    resource_accounting_complete: bool,
    hard_constraint_violations: int,
    protocol_invalid_count: int,
) -> R3UniformInterpretation:
    values = _validated_correctness(correctness)
    counts = {arm: sum(items) for arm, items in values.items()}
    oracle_headroom = counts["A3"] - counts["A0"]
    heuristic_gap = counts["A3"] - counts["A1"]
    adaptive_delta = counts["A2"] - counts["A1"]
    p_a1 = paired_directional_exact_pvalue(values["A2"], values["A1"])

    if (
        not resource_accounting_complete
        or hard_constraint_violations != 0
        or protocol_invalid_count != 0
    ):
        category = "INCONCLUSIVE"
    elif oracle_headroom < MATERIAL_TASK_GAIN:
        category = "NO_USEFUL_WORK_HEADROOM"
    elif adaptive_delta >= MATERIAL_TASK_GAIN and p_a1 <= EXACT_TEST_ALPHA:
        category = "UNIFORM_NULL_VIOLATION"
    elif heuristic_gap <= HEURISTIC_ORACLE_GAP_MAX:
        category = "HEURISTIC_SUFFICIENT_UNIFORM"
    else:
        category = "UNIFORM_NULL_CONSISTENT"

    return R3UniformInterpretation(
        category=category,
        counts=counts,
        oracle_headroom_over_fixed=oracle_headroom,
        heuristic_oracle_gap=heuristic_gap,
        adaptive_minus_heuristic=adaptive_delta,
        a2_vs_a1_pvalue=p_a1,
    )


@dataclass(frozen=True)
class R3UniformPreregistration:
    merged_pr_commit_sha: str
    root_seed: str
    tasks: tuple[R2Task, ...]
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
                "uniform_regime": UNIFORM_REGIME,
                "task_count": TASK_COUNT,
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
                    "a1": "inherited-r2-retrieval-if-available",
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
                    "NO_USEFUL_WORK_HEADROOM",
                    "UNIFORM_NULL_VIOLATION",
                    "HEURISTIC_SUFFICIENT_UNIFORM",
                    "UNIFORM_NULL_CONSISTENT",
                ),
            },
        )


def build_preregistration(merged_pr_commit_sha: str) -> R3UniformPreregistration:
    validate_qualified_transport()
    tasks = generate_tasks(merged_pr_commit_sha)
    return R3UniformPreregistration(
        merged_pr_commit_sha=merged_pr_commit_sha.lower(),
        root_seed=derive_root_seed(merged_pr_commit_sha),
        tasks=tasks,
        budget=derive_budget_contract(tasks),
    )
