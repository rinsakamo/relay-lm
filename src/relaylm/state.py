from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal


STATE_CLASS_DEFINITIONS = MappingProxyType(
    {
        "user.identity": "stable identity information explicitly stated about the user",
        "user.fact": "current factual information about the user",
        "user.preference": (
            "the user's preferences; key names a specific subject or dimension "
            "(for example tea, coffee, spicy_food, preferred_beverage) rather than a generic "
            "predicate such as likes, dislikes, or preference; value carries the preference "
            "relation or current dimension value; comparative preference does not by itself "
            "imply dislike of the weaker item or revoke an existing weaker-item liking"
        ),
        "user.goal": "a goal the user currently has",
        "user.condition": "a current condition or ongoing circumstance of the user",
        "user.experience": "an experience the user has had",
        "self.belief": "a current belief the character holds about itself",
        "self.goal": "a goal the character currently holds",
        "self.condition": "a current condition of the character",
        "relationship.state": "current qualities of the relationship",
        "relationship.commitment": "a current commitment or agreement in the relationship",
    }
)

USER_PREFERENCE_GENERIC_KEYS = frozenset({"likes", "dislikes", "preference"})

_MISSING = object()


@dataclass(frozen=True, slots=True)
class StateCandidate:
    """Model-proposed current-state existence semantics."""

    state_class: str
    key: str
    op: Literal["set", "remove"]
    sources: tuple[str, ...]
    value: Any = _MISSING

    def __post_init__(self) -> None:
        if not self.state_class.strip():
            raise ValueError("state_class must not be empty")
        if not self.key.strip():
            raise ValueError("candidate key must not be empty")
        if self.op not in {"set", "remove"}:
            raise ValueError(f"unsupported candidate op: {self.op}")
        if self.op == "set" and self.value is _MISSING:
            raise ValueError("set candidate requires value")
        if self.op == "remove" and self.value is not _MISSING:
            raise ValueError("remove candidate must not carry a semantic value")
        if not all(isinstance(source, str) and source.strip() for source in self.sources):
            raise ValueError("candidate sources must contain non-empty strings")

    @classmethod
    def set(
        cls,
        *,
        state_class: str,
        key: str,
        value: Any,
        sources: tuple[str, ...],
    ) -> "StateCandidate":
        return cls(
            state_class=state_class,
            key=key,
            op="set",
            value=value,
            sources=sources,
        )

    @classmethod
    def remove(
        cls,
        *,
        state_class: str,
        key: str,
        sources: tuple[str, ...],
    ) -> "StateCandidate":
        return cls(
            state_class=state_class,
            key=key,
            op="remove",
            sources=sources,
        )

    @property
    def has_value(self) -> bool:
        return self.value is not _MISSING


@dataclass(frozen=True, slots=True)
class StateRecord:
    """One accepted current-state record."""

    state_id: str
    state_class: str
    key: str
    value: Any
    sources: tuple[str, ...] = ()
    status: str = "active"
    valid_from: str | None = None
    valid_to: str | None = None

    def __post_init__(self) -> None:
        if not self.state_id.strip():
            raise ValueError("state_id must not be empty")
        if not self.state_class.strip():
            raise ValueError("state_class must not be empty")
        if not self.key.strip():
            raise ValueError("state key must not be empty")
        if not self.status.strip():
            raise ValueError("state status must not be empty")


@dataclass(frozen=True, slots=True)
class CanonicalState:
    """The accepted current understanding for a character."""

    format_version: int = 1
    states: tuple[StateRecord, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.format_version != 1:
            raise ValueError(f"unsupported state format_version: {self.format_version}")
