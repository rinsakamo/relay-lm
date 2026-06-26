"""Public I1-GD bounded retention, isolation, and cleanup authority.

The implementation is isolated in a private module. This facade owns safe
configuration admission plus the pure completion-proof, inventory, and
post-isolation consistency seams that must stay aligned with I1-GC and I1-GB.
"""
from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

from . import _relaymem_slp_durable_finalization_replay_impl as _replay
from . import _relaymem_slp_durable_finalization_retention_impl as _impl
from .config import RelayLMConfig
from .relaymem_slp_durable_finalization_record import canonical_json_bytes

RETENTION_PROJECTION_SCHEMA = _impl.RETENTION_PROJECTION_SCHEMA
RelayMEMSLPDurableFinalizationRetentionResult = (
    _impl.RelayMEMSLPDurableFinalizationRetentionResult
)

_original_inventory = _impl._inventory
_original_classify_locator = _impl._classify_locator
_ISOLATION_REASON_IDS = {
    "expired_incomplete_orphan": {"incomplete_orphan_expired"},
    "complete_retention_expired": {"completed_retention_expired"},
    "corrupt_known_locator": {
        "corrupt_known_record",
        "base_missing_corrupt_orphan",
        "segment_order_corrupt_orphan",
        "segment_chain_corrupt_orphan",
        "seal_evidence_mismatch",
        "completion_without_valid_seal",
    },
    "unsupported_known_locator": {"unsupported_known_schema"},
}
_COMPONENT_FLAG_NAMES = (
    "base_present",
    "segment_present",
    "seal_present",
    "completion_present",
)


def _bounded_inventory(root_fd: int, settings: Any) -> Any:
    """Apply the configured logical-record count bound after complete scan."""

    inventory = _original_inventory(root_fd, settings)
    if inventory.complete and len(inventory.groups) > settings.max_record_count:
        return _impl._Inventory(
            complete=False,
            entry_count=inventory.entry_count,
            groups=inventory.groups,
            reason_ids=(
                "durable_finalization_retention_record_capacity_exceeded",
            ),
            capacity_exceeded=True,
        )
    return inventory


def _hardened_classify_locator(
    root_fd: int,
    locator: str,
    settings: Any,
    now: float,
) -> Any:
    """Reject components that appeared or changed ownership after isolation."""

    classified = _original_classify_locator(root_fd, locator, settings, now)
    isolation = classified.isolation
    if (
        classified.blocked
        or isolation.status != "loaded"
        or not classified.component_names
    ):
        return classified
    marker = isolation.marker
    if type(marker) is not dict or type(isolation.mtime_ns) is not int:
        return _impl._blocked_classification(
            "unsafe_or_unclassifiable",
            "durable_finalization_isolation_state_invalid",
            classified.flags,
            classified.component_names,
            isolation,
        )
    marker_classification = marker.get("classification")
    marker_reason = marker.get("reason_id")
    allowed_reasons = _ISOLATION_REASON_IDS.get(marker_classification)
    if allowed_reasons is None or marker_reason not in allowed_reasons:
        return _impl._blocked_classification(
            "ambiguous",
            "durable_finalization_isolation_authority_invalid",
            classified.flags,
            classified.component_names,
            isolation,
        )
    observed = marker.get("observed_component_flags")
    if type(observed) is not dict:
        return _impl._blocked_classification(
            "unsafe_or_unclassifiable",
            "durable_finalization_isolation_flags_invalid",
            classified.flags,
            classified.component_names,
            isolation,
        )
    for flag_name in _COMPONENT_FLAG_NAMES:
        if classified.flags.get(flag_name) is True and observed.get(flag_name) is not True:
            return _impl._blocked_classification(
                "ambiguous",
                "durable_finalization_component_reappeared_after_isolation",
                classified.flags,
                classified.component_names,
                isolation,
            )
    for name in classified.component_names:
        try:
            info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        except OSError:
            return _impl._blocked_classification(
                "unsafe_or_unclassifiable",
                "durable_finalization_component_unreadable",
                classified.flags,
                classified.component_names,
                isolation,
            )
        if info.st_mtime_ns > isolation.mtime_ns:
            return _impl._blocked_classification(
                "ambiguous",
                "durable_finalization_component_newer_than_isolation",
                classified.flags,
                classified.component_names,
                isolation,
            )
    return classified


