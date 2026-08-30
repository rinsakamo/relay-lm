from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from relaylm.actual_model_evaluation import (
    ActualModelEvidence,
    ActualModelRunManifest,
    ActualModelScenario,
    run_actual_model_scenario,
)
from relaylm.cognitive import CognitiveProvider
from relaylm.continuity import ContinuityContext, ContinuityItem
from relaylm.state import StateRecord
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import ContinuityRuntime


@dataclass(frozen=True, slots=True)
class ActualModelRestartRunManifest:
    """Run identity for a controlled RelayLM process-restart condition."""

    base: ActualModelRunManifest
    restart_after_turn_count: int
    continuity_max_items: int
    continuity_lifetime_revisions: int

    def __post_init__(self) -> None:
        if self.base.restart_boundary != "none":
            raise ValueError(
                "restart wrapper requires base.restart_boundary='none'; the wrapper owns the boundary"
            )
        if self.base.cognitive_budget is not None:
            raise ValueError(
                "restart evidence does not support the ordinary-turn total cognitive-budget bridge"
            )
        if self.base.cognition_pass_requests is not None:
            raise ValueError(
                "restart evidence does not support cognition pass request evidence "
                "until the restart evidence bridge is explicitly extended"
            )
        _require_positive_int(self.restart_after_turn_count, "restart_after_turn_count")
        _require_positive_int(self.continuity_max_items, "continuity_max_items")
        _require_positive_int(
            self.continuity_lifetime_revisions,
            "continuity_lifetime_revisions",
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "base": self.base.to_mapping(),
            "restart_boundary": {
                "kind": "relaylm_process_restart",
                "after_turn_count": self.restart_after_turn_count,
            },
            "continuity_runtime": {
                "max_items": self.continuity_max_items,
                "lifetime_revisions": self.continuity_lifetime_revisions,
                "persistence": "process_local_non_durable",
            },
        }


@dataclass(frozen=True, slots=True)
class RestartBoundaryObservation:
    """Authority snapshots immediately before and after RelayLM process restart."""

    state_before_restart: tuple[dict[str, object], ...]
    state_after_restart: tuple[dict[str, object], ...]
    event_ids_before_restart: tuple[str, ...]
    event_ids_after_restart: tuple[str, ...]
    continuity_before_restart: dict[str, object]
    continuity_after_restart: dict[str, object]

    def to_mapping(self) -> dict[str, object]:
        return {
            "state_before_restart": list(self.state_before_restart),
            "state_after_restart": list(self.state_after_restart),
            "event_ids_before_restart": list(self.event_ids_before_restart),
            "event_ids_after_restart": list(self.event_ids_after_restart),
            "continuity_before_restart": self.continuity_before_restart,
            "continuity_after_restart": self.continuity_after_restart,
        }


@dataclass(frozen=True, slots=True)
class ActualModelRestartEvidence:
    run_id: str
    manifest: ActualModelRestartRunManifest
    scenario: ActualModelScenario
    before_restart: ActualModelEvidence
    boundary: RestartBoundaryObservation
    after_restart: ActualModelEvidence

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": 1,
            "run_id": self.run_id,
            "manifest": self.manifest.to_mapping(),
            "scenario": self.scenario.to_mapping(),
            "before_restart": self.before_restart.to_mapping(),
            "restart_boundary_observation": self.boundary.to_mapping(),
            "after_restart": self.after_restart.to_mapping(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_mapping(), ensure_ascii=False, allow_nan=False, indent=2)


