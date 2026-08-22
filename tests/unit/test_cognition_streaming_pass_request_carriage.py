from __future__ import annotations

import asyncio
from pathlib import Path

from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionOutput,
    CognitionPassRequest,
    CognitionReasoningMode,
)
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.two_pass_turn import (
    CognitionExecutionRuntime,
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


class _StreamingTwoPassSpyProvider:
    def __init__(self) -> None:
        self.pass1_requests: list[CognitionPassRequest | None] = []
        self.pass2_requests: list[CognitionPassRequest | None] = []

    async def stream_generate_conversation(
        self,
        _,
        emit_response_delta,
        *,
        pass_request=None,
    ):
        self.pass1_requests.append(pass_request)
        await emit_response_delta("visible")
        return CognitionConversationOutput(response="visible")

    async def generate_extraction(self, _, *, pass_request=None):
        self.pass2_requests.append(pass_request)
        return CognitionExtractionOutput()


def test_streaming_two_pass_carries_distinct_resolved_pass_requests(tmp_path: Path) -> None:
    async def run() -> None:
        character = _make_character(tmp_path / "character")
        provider = _StreamingTwoPassSpyProvider()
        deltas: list[str] = []
        off = CognitionPassRequest(reasoning_mode=CognitionReasoningMode.OFF)
        bounded = CognitionPassRequest(
            reasoning_mode=CognitionReasoningMode.BOUNDED,
            reasoning_budget=64,
        )

        turn = await run_user_turn_two_pass_streaming(
            character=character,
            provider=provider,
            content="hello",
            emit_response_delta=lambda delta: _record_delta(deltas, delta),
            execution_runtime=CognitionExecutionRuntime(),
            pass1_request=off,
            pass2_request=bounded,
        )
        extraction = await turn.extraction

        assert turn.response == "visible"
        assert deltas == ["visible"]
        assert extraction.status.value == "committed"
        assert provider.pass1_requests == [off]
        assert provider.pass2_requests == [bounded]

    asyncio.run(run())


async def _record_delta(deltas: list[str], delta: str) -> None:
    deltas.append(delta)
