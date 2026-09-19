from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.external_qualification import DurableQuestion
from tools import v1_external_qualification_history_material as history
from tools.v1_external_qualification_llama_cpp_campaign import (
    CampaignCarriageError,
    HindsightHistoryPlan,
)


def _question(question_id: str, prompt: str, session_id: str) -> dict[str, object]:
    durable = DurableQuestion.from_content(
        question_id,
        prompt,
        session_id=session_id,
    )
    return {
        "question_id": question_id,
        "prompt": prompt,
        "content_fingerprint": durable.content_fingerprint,
        "session_id": session_id,
    }


def _axes() -> list[dict[str, object]]:
    return [
        {
            "axis_id": "memconflict-axis",
            "case": {
                "case_id": "memconflict-case",
                "axis": "conflict_temporal_validity",
                "benchmark": {
                    "id": "memconflict",
                    "repository": "https://example.invalid/memconflict",
                    "revision": "a" * 40,
                    "license": "MIT",
                },
                "dataset": {
                    "revision": "b" * 40,
                    "license": "MIT",
                },
                "adapter_case_ref": "memconflict-case-ref",
            },
            "questions": [
                _question(
                    "memconflict:dynamic_conflict:Q_001",
                    "dynamic prompt",
                    "dynamic-session",
                ),
                _question(
                    "memconflict:static_conflict:Q_001",
                    "static prompt",
                    "static-session",
                ),
                _question(
                    "memconflict:conditional_conflict:Q_002",
                    "conditional prompt",
                    "conditional-session",
                ),
            ],
        },
        {
            "axis_id": "longmemeval-axis",
            "case": {
                "case_id": "longmemeval-case",
                "axis": "update_belief_revision",
                "benchmark": {
                    "id": "longmemeval",
                    "repository": "https://example.invalid/longmemeval",
                    "revision": "c" * 40,
                    "license": "MIT",
                },
                "dataset": {
                    "revision": "d" * 40,
                    "license": "MIT",
                },
                "adapter_case_ref": "longmemeval-case-ref",
            },
            "questions": [
                _question(
                    "longmemeval:knowledge-update:6a1eabeb",
                    "Where is the new office?",
                    "longmemeval-session",
                ),
            ],
        },
    ]


