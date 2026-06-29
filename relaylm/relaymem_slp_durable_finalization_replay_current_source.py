"""Current finalized-source reconstruction helper for durable replay."""
from __future__ import annotations

from copy import deepcopy

from . import _relaymem_slp_durable_finalization_replay_impl as _impl


def reconstruct_current_finalized_source(
    evidence: _impl.RelayMEMSLPDurableFinalizationEvidence,
) -> tuple[_impl.RelayMEMSLPFinalizedTurnSourceResult | None, tuple[str, ...]]:
    seal = evidence.seal
    mapping = seal.get("finalized_turn_source") if type(seal) is dict else None
    reasons = _impl.validate_finalized_source_mapping(mapping)
    if reasons or type(mapping) is not dict:
        return None, reasons or ("durable_finalization_finalized_source_invalid",)
    try:
        messages = mapping["governed_messages"]
        if type(messages) is not list:
            raise TypeError
        formation = mapping["formation_summary_artifact"]
        if type(formation) is not dict:
            return None, ("durable_finalization_formation_summary_artifact_invalid",)
        source = _impl.RelayMEMSLPFinalizedTurnSource(
            schema_version=str(mapping["schema_version"]),
            character_id=str(mapping["character_id"]),
            run_id=str(mapping["run_id"]),
            turn_index=int(mapping["turn_index"]),
            session_id=None if mapping["session_id"] is None else str(mapping["session_id"]),
            namespace=str(mapping["namespace"]),
            source_event_kind=str(mapping["source_event_kind"]),
            source_count=int(mapping["source_count"]),
            persistence_policy_status=str(mapping["persistence_policy_status"]),
            source_lineage_artifact=deepcopy(dict(mapping["source_lineage_artifact"])),
            relayscn_scene_policy_artifact=deepcopy(dict(mapping["relayscn_scene_policy_artifact"])),
            relayemo_artifact=None if mapping["relayemo_artifact"] is None else deepcopy(dict(mapping["relayemo_artifact"])),
            governed_messages=tuple(deepcopy(dict(item)) for item in messages),
            governed_experience_artifact=deepcopy(dict(mapping["governed_experience_artifact"])),
            formation_summary_artifact=deepcopy(dict(formation)),
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return None, ("durable_finalization_finalized_source_reconstruction_failed",)
    if source.schema_version != _impl.FINALIZED_TURN_SOURCE_SCHEMA:
        return None, ("durable_finalization_finalized_source_schema_mismatch",)
    return _impl.RelayMEMSLPFinalizedTurnSourceResult(
        status="ready",
        enabled=True,
        response_finalized=True,
        source_ready=True,
        blocked_reasons=(),
        source=source,
    ), ()


__all__ = ["reconstruct_current_finalized_source"]
