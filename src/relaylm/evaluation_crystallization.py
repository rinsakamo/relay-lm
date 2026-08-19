from __future__ import annotations

import tempfile
from pathlib import Path

from relaylm.crystallization import (
    CrystallizationInput,
    CrystallizationOutput,
    run_crystallization,
)
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.memory_provenance import MemoryTemporalScope, MemoryUnit
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.filesystem import CharacterDirectory


_MEMORY = """# Memory

## Preferences

Rin likes tea.

## Unverified continuity

The assistant previously said Rin lives in Hokkaido.
"""


class _DeterministicCrystallizer:
    def __init__(self, *, user_source: str, assistant_source: str) -> None:
        self.user_source = user_source
        self.assistant_source = assistant_source
        self.calls = 0
        self.inputs: list[CrystallizationInput] = []

    async def generate(self, crystallization_input: CrystallizationInput) -> CrystallizationOutput:
        self.calls += 1
        self.inputs.append(crystallization_input)
        return CrystallizationOutput(
            memory_units=(
                MemoryUnit(
                    heading="Preferences",
                    content="Rin likes tea.",
                    temporal_scope=MemoryTemporalScope.UNKNOWN,
                ),
                MemoryUnit(
                    heading="Unverified continuity",
                    content="The assistant previously said Rin lives in Hokkaido.",
                    temporal_scope=MemoryTemporalScope.UNKNOWN,
                ),
            ),
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="tea",
                    value="likes",
                    sources=(self.user_source,),
                ),
                StateCandidate.set(
                    state_class="user.fact",
                    key="residence_location",
                    value="Hokkaido",
                    sources=(self.assistant_source,),
                ),
            ),
        )


async def evaluate_crystallization_integrity() -> EvaluationScenarioResult:
    with tempfile.TemporaryDirectory(prefix="relaylm-eval-crystallization-") as temporary:
        root = Path(temporary)
        _make_character(root)
        character = CharacterDirectory(root)

        user_event = Event.create(
            type="message",
            actor="user",
            payload={"content": "紅茶が好き"},
            event_id="crystal-user",
            timestamp="2026-08-17T00:00:00+00:00",
        )
        assistant_event = Event.create(
            type="message",
            actor="assistant",
            payload={"content": "あなたは北海道に住んでいる"},
            event_id="crystal-assistant",
            timestamp="2026-08-17T00:00:01+00:00",
        )
        character.append_event(user_event)
        character.append_event(assistant_event)

        crystallizer = _DeterministicCrystallizer(
            user_source=user_event.id,
            assistant_source=assistant_event.id,
        )
        first = await run_crystallization(
            character=character,
            crystallizer=crystallizer,
        )
        first_memory = character.load_memory_markdown()
        first_state = character.load_state()

        second = await run_crystallization(
            character=character,
            crystallizer=crystallizer,
        )
        final_memory = character.load_memory_markdown()
        final_state = character.load_state()

    first_accepted = [decision for decision in first.decisions if decision.status == "accepted"]
    first_rejected = [decision for decision in first.decisions if decision.status == "rejected"]
    second_noops = [decision for decision in second.decisions if decision.status == "noop"]
    second_rejected = [decision for decision in second.decisions if decision.status == "rejected"]
    final_values = {
        (record.state_class, record.key): record.value for record in final_state.states
    }

    checks = (
        EvaluationCheck(
            check_id="crystallized_markdown_is_materialized_as_readable_synthesis",
            boundary="crystallized_memory",
            passed=first.memory_changed is True
            and first_memory == _MEMORY
            and "Hokkaido" in first_memory,
            expected=True,
            observed=first.memory_changed is True and first_memory == _MEMORY,
        ),
        EvaluationCheck(
            check_id="valid_user_state_writeback_is_governed_and_accepted",
            boundary="validator",
            passed=len(first_accepted) == 1
            and first_accepted[0].action == "create",
            expected="accepted/create",
            observed=(
                f"{first_accepted[0].status}/{first_accepted[0].action}"
                if first_accepted
                else "not accepted"
            ),
        ),
        EvaluationCheck(
            check_id="assistant_only_user_fact_writeback_is_rejected",
            boundary="validator",
            passed=len(first_rejected) == 1
            and first_rejected[0].reason == "user_state_requires_user_source",
            expected="user_state_requires_user_source",
            observed=(first_rejected[0].reason if first_rejected else "not rejected"),
        ),
        EvaluationCheck(
            check_id="markdown_prose_does_not_promote_rejected_fact_to_state",
            boundary="canonical_state",
            passed=first_state == final_state
            and final_values == {("user.preference", "tea"): "likes"},
            expected="user.preference/tea=likes only",
            observed=",".join(f"{state_class}/{key}" for state_class, key in final_values)
            or "none",
        ),
        EvaluationCheck(
            check_id="unchanged_rerun_avoids_markdown_and_state_churn",
            boundary="crystallized_memory",
            passed=second.memory_changed is False
            and final_memory == _MEMORY
            and len(second_noops) == 1
            and len(second_rejected) == 1,
            expected=True,
            observed=second.memory_changed is False,
        ),
        EvaluationCheck(
            check_id="one_crystallizer_generation_occurs_per_explicit_pass",
            boundary="crystallizer",
            passed=crystallizer.calls == 2
            and len(crystallizer.inputs) == 2
            and crystallizer.inputs[0].prior_memory is None
            and crystallizer.inputs[1].prior_memory == _MEMORY,
            expected=2,
            observed=crystallizer.calls,
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="crystallization_integrity",
        checks=checks,
        metrics={
            "crystallizer_calls": crystallizer.calls,
            "first_pass_accepted_count": len(first_accepted),
            "first_pass_rejected_count": len(first_rejected),
            "final_state_count": len(final_state.states),
        },
    )


def _make_character(root: Path) -> None:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text(
        "# Evaluation Character\n\nBe honest and grounded.\n",
        encoding="utf-8",
    )
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: evaluation\n  name: Evaluation\n",
        encoding="utf-8",
    )
    CharacterDirectory(root).save_state(CanonicalState())
