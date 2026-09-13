from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


class LongMemEvalAdapterError(ValueError):
    """A LongMemEval knowledge-update case cannot be mapped safely."""


@dataclass(frozen=True, slots=True)
class LongMemEvalSession:
    session_id: str
    session_index: int
    timestamp: str
    dialogue: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class LongMemEvalKnowledgeUpdateCase:
    question_id: str
    question: str
    question_date: str
    reference_answer: str
    answer_session_ids: tuple[str, ...]
    sessions: tuple[LongMemEvalSession, ...]

    def evaluation_reference(self) -> dict[str, object]:
        return {
            "question_id": self.question_id,
            "question_type": "knowledge-update",
            "answer": self.reference_answer,
            "answer_session_ids": list(self.answer_session_ids),
            "question_date": self.question_date,
        }


@dataclass(frozen=True, slots=True)
class PreparedLongMemEvalCase:
    case: LongMemEvalKnowledgeUpdateCase
    snapshot: object


def normalize_longmemeval_knowledge_update(
    raw: Mapping[str, object],
) -> LongMemEvalKnowledgeUpdateCase:
    """Map the released LongMemEval knowledge-update shape without answer leakage."""

    required = {
        "question_id",
        "question_type",
        "question",
        "answer",
        "question_date",
        "haystack_session_ids",
        "haystack_dates",
        "haystack_sessions",
        "answer_session_ids",
    }
    missing = sorted(required - set(raw))
    if missing:
        raise LongMemEvalAdapterError(
            f"LongMemEval case is missing required fields: {missing}"
        )
    question_id = _text(raw["question_id"], "question_id")
    question_type = _text(raw["question_type"], "question_type")
    if question_type != "knowledge-update":
        raise LongMemEvalAdapterError(
            "Core 1.0 pre-release LongMemEval adapter is bounded to knowledge-update"
        )
    question = _text(raw["question"], "question")
    answer = _text(raw["answer"], "answer")
    question_date = _text(raw["question_date"], "question_date")

    session_ids = _text_list(raw["haystack_session_ids"], "haystack_session_ids")
    dates = _text_list(raw["haystack_dates"], "haystack_dates")
    sessions_raw = raw["haystack_sessions"]
    if not isinstance(sessions_raw, list):
        raise LongMemEvalAdapterError("haystack_sessions must be a list")
    if not session_ids or len(session_ids) != len(dates) or len(dates) != len(sessions_raw):
        raise LongMemEvalAdapterError(
            "LongMemEval session IDs, dates, and sessions must be non-empty and aligned"
        )
    if len(set(session_ids)) != len(session_ids):
        raise LongMemEvalAdapterError("LongMemEval haystack session IDs must be unique")

    normalized_sessions: list[LongMemEvalSession] = []
    for session_index, (session_id, timestamp, dialogue_raw) in enumerate(
        zip(session_ids, dates, sessions_raw, strict=True)
    ):
        if not isinstance(dialogue_raw, list) or not dialogue_raw:
            raise LongMemEvalAdapterError(
                f"LongMemEval session {session_id} dialogue must be a non-empty list"
            )
        dialogue: list[dict[str, object]] = []
        for message_index, message_raw in enumerate(dialogue_raw):
            if not isinstance(message_raw, Mapping):
                raise LongMemEvalAdapterError(
                    f"LongMemEval session {session_id} message must be an object"
                )
            role = message_raw.get("role")
            if role not in {"user", "assistant"}:
                raise LongMemEvalAdapterError(
                    f"LongMemEval session {session_id} role must be user or assistant"
                )
            content = _text(
                message_raw.get("content"),
                f"LongMemEval session {session_id} message content",
            )
            dialogue.append(
                {
                    "role": role,
                    "content": content,
                    "timestamp": timestamp,
                    "provenance": {
                        "benchmark": "longmemeval",
                        "question_id": question_id,
                        "question_type": "knowledge-update",
                        "session_id": session_id,
                        "session_index": session_index,
                        "message_index": message_index,
                    },
                }
            )
        normalized_sessions.append(
            LongMemEvalSession(
                session_id=session_id,
                session_index=session_index,
                timestamp=timestamp,
                dialogue=tuple(dialogue),
            )
        )

    answer_session_ids = tuple(
        _text_list(raw["answer_session_ids"], "answer_session_ids")
    )
    unknown_answer_sessions = sorted(set(answer_session_ids) - set(session_ids))
    if unknown_answer_sessions:
        raise LongMemEvalAdapterError(
            "answer_session_ids must refer to supplied haystack sessions"
        )

    return LongMemEvalKnowledgeUpdateCase(
        question_id=question_id,
        question=question,
        question_date=question_date,
        reference_answer=answer,
        answer_session_ids=answer_session_ids,
        sessions=tuple(normalized_sessions),
    )


def prepare_longmemeval_knowledge_update(
    *,
    query_adapter: object,
    raw: Mapping[str, object],
) -> PreparedLongMemEvalCase:
    """Ingest the released timestamped sessions, then freeze before the question."""

    case = normalize_longmemeval_knowledge_update(raw)
    ingest = getattr(query_adapter, "ingest_session_dialogue", None)
    freeze = getattr(query_adapter, "freeze", None)
    if not callable(ingest) or not callable(freeze):
        raise LongMemEvalAdapterError(
            "query_adapter must expose ingest_session_dialogue() and freeze()"
        )
    for session in case.sessions:
        ingest(
            session.dialogue,
            session_id=session.session_id,
            session_index=session.session_index,
        )
    return PreparedLongMemEvalCase(case=case, snapshot=freeze())


def _text(raw: object, label: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise LongMemEvalAdapterError(f"{label} must be a non-empty string")
    return raw.strip()


def _text_list(raw: object, label: str) -> list[str]:
    if not isinstance(raw, list):
        raise LongMemEvalAdapterError(f"{label} must be a list")
    return [_text(item, f"{label} item") for item in raw]
