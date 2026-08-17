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


async def run_native_evaluation() -> EvaluationReport:
    return EvaluationReport(
        scenarios=(
            await evaluate_provider_failure_safety(),
            await evaluate_restart_continuity(),
            await evaluate_assistant_self_certification_prevention(),
            await evaluate_comparative_preference_preservation(),
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
