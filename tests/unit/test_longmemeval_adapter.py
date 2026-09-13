from __future__ import annotations

from copy import deepcopy

import pytest

from tools.longmemeval_adapter import (
    LongMemEvalAdapterError,
    normalize_longmemeval_knowledge_update,
    prepare_longmemeval_knowledge_update,
)


def _case() -> dict[str, object]:
    return {
        "question_id": "knowledge-update-1",
        "question_type": "knowledge-update",
        "question": "Where does the user work now?",
        "answer": "At the new company.",
        "question_date": "2023/04/03 (Mon) 12:00",
        "haystack_session_ids": ["old-fact", "new-fact"],
        "haystack_dates": [
            "2023/04/01 (Sat) 10:00",
            "2023/04/02 (Sun) 10:00",
        ],
        "haystack_sessions": [
            [
                {
                    "role": "user",
                    "content": "I work at the old company.",
                    "has_answer": True,
                },
                {
                    "role": "assistant",
                    "content": "Got it.",
                },
            ],
            [
                {
                    "role": "user",
                    "content": "I moved to the new company.",
                    "has_answer": True,
                },
                {
                    "role": "assistant",
                    "content": "Thanks for the update.",
                },
            ],
        ],
        "answer_session_ids": ["old-fact", "new-fact"],
    }


class _RecordingAdapter:
    def __init__(self) -> None:
        self.sessions: list[dict[str, object]] = []
        self.snapshot = object()

    def ingest_session_dialogue(
        self,
        dialogue: object,
        *,
        session_id: str,
        session_index: int,
    ) -> None:
        self.sessions.append(
            {
                "dialogue": dialogue,
                "session_id": session_id,
                "session_index": session_index,
            }
        )

    def freeze(self) -> object:
        return self.snapshot


def test_normalizer_preserves_timestamped_sessions_without_answer_label_leak() -> None:
    normalized = normalize_longmemeval_knowledge_update(_case())
    assert normalized.question_id == "knowledge-update-1"
    assert normalized.question == "Where does the user work now?"
    assert [session.session_id for session in normalized.sessions] == [
        "old-fact",
        "new-fact",
    ]
    assert [session.timestamp for session in normalized.sessions] == [
        "2023/04/01 (Sat) 10:00",
        "2023/04/02 (Sun) 10:00",
    ]

    first_message = normalized.sessions[0].dialogue[0]
    assert first_message["timestamp"] == "2023/04/01 (Sat) 10:00"
    assert first_message["provenance"]["benchmark"] == "longmemeval"
    assert "has_answer" not in first_message
    assert "answer" not in first_message
    assert "answer_session_ids" not in first_message["provenance"]

    reference = normalized.evaluation_reference()
    assert reference["answer"] == "At the new company."
    assert reference["answer_session_ids"] == ["old-fact", "new-fact"]


def test_prepare_ingests_each_session_once_then_freezes() -> None:
    adapter = _RecordingAdapter()
    prepared = prepare_longmemeval_knowledge_update(
        query_adapter=adapter,
        raw=_case(),
    )
    assert prepared.snapshot is adapter.snapshot
    assert [item["session_id"] for item in adapter.sessions] == [
        "old-fact",
        "new-fact",
    ]
    assert [item["session_index"] for item in adapter.sessions] == [0, 1]
    assert prepared.case.question == "Where does the user work now?"


def test_adapter_is_bounded_to_knowledge_update_for_core_1_0() -> None:
    raw = _case()
    raw["question_type"] = "temporal-reasoning"
    with pytest.raises(LongMemEvalAdapterError, match="bounded to knowledge-update"):
        normalize_longmemeval_knowledge_update(raw)


def test_parallel_session_fields_must_be_aligned() -> None:
    raw = _case()
    raw["haystack_dates"] = raw["haystack_dates"][:1]
    with pytest.raises(LongMemEvalAdapterError, match="must be non-empty and aligned"):
        normalize_longmemeval_knowledge_update(raw)


def test_answer_session_ids_must_reference_supplied_history() -> None:
    raw = _case()
    raw["answer_session_ids"] = ["not-in-haystack"]
    with pytest.raises(LongMemEvalAdapterError, match="must refer to supplied"):
        normalize_longmemeval_knowledge_update(raw)


def test_unknown_source_fields_do_not_enter_model_facing_dialogue() -> None:
    raw = deepcopy(_case())
    raw["haystack_sessions"][0][0]["private_gold_metadata"] = {
        "answer": "do not leak",
    }
    normalized = normalize_longmemeval_knowledge_update(raw)
    message = normalized.sessions[0].dialogue[0]
    assert set(message) == {"role", "content", "timestamp", "provenance"}
    assert "private_gold_metadata" not in str(message)


def test_prepare_rejects_non_adapter_objects_before_ingestion() -> None:
    with pytest.raises(LongMemEvalAdapterError, match="must expose"):
        prepare_longmemeval_knowledge_update(query_adapter=object(), raw=_case())
