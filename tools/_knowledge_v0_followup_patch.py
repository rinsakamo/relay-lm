from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _replace_once(path: str, old: str, new: str) -> None:
    text = _read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one exact match, found {count}")
    _write(path, text.replace(old, new, 1))


def _authority() -> None:
    _write(
        ".ai/authority/knowledge.yaml",
        '''schema_version: 1
id: knowledge
summary: >-
  Core 1.0 package-authored read-only reference KNOWLEDGE, including strict
  package loading, deterministic whole-file projection, model-facing separation
  from Identity/State/Event/MEMORY authority, and its independent Cognitive
  Budget envelope.
owner_issue: 2003
canonical_surfaces:
- docs/reference/knowledge.md
references:
- docs/reference/character-directory.md
- docs/architecture/cognitive-runtime.md
- docs/architecture/core.md
implementation:
- src/relaylm/knowledge.py
- src/relaylm/cognitive.py
- src/relaylm/storage/cognitive_package.py
- src/relaylm/budget.py
- src/relaylm/budget_controls.py
- src/relaylm/turn.py
- src/relaylm/providers/openai_compatible.py
- src/relaylm/runtime_config_loader.py
qualification_inputs:
- docs/reference/knowledge.md
- docs/reference/character-directory.md
- src/relaylm/knowledge.py
- src/relaylm/cognitive.py
- src/relaylm/storage/cognitive_package.py
- src/relaylm/budget.py
- src/relaylm/budget_controls.py
- src/relaylm/turn.py
- src/relaylm/providers/openai_compatible.py
- src/relaylm/runtime_config_loader.py
tests:
- tests/unit/test_knowledge_v0.py
- tests/unit/test_cognitive_budget_plan.py
- tests/unit/test_evaluation_budget_degradation_plan.py
depends_on:
- core_architecture
''',
    )
    _replace_once(
        ".ai/authority/cognitive_turn.yaml",
        '''- core_architecture
- provider_and_api
''',
        '''- core_architecture
- knowledge
- provider_and_api
''',
    )
    _replace_once(
        ".ai/authority/cognitive_budget.yaml",
        '''depends_on:
- context_compiler
- provider_and_api
''',
        '''depends_on:
- context_compiler
- knowledge
- provider_and_api
''',
    )
    _replace_once(
        ".ai/authority/persistence.yaml",
        '''depends_on:
- core_architecture
- state_and_validation
''',
        '''depends_on:
- core_architecture
- knowledge
- state_and_validation
''',
    )


