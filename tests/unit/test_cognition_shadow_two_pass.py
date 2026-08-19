from __future__ import annotations

import asyncio
from pathlib import Path

from relaylm.cognitive import CognitiveOutput
from relaylm.cognition_execution import CognitionExtractionInput, CognitionExtractionOutput
from relaylm.cognition_execution_evidence import (
    BUFFERED_EXECUTION_PATH,
    COGNITION_EXECUTION_EVIDENCE_FORMAT_VERSION,
    EXTRACTION_OUTPUT_CONTRACT,
    SINGLE_PASS_OUTPUT_CONTRACT,
    CognitionExecutionEvidenceIdentity,
    ShadowExtractionStatus,
)
from relaylm.continuity import ContinuityCandidate, ContinuityContext
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import ContinuityRuntime
from relaylm.shadow_turn import run_user_turn_shadow_two_pass


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind and honest.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


class _CanonicalAndShadowProvider:
    def __init__(self) -> None:
        self.shadow_started = asyncio.Event()
        self.shadow_release = asyncio.Event()
        self.shadow_inputs: list[CognitionExtractionInput] = []

    async def generate(self, cognitive_input):
        return CognitiveOutput(
            response="Canonical response",
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="drink",
                    value="tea",
                    sources=(cognitive_input.input.id,),
                ),
            ),
        )

    async def generate_extraction(
        self, extraction_input: CognitionExtractionInput
    ) -> CognitionExtractionOutput:
        self.shadow_inputs.append(extraction_input)
        self.shadow_started.set()
        await self.shadow_release.wait()
        source = extraction_input.originating_event_id
        return CognitionExtractionOutput(
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="drink",
                    value="coffee",
                    sources=(source,),
                ),
            ),
            continuity_candidates=(
                ContinuityCandidate.set(
                    kind="active_task",
                    key="shadow_only",
                    value="must not commit",
                    sources=(source,),
                    epistemic_role="user_assertion",
                ),
            ),
        )


class _FailingShadowProvider:
    async def generate(self, _):
        return CognitiveOutput(response="Canonical response")

    async def generate_extraction(self, _):
        raise RuntimeError("shadow failed")


def test_shadow_two_pass_keeps_single_pass_canonical_and_records_raw_shadow_only(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _CanonicalAndShadowProvider()
        continuity_runtime = ContinuityRuntime(
            context=ContinuityContext(max_items=4),
            lifetime_revisions=3,
        )

        result = await run_user_turn_shadow_two_pass(
            character=character,
            provider=provider,
            content="I am choosing a drink",
            continuity_runtime=continuity_runtime,
        )
        await provider.shadow_started.wait()

        assert result.turn.response == "Canonical response"
        assert [(item.key, item.value) for item in result.turn.state.states] == [
            ("drink", "tea")
        ]
        assert CharacterDirectory(tmp_path).load_state() == result.turn.state
        canonical_continuity = continuity_runtime.context

        provider.shadow_release.set()
        shadow = await result.shadow

        assert shadow.status is ShadowExtractionStatus.COMPLETED
        assert shadow.output is not None
        assert shadow.originating_event_id == result.turn.user_event.id
        assert shadow.output.state_candidates[0].value == "coffee"
        assert shadow.output.continuity_candidates[0].key == "shadow_only"

        assert CharacterDirectory(tmp_path).load_state() == result.turn.state
        assert continuity_runtime.context == canonical_continuity
        assert provider.shadow_inputs[0].assistant_response == "Canonical response"
        assert (
            provider.shadow_inputs[0].originating_event_id
            == result.turn.user_event.id
        )

    asyncio.run(run())


def test_shadow_failure_does_not_fail_or_mutate_canonical_turn(tmp_path: Path) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        result = await run_user_turn_shadow_two_pass(
            character=character,
            provider=_FailingShadowProvider(),
            content="hello",
        )

        shadow = await result.shadow
        assert result.turn.response == "Canonical response"
        assert shadow.status is ShadowExtractionStatus.FAILED
        assert shadow.failure_reason == "shadow_pass2_failed"
        assert shadow.output is None
        assert CharacterDirectory(tmp_path).load_state().states == ()
        assert [event.actor for event in CharacterDirectory(tmp_path).iter_events()] == [
            "user",
            "assistant",
        ]

    asyncio.run(run())


def test_shadow_execution_identity_binds_mode_contracts_and_delivery() -> None:
    identity = CognitionExecutionEvidenceIdentity.shadow_two_pass(
        execution_path=BUFFERED_EXECUTION_PATH
    )

    assert identity.format_version == COGNITION_EXECUTION_EVIDENCE_FORMAT_VERSION
    assert identity.mode == "shadow_two_pass"
    assert identity.execution_path == "buffered"
    assert identity.canonical_output_contract == SINGLE_PASS_OUTPUT_CONTRACT
    assert identity.shadow_output_contract == EXTRACTION_OUTPUT_CONTRACT
    assert identity.canonical_mutation_source == "single_pass"
    assert identity.to_mapping() == {
        "format_version": COGNITION_EXECUTION_EVIDENCE_FORMAT_VERSION,
        "mode": "shadow_two_pass",
        "execution_path": "buffered",
        "canonical_output_contract": SINGLE_PASS_OUTPUT_CONTRACT,
        "conversation_output_contract": None,
        "extraction_output_contract": EXTRACTION_OUTPUT_CONTRACT,
        "shadow_output_contract": EXTRACTION_OUTPUT_CONTRACT,
        "canonical_mutation_source": "single_pass",
    }
