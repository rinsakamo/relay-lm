"""RelayREL content-free relationship projection placeholder.

This module intentionally does not parse relationship Markdown yet. It provides a
small diagnostics-only projection so runtime ordering can reserve RelayREL before
RelaySCN while the file-first Character Workspace parser/compiler remains
unimplemented.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from relaylm.routing import ResolvedRoute


def build_relayrel_relationship_projection(
    *,
    route: ResolvedRoute | None = None,
    request_scope_identity: Mapping[str, Any] | object | None = None,
) -> dict[str, Any]:
    """Build a content-free RelayREL placeholder projection.

    The projection only reports route/scope presence flags and placeholder
    policy status. It must not expose raw messages, relationship bodies, memory
    bodies, private state, or assistant output.
    """

    scope = _scope_mapping(request_scope_identity)
    target_character_present = bool(getattr(route, "character_id", None))
    target_namespace_present = bool(getattr(route, "memory_namespace", None))
    scope_session_present = bool(scope.get("session_id"))

    return {
        "schema_version": "relayrel.relationship_projection.v0",
        "diagnostics_only": True,
        "content_free": True,
        "relationship_source": "route_scope",
        "relationship_policy_status": "placeholder",
        "target_character_id_present": target_character_present,
        "target_namespace_present": target_namespace_present,
        "request_session_id_present": scope_session_present,
        "workspace_source_files_read": False,
        "raw_relationship_content_present": False,
    }


def _scope_mapping(value: Mapping[str, Any] | object | None) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if value is None:
        return {}
    result: dict[str, Any] = {}
    for name in ("character_id", "memory_namespace", "cache_namespace", "session_id"):
        item = getattr(value, name, None)
        if item is not None:
            result[name] = item
    return result