def _docs() -> None:
    _write(
        "docs/reference/knowledge.md",
        '''# Package KNOWLEDGE

Core 1.0 treats package-authored reference material as a separate semantic layer:

```text
SOUL      who/what the package is and how it should behave
KNOWLEDGE what the package author supplied as reference material
MEMORY    what governed experience was later crystallized into lived synthesis
STATE     what RelayLM currently accepts as current understanding
EVENTS    what occurred and supplies occurrence provenance
```

The invariant is **Identity != Knowledge != Experience**. Reading a packaged fact does not mean the package experienced it, remembered it, observed it, or accepted it into Canonical State.

## Portable v0 format

A Cognitive Package may optionally contain:

```text
<CognitivePackage>/
└─ knowledge/
   └─ ... .md or .txt UTF-8 text assets ...
```

Packages that do not use KNOWLEDGE do not need an empty directory. v0 supports regular UTF-8 Markdown and text files only. The loader rejects symlinks, unsupported asset types, invalid UTF-8, NUL text, non-regular assets, more than 32 files, files larger than 64 KiB, or more than 256 KiB total package KNOWLEDGE. Paths exposed to cognition are deterministic package-relative locators under `knowledge/`.

Those byte bounds are package-format safety limits, not a substitute for the model context budget.

## Cognitive projection and authority

Model-facing KNOWLEDGE is carried as dedicated `KnowledgeItem` values and serialized as its own `knowledge` section. A Knowledge `location` is a document locator. It is **not an Event ID** and is never admitted as State/Continuity candidate source provenance.

The provider instruction labels KNOWLEDGE as package-authored reference material. It may be used to answer or reason according to the package role, but it must not be narrated as personal experience or memory unless separate governed evidence supports that claim.

Ordinary turns and Crystallization have no write operation for `knowledge/`. Crystallization continues to own lived `memory/MEMORY.md` and State proposals; it does not rewrite package KNOWLEDGE.

## Bounded selection

When total Cognitive Budget enforcement is configured, KNOWLEDGE has an independent Tier-3 `package_knowledge` `CountCharacterEnvelope`. Existing budget policies that omit it resolve to a zero item/character envelope, preserving their prior identity until an owner explicitly allocates KNOWLEDGE capacity.

Selection is deterministic and semantic-free: package-relative file order is preserved, whole files are included while item/character caps permit them, and a file that cannot fit the remaining character cap is skipped so a later smaller file may still fit. Files are never truncated, embedded, re-ranked, or summarized by a hidden model call. The final provider serialization still passes through the normal exact/conservative total-context counter and fail-before-generation enforcement.

A non-budgeted compatibility turn may carry the package catalog bounded by the strict package-format limits above; release/calibrated runtime capacity remains owned by Cognitive Budget and calibration policy.

## Deliberately deferred

KNOWLEDGE v0 does not add embeddings, vector databases, semantic RAG, crawlers, external URLs, autonomous refresh, binary/PDF/Office ingestion, mutable model-authored KNOWLEDGE, or a second truth database. Large-corpus retrieval and governed external knowledge import remain post-1.0 concerns unless separately promoted.
''',
    )
    _replace_once(
        "docs/reference/character-directory.md",
        '''<CognitivePackage>/
├─ SOUL.md
├─ config.yaml
└─ memory/
''',
        '''<CognitivePackage>/
├─ SOUL.md
├─ config.yaml
├─ knowledge/         # optional package-authored read-only reference text
└─ memory/
''',
    )
    _replace_once(
        "docs/reference/character-directory.md",
        '''- `SOUL.md` is required by the current runtime and must contain non-empty stable identity or role authority. For a machine-like package this may be role-oriented rather than human-persona-oriented content.
''',
        '''- `SOUL.md` is required by the current runtime and must contain non-empty stable identity or role authority. For a machine-like package this may be role-oriented rather than human-persona-oriented content.
- `knowledge/` is optional package-authored read-only reference material. KNOWLEDGE is distinct from SOUL, State, Event provenance, and lived `memory/MEMORY.md`; supported v0 assets and bounds are defined in `docs/reference/knowledge.md`.
''',
    )
    _replace_once(
        "docs/reference/character-directory.md",
        '''- `knowledge/` — package-associated reference/world knowledge;
''',
        '''- `knowledge/` — package-authored read-only reference/world knowledge; Core 1.0 v0 supports the bounded text form in `docs/reference/knowledge.md`;
''',
    )


