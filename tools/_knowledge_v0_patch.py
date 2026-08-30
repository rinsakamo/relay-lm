from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def _replace_once(path: str, old: str, new: str) -> None:
    text = _read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one exact match, found {count}")
    _write(path, text.replace(old, new, 1))


def _replace_between(path: str, start: str, end: str, replacement: str) -> None:
    text = _read(path)
    start_index = text.find(start)
    if start_index < 0:
        raise RuntimeError(f"{path}: start marker not found: {start!r}")
    end_index = text.find(end, start_index)
    if end_index < 0:
        raise RuntimeError(f"{path}: end marker not found: {end!r}")
    _write(path, text[:start_index] + replacement + text[end_index:])


def _patch_cognitive() -> None:
    _write(
        "src/relaylm/cognitive.py",
        '''from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Protocol

from relaylm.continuity import ContinuityCandidate
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import StateCandidate, StateRecord


class CognitionExecutionMode(StrEnum):
    """Closed RelayLM 1.0 ordinary-turn cognition execution-policy vocabulary."""

    SINGLE_PASS = "single_pass"
    TWO_PASS = "two_pass"
    SHADOW_TWO_PASS = "shadow_two_pass"
    AUTO = "auto"


@dataclass(frozen=True, slots=True)
class ContextItem:
    """RelayLM-prepared cognitive material with preserved provenance."""

    content: str
    sources: tuple[str, ...] = ()
    actor: str | None = None

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("context content must not be empty")
        if self.actor is not None and not self.actor.strip():
            raise ValueError("context actor must not be empty when present")
        if not all(isinstance(source, str) and source.strip() for source in self.sources):
            raise ValueError("context sources must contain non-empty strings")


@dataclass(frozen=True, slots=True)
class KnowledgeItem:
    """Package-authored read-only reference material with a document locator."""

    content: str
    location: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("knowledge content must not be empty")
        if not self.location.strip():
            raise ValueError("knowledge location must not be empty")


@dataclass(frozen=True, slots=True)
class RetrievedMemoryItem:
    """Selected crystallized synthesis with a non-authoritative document locator."""

    content: str
    location: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("memory content must not be empty")
        if not self.location.strip():
            raise ValueError("memory location must not be empty")


@dataclass(frozen=True, slots=True)
class EventEvidenceItem:
    """Selected persisted occurrence with real Event provenance."""

    event_id: str
    event_type: str
    actor: str
    timestamp: str
    content: str

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event evidence event_id must not be empty")
        if not self.event_type.strip():
            raise ValueError("event evidence event_type must not be empty")
        if not self.actor.strip():
            raise ValueError("event evidence actor must not be empty")
        if not self.timestamp.strip():
            raise ValueError("event evidence timestamp must not be empty")
        if not self.content.strip():
            raise ValueError("event evidence content must not be empty")


@dataclass(frozen=True, slots=True)
class CognitiveInput:
    identity: Identity
    state_classes: Mapping[str, str]
    state: tuple[StateRecord, ...]
    context: tuple[ContextItem, ...]
    input: Event
    knowledge: tuple[KnowledgeItem, ...] = field(default_factory=tuple)
    memory: tuple[RetrievedMemoryItem, ...] = field(default_factory=tuple)
    event_evidence: tuple[EventEvidenceItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CognitiveOutput:
    response: str
    state_candidates: tuple[StateCandidate, ...] = field(default_factory=tuple)
    continuity_candidates: tuple[ContinuityCandidate, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.response.strip():
            raise ValueError("cognitive response must not be empty")


class CognitiveProvider(Protocol):
    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        """Perform one provider generation for the supplied cognitive input."""
        ...
''',
    )


def _patch_knowledge_module() -> None:
    _write(
        "src/relaylm/knowledge.py",
        '''from __future__ import annotations

from collections.abc import Iterable

from relaylm.cognitive import KnowledgeItem


def _require_non_negative_limit(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must not be negative")


def select_knowledge_items(
    items: Iterable[KnowledgeItem],
    *,
    max_items: int,
    max_chars: int,
) -> tuple[KnowledgeItem, ...]:
    """Select deterministic whole-file package knowledge inside explicit caps.

    Input order is semantic-owner order (the package loader supplies sorted
    package-relative paths). Files are never truncated or semantically ranked.
    A file that cannot fit the remaining character budget is skipped so a later
    smaller file may still fit without changing relative order.
    """

    _require_non_negative_limit("max_items", max_items)
    _require_non_negative_limit("max_chars", max_chars)
    if max_items == 0 or max_chars == 0:
        return ()

    selected: list[KnowledgeItem] = []
    used_chars = 0
    for item in items:
        if not isinstance(item, KnowledgeItem):
            raise TypeError("items must contain KnowledgeItem values")
        if len(selected) >= max_items:
            break
        item_chars = len(item.content)
        if used_chars + item_chars > max_chars:
            continue
        selected.append(item)
        used_chars += item_chars
    return tuple(selected)
''',
    )


