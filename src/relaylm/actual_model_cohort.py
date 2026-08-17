from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from relaylm.actual_model_evaluation import ActualModelRunManifest
from relaylm.actual_model_execution import (
    ActualModelScenarioExecutionResult,
    plan_actual_model_scenario_execution,
    run_actual_model_scenario_definition,
)
from relaylm.actual_model_scenarios import ActualModelScenarioSet
from relaylm.cognitive import CognitiveProvider

ACTUAL_MODEL_COHORT_FORMAT_VERSION = 1
_TARGET_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


class ActualModelCohortError(RuntimeError):
    """A multi-model cohort is not a controlled same-fixture execution."""


@dataclass(frozen=True, slots=True)
class ActualModelExecutionTarget:
    """One exact model/provider target within a controlled semantic cohort."""

    label: str
    manifest: ActualModelRunManifest
    provider: CognitiveProvider

    def __post_init__(self) -> None:
        if _TARGET_LABEL.fullmatch(self.label) is None:
            raise ValueError(
                "target label must be 1-64 safe path characters: [A-Za-z0-9._-]"
            )

    def to_mapping(self) -> dict[str, object]:
        return {
            "label": self.label,
            "manifest": self.manifest.to_mapping(),
        }


@dataclass(frozen=True, slots=True)
class ActualModelCohortMember:
    label: str
    execution: ActualModelScenarioExecutionResult

    def to_mapping(self) -> dict[str, object]:
        return {
            "label": self.label,
            "execution": self.execution.to_mapping(),
        }


@dataclass(frozen=True, slots=True)
class ActualModelModelCohortEvidence:
    """Same semantic fixture across multiple exact models; no ranking is implied."""

    cohort_id: str
    scenario_set_version: str
    scenario_set_revision: str
    scenario_id: str
    members: tuple[ActualModelCohortMember, ...]
    format_version: int = ACTUAL_MODEL_COHORT_FORMAT_VERSION

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "cohort_id": self.cohort_id,
            "scenario_set": {
                "version": self.scenario_set_version,
                "revision": self.scenario_set_revision,
            },
            "scenario_id": self.scenario_id,
            "members": [member.to_mapping() for member in self.members],
            "ranking": None,
            "score": None,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )


async def run_actual_model_model_cohort(
    *,
    scenario_set: ActualModelScenarioSet,
    scenario_id: str,
    fixture_root: str | Path,
    workspace_root: str | Path,
    targets: tuple[ActualModelExecutionTarget, ...],
) -> ActualModelModelCohortEvidence:
    """Run one unchanged semantic definition against at least two exact models."""

    _validate_targets(targets)
    _validate_shared_runtime_identity(targets)

    # Preflight every target before any model is called so one unsupported target
    # cannot leave a partially executed cohort that looks controlled.
    for target in targets:
        plan_actual_model_scenario_execution(
            scenario_set=scenario_set,
            scenario_id=scenario_id,
            fixture_root=fixture_root,
            manifest=target.manifest,
        )
        if target.manifest.execution_path == "streaming" and not callable(
            getattr(target.provider, "stream_generate", None)
        ):
            raise ActualModelCohortError(
                f"target {target.label!r} declares streaming but provider has no "
                "stream_generate implementation"
            )

    root = Path(workspace_root)
    members: list[ActualModelCohortMember] = []
    for target in targets:
        execution = await run_actual_model_scenario_definition(
            scenario_set=scenario_set,
            scenario_id=scenario_id,
            fixture_root=fixture_root,
            workspace_root=root / target.label,
            provider=target.provider,
            manifest=target.manifest,
        )
        members.append(
            ActualModelCohortMember(
                label=target.label,
                execution=execution,
            )
        )

    identity = {
        "format_version": ACTUAL_MODEL_COHORT_FORMAT_VERSION,
        "scenario_set_version": scenario_set.scenario_set_version,
        "scenario_set_revision": scenario_set.revision,
        "scenario_id": scenario_id,
        "targets": [target.to_mapping() for target in targets],
        "execution_ids": [member.execution.execution_id for member in members],
    }
    return ActualModelModelCohortEvidence(
        cohort_id=_stable_cohort_id(identity),
        scenario_set_version=scenario_set.scenario_set_version,
        scenario_set_revision=scenario_set.revision,
        scenario_id=scenario_id,
        members=tuple(members),
    )


def write_actual_model_model_cohort(
    *,
    cohort: ActualModelModelCohortEvidence,
    artifact_root: str | Path,
) -> Path:
    """Persist one immutable cohort artifact that cites every member execution."""

    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{cohort.cohort_id}.cohort.json"
    payload = cohort.to_json() + "\n"
    if path.exists():
        return _resolve_existing(path=path, payload=payload)

    temporary = root / f".{cohort.cohort_id}.{os.getpid()}.tmp"
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
        raise ActualModelCohortError(
            f"cannot persist actual-model cohort artifact: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def load_actual_model_model_cohort_mapping(path: str | Path) -> dict[str, object]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActualModelCohortError(
            f"cannot load actual-model cohort artifact: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise ActualModelCohortError("actual-model cohort root must be a JSON object")
    return raw


def _validate_targets(targets: tuple[ActualModelExecutionTarget, ...]) -> None:
    if len(targets) < 2:
        raise ValueError("multi-model cohort requires at least two targets")
    labels = tuple(target.label for target in targets)
    if len(set(labels)) != len(labels):
        raise ValueError("multi-model cohort target labels must be unique")
    model_artifacts = tuple(target.manifest.model_artifact for target in targets)
    if len(set(model_artifacts)) < 2:
        raise ValueError(
            "multi-model cohort requires at least two distinct exact model_artifacts"
        )


def _validate_shared_runtime_identity(
    targets: tuple[ActualModelExecutionTarget, ...],
) -> None:
    expected = _matched_runtime_identity(targets[0].manifest)
    for target in targets[1:]:
        if _matched_runtime_identity(target.manifest) != expected:
            raise ValueError(
                "multi-model cohort may vary model/provider-specific identity only; "
                "RelayLM/runtime condition must match across targets"
            )


def _matched_runtime_identity(manifest: ActualModelRunManifest) -> dict[str, object]:
    mapping = manifest.to_mapping()
    mapping.pop("provider")
    mapping.pop("model_artifact")
    mapping.pop("tokenizer_identity")
    mapping.pop("effective_context_window")
    mapping.pop("decoding_configuration")
    mapping.pop("seed")
    return mapping


def _stable_cohort_id(identity: dict[str, object]) -> str:
    payload = json.dumps(
        identity,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"amm-{hashlib.sha256(payload).hexdigest()}"


def _resolve_existing(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelCohortError(
            f"cannot read existing actual-model cohort artifact: {exc}"
        ) from exc
    if existing == payload:
        return path
    raise ActualModelCohortError(
        "cohort ID already exists with different cohort evidence"
    )
