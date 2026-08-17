from __future__ import annotations

from relaylm.event_retrieval import (
    EventDiscoveryIndex,
    select_event_evidence,
    select_event_evidence_with_diagnostics,
)
from relaylm.events import Event
from relaylm.memory_retrieval import (
    select_memory_chunks,
    select_memory_chunks_with_diagnostics,
)


def _event(event_id: str, content: str) -> Event:
    return Event(
        id=event_id,
        type="message",
        actor="user",
        timestamp="2026-08-17T00:00:00+00:00",
        payload={"content": content},
    )


def test_memory_retrieval_matches_bounded_cjk_phrasing_difference() -> None:
    memory = """# Memory

## 飲み物

最近はコーヒーが好きです。

## 旅行

先週は福岡へ行きました。
"""

    plain = select_memory_chunks(
        memory_markdown=memory,
        query="コーヒーが好き",
        max_chunks=2,
        max_chars=500,
    )
    diagnosed = select_memory_chunks_with_diagnostics(
        memory_markdown=memory,
        query="コーヒーが好き",
        max_chunks=2,
        max_chars=500,
    )

    assert [chunk.heading_path[-1] for chunk in plain] == ["飲み物"]
    assert diagnosed.chunks == plain
    assert diagnosed.diagnostics.positive_candidate_count == 1


def test_memory_retrieval_keeps_unrelated_japanese_non_positive() -> None:
    memory = """# Memory

## 旅行

先週は福岡へ行きました。
"""

    assert select_memory_chunks(
        memory_markdown=memory,
        query="コーヒーが好き",
        max_chunks=2,
        max_chars=500,
    ) == ()


def test_event_iterable_index_and_diagnostics_share_cjk_selection_semantics() -> None:
    relevant_older = _event("relevant-older", "最近はコーヒーが好きです。")
    unrelated = _event("unrelated", "先週は福岡へ行きました。")
    relevant_newer = _event("relevant-newer", "コーヒーが好きだと話しました。")
    excluded = _event("excluded", "今もコーヒーが好きです。")
    events = (relevant_older, unrelated, relevant_newer, excluded)
    kwargs = {
        "query": "コーヒーが好き",
        "max_events": 2,
        "max_chars": 500,
        "exclude_event_ids": (excluded.id,),
    }

    iterable_plain = select_event_evidence(events=events, **kwargs)
    indexed_plain = select_event_evidence(events=EventDiscoveryIndex(events), **kwargs)
    iterable_diagnosed = select_event_evidence_with_diagnostics(events=events, **kwargs)
    indexed_diagnosed = select_event_evidence_with_diagnostics(
        events=EventDiscoveryIndex(events),
        **kwargs,
    )

    assert iterable_plain == indexed_plain == (relevant_older, relevant_newer)
    assert iterable_diagnosed.events == indexed_diagnosed.events == iterable_plain
    assert iterable_diagnosed.diagnostics == indexed_diagnosed.diagnostics
    assert iterable_diagnosed.diagnostics.positive_candidate_count == 2


def test_event_retrieval_keeps_unrelated_japanese_non_positive() -> None:
    unrelated = _event("unrelated", "先週は福岡へ行きました。")

    assert select_event_evidence(
        events=(unrelated,),
        query="コーヒーが好き",
        max_events=2,
        max_chars=500,
    ) == ()


def test_ascii_exact_token_protection_still_does_not_match_likes_inside_dislikes() -> None:
    likes = _event("likes", "Rin likes tea.")
    dislikes = _event("dislikes", "Rin dislikes coffee.")
    events = (dislikes, likes)

    assert select_event_evidence(
        events=events,
        query="likes",
        max_events=2,
        max_chars=200,
    ) == (likes,)
    assert select_event_evidence(
        events=EventDiscoveryIndex(events),
        query="likes",
        max_events=2,
        max_chars=200,
    ) == (likes,)
