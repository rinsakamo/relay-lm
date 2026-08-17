from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal


ContinuityKind = Literal["referent", "unresolved", "active_task"]
ContinuityOperation = Literal["set", "resolve"]
ContinuityEpistemicRole = Literal[
    "user_assertion",
    "assistant_inference",
    "assistant_commitment",
]

CONTINUITY_KINDS = frozenset({"referent", "unresolved", "active_task"})
CONTINUITY_EPISTEMIC_ROLES = frozenset(
    {"user_assertion", "assistant_inference", "assistant_commitment"}
)

_MISSING = object()


@dataclass(frozen=True, slots=True)
class ContinuityCandidate:
    """Model-produced proposal for bounded, non-durable cross-turn continuity."""

    kind: ContinuityKind
    key: str
    op: ContinuityOperation
    sources: tuple[str, ...]
    epistemic_role: ContinuityEpistemicRole
    value: Any = _MISSING

    def __post_init__(self) -> None:
        _validate_kind(self.kind)
        _validate_key(self.key, label="candidate key")
        if self.op not in {"set", "resolve"}:
            raise ValueError(f"unsupported continuity operation: {self.op}")
        _validate_sources(self.sources)
        _validate_epistemic_role(self.epistemic_role)
        if self.op == "set" and self.value is _MISSING:
            raise ValueError("set candidate requires value")
        if self.op == "resolve" and self.value is not _MISSING:
            raise ValueError("resolve candidate must not carry a semantic value")

    @classmethod
    def set(
        cls,
        *,
        kind: ContinuityKind,
        key: str,
        value: Any,
        sources: tuple[str, ...],
        epistemic_role: ContinuityEpistemicRole,
    ) -> "ContinuityCandidate":
        return cls(
            kind=kind,
            key=key,
            op="set",
            value=value,
            sources=sources,
            epistemic_role=epistemic_role,
        )

    @classmethod
    def resolve(
        cls,
        *,
        kind: ContinuityKind,
        key: str,
        sources: tuple[str, ...],
        epistemic_role: ContinuityEpistemicRole,
    ) -> "ContinuityCandidate":
        return cls(
            kind=kind,
            key=key,
            op="resolve",
            sources=sources,
            epistemic_role=epistemic_role,
        )

    @property
    def has_value(self) -> bool:
        return self.value is not _MISSING


@dataclass(frozen=True, slots=True)
class ContinuityItem:
    """One deterministically accepted item in temporary Continuity Context."""

    item_id: str
    kind: ContinuityKind
    key: str
    value: Any
    sources: tuple[str, ...]
    epistemic_role: ContinuityEpistemicRole
    accepted_revision: int
    expires_revision: int

    def __post_init__(self) -> None:
        if not self.item_id.strip():
            raise ValueError("item_id must not be empty")
        _validate_kind(self.kind)
        _validate_key(self.key, label="item key")
        _validate_sources(self.sources)
        _validate_epistemic_role(self.epistemic_role)
        _validate_revision(self.accepted_revision, label="accepted_revision")
        _validate_revision(self.expires_revision, label="expires_revision")
        if self.expires_revision <= self.accepted_revision:
            raise ValueError("item lifetime must advance beyond acceptance")
        object.__setattr__(self, "value", freeze_continuity_value(self.value))


@dataclass(frozen=True, slots=True)
class ContinuityContext:
    """Immutable, explicitly bounded holder for accepted temporary continuity."""

    max_items: int
    revision: int = 0
    items: tuple[ContinuityItem, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.max_items, bool) or not isinstance(self.max_items, int):
            raise TypeError("max_items must be an integer")
        if self.max_items <= 0:
            raise ValueError("max_items must be positive")
        _validate_revision(self.revision, label="context revision")
        if not isinstance(self.items, tuple):
            raise TypeError("continuity items must be a tuple")
        if not all(isinstance(item, ContinuityItem) for item in self.items):
            raise TypeError("continuity items must contain ContinuityItem values")
        if len(self.items) > self.max_items:
            raise ValueError("continuity item count exceeds max_items")
        if any(item.accepted_revision > self.revision for item in self.items):
            raise ValueError("continuity item cannot be accepted after context revision")
        if any(item.expires_revision <= self.revision for item in self.items):
            raise ValueError("continuity context must not contain expired items")


def freeze_continuity_value(value: Any) -> Any:
    """Detach and deeply freeze JSON-like semantic values for accepted authority."""

    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: freeze_continuity_value(nested) for key, nested in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(freeze_continuity_value(nested) for nested in value)
    return value


def _validate_kind(kind: str) -> None:
    if kind not in CONTINUITY_KINDS:
        raise ValueError(f"unsupported continuity kind: {kind}")


def _validate_key(key: str, *, label: str) -> None:
    if not isinstance(key, str) or not key.strip():
        raise ValueError(f"{label} must not be empty")


def _validate_sources(sources: tuple[str, ...]) -> None:
    if not isinstance(sources, tuple):
        raise TypeError("continuity sources must be a tuple")
    if not sources:
        raise ValueError("continuity sources must not be empty")
    if not all(isinstance(source, str) and source.strip() for source in sources):
        raise ValueError("continuity sources must contain non-empty strings")


def _validate_epistemic_role(role: str) -> None:
    if role not in CONTINUITY_EPISTEMIC_ROLES:
        raise ValueError(f"unsupported epistemic role: {role}")


def _validate_revision(revision: int, *, label: str) -> None:
    if isinstance(revision, bool) or not isinstance(revision, int):
        raise TypeError(f"{label} must be an integer")
    if revision < 0:
        raise ValueError(f"{label} must not be negative")
