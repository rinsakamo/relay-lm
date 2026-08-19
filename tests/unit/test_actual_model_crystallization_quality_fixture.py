from __future__ import annotations

import json
import re
from pathlib import Path

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.storage.filesystem import CharacterDirectory


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "characters"
    / "crystallization-quality-v1"
)
REVISION_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "characters"
    / "crystallization-quality-v1.revision.txt"
)
CASE_ID = "crystallization-consolidation-quality-v1"
CASE_VERSION = "1"
RECOMMENDED_MAX_EVENTS = 7

EXPECTED_EVENTS = (
    (
        "cry4-user-name-yuu",
        "user",
        "私の名前はユウ。",
    ),
    (
        "cry4-user-beverage-comparison",
        "user",
        "コーヒーも紅茶も好きだけど、どちらかなら紅茶のほうが好き。コーヒーが嫌いになったわけではない。",
    ),
    (
        "cry4-user-blue-box-task",
        "user",
        "今だけ、青い箱の中身を確認するのを手伝って。",
    ),
    (
        "cry4-assistant-hokkaido-claim",
        "assistant",
        "ユウは北海道に住んでいるんだね。",
    ),
    (
        "cry4-user-name-correction",
        "user",
        "訂正。名前はユウト。ユウじゃなくてユウトと呼んで。",
    ),
    (
        "cry4-user-residence-correction",
        "user",
        "以前は京都に住んでいたけど、今は大阪に住んでいる。",
    ),
    (
        "cry4-user-blue-box-complete",
        "user",
        "青い箱の確認はもう終わった。この作業を今後の目標として覚えなくていい。",
    ),
)

EXPECTED_STATE = (
    ("state-user-name", "user.identity", "name", "ユウ", ("cry4-user-name-yuu",)),
    (
        "state-pref-coffee",
        "user.preference",
        "coffee",
        "likes",
        ("cry4-user-beverage-comparison",),
    ),
    (
        "state-pref-tea",
        "user.preference",
        "tea",
        "likes",
        ("cry4-user-beverage-comparison",),
    ),
    (
        "state-preferred-beverage",
        "user.preference",
        "preferred_beverage",
        "coffee",
        ("cry4-user-beverage-comparison",),
    ),
    (
        "state-residence-location",
        "user.fact",
        "residence_location",
        "京都",
        ("cry4-user-residence-correction",),
    ),
    (
        "state-current-task",
        "user.goal",
        "current_task",
        "check_blue_box_contents",
        ("cry4-user-blue-box-task",),
    ),
)

_METADATA = re.compile(r"<!--[ ]+relaylm-memory:v1[ ]+(.+?)[ ]+-->")


def _fixture() -> CharacterDirectory:
    assert FIXTURE_ROOT.is_dir(), "CRY4 crystallization quality fixture is not implemented"
    return CharacterDirectory(FIXTURE_ROOT)


def test_fixture_loads_with_canonical_identity_and_exact_revision_receipt() -> None:
    character = _fixture()
    config = character.load_config()
    identity = character.load_identity()

    assert config.character_id == "actual-model-crystallization-quality-v1"
    assert config.name == "Aoi"
    assert identity.content.startswith("# Aoi\n")

    expected_revision = REVISION_PATH.read_text(encoding="utf-8").strip()
    assert expected_revision.startswith("sha256:")
    assert character_fixture_revision(FIXTURE_ROOT) == expected_revision


def test_fixture_freezes_exact_seven_event_semantic_story() -> None:
    character = _fixture()
    events = tuple(character.iter_events())

    assert len(events) == RECOMMENDED_MAX_EVENTS
    assert tuple(
        (event.id, event.actor, event.payload.get("content")) for event in events
    ) == EXPECTED_EVENTS
    assert tuple(event.type for event in events) == ("message",) * RECOMMENDED_MAX_EVENTS
    assert tuple(event.timestamp for event in events) == (
        "2026-08-18T00:00:00+00:00",
        "2026-08-18T00:01:00+00:00",
        "2026-08-18T00:02:00+00:00",
        "2026-08-18T00:03:00+00:00",
        "2026-08-18T00:04:00+00:00",
        "2026-08-18T00:05:00+00:00",
        "2026-08-18T00:06:00+00:00",
    )
    assert tuple(event.id for event in events[-RECOMMENDED_MAX_EVENTS:]) == tuple(
        item[0] for item in EXPECTED_EVENTS
    )


