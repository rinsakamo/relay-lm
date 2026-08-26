from __future__ import annotations

import math
from collections.abc import Mapping
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
            "relation or current dimension value; degree_hint is intensity, not confidence; "
            "comparative preference does not by itself imply dislike of the weaker item or "
            "revoke an existing weaker-item liking; when the weaker subject already has a "
            "positive preference State, keep that State unless the current Input explicitly "
            "denies or revokes it, and represent the stronger subject and any category-level "
            "preference with separate specific keys"
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


def is_state_json_value(value: Any) -> bool:
    """Return whether a State value belongs to the stable JSON semantic domain."""

    return _is_state_json_shape(value, require_finite_numbers=True)


def _has_stable_state_json_shape(value: Any) -> bool:
    """Reject Python-only shapes that JSON persistence would silently coerce."""

    return _is_state_json_shape(value, require_finite_numbers=False)


def _is_state_json_shape(value: Any, *, require_finite_numbers: bool) -> bool:
    if value is None or isinstance(value, (str, bool)):
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return not require_finite_numbers or math.isfinite(value)
    if isinstance(value, list):
        return all(
            _is_state_json_shape(item, require_finite_numbers=require_finite_numbers)
            for item in value
        )
    if isinstance(value, dict):
        return all(
            isinstance(key, str)
            and _is_state_json_shape(item, require_finite_numbers=require_finite_numbers)
            for key, item in value.items()
        )
    return False


def _degree_hint_rejection(value: object) -> str | None:
    """Validate the reserved optional semantic degree-hint envelope without inferring meaning."""

    if not isinstance(value, Mapping):
        return None
    if "semantic" not in value and "degree_hint" not in value:
        return None
    if set(value) != {"semantic", "degree_hint"}:
        return "invalid_degree_hint_value"

    semantic = value.get("semantic")
    degree = value.get("degree_hint")
    if not isinstance(semantic, str) or not semantic.strip():
        return "invalid_degree_hint_value"
    if isinstance(degree, bool) or not isinstance(degree, (int, float)):
        return "invalid_degree_hint_value"
    if not math.isfinite(float(degree)) or not 0.0 <= float(degree) <= 1.0:
        return "invalid_degree_hint_value"
    return None


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
        if self.state_class not in STATE_CLASS_DEFINITIONS:
            raise ValueError(f"unsupported state_class: {self.state_class}")
        if not self.key.strip():
            raise ValueError("state key must not be empty")
        if (
            self.state_class == "user.preference"
            and self.key.strip().casefold() in USER_PREFERENCE_GENERIC_KEYS
        ):
            raise ValueError(f"generic preference key: {self.key}")
        if _degree_hint_rejection(self.value) is not None:
            raise ValueError("invalid degree hint value")
        if not _has_stable_state_json_shape(self.value):
            raise ValueError("state value must have stable JSON persistence shape")
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

        active_slots: set[tuple[str, str]] = set()
        for record in self.states:
            if record.status != "active" or record.valid_to is not None:
                continue
            slot = (record.state_class, record.key)
            if slot in active_slots:
                raise ValueError(
                    "duplicate active state slot: "
                    f"{record.state_class}/{record.key}"
                )
            active_slots.add(slot)
