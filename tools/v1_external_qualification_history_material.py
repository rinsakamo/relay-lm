"""Deterministic benchmark-history materialization for #2986 qualification.

The builder consumes only current axis question identities and byte-pinned public
benchmark datasets. It does not accept a historical campaign descriptor as
execution authority and it performs no model/provider/semantic work.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.external_qualification import validate_case
from tools.longmemeval_adapter import normalize_longmemeval_knowledge_update
from tools.v1_external_qualification_llama_cpp_campaign import (
    CampaignCarriageError,
    CampaignQuestion,
    HindsightHistoryPlan,
    _fingerprint,
)

MEMCONFLICT_SOURCE_SHA256 = (
    "8ef9ec8589eccb86f63ab3a819a9180217405351a8d5846866721ea74babe092"
)
MEMCONFLICT_PERSONA_ID = "3c2e5fe5-a0fc-7e3c-b05c-7104ad748705"
MEMCONFLICT_SESSION_COUNT = 53
MEMCONFLICT_SELECTION = (
    ("memconflict:dynamic_conflict:Q_001", "Q_001", 5),
    ("memconflict:static_conflict:Q_001", "Q_001", 16),
    ("memconflict:conditional_conflict:Q_002", "Q_002", 22),
)

LONGMEMEVAL_SOURCE_SHA256 = (
    "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
)
LONGMEMEVAL_QUESTION_ID = "6a1eabeb"
LONGMEMEVAL_SESSION_COUNT = 40

_CONFLICT_AXIS = "conflict_temporal_validity"
_UPDATE_AXIS = "update_belief_revision"


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise CampaignCarriageError(f"cannot hash benchmark source {path}: {exc}") from exc
    return digest.hexdigest()


def _require_source(path: Path, expected_sha256: str, *, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise CampaignCarriageError(f"{label} source is not a file: {resolved}")
    observed = _sha256_file(resolved)
    if observed != expected_sha256:
        raise CampaignCarriageError(
            f"{label} source SHA256 drifted: expected {expected_sha256}, observed {observed}"
        )
    return resolved


def _mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CampaignCarriageError(f"{label} must be an object")
    return value


def _axis_kind(axis: Mapping[str, object]) -> str:
    case = _mapping(axis.get("case"), label="campaign axis case")
    value = case.get("axis")
    if not isinstance(value, str) or not value.strip():
        raise CampaignCarriageError("campaign axis case.axis must be non-empty")
    return value


def _axis_questions(axis: Mapping[str, object]) -> tuple[CampaignQuestion, ...]:
    raw = axis.get("questions")
    if not isinstance(raw, list) or not raw:
        raise CampaignCarriageError("campaign axis questions must be non-empty")
    return tuple(
        CampaignQuestion.from_mapping(
            _mapping(item, label="campaign axis question")
        )
        for item in raw
    )


def _parse_memconflict_timestamp(raw: object) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return (
                datetime.strptime(text, fmt)
                .replace(tzinfo=timezone.utc)
                .isoformat()
            )
        except ValueError:
            continue
    return None


def _memconflict_turn_order(key: object) -> int:
    try:
        return int(str(key).split("_")[-1])
    except (TypeError, ValueError):
        return 10**9


def _memconflict_dialogue(session: Mapping[str, object]) -> list[dict[str, object]]:
    raw = session.get("Session_Dialogue")
    if not isinstance(raw, Mapping):
        return []
    timestamp = _parse_memconflict_timestamp(session.get("Date"))
    items: list[dict[str, object]] = []
    for turn_key in sorted(raw.keys(), key=_memconflict_turn_order):
        turn_value = raw.get(turn_key)
        if not isinstance(turn_value, list):
            continue
        for message in turn_value:
            if not isinstance(message, Mapping):
                continue
            role = message.get("role")
            content = message.get("content")
            if role not in {"user", "assistant"} or content is None or content == "":
                continue
            items.append(
                {
                    "role": str(role),
                    "content": str(content),
                    "timestamp": timestamp,
                }
            )
    return items


def _load_memconflict_persona(path: Path) -> Mapping[str, object]:
    found: list[Mapping[str, object]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    raw = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise CampaignCarriageError(
                        f"MemConflict JSONL line {line_number} is invalid"
                    ) from exc
                if not isinstance(raw, Mapping):
                    raise CampaignCarriageError(
                        f"MemConflict JSONL line {line_number} is not an object"
                    )
                if raw.get("ID") == MEMCONFLICT_PERSONA_ID:
                    found.append(raw)
    except OSError as exc:
        raise CampaignCarriageError(f"cannot read MemConflict source: {exc}") from exc
    if len(found) != 1:
        raise CampaignCarriageError(
            "pinned MemConflict persona must occur exactly once"
        )
    return found[0]


def _find_memconflict_question(
    session: Mapping[str, object],
    *,
    raw_question_id: str,
    expected_prompt: str,
) -> None:
    questions = session.get("Session_Questions")
    if not isinstance(questions, list):
        raise CampaignCarriageError(
            "selected MemConflict session has no Session_Questions list"
        )
    matches = []
    for value in questions:
        if not isinstance(value, Mapping):
            continue
        if str(value.get("question_id", "")).strip() != raw_question_id:
            continue
        prompt = str(value.get("question", "")).strip()
        if prompt == expected_prompt:
            matches.append(value)
    if len(matches) != 1:
        raise CampaignCarriageError(
            f"MemConflict source question {raw_question_id!r} does not uniquely "
            "match the frozen campaign prompt"
        )


def build_memconflict_history_material(
    *,
    source_path: Path,
    questions: Sequence[CampaignQuestion],
) -> dict[str, object]:
    source = _require_source(
        source_path,
        MEMCONFLICT_SOURCE_SHA256,
        label="MemConflict",
    )
    by_id = {question.question_id: question for question in questions}
    expected_ids = {item[0] for item in MEMCONFLICT_SELECTION}
    if set(by_id) != expected_ids:
        raise CampaignCarriageError(
            "MemConflict campaign questions differ from the frozen three-question ring"
        )

    persona = _load_memconflict_persona(source)
    sessions_raw = persona.get("Full_Session_Chain")
    if not isinstance(sessions_raw, list) or len(sessions_raw) != MEMCONFLICT_SESSION_COUNT:
        raise CampaignCarriageError(
            f"pinned MemConflict persona must contain {MEMCONFLICT_SESSION_COUNT} sessions"
        )

    sessions: list[dict[str, object]] = []
    session_ids: list[str] = []
    for order, raw_session in enumerate(sessions_raw):
        session = _mapping(
            raw_session,
            label=f"MemConflict session {order}",
        )
        session_id = str(session.get("Session_ID", "")).strip()
        if not session_id:
            raise CampaignCarriageError(
                f"MemConflict session {order} has no Session_ID"
            )
        if session_id in session_ids:
            raise CampaignCarriageError(
                f"MemConflict session id is duplicated: {session_id!r}"
            )
        items = _memconflict_dialogue(session)
        if not items:
            raise CampaignCarriageError(
                f"MemConflict session {session_id!r} has no model-facing dialogue"
            )
        session_ids.append(session_id)
        sessions.append(
            {
                "session_id": session_id,
                "order": order,
                "items": items,
            }
        )

    question_history: dict[str, list[str]] = {}
    for campaign_id, raw_question_id, session_order in MEMCONFLICT_SELECTION:
        question = by_id[campaign_id]
        selected_session = _mapping(
            sessions_raw[session_order],
            label=f"MemConflict selected session {session_order}",
        )
        _find_memconflict_question(
            selected_session,
            raw_question_id=raw_question_id,
            expected_prompt=question.prompt,
        )
        question_history[campaign_id] = session_ids[: session_order + 1]

    return {
        "format_version": 1,
        "sessions": sessions,
        "question_history": question_history,
    }


def _load_longmemeval_case(path: Path) -> Mapping[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CampaignCarriageError(f"cannot read LongMemEval source: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CampaignCarriageError("LongMemEval source is not valid JSON") from exc

    if isinstance(raw, Mapping):
        candidates = raw.get("data")
        if not isinstance(candidates, list):
            candidates = [raw]
    elif isinstance(raw, list):
        candidates = raw
    else:
        raise CampaignCarriageError("LongMemEval source must be an object or list")

    matches = [
        item
        for item in candidates
        if isinstance(item, Mapping)
        and str(item.get("question_id", "")).strip() == LONGMEMEVAL_QUESTION_ID
    ]
    if len(matches) != 1:
        raise CampaignCarriageError(
            "pinned LongMemEval question must occur exactly once"
        )
    return matches[0]


def build_longmemeval_history_material(
    *,
    source_path: Path,
    questions: Sequence[CampaignQuestion],
) -> dict[str, object]:
    source = _require_source(
        source_path,
        LONGMEMEVAL_SOURCE_SHA256,
        label="LongMemEval",
    )
    if len(questions) != 1:
        raise CampaignCarriageError(
            "LongMemEval bounded qualification axis must contain one question"
        )
    campaign_question = questions[0]
    raw = _load_longmemeval_case(source)
    normalized = normalize_longmemeval_knowledge_update(raw)
    if normalized.question_id != LONGMEMEVAL_QUESTION_ID:
        raise CampaignCarriageError("LongMemEval selected question id drifted")
    if normalized.question != campaign_question.prompt:
        raise CampaignCarriageError(
            "LongMemEval source question does not match the frozen campaign prompt"
        )
    if len(normalized.sessions) != LONGMEMEVAL_SESSION_COUNT:
        raise CampaignCarriageError(
            f"pinned LongMemEval case must contain {LONGMEMEVAL_SESSION_COUNT} sessions"
        )

    sessions = [
        {
            "session_id": session.session_id,
            "order": session.session_index,
            "items": [
                {
                    "role": str(message["role"]),
                    "content": str(message["content"]),
                    "timestamp": session.timestamp,
                }
                for message in session.dialogue
            ],
        }
        for session in normalized.sessions
    ]
    session_ids = [str(item["session_id"]) for item in sessions]
    return {
        "format_version": 1,
        "sessions": sessions,
        "question_history": {
            campaign_question.question_id: session_ids,
        },
    }


def _write_canonical_json(path: Path, value: object) -> str:
    encoded = (_canonical_json(value) + "\n").encode("utf-8")
    if path.exists():
        try:
            current = path.read_bytes()
        except OSError as exc:
            raise CampaignCarriageError(
                f"cannot read existing history material {path}: {exc}"
            ) from exc
        if current != encoded:
            raise CampaignCarriageError(
                f"existing history material differs from deterministic output: {path}"
            )
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_bytes(encoded)
        except OSError as exc:
            raise CampaignCarriageError(
                f"cannot write history material {path}: {exc}"
            ) from exc
    return _sha256_bytes(encoded)


def materialize_bounded_history_axes(
    *,
    axes: Sequence[Mapping[str, object]],
    memconflict_source: Path,
    longmemeval_source: Path,
    output_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, object]]:
    """Attach deterministic current history_material refs to the two frozen axes."""

    root = output_root.resolve()
    if not root.is_absolute():
        raise CampaignCarriageError("history output root must be absolute")
    if len(axes) != 2:
        raise CampaignCarriageError(
            "bounded Core 1.0 history builder requires exactly two axes"
        )

    prepared = [
        copy.deepcopy(dict(axis))
        for axis in axes
    ]
    by_kind: dict[str, dict[str, Any]] = {}
    for axis in prepared:
        kind = _axis_kind(axis)
        if kind in by_kind:
            raise CampaignCarriageError(f"duplicate campaign axis kind: {kind}")
        by_kind[kind] = axis
    if set(by_kind) != {_CONFLICT_AXIS, _UPDATE_AXIS}:
        raise CampaignCarriageError(
            "history builder requires conflict_temporal_validity and "
            "update_belief_revision axes"
        )

    generated: list[tuple[dict[str, Any], dict[str, object], str]] = []
    conflict = by_kind[_CONFLICT_AXIS]
    generated.append(
        (
            conflict,
            build_memconflict_history_material(
                source_path=memconflict_source,
                questions=_axis_questions(conflict),
            ),
            "memconflict",
        )
    )
    update = by_kind[_UPDATE_AXIS]
    generated.append(
        (
            update,
            build_longmemeval_history_material(
                source_path=longmemeval_source,
                questions=_axis_questions(update),
            ),
            "longmemeval",
        )
    )

    receipt_axes: list[dict[str, object]] = []
    for axis, history, source_name in generated:
        axis_id = axis.get("axis_id")
        if not isinstance(axis_id, str) or not axis_id:
            raise CampaignCarriageError("campaign axis_id must be non-empty")
        token = hashlib.sha256(axis_id.encode("utf-8")).hexdigest()[:24]
        questions = _axis_questions(axis)

        history_path = root / f"history-{token}.json"
        history_sha256 = _write_canonical_json(history_path, history)
        HindsightHistoryPlan.from_path(history_path).validate_questions(
            [question.question_id for question in questions]
        )
        axis["history_material"] = {
            "path": str(history_path),
            "sha256": history_sha256,
        }

        case = validate_case(
            _mapping(axis.get("case"), label="campaign axis case")
        )
        if source_name == "memconflict":
            selection: dict[str, object] = {
                "persona_id": MEMCONFLICT_PERSONA_ID,
                "session_count": MEMCONFLICT_SESSION_COUNT,
                "questions": [
                    {
                        "campaign_question_id": campaign_question_id,
                        "source_question_id": source_question_id,
                        "session_order": session_order,
                    }
                    for (
                        campaign_question_id,
                        source_question_id,
                        session_order,
                    ) in MEMCONFLICT_SELECTION
                ],
            }
            source_receipt = {
                "path": str(memconflict_source.resolve()),
                "sha256": MEMCONFLICT_SOURCE_SHA256,
            }
        else:
            selection = {
                "question_id": LONGMEMEVAL_QUESTION_ID,
                "session_count": LONGMEMEVAL_SESSION_COUNT,
            }
            source_receipt = {
                "path": str(longmemeval_source.resolve()),
                "sha256": LONGMEMEVAL_SOURCE_SHA256,
            }

        benchmark_evidence = {
            "format_version": 1,
            "axis_id": axis_id,
            "source": source_receipt,
            "selection": selection,
            "questions": [
                {
                    "question_id": question.question_id,
                    "prompt": question.prompt,
                    "content_fingerprint": question.content_fingerprint,
                    "session_id": question.session_id,
                }
                for question in questions
            ],
        }
        benchmark_path = root / f"benchmark-{token}.json"
        benchmark_sha256 = _write_canonical_json(
            benchmark_path,
            benchmark_evidence,
        )
        axis["benchmark_material"] = {
            "path": str(benchmark_path),
            "sha256": benchmark_sha256,
            "case_fingerprint": _fingerprint(case),
            "question_fingerprints": [
                question.content_fingerprint for question in questions
            ],
        }

        receipt_axes.append(
            {
                "axis_id": axis_id,
                "source": source_name,
                "benchmark_path": str(benchmark_path),
                "benchmark_sha256": benchmark_sha256,
                "history_path": str(history_path),
                "history_sha256": history_sha256,
                "session_count": len(history["sessions"]),
                "question_count": len(history["question_history"]),
            }
        )

    return prepared, {
        "status": "HISTORY_MATERIAL_PREPARED",
        "semantic_generation_count": 0,
        "benchmark_question_execution_count": 0,
        "axes": sorted(receipt_axes, key=lambda item: str(item["axis_id"])),
        "sources": {
            "memconflict": {
                "path": str(memconflict_source.resolve()),
                "sha256": MEMCONFLICT_SOURCE_SHA256,
                "persona_id": MEMCONFLICT_PERSONA_ID,
            },
            "longmemeval": {
                "path": str(longmemeval_source.resolve()),
                "sha256": LONGMEMEVAL_SOURCE_SHA256,
                "question_id": LONGMEMEVAL_QUESTION_ID,
            },
        },
    }


def _load_axes(path: Path) -> list[Mapping[str, object]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CampaignCarriageError(f"cannot read axis template: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CampaignCarriageError("axis template is not valid JSON") from exc
    if isinstance(raw, Mapping):
        raw = raw.get("axes")
    if not isinstance(raw, list) or not all(isinstance(item, Mapping) for item in raw):
        raise CampaignCarriageError(
            "axis template must be a list or an object containing an axes list"
        )
    return list(raw)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Materialize pinned benchmark history for #2986."
    )
    parser.add_argument("--axes-template", type=Path, required=True)
    parser.add_argument("--memconflict-source", type=Path, required=True)
    parser.add_argument("--longmemeval-source", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output-axes", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    axes, receipt = materialize_bounded_history_axes(
        axes=_load_axes(args.axes_template.resolve()),
        memconflict_source=args.memconflict_source.resolve(),
        longmemeval_source=args.longmemeval_source.resolve(),
        output_root=args.output_root.resolve(),
    )
    axes_sha = _write_canonical_json(args.output_axes.resolve(), {"axes": axes})
    result = {
        **receipt,
        "prepared_axes_path": str(args.output_axes.resolve()),
        "prepared_axes_sha256": axes_sha,
    }
    print(_canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
