from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from relaylm.actual_model_evaluation import (
    ACTUAL_MODEL_SCENARIO_FORMAT_VERSION,
    ActualModelScenario,
    ScenarioFamily,
)
from relaylm.actual_model_quality import (
    QUALITY_RUBRIC_VERSION,
    ContinuityProposalLabel,
    ProposalScoring,
    StateProposalLabel,
    TurnProposalLabels,
)

LEGACY_ACTUAL_MODEL_SCENARIO_SET_FORMAT_VERSION = 1
ACTUAL_MODEL_SCENARIO_SET_FORMAT_VERSION = 2
_SUPPORTED_SCENARIO_SET_FORMAT_VERSIONS = frozenset(
    {
        LEGACY_ACTUAL_MODEL_SCENARIO_SET_FORMAT_VERSION,
        ACTUAL_MODEL_SCENARIO_SET_FORMAT_VERSION,
    }
)


class ActualModelScenarioSetError(ValueError):
    """A machine-readable actual-model scenario set is malformed or ambiguous."""


@dataclass(frozen=True, slots=True)
class ActualModelScenarioDefinition:
    """One provider-neutral semantic scenario plus fixture-owned proposal labels."""

    scenario: ActualModelScenario
    proposal_labels: tuple[TurnProposalLabels, ...]
    required_provider_capabilities: tuple[str, ...]
    restart_after_turn_count: int | None = None
    proposal_scoring: ProposalScoring | None = None

    def __post_init__(self) -> None:
        if len(set(self.required_provider_capabilities)) != len(
            self.required_provider_capabilities
        ):
            raise ValueError(
                "required_provider_capabilities must not contain duplicates"
            )
        if not all(
            isinstance(item, str) and item.strip()
            for item in self.required_provider_capabilities
        ):
            raise ValueError(
                "required_provider_capabilities must contain non-empty strings"
            )
        if self.proposal_scoring is not None and not isinstance(
            self.proposal_scoring, ProposalScoring
        ):
            raise TypeError("proposal_scoring must be ProposalScoring or None")

        turn_indexes = tuple(item.turn_index for item in self.proposal_labels)
        if len(set(turn_indexes)) != len(turn_indexes):
            raise ValueError("proposal labels must not duplicate turn_index")
        if any(index > len(self.scenario.turns) for index in turn_indexes):
            raise ValueError("proposal labels reference a turn outside the scenario")

        if self.proposal_scoring is not None:
            if self.proposal_scoring.state == "unscored" and any(
                item.state for item in self.proposal_labels
            ):
                raise ValueError("unscored state channel must not carry proposal labels")
            if self.proposal_scoring.continuity == "unscored" and any(
                item.continuity for item in self.proposal_labels
            ):
                raise ValueError(
                    "unscored continuity channel must not carry proposal labels"
                )
            if (
                self.proposal_scoring.state == "scored"
                and "state_candidates" not in self.required_provider_capabilities
            ):
                raise ValueError(
                    "scored state channel requires state_candidates provider capability"
                )
            if (
                self.proposal_scoring.continuity == "scored"
                and "continuity_candidates" not in self.required_provider_capabilities
            ):
                raise ValueError(
                    "scored continuity channel requires continuity_candidates provider capability"
                )

        if self.scenario.family == "restart_quality":
            if self.restart_after_turn_count is None:
                raise ValueError(
                    "restart_quality scenarios require restart_after_turn_count"
                )
            if isinstance(self.restart_after_turn_count, bool) or not isinstance(
                self.restart_after_turn_count, int
            ):
                raise TypeError("restart_after_turn_count must be an integer")
            if not 0 < self.restart_after_turn_count < len(self.scenario.turns):
                raise ValueError(
                    "restart_after_turn_count must split the scenario between turns"
                )
        elif self.restart_after_turn_count is not None:
            raise ValueError(
                "restart_after_turn_count is only valid for restart_quality scenarios"
            )

    @property
    def effective_proposal_scoring(self) -> ProposalScoring:
        """Legacy sets score both channels; current sets declare scope explicitly."""

        return self.proposal_scoring or ProposalScoring()

    def to_mapping(self) -> dict[str, object]:
        mapping: dict[str, object] = {
            **self.scenario.to_mapping(),
            "required_provider_capabilities": list(
                self.required_provider_capabilities
            ),
            "restart_after_turn_count": self.restart_after_turn_count,
            "proposal_labels": [
                _turn_labels_to_mapping(item) for item in self.proposal_labels
            ],
        }
        if self.proposal_scoring is not None:
            mapping["proposal_scoring"] = self.proposal_scoring.to_mapping()
        return mapping