def _patch_cognitive_package() -> None:
    _write(
        "src/relaylm/storage/cognitive_package.py",
        '''from __future__ import annotations

from dataclasses import dataclass

from relaylm.character import CharacterConfig
from relaylm.cognitive import KnowledgeItem
from relaylm.storage.filesystem import (
    CharacterDataError,
    CharacterDirectory,
    _required_int,
    _required_string,
)


CognitivePackageDataError = CharacterDataError

KNOWLEDGE_MAX_FILES = 32
KNOWLEDGE_MAX_FILE_BYTES = 64 * 1024
KNOWLEDGE_MAX_TOTAL_BYTES = 256 * 1024
_KNOWLEDGE_SUFFIXES = frozenset({".md", ".txt"})


@dataclass(frozen=True, slots=True)
class CognitivePackageConfig:
    """Stable metadata required by the general Cognitive Package boundary."""

    format_version: int
    package_id: str

    def __post_init__(self) -> None:
        if self.format_version != 1:
            raise ValueError(
                f"unsupported cognitive package format_version: {self.format_version}"
            )
        if not self.package_id.strip():
            raise ValueError("package.id must be a non-empty string")


class CognitivePackageDirectory(CharacterDirectory):
    """Filesystem-backed access to one portable Cognitive Package root.

    The inherited persistence implementation is intentionally shared with the
    existing Character Package adapter so State, Event, MEMORY, duplicate-key,
    and stale-write fail-closed semantics cannot diverge by package role.
    """

    @property
    def knowledge_path(self):
        return self.root / "knowledge"

    def load_config(self) -> CognitivePackageConfig:
        raw = self._load_yaml_mapping(self.config_path)
        has_package = "package" in raw
        has_character = "character" in raw
        if has_package == has_character:
            raise CognitivePackageDataError(
                "config.yaml must define exactly one package or character identity mapping"
            )

        package = raw.get("package")
        character = raw.get("character")
        if has_package and not isinstance(package, dict):
            raise CognitivePackageDataError("config.yaml: package must be a mapping")
        if has_character and not isinstance(character, dict):
            raise CognitivePackageDataError("config.yaml: character must be a mapping")

        try:
            format_version = _required_int(
                raw,
                "format_version",
                "config.yaml: format_version",
            )
            if has_package:
                assert isinstance(package, dict)
                package_id = _required_string(
                    package,
                    "id",
                    "config.yaml: package.id",
                )
            else:
                assert isinstance(character, dict)
                character_config = CharacterConfig(
                    format_version=format_version,
                    character_id=_required_string(
                        character,
                        "id",
                        "config.yaml: character.id",
                    ),
                    name=_required_string(
                        character,
                        "name",
                        "config.yaml: character.name",
                    ),
                )
                package_id = character_config.character_id
            return CognitivePackageConfig(
                format_version=format_version,
                package_id=package_id,
            )
        except (TypeError, ValueError) as exc:
            if isinstance(exc, CognitivePackageDataError):
                raise
            raise CognitivePackageDataError(f"config.yaml: {exc}") from exc

    def load_knowledge(self) -> tuple[KnowledgeItem, ...]:
        """Load the optional bounded read-only package knowledge catalog."""

        root = self.knowledge_path
        if not root.exists():
            return ()
        if root.is_symlink():
            raise CognitivePackageDataError("knowledge directory must not be a symlink")
        if not root.is_dir():
            raise CognitivePackageDataError("knowledge must be a directory")

        paths = sorted(
            root.rglob("*"),
            key=lambda path: path.relative_to(self.root).as_posix(),
        )
        files = []
        for path in paths:
            if path.is_symlink():
                raise CognitivePackageDataError(
                    f"knowledge asset must not be a symlink: {path.relative_to(self.root).as_posix()}"
                )
            if path.is_dir():
                continue
            if not path.is_file():
                raise CognitivePackageDataError(
                    f"knowledge asset must be a regular file: {path.relative_to(self.root).as_posix()}"
                )
            files.append(path)

        if len(files) > KNOWLEDGE_MAX_FILES:
            raise CognitivePackageDataError(
                f"knowledge file count exceeds limit {KNOWLEDGE_MAX_FILES}"
            )

        total_bytes = 0
        items: list[KnowledgeItem] = []
        for path in files:
            location = path.relative_to(self.root).as_posix()
            if path.suffix.lower() not in _KNOWLEDGE_SUFFIXES:
                raise CognitivePackageDataError(
                    f"unsupported knowledge asset type: {location}"
                )
            try:
                payload = path.read_bytes()
            except OSError as exc:
                raise CognitivePackageDataError(
                    f"cannot read knowledge asset {location}: {exc}"
                ) from exc
            size = len(payload)
            if size > KNOWLEDGE_MAX_FILE_BYTES:
                raise CognitivePackageDataError(
                    f"knowledge asset exceeds per-file byte limit: {location}"
                )
            total_bytes += size
            if total_bytes > KNOWLEDGE_MAX_TOTAL_BYTES:
                raise CognitivePackageDataError("knowledge total byte limit exceeded")
            try:
                content = payload.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                raise CognitivePackageDataError(
                    f"knowledge asset is not valid UTF-8: {location}"
                ) from exc
            if "\\x00" in content:
                raise CognitivePackageDataError(
                    f"knowledge asset contains NUL text: {location}"
                )
            try:
                items.append(KnowledgeItem(content=content, location=location))
            except ValueError as exc:
                raise CognitivePackageDataError(
                    f"invalid knowledge asset {location}: {exc}"
                ) from exc
        return tuple(items)
''',
    )