def _memconflict_source(path: Path) -> None:
    sessions: list[dict[str, object]] = []
    selected = {
        5: ("Q_001", "dynamic prompt"),
        16: ("Q_001", "static prompt"),
        22: ("Q_002", "conditional prompt"),
    }
    for index in range(53):
        questions: list[dict[str, object]] = []
        if index in selected:
            question_id, prompt = selected[index]
            questions.append(
                {
                    "question_id": question_id,
                    "question": prompt,
                    "answer": f"reference-only-{index}",
                }
            )
        dialogue: dict[str, object] = {
            "dialogue_turn_1": [
                {"role": "user", "content": f"user-{index}"},
                {"role": "assistant", "content": f"assistant-{index}"},
            ]
        }
        if index == 0:
            dialogue["dialogue_turn_2"] = [
                {"role": "system", "content": "must-not-appear"},
                {"role": "user", "content": ""},
                {"role": "assistant", "content": "kept-assistant"},
            ]
            dialogue["dialogue_turn_3"] = {
                "role": "user",
                "content": "non-list-turn-must-not-appear",
            }
        sessions.append(
            {
                "Session_ID": f"mc-session-{index:02d}",
                "Date": f"2026/01/{(index % 28) + 1:02d}",
                "Session_Dialogue": dialogue,
                "Session_Questions": questions,
                "reference_only": f"secret-{index}",
            }
        )
    payload = {
        "ID": history.MEMCONFLICT_PERSONA_ID,
        "Full_Session_Chain": sessions,
        "answer": "global-reference-only",
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _longmemeval_source(path: Path) -> None:
    session_ids = [f"lm-session-{index:02d}" for index in range(40)]
    dates = [f"2026-02-{(index % 28) + 1:02d}" for index in range(40)]
    sessions = [
        [
            {"role": "user", "content": f"long-user-{index}"},
            {"role": "assistant", "content": f"long-assistant-{index}"},
        ]
        for index in range(40)
    ]
    payload = [
        {
            "question_id": history.LONGMEMEVAL_QUESTION_ID,
            "question_type": "knowledge-update",
            "question": "Where is the new office?",
            "answer": "REFERENCE-ANSWER-MUST-NOT-LEAK",
            "question_date": "2026-03-01",
            "haystack_session_ids": session_ids,
            "haystack_dates": dates,
            "haystack_sessions": sessions,
            "answer_session_ids": [session_ids[-1]],
            "has_answer": True,
        }
    ]
    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def _pin_synthetic_sources(
    monkeypatch: pytest.MonkeyPatch,
    memconflict: Path,
    longmemeval: Path,
) -> None:
    monkeypatch.setattr(
        history,
        "MEMCONFLICT_SOURCE_SHA256",
        hashlib.sha256(memconflict.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(
        history,
        "LONGMEMEVAL_SOURCE_SHA256",
        hashlib.sha256(longmemeval.read_bytes()).hexdigest(),
    )


def test_memconflict_builder_reconstructs_ordered_question_prefixes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "Step4_4.jsonl"
    _memconflict_source(source)
    long_source = tmp_path / "long.json"
    _longmemeval_source(long_source)
    _pin_synthetic_sources(monkeypatch, source, long_source)

    questions = [
        history.CampaignQuestion.from_mapping(item)
        for item in _axes()[0]["questions"]
    ]
    material = history.build_memconflict_history_material(
        source_path=source,
        questions=questions,
    )

    assert len(material["sessions"]) == 53
    qh = material["question_history"]
    assert len(qh["memconflict:dynamic_conflict:Q_001"]) == 6
    assert len(qh["memconflict:static_conflict:Q_001"]) == 17
    assert len(qh["memconflict:conditional_conflict:Q_002"]) == 23
    first_items = material["sessions"][0]["items"]
    assert [item["content"] for item in first_items] == [
        "user-0",
        "assistant-0",
        "kept-assistant",
    ]
    assert all(item["role"] in {"user", "assistant"} for item in first_items)
    assert first_items[0]["timestamp"] == "2026-01-01T00:00:00+00:00"
    encoded = json.dumps(material, ensure_ascii=False)
    assert "reference-only" not in encoded
    assert "must-not-appear" not in encoded


def test_longmemeval_builder_excludes_reference_only_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mem_source = tmp_path / "Step4_4.jsonl"
    _memconflict_source(mem_source)
    source = tmp_path / "long.json"
    _longmemeval_source(source)
    _pin_synthetic_sources(monkeypatch, mem_source, source)

    question = history.CampaignQuestion.from_mapping(_axes()[1]["questions"][0])
    material = history.build_longmemeval_history_material(
        source_path=source,
        questions=[question],
    )

    assert len(material["sessions"]) == 40
    assert material["question_history"][question.question_id] == [
        f"lm-session-{index:02d}" for index in range(40)
    ]
    assert material["sessions"][0]["items"] == [
        {
            "role": "user",
            "content": "long-user-0",
            "timestamp": "2026-02-01",
        },
        {
            "role": "assistant",
            "content": "long-assistant-0",
            "timestamp": "2026-02-01",
        },
    ]
    encoded = json.dumps(material, ensure_ascii=False)
    assert "REFERENCE-ANSWER-MUST-NOT-LEAK" not in encoded
    assert "answer_session_ids" not in encoded
    assert "has_answer" not in encoded


def test_materialize_axes_is_deterministic_and_validated_by_campaign_parser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mem_source = tmp_path / "Step4_4.jsonl"
    long_source = tmp_path / "long.json"
    _memconflict_source(mem_source)
    _longmemeval_source(long_source)
    _pin_synthetic_sources(monkeypatch, mem_source, long_source)
    output_root = (tmp_path / "history").resolve()

    first, first_receipt = history.materialize_bounded_history_axes(
        axes=_axes(),
        memconflict_source=mem_source,
        longmemeval_source=long_source,
        output_root=output_root,
    )
    second, second_receipt = history.materialize_bounded_history_axes(
        axes=_axes(),
        memconflict_source=mem_source,
        longmemeval_source=long_source,
        output_root=output_root,
    )

    assert first == second
    assert first_receipt == second_receipt
    assert first_receipt["semantic_generation_count"] == 0
    assert first_receipt["benchmark_question_execution_count"] == 0
    for axis in first:
        history_material = axis["history_material"]
        history_path = Path(history_material["path"])
        assert (
            hashlib.sha256(history_path.read_bytes()).hexdigest()
            == history_material["sha256"]
        )
        plan = HindsightHistoryPlan.from_path(history_path)
        plan.validate_questions(
            [item["question_id"] for item in axis["questions"]]
        )

        benchmark_material = axis["benchmark_material"]
        benchmark_path = Path(benchmark_material["path"])
        assert (
            hashlib.sha256(benchmark_path.read_bytes()).hexdigest()
            == benchmark_material["sha256"]
        )
        benchmark_evidence = json.loads(
            benchmark_path.read_text(encoding="utf-8")
        )
        assert benchmark_evidence["axis_id"] == axis["axis_id"]
        assert "answer" not in json.dumps(
            benchmark_evidence,
            ensure_ascii=False,
        )
        assert benchmark_material["question_fingerprints"] == [
            item["content_fingerprint"] for item in axis["questions"]
        ]

    receipt_axes = first_receipt["axes"]
    assert all("benchmark_path" in item for item in receipt_axes)
    assert all("benchmark_sha256" in item for item in receipt_axes)


def test_builder_rejects_source_hash_drift_before_selection(
    tmp_path: Path,
) -> None:
    source = tmp_path / "Step4_4.jsonl"
    _memconflict_source(source)
    questions = [
        history.CampaignQuestion.from_mapping(item)
        for item in _axes()[0]["questions"]
    ]
    with pytest.raises(CampaignCarriageError, match="source SHA256 drifted"):
        history.build_memconflict_history_material(
            source_path=source,
            questions=questions,
        )


def test_builder_rejects_frozen_prompt_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mem_source = tmp_path / "Step4_4.jsonl"
    long_source = tmp_path / "long.json"
    _memconflict_source(mem_source)
    _longmemeval_source(long_source)
    _pin_synthetic_sources(monkeypatch, mem_source, long_source)
    axes = _axes()
    axes[0]["questions"][0] = _question(
        "memconflict:dynamic_conflict:Q_001",
        "changed prompt",
        "dynamic-session",
    )
    questions = [
        history.CampaignQuestion.from_mapping(item)
        for item in axes[0]["questions"]
    ]

    with pytest.raises(CampaignCarriageError, match="does not uniquely match"):
        history.build_memconflict_history_material(
            source_path=mem_source,
            questions=questions,
        )


def test_longmemeval_builder_rejects_wrong_question_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mem_source = tmp_path / "Step4_4.jsonl"
    source = tmp_path / "long.json"
    _memconflict_source(mem_source)
    _longmemeval_source(source)
    _pin_synthetic_sources(monkeypatch, mem_source, source)
    question = history.CampaignQuestion.from_mapping(
        _question(
            "longmemeval:knowledge-update:6a1eabeb",
            "changed LongMemEval prompt",
            "longmemeval-session",
        )
    )

    with pytest.raises(CampaignCarriageError, match="does not match"):
        history.build_longmemeval_history_material(
            source_path=source,
            questions=[question],
        )
