"""Shared reason_id normalization helpers."""
from __future__ import annotations

import re
from typing import Literal

InvalidReasonPolicy = Literal["drop", "marker"]
ReasonIdOutput = Literal["list", "tuple"]

_REASON_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_:-]{0,127}$")
_MAX_REASON_IDS = 32


def normalize_reason_ids(
    values: object,
    *,
    invalid: InvalidReasonPolicy = "drop",
    marker: str = "invalid_reason_id",
    output: ReasonIdOutput = "list",
    maximum: int = _MAX_REASON_IDS,
) -> list[str] | tuple[str, ...]:
    """Normalize bounded reason identifiers while preserving caller policy.

    Invalid entries are either dropped or represented by one marker, depending
    on the explicit caller policy. The function preserves first-seen order and
    deduplicates accepted values.
    """

    if invalid not in {"drop", "marker"}:
        raise ValueError("invalid reason_id policy")
    if output not in {"list", "tuple"}:
        raise ValueError("invalid reason_id output shape")
    if type(maximum) is not int or maximum < 0:
        raise ValueError("invalid reason_id maximum")
    if (
        invalid == "marker"
        and (type(marker) is not str or _REASON_ID_RE.fullmatch(marker) is None)
    ):
        raise ValueError("invalid reason_id marker")

    normalized: list[str] = []
    if isinstance(values, (str, bytes, bytearray)):
        iterator = iter((values,))
    else:
        try:
            iterator = iter(values)  # type: ignore[arg-type]
        except TypeError:
            iterator = iter((values,))

    for value in iterator:
        if type(value) is str and _REASON_ID_RE.fullmatch(value) is not None:
            reason = value
        elif invalid == "marker":
            reason = marker
        else:
            continue
        if reason not in normalized:
            normalized.append(reason)
        if len(normalized) >= maximum:
            break

    if output == "tuple":
        return tuple(normalized)
    return normalized


__all__ = ["InvalidReasonPolicy", "ReasonIdOutput", "normalize_reason_ids"]
