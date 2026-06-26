"""Public I1-GD bounded retention, isolation, and cleanup authority.

The implementation is isolated in a private module. This facade owns safe
configuration admission plus the pure completion-proof and inventory seams that
must stay aligned with I1-GC and the configured I1-G record-count authority.
"""
from __future__ import annotations

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
    if dispatch is None or dispatch.durable_job is None or payload is None or source is None:
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


# The private implementation performs global lookups at call time. These are
# deliberate production dependency seams, analogous to the I1-GC public facade.
_impl._inventory = _bounded_inventory
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