@dataclass(frozen=True, slots=True)
class ActualModelScenarioSet:
    """Versioned, isolated actual-model semantic fixtures; not a shared registry."""

    scenario_set_version: str
    quality_rubric_version: str
    character_fixture_id: str
    scenarios: tuple[ActualModelScenarioDefinition, ...]
    format_version: int = ACTUAL_MODEL_SCENARIO_SET_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version not in _SUPPORTED_SCENARIO_SET_FORMAT_VERSIONS:
            raise ValueError(
                "unsupported actual-model scenario-set format_version: "
                f"{self.format_version}"
            )
        if not self.scenario_set_version.strip():
            raise ValueError("scenario_set_version must not be empty")
        if self.quality_rubric_version != QUALITY_RUBRIC_VERSION:
            raise ValueError(
                "scenario set must pin the current actual-model quality rubric version"
            )
        if not self.character_fixture_id.strip():
            raise ValueError("character_fixture_id must not be empty")
        if not self.scenarios:
            raise ValueError("scenario set must contain at least one scenario")
        scenario_ids = tuple(item.scenario.scenario_id for item in self.scenarios)
        if len(set(scenario_ids)) != len(scenario_ids):
            raise ValueError("scenario ids must be unique within a scenario set")
        if self.format_version == LEGACY_ACTUAL_MODEL_SCENARIO_SET_FORMAT_VERSION:
            if any(item.proposal_scoring is not None for item in self.scenarios):
                raise ValueError(
                    "legacy scenario sets must not declare proposal_scoring"
                )
        elif any(item.proposal_scoring is None for item in self.scenarios):
            raise ValueError(
                "current scenario sets require explicit proposal_scoring for every scenario"
            )

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "scenario_set_version": self.scenario_set_version,
            "quality_rubric_version": self.quality_rubric_version,
            "character_fixture_id": self.character_fixture_id,
            "scenarios": [item.to_mapping() for item in self.scenarios],
        }

    @property
    def revision(self) -> str:
        payload = json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(payload).hexdigest()}"

    def scenario(self, scenario_id: str) -> ActualModelScenarioDefinition:
        for definition in self.scenarios:
            if definition.scenario.scenario_id == scenario_id:
                return definition
        raise KeyError(scenario_id)


def load_actual_model_scenario_set(path: str | Path) -> ActualModelScenarioSet:
    """Load one strict JSON scenario set with duplicate/unknown-field rejection."""

    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelScenarioSetError(
            f"cannot read actual-model scenario set: {exc}"
        ) from exc

    try:
        raw = json.loads(text, object_pairs_hook=_unique_object)
    except ActualModelScenarioSetError:
        raise
    except json.JSONDecodeError as exc:
        raise ActualModelScenarioSetError(
            f"invalid actual-model scenario-set JSON: {exc}"
        ) from exc

    mapping = _require_mapping(raw, "scenario set")
    _require_exact_keys(
        mapping,
        {
            "format_version",
            "scenario_set_version",
            "quality_rubric_version",
            "character_fixture_id",
            "scenarios",
        },
        "scenario set",
    )

    format_version = _require_int(mapping["format_version"], "format_version")
    if format_version not in _SUPPORTED_SCENARIO_SET_FORMAT_VERSIONS:
        raise ActualModelScenarioSetError(
            f"unsupported actual-model scenario-set format_version: {format_version}"
        )
    scenarios_raw = _require_list(mapping["scenarios"], "scenarios")
    try:
        return ActualModelScenarioSet(
            format_version=format_version,
            scenario_set_version=_require_string(
                mapping["scenario_set_version"], "scenario_set_version"
            ),
            quality_rubric_version=_require_string(
                mapping["quality_rubric_version"], "quality_rubric_version"
            ),
            character_fixture_id=_require_string(
                mapping["character_fixture_id"], "character_fixture_id"
            ),
            scenarios=tuple(
                _parse_scenario(
                    item,
                    index=index,
                    scenario_set_format_version=format_version,
                )
                for index, item in enumerate(scenarios_raw, start=1)
            ),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ActualModelScenarioSetError):
            raise
        raise ActualModelScenarioSetError(str(exc)) from exc


