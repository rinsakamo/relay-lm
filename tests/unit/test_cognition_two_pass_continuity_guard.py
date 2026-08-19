from __future__ import annotations

import asyncio
from pathlib import Path

from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
)
from relaylm.continuity import ContinuityContext, ContinuityItem
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import ContinuityRuntime
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


class _HeldProvider:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def generate_conversation(self, _):
        return CognitionConversationOutput(response="visible")

    async def generate_extraction(
        self, extraction_input: CognitionExtractionInput
    ) -> CognitionExtractionOutput:
        self.started.set()
        await self.release.wait()
        return CognitionExtractionOutput(
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="drink",
                    value="coffee",
                    sources=(extraction_input.originating_event_id,),
                ),
            )
        )


def test_pass2_is_stale_if_accepted_continuity_advanced_after_origin_snapshot(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _HeldProvider()
        continuity_runtime = ContinuityRuntime(
            context=ContinuityContext(max_items=4),
            lifetime_revisions=3,
        )
        result = await run_user_turn_two_pass(
            character=character,
            provider=provider,
            content="recently coffee",
            execution_runtime=CognitionExecutionRuntime(),
            continuity_runtime=continuity_runtime,
        )
        await provider.started.wait()

        advanced = ContinuityContext(
            max_items=4,
            revision=1,
            items=(
                ContinuityItem(
                    item_id="external-continuity",
                    kind="active_task",
                    key="newer_task",
                    value="preserve-me",
                    sources=(result.user_event.id,),
                    epistemic_role="user_assertion",
                    accepted_revision=0,
                    expires_revision=2,
                ),
            ),
        )
        continuity_runtime.context = advanced
        provider.release.set()

        extraction = await result.extraction
        assert extraction.status is TwoPassExtractionStatus.STALE
        assert continuity_runtime.context == advanced
        assert CharacterDirectory(tmp_path).load_state().states == ()

    asyncio.run(run())
