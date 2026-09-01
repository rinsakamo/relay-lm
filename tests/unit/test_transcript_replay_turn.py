from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
)
from relaylm.continuity import ContinuityCandidate, ContinuityContext
from relaylm.events import Event
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import ContinuityRuntime
from relaylm.two_pass_turn import (
    CognitionExecutionRuntime,
    TwoPassExtractionStatus,
    run_user_turn_two_pass,
)
import relaylm.two_pass_turn as two_pass_turn


def _make_character(root: Path, *, memory: str | None = None) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind and honest.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    if memory is not None:
        (root / "memory" / "MEMORY.md").write_text(memory, encoding="utf-8")
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


def _imported_pair(
    *,
    suffix: str,
    user_content: str,
    assistant_content: str,
) -> tuple[Event, Event]:
    user_event = Event.create(
        type="message",
        actor="user",
        event_id=f"archive-user-{suffix}",
        timestamp=f"2026-08-01T00:0{suffix}:00+00:00",
        payload={
            "content": user_content,
            "provenance": {"archive": "chat-export", "ordinal": int(suffix) * 2},
        },
    )
    assistant_event = Event.create(
        type="message",
        actor="assistant",
        event_id=f"archive-assistant-{suffix}",
        timestamp=f"2026-08-01T00:0{suffix}:30+00:00",
        payload={
            "content": assistant_content,
            "provenance": {
                "archive": "chat-export",
                "ordinal": int(suffix) * 2 + 1,
            },
        },
    )
    return user_event, assistant_event


async def _replay(**kwargs):
    return await two_pass_turn.replay_transcript_turn_two_pass(**kwargs)


class _RecordingProvider:
    def __init__(self, outputs: list[CognitionExtractionOutput | Exception]) -> None:
        self.outputs = list(outputs)
        self.conversation_calls = 0
        self.extraction_calls = 0
        self.extraction_inputs: list[CognitionExtractionInput] = []
        self.pass2_requests: list[CognitionPassRequest | None] = []

    async def generate_conversation(self, _input, **_kwargs):
        self.conversation_calls += 1
        raise AssertionError("transcript replay must never call Pass 1")

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionExtractionOutput:
        self.extraction_calls += 1
        self.extraction_inputs.append(extraction_input)
        self.pass2_requests.append(pass_request)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


