from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from tools import v2_cognitive_work_r2_preregistration as r2_v1
from tools import v2_cognitive_work_r2_replacement_preregistration as r2_v2
from tools import v2_cognitive_work_structured_output_qualification as sopq


CLAIM_STATUS = "R2_STRUCTURED_PREREGISTERED_DESIGN_ONLY"
ANSWER_PROTOCOL_VERSION = "qualified-json-schema-string-v3"
ROOT_SEED_DOMAIN = "relaylm2-2187-r2-structured-output-v3"
QUALIFIED_TRANSPORT_VERSION = "relaylm2-cognitive-work-sopq-v1"
QUALIFICATION_RESULT_SHA256 = (
    "sha256:1b0972ed92e6e3a8afad38c43b547877881935c7e7fe2318926677543aba8ed8"
)
QUALIFICATION_IDENTITY_FINGERPRINT = (
    "sha256:dcd432572adb8716d187dd899a0417ae0ff55ffb56047c53b25ea98e239268de"
)
QUALIFIED_EXECUTION_BINDING_DIGEST = (
    "sha256:8cad3e68cf6bfe1c4ea6db3d925569815c3326462fd1c359d2da073f5b8ca9d6"
)
EXPECTED_ANSWER_SCHEMA_DIGEST = (
    "sha256:d7f69ea25824f613d0b60198abe050adc66a3bf45d9f2045d1997214a55498e5"
)
EXPECTED_OPERATION_SCHEMA_DIGEST = (
    "sha256:acabff40467f48996033a4be6ee02dbfa97755bbfaf45ee1dd94cea5afeb720d"
)
EXPECTED_ANSWER_RESPONSE_FORMAT_DIGEST = (
    "sha256:e7a71f6a15e7cc936df664f19e3729cbffce6562dbebcb5e69e8f9cfd070639b"
)
EXPECTED_OPERATION_RESPONSE_FORMAT_DIGEST = (
    "sha256:a41031db0de0e912ded0fae8e8fb9687507debb6bcc86a286cfa0051de8afa76"
)
EXPECTED_QUALIFICATION_PLAN_DIGEST = (
    "sha256:e6bc9ddaa46ddd6e44d44fabb40e26ab6850542bf0a26b8908750caff77f88b5"
)

REGIMES = r2_v2.REGIMES
OPERATIONS = r2_v2.OPERATIONS
TASKS_PER_REGIME = r2_v2.TASKS_PER_REGIME
TOTAL_TASKS = r2_v2.TOTAL_TASKS
CONTEXT_LIMIT = r2_v2.CONTEXT_LIMIT
BOOTSTRAP_RESAMPLES = r2_v2.BOOTSTRAP_RESAMPLES
EXACT_TEST_ALPHA = r2_v2.EXACT_TEST_ALPHA
MATERIAL_TASK_GAIN = r2_v2.MATERIAL_TASK_GAIN
HEURISTIC_ORACLE_GAP_MAX = r2_v2.HEURISTIC_ORACLE_GAP_MAX

R2PreregistrationError = r2_v2.R2PreregistrationError
R2Task = r2_v2.R2Task
PlannedProviderCall = r2_v2.PlannedProviderCall
OperationResult = r2_v2.OperationResult
TaskOperationBank = r2_v2.TaskOperationBank
CounterfactualOutcome = r2_v2.CounterfactualOutcome
OracleDecision = r2_v2.OracleDecision
R2BudgetContract = r2_v2.R2BudgetContract
R2Interpretation = r2_v2.R2Interpretation

a0_policy = r2_v2.a0_policy
a1_policy = r2_v2.a1_policy
a3_oracle = r2_v2.a3_oracle
counterfactual_outcome = r2_v2.counterfactual_outcome
derive_budget_contract = r2_v2.derive_budget_contract
physical_call_plan = r2_v2.physical_call_plan
paired_directional_exact_pvalue = r2_v2.paired_directional_exact_pvalue
paired_bootstrap_interval = r2_v2.paired_bootstrap_interval
interpret_r2 = r2_v2.interpret_r2
answer_messages = r2_v2.answer_messages
revision_messages = r2_v2.revision_messages
allocator_messages = r2_v2.allocator_messages
parse_answer = sopq.parse_answer

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