def _evaluation() -> None:
    path = "src/relaylm/evaluation_budget_degradation_plan.py"
    _replace_once(
        path,
        '''        event_evidence=CountCharacterEnvelope(
            max_items=3,
            floor_items=0,
            max_chars=600,
            floor_chars=0,
        ),
    )
''',
        '''        event_evidence=CountCharacterEnvelope(
            max_items=3,
            floor_items=0,
            max_chars=600,
            floor_chars=0,
        ),
        package_knowledge=CountCharacterEnvelope(
            max_items=2,
            floor_items=0,
            max_chars=400,
            floor_chars=0,
        ),
    )
''',
    )
    _replace_once(
        path,
        '''            BudgetDegradationStep(
                BudgetLayer.EVENT_EVIDENCE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.WORKING_CONTEXT,
''',
        '''            BudgetDegradationStep(
                BudgetLayer.EVENT_EVIDENCE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.PACKAGE_KNOWLEDGE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.WORKING_CONTEXT,
''',
    )
    _replace_once(
        path,
        '''    after_two = full_policy.plan_after_steps(2)
    after_three = full_policy.plan_after_steps(3)
    final = full_policy.final_plan
''',
        '''    after_three = full_policy.plan_after_steps(3)
    after_four = full_policy.plan_after_steps(4)
    final = full_policy.final_plan
''',
    )
    _replace_once(
        path,
        '''            BudgetDegradationStep(
                BudgetLayer.EVENT_EVIDENCE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
        ),
    )
    event_first = BudgetDegradationPolicy(
''',
        '''            BudgetDegradationStep(
                BudgetLayer.EVENT_EVIDENCE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.PACKAGE_KNOWLEDGE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
        ),
    )
    event_first = BudgetDegradationPolicy(
''',
    )
    _replace_once(
        path,
        '''            BudgetDegradationStep(
                BudgetLayer.RETRIEVED_MEMORY,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
        ),
    )

    reverse_initial = BudgetPlan(
''',
        '''            BudgetDegradationStep(
                BudgetLayer.RETRIEVED_MEMORY,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.PACKAGE_KNOWLEDGE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
        ),
    )
    knowledge_first = BudgetDegradationPolicy(
        initial_plan=initial,
        steps=(
            BudgetDegradationStep(
                BudgetLayer.PACKAGE_KNOWLEDGE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.RETRIEVED_MEMORY,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.EVENT_EVIDENCE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
        ),
    )

    reverse_initial = BudgetPlan(
''',
    )
    _replace_once(
        path,
        '''                    "retrieved_memory",
                    "event_evidence",
                }
                and "continuity" not in managed_fields
            ),
            expected=4,
''',
        '''                    "retrieved_memory",
                    "event_evidence",
                    "package_knowledge",
                }
                and "continuity" not in managed_fields
            ),
            expected=5,
''',
    )
    _replace_once(
        path,
        '''                full_policy.plan_after_steps(0) == initial
                and after_two.retrieved_memory.at_floor
                and after_two.event_evidence.at_floor
                and after_three.working_context.at_floor
                and final.canonical_state.at_floor
''',
        '''                full_policy.plan_after_steps(0) == initial
                and after_three.retrieved_memory.at_floor
                and after_three.event_evidence.at_floor
                and after_three.package_knowledge.at_floor
                and after_four.working_context.at_floor
                and final.canonical_state.at_floor
''',
    )
    _replace_once(
        path,
        '''                memory_first.plan_after_steps(1).retrieved_memory.at_floor
                and not memory_first.plan_after_steps(1).event_evidence.at_floor
                and event_first.plan_after_steps(1).event_evidence.at_floor
                and not event_first.plan_after_steps(1).retrieved_memory.at_floor
                and memory_first.final_plan == event_first.final_plan
            ),
            expected=True,
            observed=memory_first.final_plan == event_first.final_plan,
''',
        '''                memory_first.plan_after_steps(1).retrieved_memory.at_floor
                and not memory_first.plan_after_steps(1).event_evidence.at_floor
                and not memory_first.plan_after_steps(1).package_knowledge.at_floor
                and event_first.plan_after_steps(1).event_evidence.at_floor
                and not event_first.plan_after_steps(1).retrieved_memory.at_floor
                and not event_first.plan_after_steps(1).package_knowledge.at_floor
                and knowledge_first.plan_after_steps(1).package_knowledge.at_floor
                and not knowledge_first.plan_after_steps(1).retrieved_memory.at_floor
                and not knowledge_first.plan_after_steps(1).event_evidence.at_floor
                and memory_first.final_plan == event_first.final_plan
                and event_first.final_plan == knowledge_first.final_plan
            ),
            expected=True,
            observed=(
                memory_first.final_plan == event_first.final_plan
                and event_first.final_plan == knowledge_first.final_plan
            ),
''',
    )
    _replace_once(
        path,
        '''            "tier3_order_variant_count": 2,
''',
        '''            "tier3_order_variant_count": 3,
''',
    )

    test_path = "tests/unit/test_evaluation_budget_degradation_plan.py"
    _replace_once(
        test_path,
        '''        "managed_layer_count": 4,
        "full_plan_step_count": 4,
        "tier3_order_variant_count": 2,
''',
        '''        "managed_layer_count": 5,
        "full_plan_step_count": 5,
        "tier3_order_variant_count": 3,
''',
    )


