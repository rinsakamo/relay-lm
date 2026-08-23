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
from relaylm.budget_enforcement import (
    CognitiveBudgetExceeded,
    SerializedInputTokenCount,
    TokenCountMode,
)
from relaylm.budget_runtime import TwoPassCognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
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


def _zero_plan() -> BudgetPlan:
    return BudgetPlan(
        canonical_state=CountEnvelope(0, 0),
        working_context=CountCharacterEnvelope(0, 0, 0, 0),
        retrieved_memory=CountCharacterEnvelope(0, 0, 0, 0),
        event_evidence=CountCharacterEnvelope(0, 0, 0, 0),
    )


class _PassAwareCounter:
    def __init__(
        self,
        *,
        conversation_totals: tuple[int, ...] = (50, 70),
        extraction_total: int = 90,
    ) -> None:
        self.conversation_totals = conversation_totals
        self.extraction_total = extraction_total
        self.legacy_inputs: list[CognitiveInput] = []
        self.conversation_inputs: list[tuple[CognitiveInput, CognitionPassRequest | None]] = []
        self.extraction_inputs: list[
            tuple[CognitionExtractionInput, CognitionPassRequest | None]
        ] = []

    @staticmethod
    def _count(total: int) -> SerializedInputTokenCount:
        return SerializedInputTokenCount(
            total_input_tokens=total,
            required_input_framing_tokens=10,
            mode=TokenCountMode.EXACT,
        )

    def count_serialized_input(
        self,
        cognitive_input: CognitiveInput,
    ) -> SerializedInputTokenCount:
        self.legacy_inputs.append(cognitive_input)
        return self._count(50)

    def count_conversation_input(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> SerializedInputTokenCount:
        self.conversation_inputs.append((cognitive_input, pass_request))
        index = min(len(self.conversation_inputs) - 1, len(self.conversation_totals) - 1)
        return self._count(self.conversation_totals[index])

    def count_extraction_input(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> SerializedInputTokenCount:
        self.extraction_inputs.append((extraction_input, pass_request))
        return self._count(self.extraction_total)


class _RecordingTwoPassProvider:
    def __init__(self) -> None:
        self.conversation_calls = 0
        self.streaming_calls = 0
        self.extraction_calls = 0
        self.pass1_requests: list[CognitionPassRequest | None] = []
        self.pass2_requests: list[CognitionPassRequest | None] = []

    async def generate_conversation(
        self,
        _cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionConversationOutput:
        self.conversation_calls += 1
        self.pass1_requests.append(pass_request)
        return CognitionConversationOutput(response="visible")

    async def stream_generate_conversation(
        self,
        _cognitive_input: CognitiveInput,
        emit,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionConversationOutput:
        self.streaming_calls += 1
        self.pass1_requests.append(pass_request)
        await emit("visible")
        return CognitionConversationOutput(response="visible")

    async def generate_extraction(
        self,
        _extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionExtractionOutput:
        self.extraction_calls += 1
        self.pass2_requests.append(pass_request)
        return CognitionExtractionOutput()


def _two_pass_runtime(counter: _PassAwareCounter) -> TwoPassCognitiveBudgetRuntimeConfig:
    return TwoPassCognitiveBudgetRuntimeConfig(
        pass1_total=TotalBudgetConfig(
            model_context_window=100,
            reserved_output_tokens=20,
        ),
        pass2_total=TotalBudgetConfig(
            model_context_window=100,
            reserved_output_tokens=20,
        ),
        policy=BudgetDegradationPolicy(initial_plan=_zero_plan(), steps=()),
        token_counter=counter,
    )


def test_buffered_two_pass_budget_counts_each_real_pass_and_blocks_pass2_overflow(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _RecordingTwoPassProvider()
        counter = _PassAwareCounter()
        pass1_request = CognitionPassRequest(max_output_tokens=16)
        pass2_request = CognitionPassRequest(max_output_tokens=8)

        result = await run_user_turn_two_pass(
            character=character,
            provider=provider,
            content="hello",
            execution_runtime=CognitionExecutionRuntime(),
            cognitive_budget=_two_pass_runtime(counter),
            pass1_request=pass1_request,
            pass2_request=pass2_request,
        )

        assert result.response == "visible"
        extraction = await result.extraction
        assert extraction.status is TwoPassExtractionStatus.FAILED
        assert extraction.failure_reason == "pass2_budget_exceeded"

        assert provider.conversation_calls == 1
        assert provider.extraction_calls == 0
        assert provider.pass1_requests == [pass1_request]
        assert provider.pass2_requests == []

        assert counter.legacy_inputs == []
        assert [request for _, request in counter.conversation_inputs] == [
            pass1_request,
            pass1_request,
        ]
        assert [request for _, request in counter.extraction_inputs] == [pass2_request]
        assert counter.extraction_inputs[0][0].assistant_response == "visible"

        assert CharacterDirectory(tmp_path).load_state() == CanonicalState()
        assert [event.actor for event in CharacterDirectory(tmp_path).iter_events()] == [
            "user",
            "assistant",
        ]

    asyncio.run(run())


def test_streaming_two_pass_budget_blocks_pass2_overflow_after_valid_pass1(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _RecordingTwoPassProvider()
        counter = _PassAwareCounter()
        pass1_request = CognitionPassRequest(max_output_tokens=16)
        pass2_request = CognitionPassRequest(max_output_tokens=8)
        emitted: list[str] = []

        async def emit(delta: str) -> None:
            emitted.append(delta)

        result = await run_user_turn_two_pass_streaming(
            character=character,
            provider=provider,
            content="hello",
            emit_response_delta=emit,
            execution_runtime=CognitionExecutionRuntime(),
            cognitive_budget=_two_pass_runtime(counter),
            pass1_request=pass1_request,
            pass2_request=pass2_request,
        )

        assert emitted == ["visible"]
        assert result.response == "visible"
        extraction = await result.extraction
        assert extraction.status is TwoPassExtractionStatus.FAILED
        assert extraction.failure_reason == "pass2_budget_exceeded"

        assert provider.streaming_calls == 1
        assert provider.extraction_calls == 0
        assert provider.pass1_requests == [pass1_request]
        assert provider.pass2_requests == []
        assert counter.legacy_inputs == []
        assert [request for _, request in counter.conversation_inputs] == [
            pass1_request,
            pass1_request,
        ]
        assert [request for _, request in counter.extraction_inputs] == [pass2_request]

    asyncio.run(run())


def test_buffered_two_pass_budget_delegates_when_pass2_fits(tmp_path: Path) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _RecordingTwoPassProvider()
        counter = _PassAwareCounter(extraction_total=70)
        pass1_request = CognitionPassRequest(max_output_tokens=16)
        pass2_request = CognitionPassRequest(max_output_tokens=8)

        result = await run_user_turn_two_pass(
            character=character,
            provider=provider,
            content="hello",
            execution_runtime=CognitionExecutionRuntime(),
            cognitive_budget=_two_pass_runtime(counter),
            pass1_request=pass1_request,
            pass2_request=pass2_request,
        )
        extraction = await result.extraction

        assert extraction.status is TwoPassExtractionStatus.COMMITTED
        assert extraction.failure_reason is None
        assert provider.conversation_calls == 1
        assert provider.extraction_calls == 1
        assert provider.pass2_requests == [pass2_request]
        assert [request for _, request in counter.extraction_inputs] == [pass2_request]
        assert counter.legacy_inputs == []

    asyncio.run(run())


def test_pass1_exact_budget_overflow_fails_before_conversation_provider(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _RecordingTwoPassProvider()
        counter = _PassAwareCounter(conversation_totals=(90,))
        pass1_request = CognitionPassRequest(max_output_tokens=16)

        with pytest.raises(CognitiveBudgetExceeded):
            await run_user_turn_two_pass(
                character=character,
                provider=provider,
                content="hello",
                execution_runtime=CognitionExecutionRuntime(),
                cognitive_budget=_two_pass_runtime(counter),
                pass1_request=pass1_request,
            )

        assert provider.conversation_calls == 0
        assert provider.extraction_calls == 0
        assert counter.legacy_inputs == []
        assert [request for _, request in counter.conversation_inputs] == [pass1_request]

    asyncio.run(run())
