from __future__ import annotations

import asyncio

from relaylm.evaluation import (
    evaluate_continuity_active_task_retention,
    evaluate_continuity_context_retention,
    evaluate_continuity_lifecycle,
    evaluate_continuity_turn,
)


def test_merged_continuity_evaluation_components_are_registered() -> None:
    results = tuple(
        asyncio.run(evaluate())
        for evaluate in (
            evaluate_continuity_lifecycle,
            evaluate_continuity_turn,
            evaluate_continuity_context_retention,
            evaluate_continuity_active_task_retention,
        )
    )

    assert tuple(result.scenario_id for result in results) == (
        "continuity_lifecycle",
        "continuity_turn",
        "continuity_context_retention",
        "continuity_active_task_retention",
    )
    assert all(result.status == "pass" for result in results)
