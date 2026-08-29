from __future__ import annotations

import asyncio
from pathlib import Path

from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
)
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory
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


class _CancellationAwareProvider:
    def __init__(self) -> None:
        self.conversation_calls = 0
        self.extraction_calls = 0
        self.first_extraction_started = asyncio.Event()
        self.first_extraction_cancelled = asyncio.Event()

    async def generate_conversation(self, _):
        self.conversation_calls += 1
        if self.conversation_calls == 2:
            assert self.first_extraction_cancelled.is_set()
        return CognitionConversationOutput(response=f"reply-{self.conversation_calls}")

    async def stream_generate_conversation(self, _, emit):
        self.conversation_calls += 1
        if self.conversation_calls == 2:
            assert self.first_extraction_cancelled.is_set()
        response = f"reply-{self.conversation_calls}"
        await emit(response)
        return CognitionConversationOutput(response=response)

    async def generate_extraction(
        self,
        _: CognitionExtractionInput,
    ) -> CognitionExtractionOutput:
        index = self.extraction_calls
        self.extraction_calls += 1
        if index != 0:
            return CognitionExtractionOutput()

        self.first_extraction_started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.first_extraction_cancelled.set()
            raise
        raise AssertionError("unreachable")


def test_new_buffered_turn_cancels_and_joins_stale_pass2_before_new_pass1(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _CancellationAwareProvider()
        runtime = CognitionExecutionRuntime()

        first = await run_user_turn_two_pass(
            character=character,
            provider=provider,
            content="turn one",
            execution_runtime=runtime,
        )
        await provider.first_extraction_started.wait()
        assert runtime.pending_extraction_count == 1

        second = await run_user_turn_two_pass(
            character=character,
            provider=provider,
            content="turn two",
            execution_runtime=runtime,
        )

        assert provider.first_extraction_cancelled.is_set()
        assert (await first.extraction).status is TwoPassExtractionStatus.STALE
        assert (await second.extraction).status is TwoPassExtractionStatus.COMMITTED
        assert runtime.pending_extraction_count == 0
        assert first.response == "reply-1"
        assert second.response == "reply-2"

    asyncio.run(run())


def test_new_streaming_turn_uses_same_stale_pass2_single_flight_boundary(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _CancellationAwareProvider()
        runtime = CognitionExecutionRuntime()
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        first = await run_user_turn_two_pass_streaming(
            character=character,
            provider=provider,
            content="turn one",
            emit_response_delta=emit,
            execution_runtime=runtime,
        )
        await provider.first_extraction_started.wait()

        second = await run_user_turn_two_pass_streaming(
            character=character,
            provider=provider,
            content="turn two",
            emit_response_delta=emit,
            execution_runtime=runtime,
        )

        assert provider.first_extraction_cancelled.is_set()
        assert (await first.extraction).status is TwoPassExtractionStatus.STALE
        assert (await second.extraction).status is TwoPassExtractionStatus.COMMITTED
        assert runtime.pending_extraction_count == 0
        assert emitted == ["reply-1", "reply-2"]

    asyncio.run(run())
