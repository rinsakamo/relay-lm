from __future__ import annotations

import asyncio
from pathlib import Path

from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
)
from relaylm.continuity import ContinuityCandidate, ContinuityContext
from relaylm.state import CanonicalState, StateCandidate
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


class _ControlledTwoPassProvider:
    def __init__(self) -> None:
        self.conversation_inputs = []
        self.extraction_inputs: list[CognitionExtractionInput] = []
        self.extraction_started = [asyncio.Event(), asyncio.Event()]
        self.extraction_release = [asyncio.Event(), asyncio.Event()]

    async def generate_conversation(self, cognitive_input):
        self.conversation_inputs.append(cognitive_input)
        return CognitionConversationOutput(
            response=f"reply-{len(self.conversation_inputs)}"
        )

    async def generate_extraction(
        self, extraction_input: CognitionExtractionInput
    ) -> CognitionExtractionOutput:
        index = len(self.extraction_inputs)
        self.extraction_inputs.append(extraction_input)
        self.extraction_started[index].set()
        await self.extraction_release[index].wait()
        return CognitionExtractionOutput(
            state_candidates=(
                StateCandidate.set(
                    state_class="user.fact",
                    key="latest_turn",
                    value=extraction_input.cognitive_input.input.payload["content"],
                    sources=(extraction_input.cognitive_input.input.id,),
                ),
            ),
        )


class _FailingExtractionProvider:
    async def generate_conversation(self, _):
        return CognitionConversationOutput(response="visible response")

    async def generate_extraction(self, _):
        raise RuntimeError("pass2 exploded")


class _MixedExtractionWithoutContinuityRuntimeProvider:
    async def generate_conversation(self, _):
        return CognitionConversationOutput(response="visible response")

    async def generate_extraction(
        self, extraction_input: CognitionExtractionInput
    ) -> CognitionExtractionOutput:
        source = extraction_input.cognitive_input.input.id
        return CognitionExtractionOutput(
            state_candidates=(
                StateCandidate.set(
                    state_class="user.fact",
                    key="should_not_commit",
                    value="x",
                    sources=(source,),
                ),
            ),
            continuity_candidates=(
                ContinuityCandidate.set(
                    kind="unresolved",
                    key="missing_runtime",
                    value="pending",
                    sources=(source,),
                    epistemic_role="user_assertion",
                ),
            ),
        )


class _SuccessfulContinuityProvider:
    async def generate_conversation(self, _):
        return CognitionConversationOutput(response="we can continue")

    async def generate_extraction(
        self, extraction_input: CognitionExtractionInput
    ) -> CognitionExtractionOutput:
        source = extraction_input.cognitive_input.input.id
        return CognitionExtractionOutput(
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="tea",
                    value="likes",
                    sources=(source,),
                ),
            ),
            continuity_candidates=(
                ContinuityCandidate.set(
                    kind="active_task",
                    key="choose_tea",
                    value="pick a tea",
                    sources=(source,),
                    epistemic_role="user_assertion",
                ),
            ),
        )


class _StreamingTwoPassProvider:
    def __init__(self) -> None:
        self.extraction_started = asyncio.Event()
        self.extraction_release = asyncio.Event()
        self.order: list[str] = []

    async def stream_generate_conversation(self, _, emit):
        self.order.append("pass1:start")
        await emit("hello")
        self.order.append("pass1:visible")
        await emit(" world")
        self.order.append("pass1:complete")
        return CognitionConversationOutput(response="hello world")

    async def generate_extraction(self, _):
        self.order.append("pass2:start")
        self.extraction_started.set()
        await self.extraction_release.wait()
        self.order.append("pass2:complete")
        return CognitionExtractionOutput()