def _patch_budget() -> None:
    _replace_once(
        "src/relaylm/budget.py",
        "from dataclasses import dataclass\n",
        "from dataclasses import dataclass, field\n",
    )
    _replace_between(
        "src/relaylm/budget.py",
        "class BudgetLayer(str, Enum):",
        "LayerEnvelope = CountEnvelope | CountCharacterEnvelope\n",
        '''class BudgetLayer(str, Enum):
    """Budget-managed layers whose semantic selectors already expose owner controls."""

    PACKAGE_KNOWLEDGE = "package_knowledge"
    RETRIEVED_MEMORY = "retrieved_memory"
    EVENT_EVIDENCE = "event_evidence"
    WORKING_CONTEXT = "working_context"
    CANONICAL_STATE = "canonical_state"

    @property
    def tier(self) -> int:
        if self in {
            self.PACKAGE_KNOWLEDGE,
            self.RETRIEVED_MEMORY,
            self.EVENT_EVIDENCE,
        }:
            return 3
        if self is self.WORKING_CONTEXT:
            return 2
        return 1


LayerEnvelope = CountEnvelope | CountCharacterEnvelope
''',
    )
    _replace_between(
        "src/relaylm/budget.py",
        "@dataclass(frozen=True, slots=True)\nclass BudgetPlan:",
        "@dataclass(frozen=True, slots=True)\nclass BudgetDegradationStep:",
        '''@dataclass(frozen=True, slots=True)
class BudgetPlan:
    """Explicit layer envelopes without cross-layer semantic ranking.

    Accepted Continuity is intentionally absent until its semantic owner exposes a
    deterministic pressure-selection control. Package KNOWLEDGE is an independent
    optional Tier-3 reference layer with a zero compatibility floor unless the
    caller explicitly allocates it room.
    """

    canonical_state: CountEnvelope
    working_context: CountCharacterEnvelope
    retrieved_memory: CountCharacterEnvelope
    event_evidence: CountCharacterEnvelope
    package_knowledge: CountCharacterEnvelope = field(
        default_factory=lambda: CountCharacterEnvelope(0, 0, 0, 0)
    )

    def envelope_for(self, layer: BudgetLayer) -> LayerEnvelope:
        if layer is BudgetLayer.CANONICAL_STATE:
            return self.canonical_state
        if layer is BudgetLayer.WORKING_CONTEXT:
            return self.working_context
        if layer is BudgetLayer.RETRIEVED_MEMORY:
            return self.retrieved_memory
        if layer is BudgetLayer.PACKAGE_KNOWLEDGE:
            return self.package_knowledge
        return self.event_evidence

    def with_envelope(self, layer: BudgetLayer, envelope: LayerEnvelope) -> BudgetPlan:
        expected_type = type(self.envelope_for(layer))
        if type(envelope) is not expected_type:
            raise TypeError(f"{layer.value} requires {expected_type.__name__}")
        values = {
            "canonical_state": self.canonical_state,
            "working_context": self.working_context,
            "retrieved_memory": self.retrieved_memory,
            "event_evidence": self.event_evidence,
            "package_knowledge": self.package_knowledge,
        }
        if layer is BudgetLayer.CANONICAL_STATE:
            values["canonical_state"] = envelope
        elif layer is BudgetLayer.WORKING_CONTEXT:
            values["working_context"] = envelope
        elif layer is BudgetLayer.RETRIEVED_MEMORY:
            values["retrieved_memory"] = envelope
        elif layer is BudgetLayer.PACKAGE_KNOWLEDGE:
            values["package_knowledge"] = envelope
        else:
            values["event_evidence"] = envelope
        return BudgetPlan(**values)  # type: ignore[arg-type]

    def lower_protection_tiers_at_floor(self, *, before_tier: int) -> bool:
        return all(
            self.envelope_for(layer).at_floor
            for layer in BudgetLayer
            if layer.tier > before_tier
        )


''',
    )


