"""Request scope identity extraction helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RequestScopeIdentity:
    user_id: str | None
    user_type: str | None
    room_id: str | None
    scene_id: str | None
    session_id: str | None
    source: str
    missing_fields: list[str]

    def to_log_dict(self) -> dict[str, object]:
        return asdict(self)


def _clean_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def extract_request_scope_identity(
    headers: Mapping[str, str] | None,
    payload: Mapping[str, Any] | None,
) -> RequestScopeIdentity:
    headers_map = headers or {}
    metadata: Mapping[str, Any] = {}
    if isinstance(payload, Mapping):
        raw_meta = payload.get("metadata")
        if isinstance(raw_meta, Mapping):
            metadata = raw_meta

    keys = ("user_id", "user_type", "room_id", "scene_id", "session_id")
    header_names = {
        "user_id": "x-relaylm-user-id",
        "user_type": "x-relaylm-user-type",
        "room_id": "x-relaylm-room-id",
        "scene_id": "x-relaylm-scene-id",
        "session_id": "x-relaylm-session-id",
    }
    values: dict[str, str | None] = {}
    used_header = False
    used_metadata = False
    for key in keys:
        h = _clean_str(headers_map.get(header_names[key]))
        if h is not None:
            values[key] = h
            used_header = True
            continue
        m = _clean_str(metadata.get(key))
        if m is not None:
            values[key] = m
            used_metadata = True
            continue
        values[key] = None

    if used_header and used_metadata:
        source = "mixed"
    elif used_header:
        source = "headers"
    elif used_metadata:
        source = "metadata"
    else:
        source = "missing"

    missing_fields = [key for key in keys if values[key] is None]
    return RequestScopeIdentity(
        user_id=values["user_id"],
        user_type=values["user_type"],
        room_id=values["room_id"],
        scene_id=values["scene_id"],
        session_id=values["session_id"],
        source=source,
        missing_fields=missing_fields,
    )