def test_next_pass1_cancels_prior_pending_pass2_and_old_result_is_stale(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _ControlledTwoPassProvider()
        execution_runtime = CognitionExecutionRuntime()
        assert execution_runtime.pending_extraction_count == 0

        first = await run_user_turn_two_pass(
            character=character,
            provider=provider,
            content="turn one",
            execution_runtime=execution_runtime,
        )
        await provider.extraction_started[0].wait()

        assert first.response == "reply-1"
        assert execution_runtime.pending_extraction_count == 1
        assert CharacterDirectory(tmp_path).load_state().states == ()
        assert [event.actor for event in CharacterDirectory(tmp_path).iter_events()] == [
            "user",
            "assistant",
        ]

        second = await run_user_turn_two_pass(
            character=character,
            provider=provider,
            content="turn two",
            execution_runtime=execution_runtime,
        )
        await provider.extraction_started[1].wait()

        assert second.response == "reply-2"
        assert len(provider.conversation_inputs) == 2
        assert first.extraction.done() is True
        assert (await first.extraction).status is TwoPassExtractionStatus.STALE
        assert execution_runtime.pending_extraction_count == 1
        assert CharacterDirectory(tmp_path).load_state().states == ()

        provider.extraction_release[1].set()
        second_extraction = await second.extraction
        await asyncio.sleep(0)
        assert second_extraction.status is TwoPassExtractionStatus.COMMITTED
        assert execution_runtime.pending_extraction_count == 0
        persisted = CharacterDirectory(tmp_path).load_state()
        assert [(item.key, item.value) for item in persisted.states] == [
            ("latest_turn", "turn two")
        ]

        assert provider.extraction_inputs[0].assistant_response == "reply-1"
        assert provider.extraction_inputs[0].originating_event_id == first.user_event.id
        assert provider.extraction_inputs[1].originating_event_id == second.user_event.id

    asyncio.run(run())


def test_pass2_failure_preserves_visible_response_and_commits_no_state(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        result = await run_user_turn_two_pass(
            character=character,
            provider=_FailingExtractionProvider(),
            content="hello",
            execution_runtime=CognitionExecutionRuntime(),
        )

        extraction = await result.extraction
        assert result.response == "visible response"
        assert extraction.status is TwoPassExtractionStatus.FAILED
        assert extraction.failure_reason == "pass2_failed"
        assert CharacterDirectory(tmp_path).load_state().states == ()
        assert [event.actor for event in CharacterDirectory(tmp_path).iter_events()] == [
            "user",
            "assistant",
        ]

    asyncio.run(run())


def test_missing_continuity_runtime_fails_pass2_atomically_without_state_commit(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        result = await run_user_turn_two_pass(
            character=character,
            provider=_MixedExtractionWithoutContinuityRuntimeProvider(),
            content="there is still something unresolved",
            execution_runtime=CognitionExecutionRuntime(),
        )

        extraction = await result.extraction
        assert extraction.status is TwoPassExtractionStatus.FAILED
        assert extraction.failure_reason == "continuity_runtime_required"
        assert CharacterDirectory(tmp_path).load_state().states == ()

    asyncio.run(run())


def test_successful_pass2_commits_state_and_continuity_at_one_guarded_boundary(
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
            content="I like tea and still need to choose one",
            execution_runtime=CognitionExecutionRuntime(),
            continuity_runtime=continuity_runtime,
        )

        extraction = await result.extraction
        assert extraction.status is TwoPassExtractionStatus.COMMITTED
        assert [(item.key, item.value) for item in extraction.state.states] == [
            ("tea", "likes")
        ]
        assert extraction.continuity is not None
        assert extraction.continuity.context.revision == 1
        assert [(item.kind, item.key) for item in continuity_runtime.context.items] == [
            ("active_task", "choose_tea")
        ]

    asyncio.run(run())


def test_streaming_pass1_is_visible_before_pass2_and_pass2_is_backgrounded(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _StreamingTwoPassProvider()
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        result = await run_user_turn_two_pass_streaming(
            character=character,
            provider=provider,
            content="hello",
            emit_response_delta=emit,
            execution_runtime=CognitionExecutionRuntime(),
        )
        await provider.extraction_started.wait()

        assert "".join(emitted) == "hello world"
        assert result.response == "hello world"
        assert result.extraction.done() is False
        assert provider.order[:4] == [
            "pass1:start",
            "pass1:visible",
            "pass1:complete",
            "pass2:start",
        ]

        provider.extraction_release.set()
        extraction = await result.extraction
        assert extraction.status is TwoPassExtractionStatus.COMMITTED

    asyncio.run(run())
