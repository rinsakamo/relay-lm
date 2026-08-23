from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from relaylm.actual_model_evaluation import ActualModelEvidence, ActualModelTurnEvidence
from relaylm.actual_model_execution import ActualModelScenarioExecutionResult
from relaylm.actual_model_restart import ActualModelRestartEvidence

ACTUAL_MODEL_BOUNDARY_FORMAT_VERSION = 1
BoundaryOutcome = Literal["pass", "fail"]


class ActualModelBoundaryArtifactError(RuntimeError):
    """A deterministic-boundary verdict artifact is malformed or conflicting."""


@dataclass(frozen=True, slots=True)
class DeterministicBoundaryCheck:
    """One protocol-level deterministic invariant, never a model-quality judgment."""

    invariant: str
    outcome: BoundaryOutcome
    detail: dict[str, object]

    def __post_init__(self) -> None:
        if not self.invariant.strip():
            raise ValueError("deterministic boundary invariant must not be empty")
        if self.outcome not in {"pass", "fail"}:
            raise ValueError(f"unsupported deterministic boundary outcome: {self.outcome}")
        try:
            json.dumps(self.detail, ensure_ascii=False, allow_nan=False, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise ValueError("deterministic boundary detail must be finite JSON") from exc

    def to_mapping(self) -> dict[str, object]:
        return {
            "invariant": self.invariant,
            "outcome": self.outcome,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class ActualModelDeterministicBoundaryVerdict:
    """Citable PASS/FAIL evidence for RelayLM's observed deterministic boundary only."""

    verdict_id: str
    execution_id: str
    run_id: str
    scenario_set_revision: str
    scenario_id: str
    checks: tuple[DeterministicBoundaryCheck, ...]
    format_version: int = ACTUAL_MODEL_BOUNDARY_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_BOUNDARY_FORMAT_VERSION:
            raise ValueError(
                f"unsupported actual-model boundary format_version: {self.format_version}"
            )
        for name in (
            "verdict_id",
            "execution_id",
            "run_id",
            "scenario_set_revision",
            "scenario_id",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        if not self.checks:
            raise ValueError("deterministic boundary verdict requires at least one check")
        names = tuple(check.invariant for check in self.checks)
        if len(set(names)) != len(names):
            raise ValueError("deterministic boundary invariant names must be unique")

    @property
    def outcome(self) -> BoundaryOutcome:
        return "pass" if all(check.outcome == "pass" for check in self.checks) else "fail"

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "verdict_id": self.verdict_id,
            "execution_id": self.execution_id,
            "run_id": self.run_id,
            "scenario_set_revision": self.scenario_set_revision,
            "scenario_id": self.scenario_id,
            "outcome": self.outcome,
            "checks": [check.to_mapping() for check in self.checks],
            "model_quality": None,
            "score": None,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )


def evaluate_actual_model_deterministic_boundary(
    *, result: ActualModelScenarioExecutionResult
) -> ActualModelDeterministicBoundaryVerdict:
    """Evaluate protocol invariants without re-deciding State/Continuity semantics.

    These checks assert that the real ordinary-turn evidence stayed aligned to the
    immutable semantic fixture, that every raw proposal reached exactly one recorded
    deterministic decision, and, for restart scenarios, that durable authority
    survived while process-local Continuity reset. They do not infer whether a model
    should have emitted a proposal and do not reinterpret validator acceptance rules.
    """

    definition = result.plan.definition
    scenario = definition.scenario
    evidence = result.evidence
    checks: list[DeterministicBoundaryCheck] = []

    if isinstance(evidence, ActualModelEvidence):
        checks.extend(
            _ordinary_checks(
                evidence=evidence,
                expected_turns=scenario.turns,
                invariant_prefix="ordinary",
            )
        )
    elif isinstance(evidence, ActualModelRestartEvidence):
        split = evidence.manifest.restart_after_turn_count
        checks.extend(
            _restart_phase_alignment_checks(
                evidence=evidence,
                expected_turns=scenario.turns,
                split=split,
            )
        )
        checks.extend(
            _ordinary_checks(
                evidence=evidence.before_restart,
                expected_turns=scenario.turns[:split],
                invariant_prefix="before_restart",
            )[1:]
        )
        checks.extend(
            _ordinary_checks(
                evidence=evidence.after_restart,
                expected_turns=scenario.turns[split:],
                invariant_prefix="after_restart",
            )[1:]
        )
        checks.extend(_restart_boundary_checks(evidence))
    else:
        raise TypeError("unsupported actual-model execution evidence type")

    checks_tuple = tuple(checks)
    identity = _boundary_verdict_identity(
        format_version=ACTUAL_MODEL_BOUNDARY_FORMAT_VERSION,
        execution_id=result.execution_id,
        run_id=result.run_id,
        scenario_set_revision=result.plan.scenario_set_revision,
        scenario_id=scenario.scenario_id,
        checks=checks_tuple,
    )
    return ActualModelDeterministicBoundaryVerdict(
        verdict_id=_stable_verdict_id(identity),
        execution_id=result.execution_id,
        run_id=result.run_id,
        scenario_set_revision=result.plan.scenario_set_revision,
        scenario_id=scenario.scenario_id,
        checks=checks_tuple,
    )


def write_actual_model_deterministic_boundary_verdict(
    *,
    verdict: ActualModelDeterministicBoundaryVerdict,
    artifact_root: str | Path,
) -> Path:
    """Persist an immutable boundary-verdict sidecar separate from human review."""

    identity = _boundary_verdict_identity(
        format_version=verdict.format_version,
        execution_id=verdict.execution_id,
        run_id=verdict.run_id,
        scenario_set_revision=verdict.scenario_set_revision,
        scenario_id=verdict.scenario_id,
        checks=verdict.checks,
    )
    if verdict.verdict_id != _stable_verdict_id(identity):
        raise ActualModelBoundaryArtifactError(
            "verdict_id does not match boundary evidence"
        )

    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{verdict.verdict_id}.boundary.json"
    payload = verdict.to_json() + "\n"
    if path.exists():
        return _resolve_existing(path=path, payload=payload)

    temporary = root / f".{verdict.verdict_id}.{os.getpid()}.tmp"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return _resolve_existing(path=path, payload=payload)
    except OSError as exc:
        raise ActualModelBoundaryArtifactError(
            f"cannot persist actual-model boundary verdict: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def load_actual_model_deterministic_boundary_mapping(
    path: str | Path,
) -> dict[str, object]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActualModelBoundaryArtifactError(
            f"cannot load actual-model boundary verdict: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise ActualModelBoundaryArtifactError(
            "actual-model boundary verdict root must be a JSON object"
        )
    return raw


def _ordinary_checks(
    *,
    evidence: ActualModelEvidence,
    expected_turns: tuple[str, ...],
    invariant_prefix: str,
) -> list[DeterministicBoundaryCheck]:
    observed_alignment = tuple(
        (turn.turn_index, turn.input) for turn in evidence.turns
    )
    expected_alignment = tuple(
        (index, content) for index, content in enumerate(expected_turns, start=1)
    )
    alignment_pass = observed_alignment == expected_alignment
    state_failures = _proposal_decision_failures(
        turns=evidence.turns,
        raw_attribute="state_candidates",
        decision_attribute="state_decisions",
    )
    continuity_failures = _proposal_decision_failures(
        turns=evidence.turns,
        raw_attribute="continuity_candidates",
        decision_attribute="continuity_decisions",
    )
    return [
        DeterministicBoundaryCheck(
            invariant=f"{invariant_prefix}.fixture_turn_alignment",
            outcome="pass" if alignment_pass else "fail",
            detail={
                "expected_turn_count": len(expected_alignment),
                "observed_turn_count": len(observed_alignment),
                "mismatched_turn_indexes": [
                    index
                    for index in range(
                        1, max(len(expected_alignment), len(observed_alignment)) + 1
                    )
                    if _alignment_at(expected_alignment, index)
                    != _alignment_at(observed_alignment, index)
                ],
            },
        ),
        DeterministicBoundaryCheck(
            invariant=f"{invariant_prefix}.state_proposal_decision_coverage",
            outcome="pass" if not state_failures else "fail",
            detail={"failed_turn_indexes": state_failures},
        ),
        DeterministicBoundaryCheck(
            invariant=f"{invariant_prefix}.continuity_proposal_decision_coverage",
            outcome="pass" if not continuity_failures else "fail",
            detail={"failed_turn_indexes": continuity_failures},
        ),
    ]


def _restart_phase_alignment_checks(
    *,
    evidence: ActualModelRestartEvidence,
    expected_turns: tuple[str, ...],
    split: int,
) -> list[DeterministicBoundaryCheck]:
    definition_matches_manifest = 0 < split < len(expected_turns)
    before_inputs = tuple(turn.input for turn in evidence.before_restart.turns)
    after_inputs = tuple(turn.input for turn in evidence.after_restart.turns)
    observed = before_inputs + after_inputs
    phase_shape_pass = (
        definition_matches_manifest
        and len(before_inputs) == split
        and observed == expected_turns
    )
    return [
        DeterministicBoundaryCheck(
            invariant="restart.fixture_phase_alignment",
            outcome="pass" if phase_shape_pass else "fail",
            detail={
                "restart_after_turn_count": split,
                "expected_turn_count": len(expected_turns),
                "before_turn_count": len(before_inputs),
                "after_turn_count": len(after_inputs),
            },
        )
    ]


def _restart_boundary_checks(
    evidence: ActualModelRestartEvidence,
) -> list[DeterministicBoundaryCheck]:
    boundary = evidence.boundary
    state_pass = boundary.state_before_restart == boundary.state_after_restart
    events_pass = boundary.event_ids_before_restart == boundary.event_ids_after_restart
    after = boundary.continuity_after_restart
    continuity_pass = (
        after.get("max_items") == evidence.manifest.continuity_max_items
        and after.get("revision") == 0
        and after.get("items") == []
    )
    return [
        DeterministicBoundaryCheck(
            invariant="restart.durable_state_survives_boundary",
            outcome="pass" if state_pass else "fail",
            detail={
                "before_record_count": len(boundary.state_before_restart),
                "after_record_count": len(boundary.state_after_restart),
            },
        ),
        DeterministicBoundaryCheck(
            invariant="restart.durable_events_survive_boundary",
            outcome="pass" if events_pass else "fail",
            detail={
                "before_event_count": len(boundary.event_ids_before_restart),
                "after_event_count": len(boundary.event_ids_after_restart),
            },
        ),
        DeterministicBoundaryCheck(
            invariant="restart.process_local_continuity_resets",
            outcome="pass" if continuity_pass else "fail",
            detail={
                "expected_max_items": evidence.manifest.continuity_max_items,
                "observed_max_items": after.get("max_items"),
                "observed_revision": after.get("revision"),
                "observed_item_count": (
                    len(after.get("items", []))
                    if isinstance(after.get("items"), list)
                    else None
                ),
            },
        ),
    ]


def _proposal_decision_failures(
    *,
    turns: tuple[ActualModelTurnEvidence, ...],
    raw_attribute: str,
    decision_attribute: str,
) -> list[int]:
    failures: list[int] = []
    for turn in turns:
        raw_candidates = getattr(turn.raw_model, raw_attribute)
        decisions = getattr(turn.deterministic, decision_attribute)
        raw_multiset = Counter(_canonical_json(candidate) for candidate in raw_candidates)
        decision_multiset = Counter(
            _canonical_json(decision.get("candidate")) for decision in decisions
        )
        if raw_multiset != decision_multiset:
            failures.append(turn.turn_index)
    return failures


def _alignment_at(
    alignment: tuple[tuple[int, str], ...], index: int
) -> tuple[int, str] | None:
    if 0 < index <= len(alignment):
        return alignment[index - 1]
    return None


def _boundary_verdict_identity(
    *,
    format_version: int,
    execution_id: str,
    run_id: str,
    scenario_set_revision: str,
    scenario_id: str,
    checks: tuple[DeterministicBoundaryCheck, ...],
) -> dict[str, object]:
    return {
        "format_version": format_version,
        "execution_id": execution_id,
        "run_id": run_id,
        "scenario_set_revision": scenario_set_revision,
        "scenario_id": scenario_id,
        "checks": [check.to_mapping() for check in checks],
    }


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _stable_verdict_id(identity: dict[str, object]) -> str:
    payload = _canonical_json(identity).encode("utf-8")
    return f"amb-{hashlib.sha256(payload).hexdigest()}"


def _resolve_existing(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelBoundaryArtifactError(
            f"cannot read existing actual-model boundary verdict: {exc}"
        ) from exc
    if existing == payload:
        return path
    raise ActualModelBoundaryArtifactError(
        "boundary verdict ID already exists with different evidence"
    )