def _patch_budget_controls() -> None:
    _write(
        "src/relaylm/budget_controls.py",
        '''from __future__ import annotations

from dataclasses import dataclass

from relaylm.budget import BudgetPlan


@dataclass(frozen=True, slots=True)
class ContextCompilerBudgetControls:
    """Budget-owned envelope values expressed in Context Compiler parameter units."""

    max_state_records: int
    max_working_context_events: int
    max_working_context_chars: int


@dataclass(frozen=True, slots=True)
class RetrievalBudgetControls:
    """Budget-owned envelope values expressed in Retrieval selector parameter units."""

    memory_max_chunks: int
    memory_max_chars: int
    event_max_events: int
    event_max_chars: int


@dataclass(frozen=True, slots=True)
class KnowledgeBudgetControls:
    """Budget-owned envelope for deterministic whole-file package knowledge."""

    max_items: int
    max_chars: int


@dataclass(frozen=True, slots=True)
class BudgetOwnerControls:
    """Content-free translation from a BudgetPlan into existing owner controls.

    This structure carries only envelope limits. It does not execute a selector,
    rank semantic content, or add a Continuity pressure-selection contract.
    """

    context_compiler: ContextCompilerBudgetControls
    retrieval: RetrievalBudgetControls
    knowledge: KnowledgeBudgetControls


def owner_controls_for_budget_plan(plan: BudgetPlan) -> BudgetOwnerControls:
    """Translate current plan caps into the parameter units owned by each layer."""

    return BudgetOwnerControls(
        context_compiler=ContextCompilerBudgetControls(
            max_state_records=plan.canonical_state.max_items,
            max_working_context_events=plan.working_context.max_items,
            max_working_context_chars=plan.working_context.max_chars,
        ),
        retrieval=RetrievalBudgetControls(
            memory_max_chunks=plan.retrieved_memory.max_items,
            memory_max_chars=plan.retrieved_memory.max_chars,
            event_max_events=plan.event_evidence.max_items,
            event_max_chars=plan.event_evidence.max_chars,
        ),
        knowledge=KnowledgeBudgetControls(
            max_items=plan.package_knowledge.max_items,
            max_chars=plan.package_knowledge.max_chars,
        ),
    )
''',
    )


