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
from relaylm.cognitive import CognitiveInput
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import (
    run_user_turn,
    run_user_turn_streaming,
    run_user_turn_streaming_with_cognitive_budget_diagnostics,
    run_user_turn_streaming_with_retrieval_diagnostics,
    run_user_turn_with_cognitive_budget_diagnostics,
    run_user_turn_with_retrieval_diagnostics,
)


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


class _DuckOutput:
    response = "   "
    state_candidates = ()
    continuity_candidates = ()


class _WrongTypeProvider:
    async def generate(self, _: CognitiveInput) -> object:
        return _DuckOutput()

    async def stream_generate(self, _: CognitiveInput, emit) -> object:
        await emit("prefix")
        return _DuckOutput()


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


def _assert_only_user_event(character: CharacterDirectory) -> None:
    events = list(character.iter_events())
    assert [event.actor for event in events] == ["user"]
    assert character.load_state() == CanonicalState()


def test_buffered_turn_rejects_wrong_result_type_before_semantic_commit(tmp_path: Path) -> None:
    character = _make_character(tmp_path)

    with pytest.raises(TypeError, match="provider generation must return CognitiveOutput"):
        asyncio.run(
            run_user_turn(
                character=character,
                provider=_WrongTypeProvider(),
                content="hello",
            )
        )

    _assert_only_user_event(character)


def test_streaming_turn_rejects_wrong_result_type_before_semantic_commit(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    deltas: list[str] = []

    async def emit(text: str) -> None:
        deltas.append(text)

    with pytest.raises(TypeError, match="provider generation must return CognitiveOutput"):
        asyncio.run(
            run_user_turn_streaming(
                character=character,
                provider=_WrongTypeProvider(),
                content="hello",
                emit_response_delta=emit,
            )
        )

    assert deltas == ["prefix"]
    _assert_only_user_event(character)


def test_buffered_retrieval_diagnostics_reject_wrong_result_type(tmp_path: Path) -> None:
    character = _make_character(tmp_path)

    with pytest.raises(TypeError, match="provider generation must return CognitiveOutput"):
        asyncio.run(
            run_user_turn_with_retrieval_diagnostics(
                character=character,
                provider=_WrongTypeProvider(),
                content="hello",
            )
        )

    _assert_only_user_event(character)


def test_streaming_retrieval_diagnostics_reject_wrong_result_type(tmp_path: Path) -> None:
    character = _make_character(tmp_path)

    async def emit(_: str) -> None:
        return None

    with pytest.raises(TypeError, match="provider generation must return CognitiveOutput"):
        asyncio.run(
            run_user_turn_streaming_with_retrieval_diagnostics(
                character=character,
                provider=_WrongTypeProvider(),
                content="hello",
                emit_response_delta=emit,
            )
        )

    _assert_only_user_event(character)


def test_buffered_budget_diagnostics_reject_wrong_result_type(tmp_path: Path) -> None:
    character = _make_character(tmp_path)

    with pytest.raises(TypeError, match="provider generation must return CognitiveOutput"):
        asyncio.run(
            run_user_turn_with_cognitive_budget_diagnostics(
                character=character,
                provider=_WrongTypeProvider(),
                content="hello",
                cognitive_budget=_budget_runtime(),
            )
        )

    _assert_only_user_event(character)


def test_streaming_budget_diagnostics_reject_wrong_result_type(tmp_path: Path) -> None:
    character = _make_character(tmp_path)

    async def emit(_: str) -> None:
        return None

    with pytest.raises(TypeError, match="provider generation must return CognitiveOutput"):
        asyncio.run(
            run_user_turn_streaming_with_cognitive_budget_diagnostics(
                character=character,
                provider=_WrongTypeProvider(),
                content="hello",
                emit_response_delta=emit,
                cognitive_budget=_budget_runtime(),
            )
        )

    _assert_only_user_event(character)
