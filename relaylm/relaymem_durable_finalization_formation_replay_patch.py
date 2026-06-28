"""Install E1-R3 formation-summary preservation for durable replay.

This module patches the durable-finalization record/replay authorities at package
initialisation time without changing the protected-source payload contract.  The
seal keeps the worker-internal formation summary as replay evidence, while legacy
v0 seals that predate the field remain replayable.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


_LEGACY_FINALIZED_SOURCE_FIELDS = frozenset({
    "schema_version", "character_id", "run_id", "turn_index", "session_id",
    "namespace", "source_event_kind", "source_count",
    "persistence_policy_status", "source_lineage_artifact",
    "relayscn_scene_policy_artifact", "relayemo_artifact",
    "governed_messages", "governed_experience_artifact",
})
_FINALIZED_SOURCE_FIELDS = frozenset({
    *_LEGACY_FINALIZED_SOURCE_FIELDS,
    "formation_summary_artifact",
})


def install_durable_finalization_formation_replay_patch() -> None:
    """Patch durable-finalization record/replay functions once per interpreter."""

    from . import relaymem_slp_durable_finalization_record as record
    from . import _relaymem_slp_durable_finalization_replay_impl as replay
    from .relaymem_slp_finalized_turn_source import (
        FINALIZED_TURN_SOURCE_SCHEMA,
        RelayMEMSLPFinalizedTurnSource,
        RelayMEMSLPFinalizedTurnSourceResult,
    )

    if getattr(record, "_FORMATION_REPLAY_PATCH_INSTALLED", False) is True:
        return

    def finalized_source_to_mapping(
        source: RelayMEMSLPFinalizedTurnSource,
    ) -> dict[str, object]:
        if type(source) is not RelayMEMSLPFinalizedTurnSource:
            raise TypeError("exact_finalized_turn_source_required")
        value: dict[str, object] = {
            "schema_version": source.schema_version,
            "character_id": source.character_id,
            "run_id": source.run_id,
            "turn_index": source.turn_index,
            "session_id": source.session_id,
            "namespace": source.namespace,
            "source_event_kind": source.source_event_kind,
            "source_count": source.source_count,
            "persistence_policy_status": source.persistence_policy_status,
            "source_lineage_artifact": record._copy_json_mapping(
                source.source_lineage_artifact
            ),
            "relayscn_scene_policy_artifact": record._copy_json_mapping(
                source.relayscn_scene_policy_artifact
            ),
            "relayemo_artifact": (
                record._copy_json_mapping(source.relayemo_artifact)
                if source.relayemo_artifact is not None
                else None
            ),
            "governed_messages": [
                record._copy_json_mapping(item) for item in source.governed_messages
            ],
            "governed_experience_artifact": record._copy_json_mapping(
                source.governed_experience_artifact
            ),
            "formation_summary_artifact": record._copy_json_mapping(
                source.formation_summary_artifact
            ),
        }
        reasons = validate_finalized_source_mapping(value)
        if reasons:
            raise ValueError(reasons[0])
        return value

    def validate_finalized_source_mapping(value: object) -> tuple[str, ...]:
        if type(value) is not dict:
            return ("durable_finalization_finalized_source_shape_invalid",)
        reasons: list[str] = []
        fields = frozenset(value)
        if fields not in {_FINALIZED_SOURCE_FIELDS, _LEGACY_FINALIZED_SOURCE_FIELDS}:
            reasons.append("durable_finalization_finalized_source_shape_mismatch")
        if value.get("schema_version") != FINALIZED_TURN_SOURCE_SCHEMA:
            reasons.append("durable_finalization_finalized_source_schema_mismatch")
        reasons.extend(
            record.validate_correlation(
                value.get("run_id"), value.get("turn_index"), value.get("character_id")
            )
        )
        if not record.is_token(value.get("namespace")):
            reasons.append("durable_finalization_finalized_source_namespace_invalid")
        if value.get("source_event_kind") != "turn":
            reasons.append("durable_finalization_finalized_source_event_invalid")
        if type(value.get("source_count")) is not int or value.get("source_count") < 1:
            reasons.append("durable_finalization_finalized_source_count_invalid")
        if type(value.get("governed_messages")) is not list:
            reasons.append("durable_finalization_governed_messages_invalid")
        for key in (
            "source_lineage_artifact",
            "relayscn_scene_policy_artifact",
            "governed_experience_artifact",
        ):
            if type(value.get(key)) is not dict:
                reasons.append(f"durable_finalization_{key}_invalid")
        if "formation_summary_artifact" in value and type(
            value.get("formation_summary_artifact")
        ) is not dict:
            reasons.append("durable_finalization_formation_summary_artifact_invalid")
        if value.get("relayemo_artifact") is not None and type(
            value.get("relayemo_artifact")
        ) is not dict:
            reasons.append("durable_finalization_relayemo_artifact_invalid")
        return record.dedupe(tuple(reasons))

    def reconstruct_source(
        evidence: record.RelayMEMSLPDurableFinalizationEvidence,
    ) -> tuple[RelayMEMSLPFinalizedTurnSourceResult | None, tuple[str, ...]]:
        seal = evidence.seal
        mapping = seal.get("finalized_turn_source") if type(seal) is dict else None
        reasons = validate_finalized_source_mapping(mapping)
        if reasons or type(mapping) is not dict:
            return None, reasons or ("durable_finalization_finalized_source_invalid",)
        try:
            messages = mapping["governed_messages"]
            if type(messages) is not list:
                raise TypeError
            formation = mapping.get("formation_summary_artifact", {})
            if type(formation) is not dict:
                raise TypeError
            source = RelayMEMSLPFinalizedTurnSource(
                schema_version=str(mapping["schema_version"]),
                character_id=str(mapping["character_id"]),
                run_id=str(mapping["run_id"]),
                turn_index=int(mapping["turn_index"]),
                session_id=(
                    None
                    if mapping["session_id"] is None
                    else str(mapping["session_id"])
                ),
                namespace=str(mapping["namespace"]),
                source_event_kind=str(mapping["source_event_kind"]),
                source_count=int(mapping["source_count"]),
                persistence_policy_status=str(mapping["persistence_policy_status"]),
                source_lineage_artifact=deepcopy(
                    dict(mapping["source_lineage_artifact"])
                ),
                relayscn_scene_policy_artifact=deepcopy(
                    dict(mapping["relayscn_scene_policy_artifact"])
                ),
                relayemo_artifact=(
                    None
                    if mapping["relayemo_artifact"] is None
                    else deepcopy(dict(mapping["relayemo_artifact"]))
                ),
                governed_messages=tuple(deepcopy(dict(item)) for item in messages),
                governed_experience_artifact=deepcopy(
                    dict(mapping["governed_experience_artifact"])
                ),
                formation_summary_artifact=deepcopy(dict(formation)),
            )
        except (KeyError, TypeError, ValueError, OverflowError):
            return None, ("durable_finalization_finalized_source_reconstruction_failed",)
        if source.schema_version != FINALIZED_TURN_SOURCE_SCHEMA:
            return None, ("durable_finalization_finalized_source_schema_mismatch",)
        return RelayMEMSLPFinalizedTurnSourceResult(
            status="ready",
            enabled=True,
            response_finalized=True,
            source_ready=True,
            blocked_reasons=(),
            source=source,
        ), ()

    record.FINALIZED_SOURCE_FIELDS = _FINALIZED_SOURCE_FIELDS
    record.FINALIZED_SOURCE_LEGACY_FIELDS = _LEGACY_FINALIZED_SOURCE_FIELDS
    record.finalized_source_to_mapping = finalized_source_to_mapping
    record.validate_finalized_source_mapping = validate_finalized_source_mapping
    record._FORMATION_REPLAY_PATCH_INSTALLED = True

    replay.validate_finalized_source_mapping = validate_finalized_source_mapping
    replay._reconstruct_source = reconstruct_source


__all__ = ["install_durable_finalization_formation_replay_patch"]
