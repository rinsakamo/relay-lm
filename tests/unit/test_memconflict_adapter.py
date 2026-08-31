from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
)
from relaylm.continuity import ContinuityCandidate, ContinuityContext
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.state import CanonicalState, StateCandidate, StateRecord
from relaylm.storage.cognitive_package import CognitivePackageDirectory
from relaylm.turn import EventRetrievalBudget, MemoryRetrievalBudget
from tools.memconflict_adapter import (
    RelayLMReadOnlyQueryAdapter,
    RelayLMReadOnlyQueryExecutionError,
)


Q1 = "What should be remembered about this question?"
Q1_ANSWER = "Q1_ANSWER_SENTINEL"
Q2 = "user live Kyoto residence"


def _make_package(root: Path) -> CognitivePackageDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "knowledge").mkdir()
    (root / "SOUL.md").write_text(
        "# Synthetic persona\n\nStay grounded in supplied evidence.\n",
        encoding="utf-8",
    )
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: synthetic\n  name: Synthetic\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    (root / "memory" / "MEMORY.md").write_text(
        "# Residence\n\nThe user lives in Kyoto.\n",
        encoding="utf-8",
    )
    (root / "knowledge" / "reference.md").write_text(
        "KNOWLEDGE_ONLY_SENTINEL\n",
        encoding="utf-8",
    )
    package = CognitivePackageDirectory(root)
    package.save_state(
        CanonicalState(
            states=(
                StateRecord(
                    state_id="dialogue-residence",
                    state_class="user.fact",
                    key="residence",
                    value="Kyoto",
                    sources=("dialogue-source",),
                ),
            )
        )
    )
    return package


class _SyntheticTwoPassProvider:
    def __init__(self) -> None:
        self.inputs = []

    async def generate_conversation(self, cognitive_input, **_kwargs):
        self.inputs.append(cognitive_input)
        if cognitive_input.input.payload["content"] == Q1:
            return CognitionConversationOutput(response=Q1_ANSWER)
        return CognitionConversationOutput(response="Q2_RESPONSE")

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
        **_kwargs,
    ):
        if extraction_input.assistant_response != Q1_ANSWER:
            return CognitionExtractionOutput()
        source = extraction_input.originating_event_id
        return CognitionExtractionOutput(
            state_candidates=(
                StateCandidate.set(
                    state_class="user.fact",
                    key="q1_only",
                    value=Q1_ANSWER,
                    sources=(source,),
                ),
            ),
            continuity_candidates=(
                ContinuityCandidate.set(
                    kind="active_task",
                    key="q1_only",
                    value=Q1_ANSWER,
                    sources=(source,),
                    epistemic_role="assistant_inference",
                ),
            ),
        )


def _adapter(root: Path, provider: object) -> RelayLMReadOnlyQueryAdapter:
    adapter = RelayLMReadOnlyQueryAdapter(
        package_root=root,
        provider=provider,
        mode="two_pass",
        memory_budget=MemoryRetrievalBudget(max_chunks=2, max_chars=1_000),
        event_budget=EventRetrievalBudget(max_events=2, max_chars=1_000),
        continuity_context=ContinuityContext(max_items=4),
        continuity_lifetime_revisions=4,
    )
    adapter.ingest_session_dialogue(
        (
            {
                "role": "user",
                "content": "The user live in Kyoto.",
                "timestamp": "2026-08-01T00:00:00+00:00",
            },
            {
                "role": "assistant",
                "content": "I recorded the Kyoto residence.",
                "timestamp": "2026-08-01T00:01:00+00:00",
            },
            *(
                {
                    "role": "user",
                    "content": f"unrelated dialogue note {index}",
                    "timestamp": f"2026-08-01T00:{index + 2:02d}:00+00:00",
                }
                for index in range(6)
            ),
        ),
        session_id="session-0",
        session_index=0,
    )
    return adapter


