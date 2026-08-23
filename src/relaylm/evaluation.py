from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from dataclasses import dataclass, field
from importlib import import_module
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
        if not isinstance(self.passed, bool):
            raise TypeError("evaluation passed must be a bool")

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


@dataclass(frozen=True, slots=True)
class NativeEvaluationScenario:
    group: str
    scenario_id: str
    module: str | None
    evaluator: str | None

    def __post_init__(self) -> None:
        if not self.group.strip():
            raise ValueError("native evaluation group must not be empty")
        if not self.scenario_id.strip():
            raise ValueError("native evaluation scenario_id must not be empty")
        if (self.module is None) != (self.evaluator is None):
            raise ValueError("native evaluation module/evaluator must be provided together")


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

NATIVE_EVALUATION_SCENARIOS: tuple[NativeEvaluationScenario, ...] = (
    NativeEvaluationScenario("runtime_safety", "provider_failure_safety", None, None),
    NativeEvaluationScenario("runtime_safety", "restart_continuity", 'relaylm.evaluation_restart', 'evaluate_restart_continuity'),
    NativeEvaluationScenario("authority_state", "assistant_self_certification_prevention", 'relaylm.evaluation_authority', 'evaluate_assistant_self_certification_prevention'),
    NativeEvaluationScenario("authority_state", "comparative_preference_preservation", 'relaylm.evaluation_preference', 'evaluate_comparative_preference_preservation'),
    NativeEvaluationScenario("authority_state", "degree_hint_integrity", 'relaylm.evaluation_degree', 'evaluate_degree_hint_integrity'),
    NativeEvaluationScenario("context_retrieval", "working_context_budget_atomicity", 'relaylm.evaluation_context', 'evaluate_working_context_budget_atomicity'),
    NativeEvaluationScenario("persistence", "persistence_integrity", 'relaylm.evaluation_persistence', 'evaluate_persistence_integrity'),
    NativeEvaluationScenario("persistence", "event_snapshot_reuse", 'relaylm.evaluation_persistence', 'evaluate_event_snapshot_reuse'),
    NativeEvaluationScenario("authority_state", "correction_remove_semantics", 'relaylm.evaluation_correction', 'evaluate_correction_remove_semantics'),
    NativeEvaluationScenario("persistence", "crystallization_integrity", 'relaylm.evaluation_crystallization', 'evaluate_crystallization_integrity'),
    NativeEvaluationScenario("runtime_safety", "streaming_safety", 'relaylm.evaluation_streaming', 'evaluate_streaming_safety'),
    NativeEvaluationScenario("context_retrieval", "state_selection_diagnostics", 'relaylm.evaluation_context', 'evaluate_state_selection_diagnostics'),
    NativeEvaluationScenario("context_retrieval", "cross_layer_context_diagnostics", 'relaylm.evaluation_cross_layer', 'evaluate_cross_layer_context_diagnostics'),
    NativeEvaluationScenario("context_retrieval", "working_context_budget_diagnostics", 'relaylm.evaluation_working_context', 'evaluate_working_context_budget_diagnostics'),
    NativeEvaluationScenario("context_retrieval", "memory_heading_retrieval", 'relaylm.evaluation_memory', 'evaluate_memory_heading_retrieval'),
    NativeEvaluationScenario("context_retrieval", "memory_cognitive_projection", 'relaylm.evaluation_memory', 'evaluate_memory_cognitive_projection'),
    NativeEvaluationScenario("context_retrieval", "ordinary_turn_memory_retrieval", 'relaylm.evaluation_memory', 'evaluate_ordinary_turn_memory_retrieval'),
    NativeEvaluationScenario("context_retrieval", "state_memory_authority_filter", 'relaylm.evaluation_memory', 'evaluate_state_memory_authority_filter'),
    NativeEvaluationScenario("context_retrieval", "targeted_event_retrieval", 'relaylm.evaluation_context', 'evaluate_targeted_event_retrieval'),
    NativeEvaluationScenario("context_retrieval", "event_evidence_cognitive_projection", 'relaylm.evaluation_event_evidence', 'evaluate_event_evidence_cognitive_projection'),
    NativeEvaluationScenario("context_retrieval", "ordinary_turn_event_retrieval", 'relaylm.evaluation_event_evidence', 'evaluate_ordinary_turn_event_retrieval'),
    NativeEvaluationScenario("context_retrieval", "retrieval_stage_diagnostics", 'relaylm.evaluation_retrieval_diagnostics', 'evaluate_retrieval_stage_diagnostics'),
    NativeEvaluationScenario("context_retrieval", "boolean_state_memory_authority", 'relaylm.evaluation_retrieval_refinements', 'evaluate_boolean_state_memory_authority'),
    NativeEvaluationScenario("context_retrieval", "retrieval_aggregate_diagnostics", 'relaylm.evaluation_retrieval_refinements', 'evaluate_retrieval_aggregate_diagnostics'),
    NativeEvaluationScenario("context_retrieval", "cjk_retrieval_relevance", 'relaylm.evaluation_retrieval_refinements', 'evaluate_cjk_retrieval_relevance'),
    NativeEvaluationScenario("context_retrieval", "degree_state_memory_authority", 'relaylm.evaluation_degree_state_memory_authority', 'evaluate_degree_state_memory_authority'),
    NativeEvaluationScenario("context_retrieval", "retrieval_query_features", 'relaylm.evaluation_retrieval_query_features', 'evaluate_retrieval_query_features'),
    NativeEvaluationScenario("continuity", "continuity_lifecycle", 'relaylm.evaluation_continuity_lifecycle', 'evaluate_continuity_lifecycle'),
    NativeEvaluationScenario("continuity", "continuity_turn", 'relaylm.evaluation_continuity_turn', 'evaluate_continuity_turn'),
    NativeEvaluationScenario("continuity", "continuity_context_retention", 'relaylm.evaluation_continuity_context_retention', 'evaluate_continuity_context_retention'),
    NativeEvaluationScenario("continuity", "continuity_active_task_retention", 'relaylm.evaluation_continuity_active_task', 'evaluate_continuity_active_task_retention'),
    NativeEvaluationScenario("continuity", "continuity_cognition_wiring", 'relaylm.evaluation_continuity_cognition_wiring', 'evaluate_continuity_cognition_wiring'),
    NativeEvaluationScenario("context_retrieval", "freeform_current_state_shadow", 'relaylm.evaluation_freeform_current_state_shadow', 'evaluate_freeform_current_state_shadow'),
    NativeEvaluationScenario("budget_provider", "total_budget_accounting", 'relaylm.evaluation_total_budget_accounting', 'evaluate_total_budget_accounting'),
    NativeEvaluationScenario("budget_provider", "budget_degradation_plan", 'relaylm.evaluation_budget_degradation_plan', 'evaluate_budget_degradation_plan'),
    NativeEvaluationScenario("budget_provider", "budget_owner_controls", 'relaylm.evaluation_budget_owner_controls', 'evaluate_budget_owner_controls'),
    NativeEvaluationScenario("budget_provider", "serialized_input_fit", 'relaylm.evaluation_serialized_input_fit', 'evaluate_serialized_input_fit_component'),
    NativeEvaluationScenario("budget_provider", "openai_serialized_counter", 'relaylm.evaluation_openai_serialized_counter', 'evaluate_openai_serialized_counter'),
    NativeEvaluationScenario("budget_provider", "serialized_fit_enforcement", 'relaylm.evaluation_serialized_fit_enforcement', 'evaluate_serialized_fit_enforcement'),
    NativeEvaluationScenario("budget_provider", "protected_serialized_floor", 'relaylm.evaluation_protected_serialized_floor', 'evaluate_protected_serialized_floor'),
    NativeEvaluationScenario("budget_provider", "cognitive_budget_turn_wiring", 'relaylm.evaluation_cognitive_budget_turn_wiring', 'evaluate_cognitive_budget_turn_wiring'),
    NativeEvaluationScenario("budget_provider", "cognitive_budget_turn_diagnostics", 'relaylm.evaluation_cognitive_budget_turn_diagnostics', 'evaluate_cognitive_budget_turn_diagnostics'),
    NativeEvaluationScenario("persistence", "memory_temporal_provenance", 'relaylm.evaluation_memory_temporal_provenance', 'evaluate_memory_temporal_provenance'),
)

