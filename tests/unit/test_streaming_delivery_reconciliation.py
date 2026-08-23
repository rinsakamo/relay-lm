from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.budget import (
    BudgetDegradationPolicy,
    BudgetPlan,
    CountCharacterEnvelope,
    CountEnvelope,
    TotalBudgetConfig,
)
from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
)
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import (
    run_user_turn_streaming,
    run_user_turn_streaming_with_cognitive_budget_diagnostics,
    run_user_turn_streaming_with_retrieval_diagnostics,
)
from relaylm.two_pass_turn import CognitionExecutionRuntime, run_user_turn_two_pass_streaming


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


class _ExactCounter:
    def count_serialized_input(
        self,
        _: CognitiveInput,
    ) -> SerializedInputTokenCount:
        return SerializedInputTokenCount(
            total_input_tokens=10,
            required_input_framing_tokens=5,
            mode=TokenCountMode.EXACT,
        )


def _budget_runtime() -> CognitiveBudgetRuntimeConfig:
    zero_plan = BudgetPlan(
        canonical_state=CountEnvelope(0, 0),
        working_context=CountCharacterEnvelope(0, 0, 0, 0),
        retrieved_memory=CountCharacterEnvelope(0, 0, 0, 0),
        event_evidence=CountCharacterEnvelope(0, 0, 0, 0),
    )
    return CognitiveBudgetRuntimeConfig(
        total=TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20),
        policy=BudgetDegradationPolicy(initial_plan=zero_plan, steps=()),
        token_counter=_ExactCounter(),
    )


class _SinglePassStreamingProvider:
    def __init__(self, *, fragments: tuple[str, ...], final_response: str) -> None:
        self.fragments = fragments
        self.final_response = final_response

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("streaming test must not use buffered generation")

    async def stream_generate(self, _: CognitiveInput, emit) -> CognitiveOutput:
        for fragment in self.fragments:
            await emit(fragment)
        return CognitiveOutput(response=self.final_response)


class _TwoPassStreamingProvider:
    def __init__(self, *, fragments: tuple[str, ...], final_response: str) -> None:
        self.fragments = fragments
        self.final_response = final_response
        self.extraction_calls = 0

    async def generate_conversation(self, _: CognitiveInput) -> CognitionConversationOutput:
        raise AssertionError("streaming test must not use buffered conversation generation")

    async def stream_generate_conversation(self, _: CognitiveInput, emit) -> CognitionConversationOutput:
        for fragment in self.fragments:
            await emit(fragment)
        return CognitionConversationOutput(response=self.final_response)

    async def generate_extraction(
        self,
        _: CognitionExtractionInput,
    ) -> CognitionExtractionOutput:
        self.extraction_calls += 1
        return CognitionExtractionOutput()


def _assert_only_user_event(character: CharacterDirectory) -> None:
    assert [event.actor for event in character.iter_events()] == ["user"]
    assert character.load_state() == CanonicalState()


async def _run_single_variant(
    variant: str,
    *,
    character: CharacterDirectory,
    provider: _SinglePassStreamingProvider,
    emit,
):
    if variant == "ordinary":
        return await run_user_turn_streaming(
            character=character,
            provider=provider,
            content="hello",
            emit_response_delta=emit,
        )
    if variant == "retrieval":
        return await run_user_turn_streaming_with_retrieval_diagnostics(
            character=character,
            provider=provider,
            content="hello",
            emit_response_delta=emit,
        )
    if variant == "budget":
        return await run_user_turn_streaming_with_cognitive_budget_diagnostics(
            character=character,
            provider=provider,
            content="hello",
            emit_response_delta=emit,
            cognitive_budget=_budget_runtime(),
        )
    raise AssertionError(variant)


@pytest.mark.parametrize("variant", ["ordinary", "retrieval", "budget"])
def test_single_pass_streaming_rejects_delivered_text_that_conflicts_with_final_response(
    tmp_path: Path,
    variant: str,
) -> None:
    character = _make_character(tmp_path)
    provider = _SinglePassStreamingProvider(
        fragments=("visible-a",),
        final_response="visible-b",
    )
    deltas: list[str] = []

    async def emit(text: str) -> None:
        deltas.append(text)

    with pytest.raises(RuntimeError, match="streamed response does not match final cognitive response"):
        asyncio.run(
            _run_single_variant(
                variant,
                character=character,
                provider=provider,
                emit=emit,
            )
        )

    assert deltas == ["visible-a"]
    _assert_only_user_event(character)


@pytest.mark.parametrize(
    ("fragments", "expected_deltas"),
    [
        ((), ["hello"]),
        (("hel",), ["hel", "lo"]),
    ],
)
def test_single_pass_streaming_completes_missing_delivery_suffix_before_commit(
    tmp_path: Path,
    fragments: tuple[str, ...],
    expected_deltas: list[str],
) -> None:
    character = _make_character(tmp_path)
    provider = _SinglePassStreamingProvider(
        fragments=fragments,
        final_response="hello",
    )
    deltas: list[str] = []

    async def emit(text: str) -> None:
        deltas.append(text)

    result = asyncio.run(
        run_user_turn_streaming(
            character=character,
            provider=provider,
            content="hello",
            emit_response_delta=emit,
        )
    )

    assert result.response == "hello"
    assert deltas == expected_deltas
    assert [event.actor for event in character.iter_events()] == ["user", "assistant"]


def test_two_pass_streaming_rejects_delivered_text_that_conflicts_with_final_response(
    tmp_path: Path,
) -> None:
    character = _make_character(tmp_path)
    provider = _TwoPassStreamingProvider(
        fragments=("visible-a",),
        final_response="visible-b",
    )
    deltas: list[str] = []

    async def emit(text: str) -> None:
        deltas.append(text)

    with pytest.raises(RuntimeError, match="streamed response does not match final cognitive response"):
        asyncio.run(
            run_user_turn_two_pass_streaming(
                character=character,
                provider=provider,
                content="hello",
                emit_response_delta=emit,
                execution_runtime=CognitionExecutionRuntime(),
            )
        )

    assert deltas == ["visible-a"]
    assert provider.extraction_calls == 0
    _assert_only_user_event(character)


@pytest.mark.parametrize(
    ("fragments", "expected_deltas"),
    [
        ((), ["hello"]),
        (("hel",), ["hel", "lo"]),
    ],
)
def test_two_pass_streaming_completes_missing_delivery_suffix_before_commit(
    tmp_path: Path,
    fragments: tuple[str, ...],
    expected_deltas: list[str],
) -> None:
    async def run() -> tuple[list[str], int]:
        character = _make_character(tmp_path)
        provider = _TwoPassStreamingProvider(
            fragments=fragments,
            final_response="hello",
        )
        deltas: list[str] = []

        async def emit(text: str) -> None:
            deltas.append(text)

        result = await run_user_turn_two_pass_streaming(
            character=character,
            provider=provider,
            content="hello",
            emit_response_delta=emit,
            execution_runtime=CognitionExecutionRuntime(),
        )
        extraction = await result.extraction
        assert extraction.status.value == "committed"
        assert result.response == "hello"
        assert [event.actor for event in character.iter_events()] == ["user", "assistant"]
        return deltas, provider.extraction_calls

    deltas, extraction_calls = asyncio.run(run())
    assert deltas == expected_deltas
    assert extraction_calls == 1