def _knowledge_tests() -> None:
    path = "tests/unit/test_knowledge_v0.py"
    _replace_once(
        path,
        '''from relaylm.cognitive import CognitiveInput, CognitiveOutput
''',
        '''from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.crystallization import CrystallizationOutput, run_crystallization
''',
    )
    _replace_once(
        path,
        '''from relaylm.events import Event
''',
        '''from relaylm.events import Event
from relaylm.memory_provenance import (
    MemoryProvenanceSource,
    MemoryProvenanceSourceKind,
    MemoryTemporalScope,
    MemoryUnit,
)
''',
    )
    marker = '''def test_knowledge_selector_is_deterministic_whole_file_and_bounded() -> None:
'''
    addition = '''def test_package_knowledge_enforces_file_count_size_and_total_bounds(tmp_path: Path) -> None:
    count_root = tmp_path / "count"
    count_package = _write_package(count_root)
    (count_root / "knowledge").mkdir()
    for index in range(33):
        (count_root / "knowledge" / f"{index:02d}.txt").write_text("x", encoding="utf-8")
    with pytest.raises(CognitivePackageDataError, match="file count"):
        count_package.load_knowledge()

    size_root = tmp_path / "size"
    size_package = _write_package(size_root)
    (size_root / "knowledge").mkdir()
    (size_root / "knowledge" / "large.txt").write_bytes(b"x" * (64 * 1024 + 1))
    with pytest.raises(CognitivePackageDataError, match="per-file"):
        size_package.load_knowledge()

    total_root = tmp_path / "total"
    total_package = _write_package(total_root)
    (total_root / "knowledge").mkdir()
    for index in range(5):
        (total_root / "knowledge" / f"{index}.txt").write_bytes(b"x" * (60 * 1024))
    with pytest.raises(CognitivePackageDataError, match="total byte"):
        total_package.load_knowledge()


class _KnowledgeReadOnlyCrystallizer:
    async def generate(self, crystallization_input):
        event = crystallization_input.events[-1]
        return CrystallizationOutput(
            memory_units=(
                MemoryUnit(
                    heading="Observed",
                    content="A governed lived event.",
                    temporal_scope=MemoryTemporalScope.CURRENT,
                    sources=(
                        MemoryProvenanceSource(
                            kind=MemoryProvenanceSourceKind.EVENT,
                            reference_id=event.id,
                        ),
                    ),
                ),
            ),
        )


def test_ordinary_turn_and_crystallization_do_not_rewrite_package_knowledge(
    tmp_path: Path,
) -> None:
    package = _write_package(tmp_path)
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    asset = knowledge / "reference.md"
    original = b"Package-authored reference.\n"
    asset.write_bytes(original)

    provider = _CaptureProvider()
    asyncio.run(run_user_turn(character=package, provider=provider, content="hello"))
    assert asset.read_bytes() == original

    package.append_event(
        Event.create(type="message", actor="user", payload={"content": "lived event"})
    )
    asyncio.run(
        run_crystallization(
            character=package,
            crystallizer=_KnowledgeReadOnlyCrystallizer(),
            max_events=1,
        )
    )
    assert asset.read_bytes() == original


'''
    _replace_once(path, marker, addition + marker)


def main() -> None:
    _authority()
    _docs()
    _evaluation()
    _knowledge_tests()


if __name__ == "__main__":
    main()