def _patch_turn() -> None:
    _replace_once(
        "src/relaylm/turn.py",
        "from dataclasses import dataclass\n",
        "from dataclasses import dataclass, replace\n",
    )
    _replace_once(
        "src/relaylm/turn.py",
        "from relaylm.cognitive import CognitiveInput, CognitiveOutput, CognitiveProvider\n",
        "from relaylm.cognitive import (\n    CognitiveInput,\n    CognitiveOutput,\n    CognitiveProvider,\n    KnowledgeItem,\n)\n",
    )
    _replace_once(
        "src/relaylm/turn.py",
        "from relaylm.identity import Identity\n",
        "from relaylm.identity import Identity\nfrom relaylm.knowledge import select_knowledge_items\n",
    )
    _replace_once(
        "src/relaylm/turn.py",
        '''    controls = owner_controls_for_budget_plan(plan)\n\n    retrieved_memory = ()\n''',
        '''    controls = owner_controls_for_budget_plan(plan)\n\n    package_knowledge = ()\n    if controls.knowledge.max_items > 0 and controls.knowledge.max_chars > 0:\n        package_knowledge = select_knowledge_items(\n            _load_package_knowledge(character),\n            max_items=controls.knowledge.max_items,\n            max_chars=controls.knowledge.max_chars,\n        )\n\n    retrieved_memory = ()\n''',
    )
    _replace_once(
        "src/relaylm/turn.py",
        '''    return compile_cognitive_input(\n        identity=identity,\n        state=state,\n        current_event=user_event,\n        recent_events=character.iter_events(),\n        continuity_context=continuity_context,\n        retrieved_memory=retrieved_memory,\n        event_evidence=event_evidence,\n        max_working_context_events=(\n            controls.context_compiler.max_working_context_events\n        ),\n        max_working_context_chars=controls.context_compiler.max_working_context_chars,\n        max_state_records=controls.context_compiler.max_state_records,\n    )\n\n\ndef _prepare_user_turn(\n''',
        '''    cognitive_input = compile_cognitive_input(\n        identity=identity,\n        state=state,\n        current_event=user_event,\n        recent_events=character.iter_events(),\n        continuity_context=continuity_context,\n        retrieved_memory=retrieved_memory,\n        event_evidence=event_evidence,\n        max_working_context_events=(\n            controls.context_compiler.max_working_context_events\n        ),\n        max_working_context_chars=controls.context_compiler.max_working_context_chars,\n        max_state_records=controls.context_compiler.max_state_records,\n    )\n    return replace(cognitive_input, knowledge=package_knowledge)\n\n\ndef _prepare_user_turn(\n''',
    )
    _replace_once(
        "src/relaylm/turn.py",
        '''    cognitive_input = compile_cognitive_input(\n        identity=identity,\n        state=state,\n        current_event=user_event,\n        recent_events=recent_events,\n        continuity_context=continuity_context,\n        retrieved_memory=retrieved_memory,\n        event_evidence=event_evidence,\n    )\n    if not include_retrieval_diagnostics:\n''',
        '''    cognitive_input = compile_cognitive_input(\n        identity=identity,\n        state=state,\n        current_event=user_event,\n        recent_events=recent_events,\n        continuity_context=continuity_context,\n        retrieved_memory=retrieved_memory,\n        event_evidence=event_evidence,\n    )\n    cognitive_input = replace(\n        cognitive_input,\n        knowledge=_load_package_knowledge(character),\n    )\n    if not include_retrieval_diagnostics:\n''',
    )
    marker = "\ndef _aggregate_retrieval_diagnostics(\n"
    helper = '''\ndef _load_package_knowledge(\n    character: CharacterDirectory,\n) -> tuple[KnowledgeItem, ...]:\n    loader = getattr(character, "load_knowledge", None)\n    if loader is None:\n        return ()\n    if not callable(loader):\n        raise TypeError("package load_knowledge must be callable")\n    items = loader()\n    if not isinstance(items, tuple) or not all(\n        isinstance(item, KnowledgeItem) for item in items\n    ):\n        raise TypeError("package load_knowledge must return KnowledgeItem values")\n    return items\n\n\n'''
    _replace_once("src/relaylm/turn.py", marker, helper + marker.lstrip("\n"))


def _patch_provider() -> None:
    _replace_once(
        "src/relaylm/providers/openai_compatible.py",
        '''Context contains RelayLM-prepared information relevant to this turn. Context may include recent user- or assistant-authored dialogue; preserve its actor provenance.\nMemory contains optional retrieved crystallized synthesis. Memory is not accepted current State, and its location is a document locator rather than Event provenance. When Memory conflicts with active State, treat active State as the current understanding.\n''',
        '''Context contains RelayLM-prepared information relevant to this turn. Context may include recent user- or assistant-authored dialogue; preserve its actor provenance.\nKnowledge contains optional package-authored read-only reference material. Knowledge is not Identity, lived Memory, Event evidence, or accepted State. Its location is a package-relative document locator, not Event provenance. Use Knowledge as reference material according to the package role, and do not claim it was personally experienced or remembered unless separate governed evidence supports that claim.\nMemory contains optional retrieved crystallized synthesis. Memory is not accepted current State, and its location is a document locator rather than Event provenance. When Memory conflicts with active State, treat active State as the current understanding.\n''',
    )
    _replace_once(
        "src/relaylm/providers/openai_compatible.py",
        '''- Use only Event IDs present in State, Context, Event Evidence, or Input as candidate `sources`. Memory `location` values are document locators, not Event IDs, and must never be used as `sources`.\n''',
        '''- Use only Event IDs present in State, Context, Event Evidence, or Input as candidate `sources`. Knowledge and Memory `location` values are document locators, not Event IDs, and must never be used as `sources`.\n''',
    )
    _replace_once(
        "src/relaylm/providers/openai_compatible.py",
        '''        "context": context,\n        "memory": [\n''',
        '''        "context": context,\n        "knowledge": [\n            {\n                "content": item.content,\n                "location": item.location,\n            }\n            for item in cognitive_input.knowledge\n        ],\n        "memory": [\n''',
    )


