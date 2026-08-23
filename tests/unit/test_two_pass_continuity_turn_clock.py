from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
)
from relaylm.continuity import ContinuityCandidate, ContinuityContext, ContinuityItem
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import ContinuityRuntime
from relaylm.two_pass_turn import (
    CognitionExecutionRuntime,
    TwoPassExtractionStatus,
    run_user_turn_two_pass,
    run_user_turn_two_pass_streaming,
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


class _FailingExtractionProvider:
    async def generate_conversation(self, _):
        return CognitionConversationOutput(response="visible")

    async def stream_generate_conversation(self, _, emit):
        await emit("visible")
        return CognitionConversationOutput(response="visible")

    async def generate_extraction(self, _):
        raise RuntimeError("pass2 failed")


class _SuccessfulContinuityProvider:
    async def generate_conversation(self, _):
        return CognitionConversationOutput(response="visible")

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
    ) -> CognitionExtractionOutput:
        source = extraction_input.originating_event_id
        return CognitionExtractionOutput(
            continuity_candidates=(
                ContinuityCandidate.set(
                    kind="active_task",
                    key="finish_note",
                    value="finish the note",
                    sources=(source,),
                    epistemic_role="user_assertion",
                ),
            )
        )


class _HeldEmptyExtractionProvider:
    def __init__(self) -> None:
        self.started = [asyncio.Event(), asyncio.Event()]
        self.release = [asyncio.Event(), asyncio.Event()]
        self.extraction_count = 0
        self.conversation_count = 0

    async def generate_conversation(self, _):
        self.conversation_count += 1
        return CognitionConversationOutput(response=f"visible-{self.conversation_count}")

    async def generate_extraction(self, _):
        index = self.extraction_count
        self.extraction_count += 1
        self.started[index].set()
        await self.release[index].wait()
        return CognitionExtractionOutput()


class _FailingConversationProvider:
    async def generate_conversation(self, _):
        raise RuntimeError("pass1 failed")

    async def generate_extraction(self, _):
        return CognitionExtractionOutput()


def _expiring_context() -> ContinuityContext:
    return ContinuityContext(
        max_items=4,
        revision=0,
        items=(
            ContinuityItem(
                item_id="continuity:0:1",
                kind="active_task",
                key="old_task",
                value="expire me",
                sources=("old-event",),
                epistemic_role="user_assertion",
                accepted_revision=0,
                expires_revision=1,
            ),
        ),
    )


def test_buffered_successful_pass1_advances_lifecycle_even_when_pass2_fails(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        continuity_runtime = ContinuityRuntime(
            context=_expiring_context(),
            lifetime_revisions=3,
        )

        result = await run_user_turn_two_pass(
            character=character,
            provider=_FailingExtractionProvider(),
            content="continue",
            execution_runtime=CognitionExecutionRuntime(),
            continuity_runtime=continuity_runtime,
        )

        assert continuity_runtime.context.revision == 1
        assert continuity_runtime.context.items == ()

        extraction = await result.extraction
        assert extraction.status is TwoPassExtractionStatus.FAILED
        assert extraction.failure_reason == "pass2_failed"
        assert continuity_runtime.context.revision == 1
        assert continuity_runtime.context.items == ()

    asyncio.run(run())


def test_streaming_successful_pass1_advances_lifecycle_even_when_pass2_fails(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        continuity_runtime = ContinuityRuntime(
            context=_expiring_context(),
            lifetime_revisions=3,
        )
        emitted: list[str] = []

        async def emit(delta: str) -> None:
            emitted.append(delta)

        result = await run_user_turn_two_pass_streaming(
            character=character,
            provider=_FailingExtractionProvider(),
            content="continue",
            emit_response_delta=emit,
            execution_runtime=CognitionExecutionRuntime(),
            continuity_runtime=continuity_runtime,
        )

        assert emitted == ["visible"]
        assert continuity_runtime.context.revision == 1
        assert continuity_runtime.context.items == ()

        extraction = await result.extraction
        assert extraction.status is TwoPassExtractionStatus.FAILED
        assert continuity_runtime.context.revision == 1

    asyncio.run(run())


def test_successful_pass2_applies_candidates_at_existing_turn_revision(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        continuity_runtime = ContinuityRuntime(
            context=ContinuityContext(max_items=4),
            lifetime_revisions=3,
        )

        result = await run_user_turn_two_pass(
            character=character,
            provider=_SuccessfulContinuityProvider(),
            content="I still need to finish the note",
            execution_runtime=CognitionExecutionRuntime(),
            continuity_runtime=continuity_runtime,
        )

        assert continuity_runtime.context.revision == 1
        extraction = await result.extraction
        assert extraction.status is TwoPassExtractionStatus.COMMITTED
        assert extraction.continuity is not None
        assert extraction.continuity.context.revision == 1
        assert continuity_runtime.context.revision == 1
        assert len(continuity_runtime.context.items) == 1
        item = continuity_runtime.context.items[0]
        assert item.key == "finish_note"
        assert item.accepted_revision == 1
        assert item.expires_revision == 4

    asyncio.run(run())


def test_rapid_next_turn_advances_in_conversation_order_and_stale_pass2_does_not_advance(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _HeldEmptyExtractionProvider()
        execution_runtime = CognitionExecutionRuntime()
        continuity_runtime = ContinuityRuntime(
            context=ContinuityContext(max_items=4),
            lifetime_revisions=3,
        )

        first = await run_user_turn_two_pass(
            character=character,
            provider=provider,
            content="turn one",
            execution_runtime=execution_runtime,
            continuity_runtime=continuity_runtime,
        )
        await provider.started[0].wait()
        assert continuity_runtime.context.revision == 1

        second = await run_user_turn_two_pass(
            character=character,
            provider=provider,
            content="turn two",
            execution_runtime=execution_runtime,
            continuity_runtime=continuity_runtime,
        )
        await provider.started[1].wait()
        assert continuity_runtime.context.revision == 2

        provider.release[0].set()
        first_extraction = await first.extraction
        assert first_extraction.status is TwoPassExtractionStatus.STALE
        assert continuity_runtime.context.revision == 2

        provider.release[1].set()
        second_extraction = await second.extraction
        assert second_extraction.status is TwoPassExtractionStatus.COMMITTED
        assert second_extraction.continuity is not None
        assert second_extraction.continuity.context.revision == 2
        assert continuity_runtime.context.revision == 2

    asyncio.run(run())


def test_failed_pass1_does_not_advance_continuity_lifecycle(tmp_path: Path) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        continuity_runtime = ContinuityRuntime(
            context=_expiring_context(),
            lifetime_revisions=3,
        )

        with pytest.raises(RuntimeError, match="pass1 failed"):
            await run_user_turn_two_pass(
                character=character,
                provider=_FailingConversationProvider(),
                content="continue",
                execution_runtime=CognitionExecutionRuntime(),
                continuity_runtime=continuity_runtime,
            )

        assert continuity_runtime.context == _expiring_context()

    asyncio.run(run())
