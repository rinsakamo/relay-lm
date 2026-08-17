from __future__ import annotations

import asyncio
import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import run_user_turn

MetricValue = str | int | float | bool


@dataclass(frozen=True, slots=True)
class EvaluationCheck:
    check_id: str
    boundary: str
    passed: bool
    expected: MetricValue
    observed: MetricValue

    def __post_init__(self) -> None:
        if not self.check_id.strip():
            raise ValueError("evaluation check_id must not be empty")
        if not self.boundary.strip():
            raise ValueError("evaluation boundary must not be empty")

    def to_mapping(self) -> dict[str, MetricValue]:
        return {
            "id": self.check_id,
            "boundary": self.boundary,
            "passed": self.passed,
            "expected": self.expected,
            "observed": self.observed,
        }


@dataclass(frozen=True, slots=True)
class EvaluationScenarioResult:
    scenario_id: str
    checks: tuple[EvaluationCheck, ...]
    metrics: Mapping[str, MetricValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("evaluation scenario_id must not be empty")
        if not self.checks:
            raise ValueError("evaluation scenario must contain at least one check")

    @property
    def status(self) -> str:
        return "pass" if all(check.passed for check in self.checks) else "fail"

    def to_mapping(self) -> dict[str, object]:
        return {
            "id": self.scenario_id,
            "status": self.status,
            "checks": [check.to_mapping() for check in self.checks],
            "metrics": dict(self.metrics),
        }


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    scenarios: tuple[EvaluationScenarioResult, ...]
    format_version: int = 1
    suite: str = "relaylm-native"

    def __post_init__(self) -> None:
        if self.format_version != 1:
            raise ValueError(f"unsupported evaluation format_version: {self.format_version}")
        if not self.suite.strip():
            raise ValueError("evaluation suite must not be empty")
        if not self.scenarios:
            raise ValueError("evaluation report must contain at least one scenario")

    @property
    def status(self) -> str:
        return "pass" if all(scenario.status == "pass" for scenario in self.scenarios) else "fail"

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "suite": self.suite,
            "status": self.status,
            "scenarios": [scenario.to_mapping() for scenario in self.scenarios],
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )


class _FailingEvaluationProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        raise RuntimeError("intentional evaluation provider failure")