def _parse_scenario(
    raw: object,
    *,
    index: int,
    scenario_set_format_version: int,
) -> ActualModelScenarioDefinition:
    label = f"scenarios[{index}]"
    mapping = _require_mapping(raw, label)
    expected_keys = {
        "format_version",
        "id",
        "family",
        "version",
        "turns",
        "required_provider_capabilities",
        "restart_after_turn_count",
        "proposal_labels",
    }
    if scenario_set_format_version == ACTUAL_MODEL_SCENARIO_SET_FORMAT_VERSION:
        expected_keys.add("proposal_scoring")
    _require_exact_keys(mapping, expected_keys, label)

    family = _require_string(mapping["family"], f"{label}.family")
    turns_raw = _require_list(mapping["turns"], f"{label}.turns")
    capabilities_raw = _require_list(
        mapping["required_provider_capabilities"],
        f"{label}.required_provider_capabilities",
    )
    labels_raw = _require_list(mapping["proposal_labels"], f"{label}.proposal_labels")
    restart_after = mapping["restart_after_turn_count"]
    if restart_after is not None:
        restart_after = _require_int(restart_after, f"{label}.restart_after_turn_count")

    scenario_format = _require_int(mapping["format_version"], f"{label}.format_version")
    if scenario_format != ACTUAL_MODEL_SCENARIO_FORMAT_VERSION:
        raise ActualModelScenarioSetError(
            f"{label} has unsupported scenario format_version: {scenario_format}"
        )

    proposal_scoring = None
    if scenario_set_format_version == ACTUAL_MODEL_SCENARIO_SET_FORMAT_VERSION:
        proposal_scoring = _parse_proposal_scoring(
            mapping["proposal_scoring"],
            label=f"{label}.proposal_scoring",
        )

    return ActualModelScenarioDefinition(
        scenario=ActualModelScenario(
            scenario_id=_require_string(mapping["id"], f"{label}.id"),
            family=cast(ScenarioFamily, family),
            version=_require_string(mapping["version"], f"{label}.version"),
            turns=tuple(
                _require_string(turn, f"{label}.turns[{turn_index}]")
                for turn_index, turn in enumerate(turns_raw, start=1)
            ),
            format_version=scenario_format,
        ),
        required_provider_capabilities=tuple(
            _require_string(
                item,
                f"{label}.required_provider_capabilities[{capability_index}]",
            )
            for capability_index, item in enumerate(capabilities_raw, start=1)
        ),
        restart_after_turn_count=restart_after,
        proposal_labels=tuple(
            _parse_turn_labels(item, scenario_index=index, label_index=label_index)
            for label_index, item in enumerate(labels_raw, start=1)
        ),
        proposal_scoring=proposal_scoring,
    )


def _parse_proposal_scoring(raw: object, *, label: str) -> ProposalScoring:
    mapping = _require_mapping(raw, label)
    _require_exact_keys(mapping, {"state", "continuity"}, label)
    return ProposalScoring(
        state=cast(Any, _require_string(mapping["state"], f"{label}.state")),
        continuity=cast(
            Any,
            _require_string(mapping["continuity"], f"{label}.continuity"),
        ),
    )


def _parse_turn_labels(
    raw: object, *, scenario_index: int, label_index: int
) -> TurnProposalLabels:
    label = f"scenarios[{scenario_index}].proposal_labels[{label_index}]"
    mapping = _require_mapping(raw, label)
    _require_exact_keys(mapping, {"turn_index", "state", "continuity"}, label)
    state_raw = _require_list(mapping["state"], f"{label}.state")
    continuity_raw = _require_list(mapping["continuity"], f"{label}.continuity")
    return TurnProposalLabels(
        turn_index=_require_int(mapping["turn_index"], f"{label}.turn_index"),
        state=tuple(
            _parse_state_label(item, label=f"{label}.state[{index}]")
            for index, item in enumerate(state_raw, start=1)
        ),
        continuity=tuple(
            _parse_continuity_label(item, label=f"{label}.continuity[{index}]")
            for index, item in enumerate(continuity_raw, start=1)
        ),
    )