def validate_qualified_transport() -> None:
    checks = {
        "qualification version": (
            sopq.QUALIFICATION_VERSION,
            QUALIFIED_TRANSPORT_VERSION,
        ),
        "answer schema": (
            sopq.ANSWER_SCHEMA_DIGEST,
            EXPECTED_ANSWER_SCHEMA_DIGEST,
        ),
        "operation schema": (
            sopq.OPERATION_SCHEMA_DIGEST,
            EXPECTED_OPERATION_SCHEMA_DIGEST,
        ),
        "answer response_format": (
            sopq.ANSWER_RESPONSE_FORMAT_DIGEST,
            EXPECTED_ANSWER_RESPONSE_FORMAT_DIGEST,
        ),
        "operation response_format": (
            sopq.OPERATION_RESPONSE_FORMAT_DIGEST,
            EXPECTED_OPERATION_RESPONSE_FORMAT_DIGEST,
        ),
        "qualification plan": (
            sopq.QUALIFICATION_PLAN_DIGEST,
            EXPECTED_QUALIFICATION_PLAN_DIGEST,
        ),
    }
    for label, (actual, expected) in checks.items():
        if actual != expected:
            raise R2PreregistrationError(
                f"qualified structured-output {label} identity drifted"
            )


def derive_root_seed(merged_pr_commit_sha: str) -> str:
    if not _HEX40.fullmatch(merged_pr_commit_sha):
        raise R2PreregistrationError("merged PR commit must be exactly 40 hex characters")
    return _sha256(ROOT_SEED_DOMAIN, merged_pr_commit_sha.lower())


def generate_tasks(merged_pr_commit_sha: str) -> tuple[R2Task, ...]:
    root_seed = derive_root_seed(merged_pr_commit_sha)
    tasks = tuple(
        r2_v1._make_task(root_seed, regime, index)
        for regime in REGIMES
        for index in range(TASKS_PER_REGIME)
    )
    if len(tasks) != TOTAL_TASKS or len({task.task_id for task in tasks}) != TOTAL_TASKS:
        raise R2PreregistrationError(
            "structured-output R2 generator did not produce 40 unique tasks"
        )
    return tasks


def parse_operation(text: str, *, task: R2Task) -> str:
    sopq.parse_operation(text)
    return r2_v1.parse_operation(text, task=task)


def schema_kind_for_call(call: PlannedProviderCall) -> str:
    if call.role == "A2_ALLOCATE":
        return "operation"
    if call.role in {"BASE", "BANK"}:
        return "answer"
    raise R2PreregistrationError("unknown physical call role")


def response_format_for_call(call: PlannedProviderCall) -> dict[str, object]:
    validate_qualified_transport()
    return sopq.response_format_for(schema_kind_for_call(call))


@dataclass(frozen=True)
class R2StructuredPreregistration:
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
        plan = physical_call_plan(self.tasks)
        return _sha256(
            "relaylm2-cognitive-work-r2-structured-preregistration-v3",
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
                "physical_call_plan": [item.__dict__ for item in plan],
                "oracle_tie_break": "pareto-frontier-then-fixed-operation-priority",
                "root_seed_domain": ROOT_SEED_DOMAIN,
                "semantic_predecessor": r2_v2.CLAIM_STATUS,
                "transport": {
                    "qualification_version": QUALIFIED_TRANSPORT_VERSION,
                    "answer_schema_digest": sopq.ANSWER_SCHEMA_DIGEST,
                    "operation_schema_digest": sopq.OPERATION_SCHEMA_DIGEST,
                    "answer_response_format_digest": sopq.ANSWER_RESPONSE_FORMAT_DIGEST,
                    "operation_response_format_digest": sopq.OPERATION_RESPONSE_FORMAT_DIGEST,
                    "qualification_plan_digest": sopq.QUALIFICATION_PLAN_DIGEST,
                    "qualification_result_sha256": QUALIFICATION_RESULT_SHA256,
                    "qualification_identity_fingerprint": QUALIFICATION_IDENTITY_FINGERPRINT,
                    "qualified_execution_binding_digest": QUALIFIED_EXECUTION_BINDING_DIGEST,
                    "per_call_schema_kind": [schema_kind_for_call(item) for item in plan],
                },
            },
        )


def build_preregistration(merged_pr_commit_sha: str) -> R2StructuredPreregistration:
    validate_qualified_transport()
    tasks = generate_tasks(merged_pr_commit_sha)
    return R2StructuredPreregistration(
        merged_pr_commit_sha=merged_pr_commit_sha.lower(),
        root_seed=derive_root_seed(merged_pr_commit_sha),
        tasks=tasks,
        budget=derive_budget_contract(tasks),
    )