async def run_actual_model_restart_scenario(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    manifest: ActualModelRestartRunManifest,
    scenario: ActualModelScenario,
    execution_id: str | None = None,
    scenario_revision: str | None = None,
) -> ActualModelRestartEvidence:
    """Run one semantic fixture across a real persistent-Character process restart.

    Durable Character Package State/Event data remains on disk and the
    CharacterDirectory object is recreated. Process-local Continuity Context is
    deliberately replaced by a fresh empty context using the same explicit runtime
    configuration. No additional semantic model call is introduced.
    """

    if scenario.family != "restart_quality":
        raise ValueError("restart runner requires scenario.family='restart_quality'")
    split = manifest.restart_after_turn_count
    if split >= len(scenario.turns):
        raise ValueError("restart boundary must leave at least one turn after restart")

    continuity_runtime = ContinuityRuntime(
        context=ContinuityContext(max_items=manifest.continuity_max_items),
        lifetime_revisions=manifest.continuity_lifetime_revisions,
    )
    before_scenario = _phase_scenario(
        scenario=scenario,
        phase="before_restart",
        turns=scenario.turns[:split],
    )
    before = await run_actual_model_scenario(
        character=character,
        provider=provider,
        manifest=manifest.base,
        scenario=before_scenario,
        continuity_runtime=continuity_runtime,
        execution_id=execution_id,
        scenario_revision=scenario_revision,
    )

    state_before = character.load_state()
    events_before = tuple(character.iter_events())
    continuity_before = continuity_runtime.context

    restarted_character = CharacterDirectory(character.root)
    state_after = restarted_character.load_state()
    events_after = tuple(restarted_character.iter_events())
    restarted_continuity = ContinuityRuntime(
        context=ContinuityContext(max_items=manifest.continuity_max_items),
        lifetime_revisions=manifest.continuity_lifetime_revisions,
    )
    boundary = RestartBoundaryObservation(
        state_before_restart=tuple(_serialize_state_record(item) for item in state_before.states),
        state_after_restart=tuple(_serialize_state_record(item) for item in state_after.states),
        event_ids_before_restart=tuple(item.id for item in events_before),
        event_ids_after_restart=tuple(item.id for item in events_after),
        continuity_before_restart=_serialize_continuity_context(continuity_before),
        continuity_after_restart=_serialize_continuity_context(restarted_continuity.context),
    )

    after_scenario = _phase_scenario(
        scenario=scenario,
        phase="after_restart",
        turns=scenario.turns[split:],
    )
    after = await run_actual_model_scenario(
        character=restarted_character,
        provider=provider,
        manifest=manifest.base,
        scenario=after_scenario,
        continuity_runtime=restarted_continuity,
        execution_id=execution_id,
        scenario_revision=scenario_revision,
    )

    return ActualModelRestartEvidence(
        run_id=stable_actual_model_restart_run_id(manifest=manifest, scenario=scenario),
        manifest=manifest,
        scenario=scenario,
        before_restart=before,
        boundary=boundary,
        after_restart=after,
    )


def stable_actual_model_restart_run_id(
    *,
    manifest: ActualModelRestartRunManifest,
    scenario: ActualModelScenario,
) -> str:
    payload = json.dumps(
        {"manifest": manifest.to_mapping(), "scenario": scenario.to_mapping()},
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"amrr-{hashlib.sha256(payload).hexdigest()}"


def _phase_scenario(
    *, scenario: ActualModelScenario, phase: str, turns: tuple[str, ...]
) -> ActualModelScenario:
    return ActualModelScenario(
        scenario_id=f"{scenario.scenario_id}:{phase}",
        family="restart_quality",
        turns=turns,
        version=scenario.version,
        format_version=scenario.format_version,
    )


def _serialize_state_record(record: StateRecord) -> dict[str, object]:
    return {
        "state_id": record.state_id,
        "state_class": record.state_class,
        "key": record.key,
        "value": _thaw_json(record.value),
        "sources": list(record.sources),
        "status": record.status,
        "valid_from": record.valid_from,
        "valid_to": record.valid_to,
    }


def _serialize_continuity_context(context: ContinuityContext) -> dict[str, object]:
    return {
        "max_items": context.max_items,
        "revision": context.revision,
        "items": [_serialize_continuity_item(item) for item in context.items],
    }


def _serialize_continuity_item(item: ContinuityItem) -> dict[str, object]:
    return {
        "item_id": item.item_id,
        "kind": item.kind,
        "key": item.key,
        "value": _thaw_json(item.value),
        "sources": list(item.sources),
        "epistemic_role": item.epistemic_role,
        "accepted_revision": item.accepted_revision,
        "expires_revision": item.expires_revision,
    }


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(nested) for nested in value]
    return value


def _require_positive_int(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    if value <= 0:
        raise ValueError(f"{label} must be positive")
