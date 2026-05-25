"""Small diagnostics helpers for RelayLM MVP-0."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


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
    memory_block_used: bool = False
    memory_source: str | None = None
    memory_selection_summary: dict[str, Any] | None = None
    memory_block_assembly: dict[str, Any] | None = None
    token_memory_dry_run: dict[str, Any] | None = None
    token_policy_signal: dict[str, Any] | None = None
    token_policy_decision: dict[str, Any] | None = None
    token_policy_readiness: dict[str, Any] | None = None
    token_budget_truncation: dict[str, Any] | None = None
    stable_prefix_hash: str | None = None
    stable_prefix_block_ids: list[str] | None = None
    memory_adapter_dry_run: dict[str, Any] | None = None
    memory_adapter_readiness: dict[str, Any] | None = None
    memory_adapter_conflicts: dict[str, Any] | None = None
    request_scope_identity: dict[str, Any] | None = None
    scope_resolution_diagnostics: dict[str, Any] | None = None
    memory_adapter_shadow_dry_run: dict[str, Any] | None = None
    memory_adapter_shadow_readiness: dict[str, Any] | None = None
    memory_adapter_shadow_conflicts: dict[str, Any] | None = None
    trace_enabled: bool = False
    profile_compile_dry_run_enabled: bool | None = None
    profile_compile_fallback_reason: str | None = None
    fallback_reason: str | None = None

    def to_headers(self) -> dict[str, str]:
        headers = {"x-relaylm-request-id": self.request_id}
        if self.mode_applied:
            headers["x-relaylm-mode"] = self.mode_applied
        headers["x-relaylm-compiler-used"] = "true" if self.compiler_used else "false"
        headers["x-relaylm-memory-block-used"] = "true" if self.memory_block_used else "false"
        if self.memory_source:
            headers["x-relaylm-memory-source"] = self.memory_source
        headers["x-relaylm-trace-enabled"] = "true" if self.trace_enabled else "false"
        if self.profile_compile_dry_run_enabled is not None:
            headers["x-relaylm-profile-compile-dry-run"] = (
                "true" if self.profile_compile_dry_run_enabled else "false"
            )
        if self.profile_compile_fallback_reason:
            headers["x-relaylm-profile-compile-fallback-reason"] = (
                self.profile_compile_fallback_reason
            )
        if self.fallback_reason:
            headers["x-relaylm-fallback-reason"] = self.fallback_reason
        return headers

    def to_log_dict(self) -> dict[str, object]:
        return asdict(self)
