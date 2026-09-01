from __future__ import annotations

import asyncio
import json
from pathlib import Path

from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
)
from relaylm.continuity import ContinuityCandidate, ContinuityContext
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.cognitive_package import CognitivePackageDirectory
from relaylm.turn import EventRetrievalBudget
from tools.memconflict_adapter import RelayLMReadOnlyQueryAdapter


def _blank_package(root: Path) -> CognitivePackageDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# Blank\n\nStay grounded.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: blank\n  name: Blank\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    package = CognitivePackageDirectory(root)
    package.save_state(CanonicalState())
    return package


class _ReplayProvider:
    def __init__(self) -> None:
        self.conversation_calls = 0
        self.extraction_calls = 0
        self.extraction_inputs: list[CognitionExtractionInput] = []

    async def generate_conversation(self, _cognitive_input, **_kwargs):
        self.conversation_calls += 1
        return CognitionConversationOutput(response="query-response")

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
        **_kwargs,
    ):
        self.extraction_calls += 1
        self.extraction_inputs.append(extraction_input)
        content = extraction_input.cognitive_input.input.payload["content"]
        if content == "I moved to Kyoto and still need to choose a tea shop.":
            source = extraction_input.originating_event_id
            return CognitionExtractionOutput(
                state_candidates=(
                    StateCandidate.set(
                        state_class="user.fact",
                        key="residence",
                        value="Kyoto",
                        sources=(source,),
                    ),
                ),
                continuity_candidates=(
                    ContinuityCandidate.set(
                        kind="active_task",
                        key="choose_tea_shop",
                        value="choose a tea shop",
                        sources=(source,),
                        epistemic_role="user_assertion",
                    ),
                ),
            )
        return CognitionExtractionOutput()


def _dialogue() -> tuple[dict[str, object], ...]:
    return (
        {
            "role": "user",
            "content": "I moved to Kyoto and still need to choose a tea shop.",
            "timestamp": "2026-08-01T00:00:00+00:00",
            "provenance": {"archive": "memconflict", "ordinal": 0},
        },
        {
            "role": "assistant",
            "content": "Kyoto is current; the tea-shop choice remains open.",
            "timestamp": "2026-08-01T00:00:30+00:00",
            "provenance": {"archive": "memconflict", "ordinal": 1},
        },
        {
            "role": "user",
            "content": "Please focus on shops near the station.",
            "timestamp": "2026-08-01T00:01:00+00:00",
            "provenance": {"archive": "memconflict", "ordinal": 2},
        },
        {
            "role": "assistant",
            "content": "I will keep the station constraint in mind.",
            "timestamp": "2026-08-01T00:01:30+00:00",
            "provenance": {"archive": "memconflict", "ordinal": 3},
        },
    )