async def _run_native_scenario(spec: NativeEvaluationScenario) -> EvaluationScenarioResult:
    if spec.module is None:
        result = await evaluate_provider_failure_safety()
    else:
        module = import_module(spec.module)
        evaluator = getattr(module, spec.evaluator or "")
        result = await evaluator()

    if not isinstance(result, EvaluationScenarioResult):
        raise TypeError(
            f"native evaluation {spec.scenario_id} returned "
            f"{type(result).__name__}, expected EvaluationScenarioResult"
        )
    if result.scenario_id != spec.scenario_id:
        raise ValueError(
            f"native evaluation registry mismatch: expected {spec.scenario_id}, "
            f"observed {result.scenario_id}"
        )
    return result


async def run_native_evaluation() -> EvaluationReport:
    scenarios = []
    for spec in NATIVE_EVALUATION_SCENARIOS:
        scenarios.append(await _run_native_scenario(spec))
    return EvaluationReport(scenarios=tuple(scenarios))


def main() -> int:
    executable = Path(sys.argv[0]).name.removesuffix(".exe")
    arguments = sys.argv[1:] if executable == "relaylm-eval" else []
    if arguments:
        rendered = " ".join(repr(argument) for argument in arguments)
        print(
            f"relaylm-eval: error: unsupported arguments: {rendered}",
            file=sys.stderr,
        )
        return 2
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
