"""Content-free result type for EV-1 assistant response capture."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class EvidenceResponseCaptureResult:
    status: str
    blocked_reasons: tuple[str, ...] = ()
    evidence_space_id: str | None = None
    source_event_id: str | None = None
    admission_decision_id: str | None = None
    persisted: bool = False

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": "relaylm.evidence_response_capture_result.v0",
            "diagnostics_only": True,
            "content_free": True,
            "status": self.status,
            "blocked_reason_ids": list(self.blocked_reasons),
            "source_event_id_present": self.source_event_id is not None,
            "persisted": self.persisted,
        }
