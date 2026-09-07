from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from tools import v2_cognitive_work_r2_preregistration as r2_v1


CLAIM_STATUS = "R2_REPLACEMENT_PREREGISTERED_DESIGN_ONLY"
ANSWER_PROTOCOL_VERSION = "canonical-string-or-integer-v2"
ROOT_SEED_DOMAIN = "relaylm2-2187-r2-replacement-v2"
ORIGINAL_ROOT_SEED_DOMAIN = "relaylm2-2187-r2"

REGIMES = r2_v1.REGIMES
OPERATIONS = r2_v1.OPERATIONS
TASKS_PER_REGIME = r2_v1.TASKS_PER_REGIME
TOTAL_TASKS = r2_v1.TOTAL_TASKS
CONTEXT_LIMIT = r2_v1.CONTEXT_LIMIT
BOOTSTRAP_RESAMPLES = r2_v1.BOOTSTRAP_RESAMPLES
EXACT_TEST_ALPHA = r2_v1.EXACT_TEST_ALPHA
MATERIAL_TASK_GAIN = r2_v1.MATERIAL_TASK_GAIN
HEURISTIC_ORACLE_GAP_MAX = r2_v1.HEURISTIC_ORACLE_GAP_MAX

R2PreregistrationError = r2_v1.R2PreregistrationError
R2Task = r2_v1.R2Task
PlannedProviderCall = r2_v1.PlannedProviderCall
OperationResult = r2_v1.OperationResult
TaskOperationBank = r2_v1.TaskOperationBank
CounterfactualOutcome = r2_v1.CounterfactualOutcome
OracleDecision = r2_v1.OracleDecision
R2BudgetContract = r2_v1.R2BudgetContract
R2Interpretation = r2_v1.R2Interpretation

a0_policy = r2_v1.a0_policy
a1_policy = r2_v1.a1_policy
a3_oracle = r2_v1.a3_oracle
counterfactual_outcome = r2_v1.counterfactual_outcome
derive_budget_contract = r2_v1.derive_budget_contract
physical_call_plan = r2_v1.physical_call_plan
parse_operation = r2_v1.parse_operation
paired_directional_exact_pvalue = r2_v1.paired_directional_exact_pvalue
paired_bootstrap_interval = r2_v1.paired_bootstrap_interval
interpret_r2 = r2_v1.interpret_r2
allocator_messages = r2_v1.allocator_messages

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
    """Derive an unseen replacement-suite seed from its own merged identity."""
    if not _HEX40.fullmatch(merged_pr_commit_sha):
        raise R2PreregistrationError("merged PR commit must be exactly 40 hex characters")
    return _sha256(ROOT_SEED_DOMAIN, merged_pr_commit_sha.lower())


def generate_tasks(merged_pr_commit_sha: str) -> tuple[R2Task, ...]:
    """Reuse the frozen v1 task generator semantics under a fresh seed domain."""
    root_seed = derive_root_seed(merged_pr_commit_sha)
    tasks = tuple(
        r2_v1._make_task(root_seed, regime, index)
        for regime in REGIMES
        for index in range(TASKS_PER_REGIME)
    )
    if len(tasks) != TOTAL_TASKS or len({task.task_id for task in tasks}) != TOTAL_TASKS:
        raise R2PreregistrationError("replacement R2 generator did not produce 40 unique tasks")
    return tasks


def _strict_json_object(text: str) -> dict[str, object]:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise R2PreregistrationError(f"duplicate JSON member: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise R2PreregistrationError(f"non-standard JSON numeric constant: {value}")

    try:
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except R2PreregistrationError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise R2PreregistrationError("model output is not strict JSON") from exc
    if not isinstance(value, dict):
        raise R2PreregistrationError("model output must be a JSON object")
    return value


def parse_answer(text: str) -> str:
    """Canonicalize representation-only string/integer variation without evaluator truth."""
    payload = _strict_json_object(text)
    if set(payload) != {"answer"}:
        raise R2PreregistrationError("answer output must contain exactly answer")
    answer = payload["answer"]
    if isinstance(answer, bool):
        raise R2PreregistrationError("answer must be a non-empty string or integer")
    if isinstance(answer, int):
        return str(answer)
    if isinstance(answer, str) and answer.strip():
        return answer.strip()
    raise R2PreregistrationError("answer must be a non-empty string or integer")


def _answer_protocol_instruction(prefix: str) -> str:
    return (
        prefix
        + " Return strict JSON with exactly one key named answer. "
        "The answer value must be either a non-empty JSON string or a JSON integer. "
        "Return no other keys or prose."
    )


def answer_messages(task: R2Task) -> tuple[dict[str, str], ...]:
    return (
        {
            "role": "system",
            "content": _answer_protocol_instruction(
                "Answer the task from the information currently available."
            ),
        },
        {"role": "user", "content": _canonical_json(task.public_mapping())},
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
        {"role": "system", "content": _answer_protocol_instruction(instruction)},
        {"role": "user", "content": _canonical_json(packet)},
    )


@dataclass(frozen=True)
class R2ReplacementPreregistration:
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
            "relaylm2-cognitive-work-r2-replacement-preregistration-v2",
            self.merged_pr_commit_sha,
            self.root_seed,
            ANSWER_PROTOCOL_VERSION,
            task_payload,
            {
                "operations": OPERATIONS,
                "tasks_per_regime": TASKS_PER_REGIME,
                "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
                "exact_test_alpha": EXACT_TEST_ALPHA,
                "material_task_gain": MATERIAL_TASK_GAIN,
                "heuristic_oracle_gap_max": HEURISTIC_ORACLE_GAP_MAX,
                "budget": self.budget.__dict__,
                "physical_call_plan": [
                    item.__dict__ for item in physical_call_plan(self.tasks)
                ],
                "oracle_tie_break": "pareto-frontier-then-fixed-operation-priority",
                "answer_protocol": ANSWER_PROTOCOL_VERSION,
                "root_seed_domain": ROOT_SEED_DOMAIN,
            },
        )


def build_preregistration(merged_pr_commit_sha: str) -> R2ReplacementPreregistration:
    tasks = generate_tasks(merged_pr_commit_sha)
    return R2ReplacementPreregistration(
        merged_pr_commit_sha=merged_pr_commit_sha.lower(),
        root_seed=derive_root_seed(merged_pr_commit_sha),
        tasks=tasks,
        budget=derive_budget_contract(tasks),
    )
