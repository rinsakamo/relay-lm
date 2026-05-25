"""Request scope identity extraction helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from relaylm.routing import ResolvedRoute


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


@dataclass(frozen=True)
class ScopeResolutionDiagnostics:
    resolution_status: str
    merged_scope: dict[str, str | None]
    route_scope: dict[str, str | None]
    request_scope: dict[str, str | None]
    conflict_fields: list[str]
    request_override_fields: list[str]
    request_fill_fields: list[str]
    missing_fields: list[str]
    source: str

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


def build_scope_resolution_diagnostics(
    route: ResolvedRoute,
    request_scope: RequestScopeIdentity,
) -> ScopeResolutionDiagnostics:
    keys = ("user_id", "user_type", "room_id", "scene_id", "session_id")
    route_scope: dict[str, str | None] = {key: getattr(route, key) for key in keys}
    request_scope_values: dict[str, str | None] = {key: getattr(request_scope, key) for key in keys}
    merged_scope: dict[str, str | None] = {}
    conflict_fields: list[str] = []
    request_override_fields: list[str] = []
    request_fill_fields: list[str] = []
    missing_fields: list[str] = []

    for key in keys:
        route_value = route_scope[key]
        request_value = request_scope_values[key]
        if route_value is not None and request_value is None:
            merged_scope[key] = route_value
        elif route_value is None and request_value is not None:
            merged_scope[key] = request_value
            request_fill_fields.append(key)
        elif route_value is not None and request_value is not None:
            merged_scope[key] = route_value
            if route_value != request_value:
                conflict_fields.append(key)
                request_override_fields.append(key)
        else:
            merged_scope[key] = None
            missing_fields.append(key)

    if conflict_fields:
        resolution_status = "conflict"
    elif missing_fields:
        resolution_status = "partial"
    else:
        resolution_status = "ok"

    return ScopeResolutionDiagnostics(
        resolution_status=resolution_status,
        merged_scope=merged_scope,
        route_scope=route_scope,
        request_scope=request_scope_values,
        conflict_fields=conflict_fields,
        request_override_fields=request_override_fields,
        request_fill_fields=request_fill_fields,
        missing_fields=missing_fields,
        source=request_scope.source,
    )
