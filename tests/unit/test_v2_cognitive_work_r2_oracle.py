from __future__ import annotations

from relaylm.v2_interventions import ResourceVector
from tools.v2_cognitive_work_r2_preregistration import (
    OperationResult,
    TaskOperationBank,
    a3_oracle,
    build_preregistration,
)


_COMMIT = "3" * 40


def _retrieval_task():
    preregistration = build_preregistration(_COMMIT)
    return next(
        task
        for task in preregistration.tasks
        if task.hidden_regime == "RETRIEVAL_BENEFICIAL"
    )


def test_r2_oracle_removes_pareto_dominated_correct_candidate():
    task = _retrieval_task()
    bank = TaskOperationBank(
        task_id=task.task_id,
        base_answer="UNKNOWN",
        base_correct=False,
        base_cost=ResourceVector(calls=1),
        operation_results=(
            OperationResult(
                "THINK",
                task.expected_answer,
                True,
                ResourceVector(calls=1, input_tokens=20, output_tokens=5),
            ),
            OperationResult(
                "RETRIEVE",
                task.expected_answer,
                True,
                ResourceVector(
                    calls=1,
                    input_tokens=30,
                    output_tokens=5,
                    retrieval_units=1,
                ),
            ),
        ),
    )

    decision = a3_oracle(task, bank)
    assert decision.operation == "THINK"
    assert decision.correct is True


def test_r2_oracle_uses_fixed_priority_when_resource_vectors_are_incomparable():
    task = _retrieval_task()
    bank = TaskOperationBank(
        task_id=task.task_id,
        base_answer="UNKNOWN",
        base_correct=False,
        base_cost=ResourceVector(calls=1),
        operation_results=(
            OperationResult(
                "THINK",
                task.expected_answer,
                True,
                ResourceVector(calls=1, input_tokens=40, output_tokens=5),
            ),
            OperationResult(
                "RETRIEVE",
                task.expected_answer,
                True,
                ResourceVector(
                    calls=1,
                    input_tokens=20,
                    output_tokens=20,
                    retrieval_units=1,
                ),
            ),
        ),
    )

    # Neither correct candidate Pareto-dominates the other: THINK spends more
    # input tokens, while RETRIEVE spends more output tokens and one external unit.
    # The oracle therefore uses the frozen non-scientific operation priority
    # rather than lexicographically scalarizing the ResourceVector.
    decision = a3_oracle(task, bank)
    assert decision.operation == "THINK"
    assert decision.correct is True