def test_fixture_freezes_plausible_but_imperfect_prepass_canonical_state() -> None:
    character = _fixture()
    state = character.load_state()

    assert tuple(
        (record.state_id, record.state_class, record.key, record.value, record.sources)
        for record in state.states
    ) == EXPECTED_STATE

    events = {event.id: event for event in character.iter_events()}
    for record in state.states:
        assert record.status == "active"
        assert record.sources
        assert all(source in events for source in record.sources)
        assert all(events[source].actor == "user" for source in record.sources)

    state_keys = {(record.state_class, record.key) for record in state.states}
    assert ("user.fact", "residence_location") in state_keys
    assert ("user.goal", "current_task") in state_keys
    assert all("hokkaido" not in record.key.casefold() for record in state.states)
    assert all(record.value != "北海道" for record in state.states)


def test_prior_memory_is_governed_but_intentionally_stale_duplicate_and_messy() -> None:
    character = _fixture()
    memory = character.load_memory_markdown()
    assert memory is not None

    for text in (
        "The user's name is ユウ.",
        "Coffee is the preferred beverage.",
        "The user's preferred drink is coffee.",
        "The user currently lives in 京都.",
        "The user previously lived in 京都.",
        "The user lives in 北海道.",
        "check the contents of the blue box",
    ):
        assert text in memory

    event_ids = {event.id for event in character.iter_events()}
    state_ids = {record.state_id for record in character.load_state().states}
    metadata = tuple(json.loads(payload) for payload in _METADATA.findall(memory))
    assert len(metadata) == 7

    for item in metadata:
        assert set(item) == {"memory_id", "derivation_id", "temporal_scope", "sources"}
        assert item["temporal_scope"] in {"current", "historical", "unknown"}
        assert item["sources"]
        for source in item["sources"]:
            assert set(source) == {"kind", "reference_id"}
            if source["kind"] == "event":
                assert source["reference_id"] in event_ids
            elif source["kind"] == "state":
                assert source["reference_id"] in state_ids
            else:
                raise AssertionError(f"unsupported fixture MEMORY source kind: {source['kind']}")

    unsupported = next(item for item in metadata if item["memory_id"] == "cry4-hokkaido-note")
    assert unsupported["temporal_scope"] == "current"
    assert unsupported["sources"] == [
        {"kind": "event", "reference_id": "cry4-assistant-hokkaido-claim"}
    ]


def test_fixture_exposes_all_seven_review_opportunities_without_exact_model_oracle() -> None:
    character = _fixture()
    events = {event.id: event for event in character.iter_events()}
    state = {(record.state_class, record.key): record for record in character.load_state().states}

    assert state[("user.identity", "name")].value == "ユウ"
    assert events["cry4-user-name-correction"].payload["content"].find("ユウト") >= 0

    assert state[("user.preference", "coffee")].value == "likes"
    assert state[("user.preference", "tea")].value == "likes"
    assert state[("user.preference", "preferred_beverage")].value == "coffee"
    assert "紅茶のほうが好き" in events["cry4-user-beverage-comparison"].payload["content"]
    assert "嫌いになったわけではない" in events[
        "cry4-user-beverage-comparison"
    ].payload["content"]

    assert state[("user.fact", "residence_location")].value == "京都"
    assert "今は大阪" in events["cry4-user-residence-correction"].payload["content"]

    assert state[("user.goal", "current_task")].value == "check_blue_box_contents"
    assert "もう終わった" in events["cry4-user-blue-box-complete"].payload["content"]

    assert events["cry4-assistant-hokkaido-claim"].actor == "assistant"
    assert CASE_ID == "crystallization-consolidation-quality-v1"
    assert CASE_VERSION == "1"