def _exact_completion_collision_reason(
    completion: dict[str, object],
    seal: dict[str, object],
) -> str | None:
    """Rebuild the exact I1-GC completion proof from validated sealed evidence."""

    evidence = SimpleNamespace(seal=seal)
    source_result, source_reasons = _replay._reconstruct_source(evidence)
    if source_result is None or source_reasons:
        return "durable_finalization_completion_identity_collision"
    preparation = _replay.prepare_relaymem_slp_runtime_enqueue(source_result)
    if preparation.status != "dry_run_ready":
        return "durable_finalization_completion_identity_collision"
    identity_reasons = _replay._verify_identity(evidence, preparation)
    if identity_reasons:
        return "durable_finalization_completion_identity_collision"
    dispatch = preparation.dispatch_result
    payload = preparation.protected_source_payload
    source = source_result.source
    if (
        dispatch is None
        or dispatch.durable_job is None
        or payload is None
        or source is None
    ):
        return "durable_finalization_completion_identity_collision"
    try:
        source_digest = _replay._source_digest(
            payload,
            dispatch.durable_job,
            source.character_id,
        )
        expected = _replay._completion_marker(
            str(seal["locator_digest"]),
            seal,
            preparation,
            source_digest,
        )
        if canonical_json_bytes(completion) != canonical_json_bytes(expected):
            return "durable_finalization_completion_identity_collision"
    except (KeyError, TypeError, ValueError, RecursionError, OverflowError):
        return "durable_finalization_completion_identity_collision"
    return None


def _public_bound_reasons(config: RelayLMConfig) -> tuple[str, ...]:
    limits = (
        (
            "relaymem_slp_durable_finalization_completed_retention_seconds",
            10 * 365 * 24 * 60 * 60,
        ),
        (
            "relaymem_slp_durable_finalization_orphan_grace_seconds",
            365 * 24 * 60 * 60,
        ),
        (
            "relaymem_slp_durable_finalization_isolated_retention_seconds",
            10 * 365 * 24 * 60 * 60,
        ),
        (
            "relaymem_slp_durable_finalization_cleanup_max_records_per_pass",
            4096,
        ),
        (
            "relaymem_slp_durable_finalization_cleanup_timeout_ms",
            60_000,
        ),
    )
    reasons: list[str] = []
    for field_name, maximum in limits:
        value = getattr(config, field_name)
        if type(value) is not int or not 1 <= value <= maximum:
            reasons.append(f"{field_name}_invalid")
    return tuple(reasons)


# The private implementation performs global lookups at call time. These are
# deliberate production dependency seams, analogous to the I1-GC public facade.
_impl._inventory = _bounded_inventory
_impl._classify_locator = _hardened_classify_locator
_impl._completion_collision_reason = _exact_completion_collision_reason


def maintain_relaymem_slp_durable_finalization_retention(
    *,
    config: RelayLMConfig,
    now_provider: Any = _impl.time.time,
    fault_injector: Any = None,
) -> RelayMEMSLPDurableFinalizationRetentionResult:
    """Run one bounded maintenance pass and return without polling or sleeping."""

    if type(config) is RelayLMConfig:
        enabled = config.relaymem_slp_durable_finalization_retention_enabled
        dry = config.relaymem_slp_durable_finalization_retention_dry_run_only
        apply = config.relaymem_slp_durable_finalization_retention_apply_enabled
        if enabled is False:
            if dry is True and apply is False:
                return _impl._empty_result(
                    "disabled",
                    False,
                    True,
                    False,
                    (),
                )
            return _impl._empty_result(
                "invalid_input",
                False,
                bool(dry),
                bool(apply),
                ("durable_finalization_retention_gate_invalid",),
            )
        bound_reasons = _public_bound_reasons(config)
        if bound_reasons:
            return _impl._empty_result(
                "invalid_input",
                bool(enabled),
                bool(dry),
                bool(apply),
                bound_reasons,
            )
    return _impl.maintain_relaymem_slp_durable_finalization_retention(
        config=config,
        now_provider=now_provider,
        fault_injector=fault_injector,
    )


__all__ = [
    "RETENTION_PROJECTION_SCHEMA",
    "RelayMEMSLPDurableFinalizationRetentionResult",
    "maintain_relaymem_slp_durable_finalization_retention",
]