def test_blank_package_transcript_replay_forms_state_and_continuity_then_freezes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "blank"
    package = _blank_package(root)
    provider = _ReplayProvider()
    adapter = RelayLMReadOnlyQueryAdapter(
        package_root=root,
        provider=provider,
        mode="two_pass",
        event_budget=EventRetrievalBudget(max_events=4, max_chars=2_000),
        continuity_context=ContinuityContext(max_items=4),
        continuity_lifetime_revisions=4,
    )

    events = adapter.ingest_session_dialogue(
        _dialogue(),
        session_id="persona-0-session-0",
        session_index=0,
    )

    assert provider.conversation_calls == 0
    assert provider.extraction_calls == 2
    assert [event.actor for event in events] == ["user", "assistant", "user", "assistant"]
    assert [event.timestamp for event in events] == [
        "2026-08-01T00:00:00+00:00",
        "2026-08-01T00:00:30+00:00",
        "2026-08-01T00:01:00+00:00",
        "2026-08-01T00:01:30+00:00",
    ]
    assert [event.payload["content"] for event in events] == [
        item["content"] for item in _dialogue()
    ]
    assert [event.payload["provenance"] for event in events] == [
        item["provenance"] for item in _dialogue()
    ]

    persisted = CognitivePackageDirectory(root)
    assert tuple(persisted.iter_events()) == events
    state = persisted.load_state()
    assert [(item.key, item.value) for item in state.states] == [("residence", "Kyoto")]
    assert not (root / "memory" / "MEMORY.md").exists()

    second_origin = provider.extraction_inputs[1].cognitive_input
    assert [(item.key, item.value) for item in second_origin.state] == [
        ("residence", "Kyoto")
    ]
    assert any(
        json.loads(item.content).get("continuity", {}).get("value") == "choose a tea shop"
        for item in second_origin.context
        if item.content.startswith("{")
    )
    assert all(events[3].id not in item.sources for item in second_origin.context)

    ingestion = adapter.dialogue_ingestion_evidence
    assert len(ingestion) == 2
    assert [item["pass1_calls"] for item in ingestion] == [0, 0]
    assert [item["pass2_attempts"] for item in ingestion] == [1, 1]
    assert [item["pass2_status"] for item in ingestion] == ["committed", "committed"]
    assert all(item["failure_diagnostics"] == [] for item in ingestion)

    with adapter:
        with adapter.freeze() as snapshot:
            mechanics = snapshot.mechanics
            assert mechanics["dialogue_ingest"] == (
                "relaylm.two_pass_turn.replay_transcript_turn_two_pass"
            )
            assert mechanics["dialogue_ingest_pass1_calls"] == 0
            assert mechanics["dialogue_ingest_pass2_attempts"] == 2
            assert mechanics["dialogue_ingest_pass2_committed"] == 2
            assert mechanics["dialogue_ingest_pass2_failed"] == 0
            result = asyncio.run(snapshot.query("Where do I live?", question_index=1))
            assert [(item.key, item.value) for item in result.cognitive_input.state] == [
                ("residence", "Kyoto")
            ]

    assert provider.conversation_calls == 1
    assert provider.extraction_calls == 3
    assert package.load_state().states == persisted.load_state().states


class _FailureThenSuccessProvider:
    def __init__(self) -> None:
        self.conversation_calls = 0
        self.extraction_calls = 0

    async def generate_conversation(self, _cognitive_input, **_kwargs):
        self.conversation_calls += 1
        raise AssertionError("ingestion must not call Pass 1")

    async def generate_extraction(self, _extraction_input, **_kwargs):
        self.extraction_calls += 1
        if self.extraction_calls == 1:
            raise ProviderProtocolError("synthetic bounded replay failure")
        return CognitionExtractionOutput()


def test_ingestion_pass2_failure_keeps_transcript_and_continues_without_retry(
    tmp_path: Path,
) -> None:
    root = tmp_path / "blank"
    _blank_package(root)
    provider = _FailureThenSuccessProvider()
    adapter = RelayLMReadOnlyQueryAdapter(
        package_root=root,
        provider=provider,
        mode="two_pass",
        continuity_context=ContinuityContext(max_items=4),
        continuity_lifetime_revisions=4,
    )

    events = adapter.ingest_session_dialogue(
        _dialogue(),
        session_id="persona-0-session-0",
        session_index=0,
    )

    assert provider.conversation_calls == 0
    assert provider.extraction_calls == 2
    assert tuple(CognitivePackageDirectory(root).iter_events()) == events
    assert CognitivePackageDirectory(root).load_state().states == ()
    assert not (root / "memory" / "MEMORY.md").exists()

    evidence = adapter.dialogue_ingestion_evidence
    assert [item["pass2_status"] for item in evidence] == ["failed", "committed"]
    assert evidence[0]["pass2_failure_reason"] == "pass2_failed"
    assert evidence[0]["failure_diagnostics"] == [
        {
            "turn_index": 1,
            "phase": "pass2",
            "exception_type": "ProviderProtocolError",
            "exception_message": "synthetic bounded replay failure",
        }
    ]
    assert evidence[1]["failure_diagnostics"] == []