def test_questions_are_read_only_and_q2_matches_standalone_frozen_surface(
    tmp_path: Path,
) -> None:
    root = tmp_path / "persona"
    package = _make_package(root)
    provider = _SyntheticTwoPassProvider()
    adapter = _adapter(root, provider)

    with adapter:
        with adapter.freeze() as snapshot:
            q1 = asyncio.run(snapshot.query(Q1, question_index=1))
            q2_after_q1 = asyncio.run(snapshot.query(Q2, question_index=2))
            q2_alone = asyncio.run(snapshot.query(Q2, question_index=2))

            q2_mapping = q2_after_q1.answer_time_evidence.to_mapping()
            assert q2_mapping == q2_alone.answer_time_evidence.to_mapping()
            assert q2_after_q1.cognitive_input.context == q2_alone.cognitive_input.context

            encoded_q2 = json.dumps(q2_mapping, ensure_ascii=False, sort_keys=True)
            assert Q1 not in encoded_q2
            assert Q1_ANSWER not in encoded_q2
            assert "q1_only" not in encoded_q2
            assert "KNOWLEDGE_ONLY_SENTINEL" not in encoded_q2

            projected = q2_after_q1.answer_time_evidence.retrieved_memories_projection()
            assert {item["source_role"] for item in projected} == {
                "memory",
                "event",
                "state",
            }
            assert all(
                item.get("source_role") != "knowledge" for item in projected
            )
            assert q1.to_external_evidence()["failure_diagnostics"] == []

            mechanics = snapshot.mechanics
            assert q1.to_external_evidence()["adapter_mechanics"] == mechanics
            assert mechanics["question_ingest"] == (
                "none into live or frozen package"
            )
            assert mechanics["answer_ingest"] == (
                "none into live or frozen package"
            )
            assert mechanics["question_isolation"] == (
                "fresh package clone per question, discarded after turn"
            )

    persisted = CognitivePackageDirectory(root)
    persisted_events = tuple(persisted.iter_events())
    assert [event.actor for event in persisted_events] == [
        "user",
        "assistant",
        *(["user"] * 6),
    ]
    assert all(
        Q1 not in str(event.payload) and Q1_ANSWER not in str(event.payload)
        for event in persisted_events
    )
    assert persisted.load_state().states == package.load_state().states
    assert persisted.load_memory_markdown() == package.load_memory_markdown()


class _FailingPass2Provider:
    async def generate_conversation(self, _cognitive_input, **_kwargs):
        return CognitionConversationOutput(response="visible")

    async def generate_extraction(self, _extraction_input, **_kwargs):
        raise ProviderProtocolError("provider extraction top-level shape is invalid")


def test_bounded_pass2_failure_identity_is_available_for_external_evidence(
    tmp_path: Path,
) -> None:
    root = tmp_path / "persona"
    _make_package(root)
    adapter = _adapter(root, _FailingPass2Provider())

    with adapter:
        with adapter.freeze() as snapshot:
            result = asyncio.run(snapshot.query(Q2, question_index=7))

    assert result.pass2_status == "failed"
    assert result.pass2_failure_reason == "pass2_failed"
    assert [item.to_mapping() for item in result.failure_diagnostics] == [
        {
            "turn_index": 7,
            "phase": "pass2",
            "exception_type": "ProviderProtocolError",
            "exception_message": "provider extraction top-level shape is invalid",
        }
    ]
    external = result.to_external_evidence()
    assert external["failure_diagnostics"] == [
        {
            "turn_index": 7,
            "phase": "pass2",
            "exception_type": "ProviderProtocolError",
            "exception_message": "provider extraction top-level shape is invalid",
        }
    ]


class _UnsafePass1Provider:
    async def generate_conversation(self, _cognitive_input, **_kwargs):
        raise RuntimeError("raw semantic payload must not be persisted")

    async def generate_extraction(self, _extraction_input, **_kwargs):
        return CognitionExtractionOutput()


def test_untrusted_provider_message_is_not_retained_and_query_clone_is_discarded(
    tmp_path: Path,
) -> None:
    root = tmp_path / "persona"
    _make_package(root)
    adapter = _adapter(root, _UnsafePass1Provider())

    with adapter:
        with adapter.freeze() as snapshot:
            with pytest.raises(RelayLMReadOnlyQueryExecutionError) as caught:
                asyncio.run(snapshot.query(Q2, question_index=3))
            assert [item.to_mapping() for item in caught.value.diagnostics] == [
                {
                    "turn_index": 3,
                    "phase": "pass1",
                    "exception_type": "RuntimeError",
                    "exception_message": None,
                    }
                ]
            assert caught.value.to_external_evidence()["adapter_mechanics"] == snapshot.mechanics

    assert [event.actor for event in CognitivePackageDirectory(root).iter_events()] == [
        "user",
        "assistant",
        *(["user"] * 6),
    ]
