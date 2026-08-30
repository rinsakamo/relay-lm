from __future__ import annotations

import asyncio
import dataclasses
import importlib
from pathlib import Path

import pytest

import relaylm.cognitive as cognitive
from relaylm.budget import (
    BudgetLayer,
    BudgetPlan,
    CountCharacterEnvelope,
    CountEnvelope,
)
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import (
    ProviderProtocolError,
    _require_candidate_sources_in_cognitive_input,
    serialize_cognitive_input,
)
from relaylm.state import StateCandidate
from relaylm.storage.cognitive_package import (
    CognitivePackageDataError,
    CognitivePackageDirectory,
)
from relaylm.turn import run_user_turn


def _write_package(root: Path) -> CognitivePackageDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# Machine\n\nUse package reference material.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\npackage:\n  id: knowledge-fixture\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    (root / "memory" / "state.json").write_text(
        '{"format_version":1,"states":[]}\n', encoding="utf-8"
    )
    return CognitivePackageDirectory(root)


def _knowledge_item(content: str = "Reference fact.", location: str = "knowledge/reference.md"):
    item_type = getattr(cognitive, "KnowledgeItem", None)
    assert item_type is not None, "KNOWLEDGE requires a dedicated KnowledgeItem type"
    return item_type(content=content, location=location)


class _CaptureProvider:
    def __init__(self) -> None:
        self.cognitive_input: CognitiveInput | None = None

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.cognitive_input = cognitive_input
        return CognitiveOutput(response="ok")


def test_package_without_knowledge_is_valid_and_projects_empty_layer(tmp_path: Path) -> None:
    package = _write_package(tmp_path)
    loader = getattr(package, "load_knowledge", None)

    assert callable(loader)
    assert loader() == ()

    provider = _CaptureProvider()
    asyncio.run(run_user_turn(character=package, provider=provider, content="hello"))
    assert provider.cognitive_input is not None
    assert provider.cognitive_input.knowledge == ()


def test_package_knowledge_loads_strict_text_in_deterministic_relative_path_order(
    tmp_path: Path,
) -> None:
    package = _write_package(tmp_path)
    knowledge = tmp_path / "knowledge"
    (knowledge / "nested").mkdir(parents=True)
    (knowledge / "z.md").write_text("Zed\n", encoding="utf-8")
    (knowledge / "a.txt").write_text("Alpha\n", encoding="utf-8")
    (knowledge / "nested" / "m.md").write_text("Middle\n", encoding="utf-8")

    items = package.load_knowledge()

    assert [item.location for item in items] == [
        "knowledge/a.txt",
        "knowledge/nested/m.md",
        "knowledge/z.md",
    ]
    assert [item.content for item in items] == ["Alpha\n", "Middle\n", "Zed\n"]


def test_package_knowledge_fails_closed_on_invalid_utf8_and_unsupported_assets(
    tmp_path: Path,
) -> None:
    invalid_root = tmp_path / "invalid"
    invalid = _write_package(invalid_root)
    (invalid_root / "knowledge").mkdir()
    (invalid_root / "knowledge" / "bad.md").write_bytes(b"\xff\xfe")
    with pytest.raises(CognitivePackageDataError, match="UTF-8"):
        invalid.load_knowledge()

    unsupported_root = tmp_path / "unsupported"
    unsupported = _write_package(unsupported_root)
    (unsupported_root / "knowledge").mkdir()
    (unsupported_root / "knowledge" / "data.json").write_text("{}", encoding="utf-8")
    with pytest.raises(CognitivePackageDataError, match="unsupported"):
        unsupported.load_knowledge()


def test_package_knowledge_rejects_symlink_instead_of_following_it(tmp_path: Path) -> None:
    package = _write_package(tmp_path / "package")
    knowledge = package.root / "knowledge"
    knowledge.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("outside\n", encoding="utf-8")
    try:
        (knowledge / "escape.md").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable on this platform")

    with pytest.raises(CognitivePackageDataError, match="symlink"):
        package.load_knowledge()