def test_replay_skips_pass1_calls_pass2_once_and_preserves_supplied_events(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        user_event, assistant_event = _imported_pair(
            suffix="1",
            user_content="I prefer jasmine tea.",
            assistant_content="Understood — jasmine tea is your preference.",
        )
        provider = _RecordingProvider([CognitionExtractionOutput()])
        pass2_request = CognitionPassRequest(temperature=0)

        result = await _replay(
            character=character,
            provider=provider,
            user_event=user_event,
            assistant_event=assistant_event,
            execution_runtime=CognitionExecutionRuntime(),
            pass2_request=pass2_request,
        )

        assert provider.conversation_calls == 0
        assert provider.extraction_calls == 1
        assert provider.pass2_requests == [pass2_request]
        assert provider.extraction_inputs[0].assistant_response == assistant_event.payload[
            "content"
        ]
        assert provider.extraction_inputs[0].originating_event_id == user_event.id
        assert result.extraction.status is TwoPassExtractionStatus.COMMITTED
        assert result.user_event == user_event
        assert result.assistant_event == assistant_event
        assert CharacterDirectory(tmp_path).iter_events() == (
            user_event,
            assistant_event,
        )

    asyncio.run(run())


def test_replay_applies_valid_state_and_continuity_through_existing_validators(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        user_event, assistant_event = _imported_pair(
            suffix="1",
            user_content="I like jasmine tea and still need to choose a shop.",
            assistant_content="We can choose a tea shop next.",
        )
        provider = _RecordingProvider(
            [
                CognitionExtractionOutput(
                    state_candidates=(
                        StateCandidate.set(
                            state_class="user.preference",
                            key="jasmine_tea",
                            value="likes",
                            sources=(user_event.id,),
                        ),
                    ),
                    continuity_candidates=(
                        ContinuityCandidate.set(
                            kind="active_task",
                            key="choose_tea_shop",
                            value="choose a tea shop",
                            sources=(user_event.id,),
                            epistemic_role="user_assertion",
                        ),
                    ),
                )
            ]
        )
        continuity_runtime = ContinuityRuntime(
            context=ContinuityContext(max_items=4),
            lifetime_revisions=3,
        )

        result = await _replay(
            character=character,
            provider=provider,
            user_event=user_event,
            assistant_event=assistant_event,
            execution_runtime=CognitionExecutionRuntime(),
            continuity_runtime=continuity_runtime,
        )

        assert result.extraction.status is TwoPassExtractionStatus.COMMITTED
        assert result.extraction.decisions[0].status == "accepted"
        assert [(item.key, item.value) for item in result.extraction.state.states] == [
            ("jasmine_tea", "likes")
        ]
        assert result.extraction.continuity is not None
        assert result.extraction.continuity.decisions[0].status == "accepted"
        assert continuity_runtime.context.revision == 1
        assert [(item.kind, item.key) for item in continuity_runtime.context.items] == [
            ("active_task", "choose_tea_shop")
        ]

    asyncio.run(run())


def test_sequential_replay_uses_prior_accepted_authority_and_no_future_turn(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        first_user, first_assistant = _imported_pair(
            suffix="1",
            user_content="I prefer tea and need to pick a shop.",
            assistant_content="Let's keep the shop choice open.",
        )
        second_user, second_assistant = _imported_pair(
            suffix="2",
            user_content="Find one near the station.",
            assistant_content="I'll focus on shops near the station.",
        )
        provider = _RecordingProvider(
            [
                CognitionExtractionOutput(
                    state_candidates=(
                        StateCandidate.set(
                            state_class="user.preference",
                            key="tea",
                            value="preferred",
                            sources=(first_user.id,),
                        ),
                    ),
                    continuity_candidates=(
                        ContinuityCandidate.set(
                            kind="active_task",
                            key="choose_shop",
                            value="choose a tea shop",
                            sources=(first_user.id,),
                            epistemic_role="user_assertion",
                        ),
                    ),
                ),
                CognitionExtractionOutput(),
            ]
        )
        continuity_runtime = ContinuityRuntime(
            context=ContinuityContext(max_items=4),
            lifetime_revisions=4,
        )
        execution_runtime = CognitionExecutionRuntime()

        first = await _replay(
            character=character,
            provider=provider,
            user_event=first_user,
            assistant_event=first_assistant,
            execution_runtime=execution_runtime,
            continuity_runtime=continuity_runtime,
        )
        assert first.extraction.status is TwoPassExtractionStatus.COMMITTED

        second = await _replay(
            character=character,
            provider=provider,
            user_event=second_user,
            assistant_event=second_assistant,
            execution_runtime=execution_runtime,
            continuity_runtime=continuity_runtime,
        )

        first_origin = provider.extraction_inputs[0].cognitive_input
        second_origin = provider.extraction_inputs[1].cognitive_input
        assert first_origin.context == ()
        assert all(second_user.id not in item.sources for item in first_origin.context)
        assert all(second_assistant.id not in item.sources for item in first_origin.context)
        assert [(item.key, item.value) for item in second_origin.state] == [
            ("tea", "preferred")
        ]
        assert any(
            item.content == "choose a tea shop" and first_user.id in item.sources
            for item in second_origin.context
        )
        assert all(second_assistant.id not in item.sources for item in second_origin.context)
        assert second.extraction.status is TwoPassExtractionStatus.COMMITTED
        assert continuity_runtime.context.revision == 2

    asyncio.run(run())


def test_pass2_failure_keeps_transcript_unchanged_without_retry_or_memory_write(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        memory = "# MEMORY\n\n## Tea\n\nImported before replay.\n"
        character = _make_character(tmp_path, memory=memory)
        user_event, assistant_event = _imported_pair(
            suffix="1",
            user_content="This turn happened already.",
            assistant_content="This answer also happened already.",
        )
        provider = _RecordingProvider([RuntimeError("malformed extraction")])

        result = await _replay(
            character=character,
            provider=provider,
            user_event=user_event,
            assistant_event=assistant_event,
            execution_runtime=CognitionExecutionRuntime(),
        )

        assert result.extraction.status is TwoPassExtractionStatus.FAILED
        assert result.extraction.failure_reason == "pass2_failed"
        assert provider.conversation_calls == 0
        assert provider.extraction_calls == 1
        assert CharacterDirectory(tmp_path).iter_events() == (
            user_event,
            assistant_event,
        )
        assert CharacterDirectory(tmp_path).load_state().states == ()
        assert (tmp_path / "memory" / "MEMORY.md").read_text(encoding="utf-8") == memory

    asyncio.run(run())


def test_replay_candidate_source_validation_remains_fail_closed(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        user_event, assistant_event = _imported_pair(
            suffix="1",
            user_content="Do not trust the assistant as my factual source.",
            assistant_content="I might infer a preference.",
        )
        provider = _RecordingProvider(
            [
                CognitionExtractionOutput(
                    state_candidates=(
                        StateCandidate.set(
                            state_class="user.preference",
                            key="tea",
                            value="likes",
                            sources=(assistant_event.id,),
                        ),
                    ),
                    continuity_candidates=(
                        ContinuityCandidate.set(
                            kind="referent",
                            key="tea_choice",
                            value="tea",
                            sources=(assistant_event.id,),
                            epistemic_role="assistant_inference",
                        ),
                    ),
                )
            ]
        )
        continuity_runtime = ContinuityRuntime(
            context=ContinuityContext(max_items=4),
            lifetime_revisions=3,
        )

        result = await _replay(
            character=character,
            provider=provider,
            user_event=user_event,
            assistant_event=assistant_event,
            execution_runtime=CognitionExecutionRuntime(),
            continuity_runtime=continuity_runtime,
        )

        assert result.extraction.status is TwoPassExtractionStatus.COMMITTED
        assert result.extraction.decisions[0].status == "rejected"
        assert result.extraction.decisions[0].reason == "missing_current_evidence"
        assert result.extraction.continuity is not None
        assert result.extraction.continuity.decisions[0].status == "rejected"
        assert (
            result.extraction.continuity.decisions[0].reason
            == "missing_current_evidence"
        )
        assert CharacterDirectory(tmp_path).load_state().states == ()
        assert continuity_runtime.context.items == ()

    asyncio.run(run())


@pytest.mark.parametrize(
    ("user_event", "assistant_event", "match"),
    [
        (
            Event.create(
                type="message",
                actor="assistant",
                event_id="wrong-user-role",
                timestamp="2026-08-01T00:00:00+00:00",
                payload={"content": "wrong role"},
            ),
            Event.create(
                type="message",
                actor="assistant",
                event_id="assistant-ok",
                timestamp="2026-08-01T00:00:01+00:00",
                payload={"content": "ok"},
            ),
            "user_event actor must be user",
        ),
        (
            Event.create(
                type="message",
                actor="user",
                event_id="user-ok",
                timestamp="2026-08-01T00:00:00+00:00",
                payload={"content": "ok"},
            ),
            Event.create(
                type="message",
                actor="assistant",
                event_id="assistant-invalid-content",
                timestamp="2026-08-01T00:00:01+00:00",
                payload={"content": 3},
            ),
            "assistant_event content must be a non-empty string",
        ),
    ],
)
def test_invalid_supplied_events_fail_before_persistence_or_provider_call(
    tmp_path: Path,
    user_event: Event,
    assistant_event: Event,
    match: str,
) -> None:
    async def run() -> None:
        character = _make_character(tmp_path)
        provider = _RecordingProvider([CognitionExtractionOutput()])

        with pytest.raises((TypeError, ValueError), match=match):
            await _replay(
                character=character,
                provider=provider,
                user_event=user_event,
                assistant_event=assistant_event,
                execution_runtime=CognitionExecutionRuntime(),
            )

        assert CharacterDirectory(tmp_path).iter_events() == ()
        assert provider.conversation_calls == 0
        assert provider.extraction_calls == 0

    asyncio.run(run())


class _EquivalenceProvider:
    def __init__(self, assistant_response: str) -> None:
        self.assistant_response = assistant_response
        self.conversation_calls = 0
        self.extraction_calls = 0

    async def generate_conversation(self, _input):
        self.conversation_calls += 1
        return CognitionConversationOutput(response=self.assistant_response)

    async def generate_extraction(
        self, extraction_input: CognitionExtractionInput
    ) -> CognitionExtractionOutput:
        self.extraction_calls += 1
        source = extraction_input.originating_event_id
        return CognitionExtractionOutput(
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="jasmine_tea",
                    value="likes",
                    sources=(source,),
                ),
            ),
            continuity_candidates=(
                ContinuityCandidate.set(
                    kind="active_task",
                    key="choose_shop",
                    value="choose a tea shop",
                    sources=(source,),
                    epistemic_role="user_assertion",
                ),
            ),
        )


def test_synthetic_live_two_pass_and_replay_converge_semantically(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        live_character = _make_character(tmp_path / "live")
        replay_character = _make_character(tmp_path / "replay")
        assistant_response = "Let's choose a jasmine tea shop."
        live_provider = _EquivalenceProvider(assistant_response)
        replay_provider = _EquivalenceProvider(assistant_response)
        live_continuity = ContinuityRuntime(
            context=ContinuityContext(max_items=4),
            lifetime_revisions=3,
        )
        replay_continuity = ContinuityRuntime(
            context=ContinuityContext(max_items=4),
            lifetime_revisions=3,
        )

        live = await run_user_turn_two_pass(
            character=live_character,
            provider=live_provider,
            content="I like jasmine tea and need to choose a shop.",
            execution_runtime=CognitionExecutionRuntime(),
            continuity_runtime=live_continuity,
        )
        live_extraction = await live.extraction

        user_event, assistant_event = _imported_pair(
            suffix="1",
            user_content="I like jasmine tea and need to choose a shop.",
            assistant_content=assistant_response,
        )
        replay = await _replay(
            character=replay_character,
            provider=replay_provider,
            user_event=user_event,
            assistant_event=assistant_event,
            execution_runtime=CognitionExecutionRuntime(),
            continuity_runtime=replay_continuity,
        )

        state_semantics = lambda state: tuple(
            (item.state_class, item.key, item.value) for item in state.states
        )
        continuity_semantics = lambda context: tuple(
            (item.kind, item.key, item.value, item.epistemic_role)
            for item in context.items
        )
        assert live_extraction.status is TwoPassExtractionStatus.COMMITTED
        assert replay.extraction.status is TwoPassExtractionStatus.COMMITTED
        assert state_semantics(live_extraction.state) == state_semantics(
            replay.extraction.state
        )
        assert continuity_semantics(live_continuity.context) == continuity_semantics(
            replay_continuity.context
        )
        assert live_continuity.context.revision == replay_continuity.context.revision == 1
        assert live_provider.conversation_calls == 1
        assert replay_provider.conversation_calls == 0
        assert live_provider.extraction_calls == replay_provider.extraction_calls == 1

    asyncio.run(run())
