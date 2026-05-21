"""Local JSONL conversation trace helpers for RelayLM MVP-3."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TraceRecord:
    trace_id: str
    created_at: str
    character_id: str | None
    route_model: str | None
    mode_applied: str | None
    compiler_used: bool
    messages: list[dict[str, Any]]
    response_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_trace_record(
    *,
    trace_id: str,
    character_id: str | None,
    route_model: str | None,
    mode_applied: str | None,
    compiler_used: bool,
    messages: list[dict[str, Any]],
    response_text: str | None = None,
    metadata: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> TraceRecord:
    return TraceRecord(
        trace_id=trace_id,
        created_at=created_at or utc_now_iso(),
        character_id=character_id,
        route_model=route_model,
        mode_applied=mode_applied,
        compiler_used=compiler_used,
        messages=list(messages),
        response_text=response_text,
        metadata=dict(metadata or {}),
    )


def append_trace_record(path: str | Path, record: TraceRecord) -> None:
    trace_path = Path(path)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record.to_json_dict(), ensure_ascii=False, sort_keys=True) + "\n"
    with trace_path.open("a", encoding="utf-8") as f:
        f.write(line)


def read_trace_records(path: str | Path) -> list[TraceRecord]:
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
            records.append(TraceRecord(**payload))
    return records