def test_knowledge_selector_is_deterministic_whole_file_and_bounded() -> None:
    knowledge_module = importlib.import_module("relaylm.knowledge")
    select_knowledge_items = knowledge_module.select_knowledge_items
    items = (
        _knowledge_item("aaaa", "knowledge/a.md"),
        _knowledge_item("bbbb", "knowledge/b.md"),
        _knowledge_item("cc", "knowledge/c.md"),
    )

    assert select_knowledge_items(items, max_items=2, max_chars=8) == items[:2]
    assert select_knowledge_items(items, max_items=3, max_chars=6) == (items[0], items[2])
    assert select_knowledge_items(items, max_items=0, max_chars=100) == ()
    assert select_knowledge_items(items, max_items=3, max_chars=0) == ()


def test_cognitive_input_and_provider_serialize_knowledge_as_distinct_reference_layer() -> None:
    item = _knowledge_item()
    cognitive_input = CognitiveInput(
        identity=Identity("Role"),
        state_classes={},
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "question"},
            event_id="current-event",
        ),
        knowledge=(item,),
    )

    serialized = serialize_cognitive_input(cognitive_input)

    assert serialized["knowledge"] == [
        {"content": "Reference fact.", "location": "knowledge/reference.md"}
    ]
    assert "knowledge" not in serialized["memory"]


def test_knowledge_locator_is_not_candidate_event_provenance() -> None:
    item = _knowledge_item()
    cognitive_input = CognitiveInput(
        identity=Identity("Role"),
        state_classes={},
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "question"},
            event_id="current-event",
        ),
        knowledge=(item,),
    )
    output = CognitiveOutput(
        response="answer",
        state_candidates=(
            StateCandidate.set(
                state_class="user.fact",
                key="knowledge_only",
                value="Reference fact.",
                sources=(item.location,),
            ),
        ),
    )

    with pytest.raises(ProviderProtocolError, match="absent from CognitiveInput"):
        _require_candidate_sources_in_cognitive_input(output, cognitive_input)


def _base_plan(**overrides: object) -> BudgetPlan:
    values: dict[str, object] = {
        "canonical_state": CountEnvelope(4, 1),
        "working_context": CountCharacterEnvelope(2, 0, 100, 0),
        "retrieved_memory": CountCharacterEnvelope(2, 0, 100, 0),
        "event_evidence": CountCharacterEnvelope(2, 0, 100, 0),
    }
    values.update(overrides)
    return BudgetPlan(**values)  # type: ignore[arg-type]


def test_budget_plan_has_independent_tier3_package_knowledge_envelope_with_zero_compat_floor() -> None:
    fields = {field.name for field in dataclasses.fields(BudgetPlan)}
    assert "package_knowledge" in fields
    assert BudgetLayer.PACKAGE_KNOWLEDGE.tier == 3

    legacy_shape = _base_plan()
    assert legacy_shape.package_knowledge == CountCharacterEnvelope(0, 0, 0, 0)

    enabled = _base_plan(
        package_knowledge=CountCharacterEnvelope(3, 0, 1200, 0),
    )
    assert enabled.envelope_for(BudgetLayer.PACKAGE_KNOWLEDGE) == enabled.package_knowledge
    assert enabled.package_knowledge.at_floor is False


def test_budget_policy_cannot_reduce_tier2_while_package_knowledge_is_above_floor() -> None:
    from relaylm.budget import BudgetDegradationPolicy, BudgetDegradationStep

    plan = _base_plan(
        retrieved_memory=CountCharacterEnvelope(0, 0, 0, 0),
        event_evidence=CountCharacterEnvelope(0, 0, 0, 0),
        package_knowledge=CountCharacterEnvelope(1, 0, 100, 0),
    )
    with pytest.raises(ValueError, match="lower-protection tiers reach floors"):
        BudgetDegradationPolicy(
            initial_plan=plan,
            steps=(
                BudgetDegradationStep(
                    BudgetLayer.WORKING_CONTEXT,
                    CountCharacterEnvelope(0, 0, 0, 0),
                ),
            ),
        )
