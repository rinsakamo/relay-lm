"""Small diagnostics helpers for RelayLM MVP-0."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RequestDiagnostics:
    request_id: str
    route_model: str | None = None
    backend_model: str | None = None
    backend_name: str | None = None
    character_id: str | None = None
    mode_requested: str | None = None
    mode_applied: str | None = None
    stream_enabled: bool | None = None
    compiler_used: bool = False
    fallback_reason: str | None = None

    def to_headers(self) -> dict[str, str]:
        headers = {"x-relaylm-request-id": self.request_id}
        if self.mode_applied:
            headers["x-relaylm-mode"] = self.mode_applied
        if self.fallback_reason:
            headers["x-relaylm-fallback-reason"] = self.fallback_reason
        return headers

    def to_log_dict(self) -> dict[str, object]:
        return asdict(self)
