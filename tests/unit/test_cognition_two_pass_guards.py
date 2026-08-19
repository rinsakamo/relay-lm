from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
)
from relaylm.state import CanonicalState, StateCandidate, StateRecord
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


class _HeldExtractionProvider:
    def __init__(self) -> None:
        self.extraction_started = asyncio.Event()
        self.extraction_release = asyncio.Event()

    async def generate_conversation(self, _):
        return CognitionConversationOutput(response="visible")

    async def generate_extraction(
        self, extraction_input: CognitionExtractionInput
    ) -> CognitionExtractionOutput:
        self.extraction_started.set()
        await self.extraction_release.wait()
        source = extraction_input.originating_event_id
        return CognitionExtractionOutput(
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="drink",
                    value="coffee",
                    sources=(source,),
                ),
            )
        )


class _FailingConversationProvider:
    def __init__(self) -> None:
        self.extraction_calls = 0

    async def generate_conversation(self, _):
        raise RuntimeError("pass1 failed")

    async def generate_extraction(self, _):
        self.extraction_calls += 1
        return CognitionExtractionOutput()


def test_pass2_is_stale_if_canonical_state_advanced_after_origin_snapshot(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _HeldExtractionProvider()
        result = await run_user_turn_two_pass(
            character=character,
            provider=provider,
            content="recently coffee",
            execution_runtime=CognitionExecutionRuntime(),
        )
        await provider.extraction_started.wait()

        external = CanonicalState(
            states=(
                StateRecord(
                    state_id="external-state",
                    state_class="user.fact",
                    key="newer_authority",
                    value="preserve-me",
                    sources=(result.user_event.id,),
                ),
            )
        )
        character.save_state(external)
        provider.extraction_release.set()

        extraction = await result.extraction
        assert extraction.status is TwoPassExtractionStatus.STALE
        assert CharacterDirectory(tmp_path).load_state() == external

    asyncio.run(run())


def test_pass1_failure_creates_no_assistant_event_and_never_starts_pass2(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _FailingConversationProvider()

        with pytest.raises(RuntimeError, match="pass1 failed"):
            await run_user_turn_two_pass(
                character=character,
                provider=provider,
                content="hello",
                execution_runtime=CognitionExecutionRuntime(),
            )

        assert provider.extraction_calls == 0
        assert [event.actor for event in CharacterDirectory(tmp_path).iter_events()] == [
            "user"
        ]
        assert CharacterDirectory(tmp_path).load_state().states == ()

    asyncio.run(run())