def _parse_state_label(raw: object, *, label: str) -> StateProposalLabel:
    mapping = _require_mapping(raw, label)
    _require_label_keys(mapping, label)
    match_value = _require_bool(mapping.get("match_value", False), f"{label}.match_value")
    _validate_label_value_shape(mapping, match_value=match_value, label=label)
    return StateProposalLabel(
        state_class=_require_string(mapping["state_class"], f"{label}.state_class"),
        key=_require_string(mapping["key"], f"{label}.key"),
        op=cast(Any, _require_string(mapping["op"], f"{label}.op")),
        match_value=match_value,
        value=mapping.get("value"),
    )


def _parse_continuity_label(
    raw: object, *, label: str
) -> ContinuityProposalLabel:
    mapping = _require_mapping(raw, label)
    _require_label_keys(mapping, label, continuity=True)
    match_value = _require_bool(mapping.get("match_value", False), f"{label}.match_value")
    _validate_label_value_shape(mapping, match_value=match_value, label=label)
    return ContinuityProposalLabel(
        kind=_require_string(mapping["kind"], f"{label}.kind"),
        key=_require_string(mapping["key"], f"{label}.key"),
        op=cast(Any, _require_string(mapping["op"], f"{label}.op")),
        match_value=match_value,
        value=mapping.get("value"),
    )


def _require_label_keys(
    mapping: Mapping[str, object], label: str, *, continuity: bool = False
) -> None:
    base = {"kind", "key", "op"} if continuity else {"state_class", "key", "op"}
    allowed = base | {"match_value", "value"}
    unknown = set(mapping) - allowed
    missing = base - set(mapping)
    if unknown or missing:
        _raise_key_error(label=label, unknown=unknown, missing=missing)


def _validate_label_value_shape(
    mapping: Mapping[str, object], *, match_value: bool, label: str
) -> None:
    if match_value and "value" not in mapping:
        raise ActualModelScenarioSetError(
            f"{label}: value is required when match_value is true"
        )
    if not match_value and "value" in mapping:
        raise ActualModelScenarioSetError(
            f"{label}: value is only allowed when match_value is true"
        )


def _turn_labels_to_mapping(item: TurnProposalLabels) -> dict[str, object]:
    return {
        "turn_index": item.turn_index,
        "state": [_state_label_to_mapping(label) for label in item.state],
        "continuity": [
            _continuity_label_to_mapping(label) for label in item.continuity
        ],
    }


def _state_label_to_mapping(label: StateProposalLabel) -> dict[str, object]:
    result: dict[str, object] = {
        "state_class": label.state_class,
        "key": label.key,
        "op": label.op,
        "match_value": label.match_value,
    }
    if label.match_value:
        result["value"] = label.value
    return result


def _continuity_label_to_mapping(
    label: ContinuityProposalLabel,
) -> dict[str, object]:
    result: dict[str, object] = {
        "kind": label.kind,
        "key": label.key,
        "op": label.op,
        "match_value": label.match_value,
    }
    if label.match_value:
        result["value"] = label.value
    return result


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ActualModelScenarioSetError(
                f"duplicate JSON object key in scenario set: {key}"
            )
        result[key] = value
    return result


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ActualModelScenarioSetError(f"{label} must be a JSON object")
    return cast(Mapping[str, object], value)


def _require_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ActualModelScenarioSetError(f"{label} must be a JSON array")
    return value


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActualModelScenarioSetError(f"{label} must be a non-empty string")
    return value


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ActualModelScenarioSetError(f"{label} must be an integer")
    return value


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ActualModelScenarioSetError(f"{label} must be a boolean")
    return value


def _require_exact_keys(
    mapping: Mapping[str, object], required: set[str], label: str
) -> None:
    unknown = set(mapping) - required
    missing = required - set(mapping)
    if unknown or missing:
        _raise_key_error(label=label, unknown=unknown, missing=missing)


def _raise_key_error(*, label: str, unknown: set[str], missing: set[str]) -> None:
    details: list[str] = []
    if missing:
        details.append(f"missing {', '.join(sorted(missing))}")
    if unknown:
        details.append(f"unknown {', '.join(sorted(unknown))}")
    raise ActualModelScenarioSetError(f"{label}: {'; '.join(details)}")
