"""Server-owned trusted Home scene-admission gate for E1-R1.

This module decides whether a SOUL Lab Home-origin ordinary conversation may use
RelayLM's existing finalized-turn source and durable queue authority.  It does
not persist source, enqueue, claim, run a worker, start a scheduler, or trust
browser-provided persistence claims.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from relaylm.config import ModelRoute, RelayLMConfig
from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from relaylm.relaymem_slp_queue_record import dedupe, is_token
from relaylm.routing import ResolvedRoute

TRUSTED_HOME_SCENE_ADMISSION_SCHEMA = "relaylm.trusted_home_scene_admission.v0"
TRUSTED_HOME_SCENE_ADMISSION_PROJECTION_SCHEMA = (
    "relaylm.trusted_home_scene_admission_projection.v0"
)

TrustedHomeSceneAdmissionStatus = Literal[
    "disabled",
    "dry_run_ready",
    "accepted",
    "rejected_browser_owned_trust",
    "invalid_scene",
    "unsupported_scope",
    "missing_character_store",
    "downstream_existing_admission_failure",
]

_BROWSER_TRUST_KEYS = {
    "trusted_scene_admission",
    "trusted_home_scene_admission",
    "relaylm_trusted_scene_admission",
    "relaylm_trusted_home_scene_admission",
    "relaymem_trusted_scene_admission",
    "memory_persistence_trust",
    "persistence_trust",
}
_BROWSER_TRUST_HEADERS = {
    "x-relaylm-trusted-scene-admission",
    "x-relaylm-trusted-home-scene-admission",
    "x-relaylm-memory-persistence-trust",
}


@dataclass(frozen=True)
class TrustedHomeSceneAdmissionDecision:
    """Content-free result of the server-owned E1-R1 admission decision."""

    status: TrustedHomeSceneAdmissionStatus
    mode: str
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    route_owned: bool
    browser_trust_rejected: bool
    scene_supported: bool
    scope_supported: bool
    character_store_available: bool
    downstream_ready: bool
    blocked_reasons: tuple[str, ...]

    @property
    def admitted(self) -> bool:
        return self.status in {"dry_run_ready", "accepted"}

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": TRUSTED_HOME_SCENE_ADMISSION_PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "raw_text_included": False,
            "raw_messages_included": False,
            "raw_scene_payload_included": False,
            "identifier_values_included": False,
            "namespace_value_included": False,
            "store_path_included": False,
            "queue_path_included": False,
            "protected_source_path_included": False,
            "job_id_included": False,
            "dispatch_id_included": False,
            "lease_token_included": False,
            "exception_text_included": False,
            "exact_timestamp_included": False,
            "status": self.status,
            "mode": self.mode,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "apply_enabled": self.apply_enabled,
            "route_owned": self.route_owned,
            "browser_trust_rejected": self.browser_trust_rejected,
            "scene_supported": self.scene_supported,
            "scope_supported": self.scope_supported,
            "character_store_available": self.character_store_available,
            "downstream_ready": self.downstream_ready,
            "worker_invoked": False,
            "queue_io_performed": False,
            "writes_memory": False,
            "changes_visible_response": False,
            "blocked_reason_ids": list(self.blocked_reasons),
        }


def resolve_trusted_home_scene_admission(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
    payload: Mapping[str, Any] | None,
    headers: Mapping[str, str] | None = None,
) -> TrustedHomeSceneAdmissionDecision:
    """Resolve one route-owned Home admission decision without trusting the browser."""

    route_cfg = _route_config(config, route)
    mode = (
        route_cfg.trusted_home_scene_admission_mode
        if route_cfg is not None
        else "disabled"
    )
    if _browser_asserts_trust(payload, headers):
        return _decision(
            "rejected_browser_owned_trust",
            mode=mode,
            enabled=False,
            dry_run_only=True,
            apply_enabled=False,
            route_owned=route_cfg is not None,
            browser_trust_rejected=True,
            scene_supported=False,
            scope_supported=False,
            character_store_available=False,
            downstream_ready=False,
            blocked_reasons=("browser_owned_trust_rejected",),
        )
    if route_cfg is None or mode == "disabled":
        return _decision(
            "disabled",
            mode="disabled",
            enabled=False,
            dry_run_only=True,
            apply_enabled=False,
            route_owned=route_cfg is not None,
        )

    expected_scene_id = route_cfg.trusted_home_scene_admission_scene_id
    if not is_token(expected_scene_id):
        return _decision(
            "invalid_scene",
            mode=mode,
            enabled=True,
            dry_run_only=True,
            apply_enabled=False,
            route_owned=True,
            scene_supported=False,
            blocked_reasons=("configured_home_scene_invalid",),
        )
    if route.scene_id != expected_scene_id:
        return _decision(
            "invalid_scene",
            mode=mode,
            enabled=True,
            dry_run_only=True,
            apply_enabled=False,
            route_owned=True,
            scene_supported=False,
            blocked_reasons=("route_scene_not_home",),
        )

    scope_reasons = _scope_reasons(route)
    if scope_reasons:
        return _decision(
            "unsupported_scope",
            mode=mode,
            enabled=True,
            dry_run_only=True,
            apply_enabled=False,
            route_owned=True,
            scene_supported=True,
            scope_supported=False,
            blocked_reasons=scope_reasons,
        )

    if not _character_store_available(config, route):
        return _decision(
            "missing_character_store",
            mode=mode,
            enabled=True,
            dry_run_only=True,
            apply_enabled=False,
            route_owned=True,
            scene_supported=True,
            scope_supported=True,
            character_store_available=False,
            blocked_reasons=("character_store_unavailable",),
        )

    downstream_reasons = _downstream_reasons(config, mode)
    if downstream_reasons:
        return _decision(
            "downstream_existing_admission_failure",
            mode=mode,
            enabled=True,
            dry_run_only=True,
            apply_enabled=False,
            route_owned=True,
            scene_supported=True,
            scope_supported=True,
            character_store_available=True,
            downstream_ready=False,
            blocked_reasons=downstream_reasons,
        )

    if mode == "dry_run":
        return _decision(
            "dry_run_ready",
            mode=mode,
            enabled=True,
            dry_run_only=True,
            apply_enabled=False,
            route_owned=True,
            scene_supported=True,
            scope_supported=True,
            character_store_available=True,
            downstream_ready=True,
        )
    return _decision(
        "accepted",
        mode=mode,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
        route_owned=True,
        scene_supported=True,
        scope_supported=True,
        character_store_available=True,
        downstream_ready=True,
    )


def trusted_home_scene_runtime_gate(
    config: RelayLMConfig,
    decision: TrustedHomeSceneAdmissionDecision,
) -> tuple[bool, bool, bool]:
    """Return effective existing-runtime enqueue gates for one finalized turn."""

    explicit_existing_lane = bool(
        config.relaymem_slp_runtime_enqueue_enabled
        and not config.trusted_home_scene_admission_runtime_trigger_enabled
    )
    if explicit_existing_lane:
        return (
            config.relaymem_slp_runtime_enqueue_enabled,
            config.relaymem_slp_runtime_enqueue_dry_run_only,
            config.relaymem_slp_runtime_enqueue_apply_enabled,
        )
    if decision.status == "accepted":
        return True, False, True
    if decision.status == "dry_run_ready":
        return True, True, False
    return False, True, False


def build_trusted_home_scene_admission_node_result(
    decision: TrustedHomeSceneAdmissionDecision,
) -> PipelineNodeResult:
    status = {
        "disabled": "skipped",
        "dry_run_ready": "diagnostic_only",
        "accepted": "diagnostic_only",
        "rejected_browser_owned_trust": "blocked",
        "invalid_scene": "blocked",
        "unsupported_scope": "blocked",
        "missing_character_store": "blocked",
        "downstream_existing_admission_failure": "failed",
    }[decision.status]
    return build_pipeline_node_result(
        node_name="trusted_home_scene_admission",
        status=status,
        decision=decision.status,
        blocked_reasons=decision.blocked_reasons,
        diagnostics=decision.to_log_dict(),
        artifacts=[
            {
                "artifact_name": "trusted_home_scene_admission",
                "schema_version": TRUSTED_HOME_SCENE_ADMISSION_SCHEMA,
                "present": decision.enabled,
                "content_free": True,
                "runtime_private": False,
                "source_omitted": True,
                "raw_messages_included": False,
                "raw_scene_payload_included": False,
                "identifier_values_included": False,
                "queue_io_performed": False,
                "worker_invoked": False,
                "writes_memory": False,
                "changes_visible_response": False,
            }
        ],
    )


def _route_config(config: RelayLMConfig, route: ResolvedRoute) -> ModelRoute | None:
    route_cfg = config.model_routes.get(route.route_model)
    return route_cfg if type(route_cfg) is ModelRoute else None


def _browser_asserts_trust(
    payload: Mapping[str, Any] | None,
    headers: Mapping[str, str] | None,
) -> bool:
    if headers is not None:
        for key in headers:
            if isinstance(key, str) and key.lower() in _BROWSER_TRUST_HEADERS:
                return True
    if not isinstance(payload, Mapping):
        return False
    for key in payload:
        if isinstance(key, str) and key in _BROWSER_TRUST_KEYS:
            return True
    metadata = payload.get("metadata")
    if isinstance(metadata, Mapping):
        for key in metadata:
            if isinstance(key, str) and key in _BROWSER_TRUST_KEYS:
                return True
    return False


def _scope_reasons(route: ResolvedRoute) -> tuple[str, ...]:
    reasons: list[str] = []
    if route.mode_applied == "pass_through":
        reasons.append("pass_through_route_exempt")
    if not is_token(route.character_id):
        reasons.append("character_id_invalid")
    if not is_token(route.memory_namespace):
        reasons.append("memory_namespace_invalid")
    return tuple(reasons)


def _character_store_available(config: RelayLMConfig, route: ResolvedRoute) -> bool:
    root = config.memory.root_path
    if not isinstance(root, str) or not root:
        return False
    if not is_token(route.character_id):
        return False
    store_root = Path(root) / "characters" / str(route.character_id)
    return store_root.exists() or store_root.is_symlink()


def _downstream_reasons(config: RelayLMConfig, mode: str) -> tuple[str, ...]:
    if mode == "dry_run":
        return ()
    reasons: list[str] = []
    if not _directory_available(config.relaymem_slp_queue_root):
        reasons.append("queue_root_unavailable")
    if not _directory_available(config.relaymem_slp_protected_source_root):
        reasons.append("protected_source_root_unavailable")
    return tuple(reasons)


def _directory_available(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = Path(value)
    return path.exists() and path.is_dir()


def _decision(
    status: TrustedHomeSceneAdmissionStatus,
    *,
    mode: str,
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
    route_owned: bool,
    browser_trust_rejected: bool = False,
    scene_supported: bool = False,
    scope_supported: bool = False,
    character_store_available: bool = False,
    downstream_ready: bool = False,
    blocked_reasons: tuple[str, ...] = (),
) -> TrustedHomeSceneAdmissionDecision:
    return TrustedHomeSceneAdmissionDecision(
        status=status,
        mode=mode,
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
        route_owned=route_owned,
        browser_trust_rejected=browser_trust_rejected,
        scene_supported=scene_supported,
        scope_supported=scope_supported,
        character_store_available=character_store_available,
        downstream_ready=downstream_ready,
        blocked_reasons=dedupe(blocked_reasons),
    )


__all__ = [
    "TRUSTED_HOME_SCENE_ADMISSION_PROJECTION_SCHEMA",
    "TRUSTED_HOME_SCENE_ADMISSION_SCHEMA",
    "TrustedHomeSceneAdmissionDecision",
    "build_trusted_home_scene_admission_node_result",
    "resolve_trusted_home_scene_admission",
    "trusted_home_scene_runtime_gate",
]