async def evaluate_provider_failure_safety() -> EvaluationScenarioResult:
    with tempfile.TemporaryDirectory(prefix="relaylm-eval-") as temporary:
        root = Path(temporary)
        character = _make_character(root)
        provider = _FailingEvaluationProvider()
        failure_observed = False

        try:
            await run_user_turn(
                character=character,
                provider=provider,
                content="この入力は記録される？",
            )
        except RuntimeError as exc:
            failure_observed = str(exc) == "intentional evaluation provider failure"

        reopened = CharacterDirectory(root)
        events = list(reopened.iter_events())
        actors = [event.actor for event in events]
        state = reopened.load_state()

    checks = (
        EvaluationCheck(
            check_id="provider_failure_observed",
            boundary="provider",
            passed=failure_observed,
            expected=True,
            observed=failure_observed,
        ),
        EvaluationCheck(
            check_id="provider_called_once",
            boundary="provider",
            passed=provider.calls == 1,
            expected=1,
            observed=provider.calls,
        ),
        EvaluationCheck(
            check_id="current_user_event_persisted",
            boundary="event_journal",
            passed=actors == ["user"],
            expected="user",
            observed=",".join(actors) if actors else "none",
        ),
        EvaluationCheck(
            check_id="assistant_event_not_persisted",
            boundary="event_journal",
            passed="assistant" not in actors,
            expected=False,
            observed="assistant" in actors,
        ),
        EvaluationCheck(
            check_id="canonical_state_unchanged",
            boundary="canonical_state",
            passed=state == CanonicalState(),
            expected=0,
            observed=len(state.states),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="provider_failure_safety",
        checks=checks,
        metrics={
            "provider_calls": provider.calls,
            "persisted_event_count": len(events),
            "persisted_state_count": len(state.states),
        },
    )


async def evaluate_restart_continuity() -> EvaluationScenarioResult:
    from relaylm.evaluation_restart import evaluate_restart_continuity as evaluate

    return await evaluate()


async def evaluate_assistant_self_certification_prevention() -> EvaluationScenarioResult:
    from relaylm.evaluation_authority import (
        evaluate_assistant_self_certification_prevention as evaluate,
    )

    return await evaluate()


async def evaluate_comparative_preference_preservation() -> EvaluationScenarioResult:
    from relaylm.evaluation_preference import (
        evaluate_comparative_preference_preservation as evaluate,
    )

    return await evaluate()


async def evaluate_degree_hint_integrity() -> EvaluationScenarioResult:
    from relaylm.evaluation_degree import evaluate_degree_hint_integrity as evaluate

    return await evaluate()


async def evaluate_working_context_budget_atomicity() -> EvaluationScenarioResult:
    from relaylm.evaluation_context import (
        evaluate_working_context_budget_atomicity as evaluate,
    )

    return await evaluate()


async def evaluate_state_selection_diagnostics() -> EvaluationScenarioResult:
    from relaylm.evaluation_context import evaluate_state_selection_diagnostics as evaluate

    return await evaluate()


async def evaluate_cross_layer_context_diagnostics() -> EvaluationScenarioResult:
    from relaylm.evaluation_cross_layer import (
        evaluate_cross_layer_context_diagnostics as evaluate,
    )

    return await evaluate()


async def evaluate_working_context_budget_diagnostics() -> EvaluationScenarioResult:
    from relaylm.evaluation_working_context import (
        evaluate_working_context_budget_diagnostics as evaluate,
    )

    return await evaluate()


async def evaluate_persistence_integrity() -> EvaluationScenarioResult:
    from relaylm.evaluation_persistence import evaluate_persistence_integrity as evaluate

    return await evaluate()


async def evaluate_event_snapshot_reuse() -> EvaluationScenarioResult:
    from relaylm.evaluation_persistence import evaluate_event_snapshot_reuse as evaluate

    return await evaluate()


async def evaluate_correction_remove_semantics() -> EvaluationScenarioResult:
    from relaylm.evaluation_correction import evaluate_correction_remove_semantics as evaluate

    return await evaluate()


async def evaluate_crystallization_integrity() -> EvaluationScenarioResult:
    from relaylm.evaluation_crystallization import evaluate_crystallization_integrity as evaluate

    return await evaluate()


async def evaluate_streaming_safety() -> EvaluationScenarioResult:
    from relaylm.evaluation_streaming import evaluate_streaming_safety as evaluate

    return await evaluate()


async def evaluate_memory_heading_retrieval() -> EvaluationScenarioResult:
    from relaylm.evaluation_memory import evaluate_memory_heading_retrieval as evaluate

    return await evaluate()


async def evaluate_memory_cognitive_projection() -> EvaluationScenarioResult:
    from relaylm.evaluation_memory import evaluate_memory_cognitive_projection as evaluate

    return await evaluate()


async def evaluate_ordinary_turn_memory_retrieval() -> EvaluationScenarioResult:
    from relaylm.evaluation_memory import evaluate_ordinary_turn_memory_retrieval as evaluate

    return await evaluate()


async def evaluate_state_memory_authority_filter() -> EvaluationScenarioResult:
    from relaylm.evaluation_memory import evaluate_state_memory_authority_filter as evaluate

    return await evaluate()


async def evaluate_targeted_event_retrieval() -> EvaluationScenarioResult:
    from relaylm.evaluation_context import evaluate_targeted_event_retrieval as evaluate

    return await evaluate()


async def evaluate_event_evidence_cognitive_projection() -> EvaluationScenarioResult:
    from relaylm.evaluation_event_evidence import (
        evaluate_event_evidence_cognitive_projection as evaluate,
    )

    return await evaluate()


async def evaluate_ordinary_turn_event_retrieval() -> EvaluationScenarioResult:
    from relaylm.evaluation_event_evidence import (
        evaluate_ordinary_turn_event_retrieval as evaluate,
    )

    return await evaluate()


async def evaluate_retrieval_stage_diagnostics() -> EvaluationScenarioResult:
    from relaylm.evaluation_retrieval_diagnostics import (
        evaluate_retrieval_stage_diagnostics as evaluate,
    )

    return await evaluate()


async def evaluate_boolean_state_memory_authority() -> EvaluationScenarioResult:
    from relaylm.evaluation_retrieval_refinements import (
        evaluate_boolean_state_memory_authority as evaluate,
    )

    return await evaluate()


async def evaluate_retrieval_aggregate_diagnostics() -> EvaluationScenarioResult:
    from relaylm.evaluation_retrieval_refinements import (
        evaluate_retrieval_aggregate_diagnostics as evaluate,
    )

    return await evaluate()


async def evaluate_cjk_retrieval_relevance() -> EvaluationScenarioResult:
    from relaylm.evaluation_retrieval_refinements import (
        evaluate_cjk_retrieval_relevance as evaluate,
    )

    return await evaluate()


async def evaluate_degree_state_memory_authority() -> EvaluationScenarioResult:
    from relaylm.evaluation_degree_state_memory_authority import (
        evaluate_degree_state_memory_authority as evaluate,
    )

    return await evaluate()


async def evaluate_retrieval_query_features() -> EvaluationScenarioResult:
    from relaylm.evaluation_retrieval_query_features import (
        evaluate_retrieval_query_features as evaluate,
    )

    return await evaluate()


async def evaluate_continuity_lifecycle() -> EvaluationScenarioResult:
    from relaylm.evaluation_continuity_lifecycle import (
        evaluate_continuity_lifecycle as evaluate,
    )

    return await evaluate()


async def evaluate_continuity_turn() -> EvaluationScenarioResult:
    from relaylm.evaluation_continuity_turn import evaluate_continuity_turn as evaluate

    return await evaluate()


async def evaluate_continuity_context_retention() -> EvaluationScenarioResult:
    from relaylm.evaluation_continuity_context_retention import (
        evaluate_continuity_context_retention as evaluate,
    )

    return await evaluate()


async def evaluate_continuity_active_task_retention() -> EvaluationScenarioResult:
    from relaylm.evaluation_continuity_active_task import (
        evaluate_continuity_active_task_retention as evaluate,
    )

    return await evaluate()


async def evaluate_continuity_cognition_wiring() -> EvaluationScenarioResult:
    from relaylm.evaluation_continuity_cognition_wiring import (
        evaluate_continuity_cognition_wiring as evaluate,
    )

    return await evaluate()


async def evaluate_freeform_current_state_shadow() -> EvaluationScenarioResult:
    from relaylm.evaluation_freeform_current_state_shadow import (
        evaluate_freeform_current_state_shadow as evaluate,
    )

    return await evaluate()


async def evaluate_total_budget_accounting() -> EvaluationScenarioResult:
    from relaylm.evaluation_total_budget_accounting import (
        evaluate_total_budget_accounting as evaluate,
    )

    return await evaluate()


async def evaluate_budget_degradation_plan() -> EvaluationScenarioResult:
    from relaylm.evaluation_budget_degradation_plan import (
        evaluate_budget_degradation_plan as evaluate,
    )

    return await evaluate()


async def evaluate_budget_owner_controls() -> EvaluationScenarioResult:
    from relaylm.evaluation_budget_owner_controls import (
        evaluate_budget_owner_controls as evaluate,
    )

    return await evaluate()


async def evaluate_serialized_input_fit() -> EvaluationScenarioResult:
    from relaylm.evaluation_serialized_input_fit import (
        evaluate_serialized_input_fit_component as evaluate,
    )

    return await evaluate()


async def evaluate_openai_serialized_counter() -> EvaluationScenarioResult:
    from relaylm.evaluation_openai_serialized_counter import (
        evaluate_openai_serialized_counter as evaluate,
    )

    return await evaluate()


async def evaluate_serialized_fit_enforcement() -> EvaluationScenarioResult:
    from relaylm.evaluation_serialized_fit_enforcement import (
        evaluate_serialized_fit_enforcement as evaluate,
    )

    return await evaluate()


async def evaluate_protected_serialized_floor() -> EvaluationScenarioResult:
    from relaylm.evaluation_protected_serialized_floor import (
        evaluate_protected_serialized_floor as evaluate,
    )

    return await evaluate()


async def evaluate_cognitive_budget_turn_wiring() -> EvaluationScenarioResult:
    from relaylm.evaluation_cognitive_budget_turn_wiring import (
        evaluate_cognitive_budget_turn_wiring as evaluate,
    )

    return await evaluate()


async def evaluate_cognitive_budget_turn_diagnostics() -> EvaluationScenarioResult:
    from relaylm.evaluation_cognitive_budget_turn_diagnostics import (
        evaluate_cognitive_budget_turn_diagnostics as evaluate,
    )

    return await evaluate()


async def evaluate_memory_temporal_provenance() -> EvaluationScenarioResult:
    from relaylm.evaluation_memory_temporal_provenance import (
        evaluate_memory_temporal_provenance as evaluate,
    )

    return await evaluate()


async def run_native_evaluation() -> EvaluationReport:
    return EvaluationReport(
        scenarios=(
            await evaluate_provider_failure_safety(),
            await evaluate_restart_continuity(),
            await evaluate_assistant_self_certification_prevention(),
            await evaluate_comparative_preference_preservation(),
            await evaluate_degree_hint_integrity(),
            await evaluate_working_context_budget_atomicity(),
            await evaluate_persistence_integrity(),
            await evaluate_event_snapshot_reuse(),
            await evaluate_correction_remove_semantics(),
            await evaluate_crystallization_integrity(),
            await evaluate_streaming_safety(),
            await evaluate_state_selection_diagnostics(),
            await evaluate_cross_layer_context_diagnostics(),
            await evaluate_working_context_budget_diagnostics(),
            await evaluate_memory_heading_retrieval(),
            await evaluate_memory_cognitive_projection(),
            await evaluate_ordinary_turn_memory_retrieval(),
            await evaluate_state_memory_authority_filter(),
            await evaluate_targeted_event_retrieval(),
            await evaluate_event_evidence_cognitive_projection(),
            await evaluate_ordinary_turn_event_retrieval(),
            await evaluate_retrieval_stage_diagnostics(),
            await evaluate_boolean_state_memory_authority(),
            await evaluate_retrieval_aggregate_diagnostics(),
            await evaluate_cjk_retrieval_relevance(),
            await evaluate_degree_state_memory_authority(),
            await evaluate_retrieval_query_features(),
            await evaluate_continuity_lifecycle(),
            await evaluate_continuity_turn(),
            await evaluate_continuity_context_retention(),
            await evaluate_continuity_active_task_retention(),
            await evaluate_continuity_cognition_wiring(),
            await evaluate_freeform_current_state_shadow(),
            await evaluate_total_budget_accounting(),
            await evaluate_budget_degradation_plan(),
            await evaluate_budget_owner_controls(),
            await evaluate_serialized_input_fit(),
            await evaluate_openai_serialized_counter(),
            await evaluate_serialized_fit_enforcement(),
            await evaluate_protected_serialized_floor(),
            await evaluate_cognitive_budget_turn_wiring(),
            await evaluate_cognitive_budget_turn_diagnostics(),
            await evaluate_memory_temporal_provenance(),
        ),
    )


def main() -> int:
    report = asyncio.run(run_native_evaluation())
    print(report.to_json())
    return 0 if report.status == "pass" else 1


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text(
        "# Evaluation Character\n\nBe honest and grounded.\n",
        encoding="utf-8",
    )
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: evaluation\n  name: Evaluation\n",
        encoding="utf-8",
    )
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character
