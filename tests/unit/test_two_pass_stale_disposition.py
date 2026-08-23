from __future__ import annotations

import asyncio
from pathlib import Path

from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
)
from relaylm.continuity import ContinuityCandidate
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.two_pass_turn import (
    CognitionExecutionRuntime,
    TwoPassExtractionStatus,
    run_user_turn_two_pass,
)


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


class _LateContinuityProvider:
    def __init__(self) -> None:
        self.conversation_calls = 0
        self.extraction_calls = 0
        self.first_extraction_started = asyncio.Event()
        self.release_first_extraction = asyncio.Event()

    async def generate_conversation(self, _):
        self.conversation_calls += 1
        return CognitionConversationOutput(response=f"reply-{self.conversation_calls}")

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
    ) -> CognitionExtractionOutput:
        index = self.extraction_calls
        self.extraction_calls += 1
        if index != 0:
            return CognitionExtractionOutput()

        self.first_extraction_started.set()
        await self.release_first_extraction.wait()
        source = extraction_input.originating_event_id
        return CognitionExtractionOutput(
            state_candidates=(
                StateCandidate.set(
                    state_class="user.fact",
                    key="stale_state",
                    value="must not commit",
                    sources=(source,),
                ),
            ),
            continuity_candidates=(
                ContinuityCandidate.set(
                    kind="unresolved",
                    key="stale_continuity",
                    value="must not commit",
                    sources=(source,),
                    epistemic_role="user_assertion",
                ),
            ),
        )


def test_superseded_extraction_is_stale_before_continuity_runtime_applicability(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _LateContinuityProvider()
        runtime = CognitionExecutionRuntime()

        first = await run_user_turn_two_pass(
            character=character,
            provider=provider,
            content="turn one",
            execution_runtime=runtime,
        )
        await provider.first_extraction_started.wait()

        second = await run_user_turn_two_pass(
            character=character,
            provider=provider,
            content="turn two",
            execution_runtime=runtime,
        )
        second_extraction = await second.extraction
        assert second_extraction.status is TwoPassExtractionStatus.COMMITTED

        provider.release_first_extraction.set()
        first_extraction = await first.extraction

        assert first_extraction.status is TwoPassExtractionStatus.STALE
        assert first_extraction.failure_reason is None
        assert CharacterDirectory(tmp_path).load_state().states == ()
        assert [event.actor for event in CharacterDirectory(tmp_path).iter_events()] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]

    asyncio.run(run())