def _patch_runtime_config_loader() -> None:
    _replace_between(
        "src/relaylm/runtime_config_loader.py",
        "def _parse_budget_policy(raw: object, path: str) -> BudgetDegradationPolicy:\n",
        "def _parse_count_envelope(raw: object, path: str) -> CountEnvelope:\n",
        '''def _parse_budget_policy(raw: object, path: str) -> BudgetDegradationPolicy:
    mapping = _mapping(raw, path)
    _require_exact_keys(mapping, path, {"initial_plan", "steps"})

    plan_path = f"{path}.initial_plan"
    plan_raw = _mapping(mapping["initial_plan"], plan_path)
    required_layers = {
        "canonical_state",
        "working_context",
        "retrieved_memory",
        "event_evidence",
    }
    _reject_unknown(plan_raw, plan_path, required_layers | {"package_knowledge"})
    for required in required_layers:
        if required not in plan_raw:
            _missing(f"{plan_path}.{required}")
    try:
        canonical_state = _parse_count_envelope(
            plan_raw["canonical_state"],
            f"{plan_path}.canonical_state",
        )
        working_context = _parse_count_character_envelope(
            plan_raw["working_context"],
            f"{plan_path}.working_context",
        )
        retrieved_memory = _parse_count_character_envelope(
            plan_raw["retrieved_memory"],
            f"{plan_path}.retrieved_memory",
        )
        event_evidence = _parse_count_character_envelope(
            plan_raw["event_evidence"],
            f"{plan_path}.event_evidence",
        )
        package_knowledge = (
            _parse_count_character_envelope(
                plan_raw["package_knowledge"],
                f"{plan_path}.package_knowledge",
            )
            if "package_knowledge" in plan_raw
            else CountCharacterEnvelope(0, 0, 0, 0)
        )
    except RuntimeConfigResolutionError as exc:
        if exc.code is RuntimeConfigErrorCode.INVALID_VALUE:
            _invalid_value(path, "invalid owner-defined budget envelope")
        raise

    plan = BudgetPlan(
        canonical_state=canonical_state,
        working_context=working_context,
        retrieved_memory=retrieved_memory,
        event_evidence=event_evidence,
        package_knowledge=package_knowledge,
    )

    steps_raw = mapping["steps"]
    if not isinstance(steps_raw, list):
        _invalid_type(f"{path}.steps", "must be a sequence")
    steps: list[BudgetDegradationStep] = []
    for index, item in enumerate(steps_raw):
        step_path = f"{path}.steps.{index}"
        step_raw = _mapping(item, step_path)
        _require_exact_keys(step_raw, step_path, {"layer", "target"})
        layer_name = _string(step_raw["layer"], f"{step_path}.layer")
        try:
            layer = BudgetLayer(layer_name)
        except ValueError:
            _invalid_value(f"{step_path}.layer", "unsupported budget layer")
        if layer is BudgetLayer.CANONICAL_STATE:
            target = _parse_count_envelope(step_raw["target"], f"{step_path}.target")
        else:
            target = _parse_count_character_envelope(
                step_raw["target"],
                f"{step_path}.target",
            )
        steps.append(BudgetDegradationStep(layer=layer, target=target))

    try:
        return BudgetDegradationPolicy(initial_plan=plan, steps=tuple(steps))
    except (TypeError, ValueError) as exc:
        _invalid_value(path, str(exc))


''',
    )


def _patch_existing_budget_test() -> None:
    _replace_once(
        "tests/unit/test_cognitive_budget_plan.py",
        '''        "retrieved_memory",\n        "event_evidence",\n    }\n''',
        '''        "retrieved_memory",\n        "event_evidence",\n        "package_knowledge",\n    }\n''',
    )


def main() -> None:
    _patch_cognitive()
    _patch_knowledge_module()
    _patch_cognitive_package()
    _patch_budget()
    _patch_budget_controls()
    _patch_turn()
    _patch_provider()
    _patch_runtime_config_loader()
    _patch_existing_budget_test()


if __name__ == "__main__":
    main()
