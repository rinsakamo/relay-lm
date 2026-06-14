"""Content-free local JSONL audit trace helpers for RelayLM."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from relaylm.audit_projection import project_audit_metadata

AUDIT_TRACE_SCHEMA_VERSION = "relaylm.audit_trace.v1"

@dataclass(frozen=True)
class TraceRecord:
    """One content-free audit record.

    The persisted schema deliberately has no messages, response text, snippet,
    evidence, tool payload, or local path fields.
    """

    trace_id: str
    request_id: str
    created_at: str
    character_id: str | None
    route_model: str | None
    mode_applied: str | None
    compiler_used: bool
    message_count: int
    response_present: bool
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = AUDIT_TRACE_SCHEMA_VERSION
    content_free: bool = True

    def to_json_dict(self) -> dict[str, Any]:
        # Explicit serialization allowlist: adding a future dataclass field does
        # not make it persistent by accident.
        return {
            "schema_version": AUDIT_TRACE_SCHEMA_VERSION,
            "content_free": True,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "created_at": self.created_at,
            "character_id": self.character_id,
            "route_model": self.route_model,
            "mode_applied": self.mode_applied,
            "compiler_used": bool(self.compiler_used),
            "message_count": max(0, int(self.message_count)),
            "response_present": bool(self.response_present),
            "metadata": dict(self.metadata),
        }

    @property
    def messages(self) -> list[dict[str, Any]]:
        """Deprecated compatibility view; audit traces never expose messages."""

        return []

    @property
    def response_text(self) -> None:
        """Deprecated compatibility view; audit traces never expose response text."""

        return None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_trace_record(
    *,
    trace_id: str,
    character_id: str | None,
    route_model: str | None,
    mode_applied: str | None,
    compiler_used: bool,
    messages: list[dict[str, Any]] | None = None,
    response_text: str | None = None,
    message_count: int | None = None,
    response_present: bool | None = None,
    metadata: dict[str, Any] | None = None,
    created_at: str | None = None,
    request_id: str | None = None,
) -> TraceRecord:
    """Build a content-free audit record from legacy runtime inputs.

    ``messages`` and ``response_text`` remain compatibility inputs until the
    P0-A2 runtime wiring change. Their content is never stored on TraceRecord;
    only message count and response presence are retained.
    """

    sensitive_values = _collect_message_content_strings(messages)
    if isinstance(response_text, str) and response_text:
        sensitive_values.add(response_text)
    projection = project_audit_metadata(metadata, sensitive_values=sensitive_values)
    inferred_message_count = len(messages) if isinstance(messages, list) else 0
    inferred_response_present = isinstance(response_text, str)
    return TraceRecord(
        trace_id=trace_id,
        request_id=request_id or trace_id,
        created_at=created_at or utc_now_iso(),
        character_id=character_id,
        route_model=route_model,
        mode_applied=mode_applied,
        compiler_used=bool(compiler_used),
        message_count=_non_negative_int(message_count) if message_count is not None else inferred_message_count,
        response_present=bool(response_present) if response_present is not None else inferred_response_present,
        metadata=projection.metadata,
    )


def sanitize_audit_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    sensitive_values: set[str] | None = None,
) -> dict[str, Any]:
    """Project runtime metadata through the typed audit projection registry."""

    return project_audit_metadata(metadata, sensitive_values=sensitive_values).metadata


def append_trace_record(path: str | Path, record: TraceRecord) -> None:
    trace_path = Path(path)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record.to_json_dict(), ensure_ascii=False, sort_keys=True) + "\n"
    with trace_path.open("a", encoding="utf-8") as f:
        f.write(line)


def read_trace_records(path: str | Path) -> list[TraceRecord]:
    """Read audit records, discarding content from legacy trace rows."""

    trace_path = Path(path)
    if not trace_path.exists():
        return []

    records: list[TraceRecord] = []
    with trace_path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if not isinstance(payload, Mapping):
                continue
            records.append(_trace_record_from_dict(payload))
    return records


def _trace_record_from_dict(payload: Mapping[str, Any]) -> TraceRecord:
    legacy_messages = payload.get("messages")
    message_count = _non_negative_int(payload.get("message_count"))
    if message_count == 0 and isinstance(legacy_messages, list):
        message_count = len(legacy_messages)

    legacy_response = payload.get("response_text")
    response_present = payload.get("response_present") is True
    if not response_present:
        response_present = isinstance(legacy_response, str)

    sensitive_values = _collect_message_content_strings(legacy_messages)
    if isinstance(legacy_response, str) and legacy_response:
        sensitive_values.add(legacy_response)

    trace_id = str(payload.get("trace_id") or payload.get("request_id") or "")
    request_id = str(payload.get("request_id") or trace_id)
    return TraceRecord(
        trace_id=trace_id,
        request_id=request_id,
        created_at=str(payload.get("created_at") or utc_now_iso()),
        character_id=_optional_string(payload.get("character_id")),
        route_model=_optional_string(payload.get("route_model")),
        mode_applied=_optional_string(payload.get("mode_applied")),
        compiler_used=payload.get("compiler_used") is True,
        message_count=message_count,
        response_present=response_present,
        metadata=sanitize_audit_metadata(
            payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else None,
            sensitive_values=sensitive_values,
        ),
        schema_version=AUDIT_TRACE_SCHEMA_VERSION,
        content_free=True,
    )


def _non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int) and value >= 0:
        return value
    return 0


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _collect_message_content_strings(value: Any) -> set[str]:
    collected: set[str] = set()
    if isinstance(value, str):
        if value.strip():
            collected.add(value.strip())
    elif isinstance(value, Mapping):
        for raw_key, child_value in value.items():
            key = str(raw_key).strip().lower()
            if key in {"role", "type", "name", "id", "tool_call_id", "index", "object"}:
                continue
            collected.update(_collect_message_content_strings(child_value))
    elif isinstance(value, list):
        for item in value:
            collected.update(_collect_message_content_strings(item))
    return collected
