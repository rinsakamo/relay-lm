from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

from relaylm.actual_model_cognitive_budget import (
    validate_cognitive_budget_runtime_identity,
)
from relaylm.actual_model_evaluation import (
    ActualModelEvidence,
    ActualModelRunManifest,
    ActualModelScenario,
    run_actual_model_scenario,
    stable_actual_model_run_id,
)
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveProvider
from relaylm.storage.filesystem import CharacterDirectory


class ActualModelArtifactError(RuntimeError):
    """An actual-model fixture or evidence artifact violated reproducibility rules."""


def character_fixture_revision(root: str | Path) -> str:
    """Return a stable digest of an explicit Character Package fixture snapshot."""

    fixture_root = Path(root)
    if not fixture_root.is_dir():
        raise ActualModelArtifactError("character fixture root must be a directory")

    digest = hashlib.sha256()
    files = []
    for path in fixture_root.rglob("*"):
        if path.is_symlink():
            raise ActualModelArtifactError("character fixture must not contain symbolic links")
        if path.is_file():
            files.append(path)
    if not files:
        raise ActualModelArtifactError("character fixture must contain at least one file")

    for path in sorted(files, key=lambda item: item.relative_to(fixture_root).as_posix()):
        relative = path.relative_to(fixture_root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return f"sha256:{digest.hexdigest()}"


def prepare_character_fixture_workspace(
    *,
    fixture_root: str | Path,
    workspace_root: str | Path,
    manifest: ActualModelRunManifest,
) -> CharacterDirectory:
    """Verify and copy one immutable fixture into a fresh mutable run workspace."""

    source = Path(fixture_root)
    destination = Path(workspace_root)
    observed_revision = character_fixture_revision(source)
    if manifest.character_fixture_revision != observed_revision:
        raise ActualModelArtifactError(
            "character fixture revision does not match run manifest: "
            f"expected {manifest.character_fixture_revision}, observed {observed_revision}"
        )
    if destination.exists():
        raise ActualModelArtifactError("actual-model workspace must not already exist")

    try:
        shutil.copytree(source, destination, copy_function=shutil.copy2)
        copied_revision = character_fixture_revision(destination)
    except (OSError, ActualModelArtifactError) as exc:
        shutil.rmtree(destination, ignore_errors=True)
        raise ActualModelArtifactError(f"cannot create actual-model workspace: {exc}") from exc
    if copied_revision != manifest.character_fixture_revision:
        shutil.rmtree(destination, ignore_errors=True)
        raise ActualModelArtifactError(
            "character fixture changed while preparing the run workspace"
        )
    return CharacterDirectory(destination)


async def run_actual_model_fixture(
    *,
    fixture_root: str | Path,
    workspace_root: str | Path,
    provider: CognitiveProvider,
    manifest: ActualModelRunManifest,
    scenario: ActualModelScenario,
    cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
    execution_id: str | None = None,
    scenario_revision: str | None = None,
) -> ActualModelEvidence:
    """Run one verified fixture snapshot in a fresh workspace.

    Durable Character Package state is copied exactly. Process-local Continuity is
    never persisted in the fixture. A declared total cognitive-budget condition
    must receive the exact caller-supplied #1387 runtime object; only total/policy
    identity is persisted while the configured token counter remains process-local.
    """

    validate_cognitive_budget_runtime_identity(
        declared=manifest.cognitive_budget,
        runtime=cognitive_budget,
        effective_context_window=manifest.effective_context_window,
    )
    character = prepare_character_fixture_workspace(
        fixture_root=fixture_root,
        workspace_root=workspace_root,
        manifest=manifest,
    )
    return await run_actual_model_scenario(
        character=character,
        provider=provider,
        manifest=manifest,
        scenario=scenario,
        continuity_runtime=None,
        cognitive_budget=cognitive_budget,
        execution_id=execution_id,
        scenario_revision=scenario_revision,
    )


def write_actual_model_evidence(
    *, evidence: ActualModelEvidence, artifact_root: str | Path
) -> Path:
    """Persist one run as an immutable, run-id-addressed JSON evidence artifact."""

    expected_run_id = stable_actual_model_run_id(
        manifest=evidence.manifest,
        scenario=evidence.scenario,
    )
    if evidence.run_id != expected_run_id:
        raise ActualModelArtifactError("run_id does not match actual-model evidence")

    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{evidence.run_id}.json"
    payload = evidence.to_json() + "\n"

    if path.exists():
        return _resolve_existing_evidence(path=path, payload=payload)

    temporary = root / f".{evidence.run_id}.{os.getpid()}.tmp"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return _resolve_existing_evidence(path=path, payload=payload)
    except OSError as exc:
        raise ActualModelArtifactError(f"cannot persist actual-model evidence: {exc}") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def load_actual_model_evidence_mapping(path: str | Path) -> dict[str, object]:
    """Read a machine-auditable evidence artifact without reconstructing runtime objects."""

    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActualModelArtifactError(f"cannot load actual-model evidence: {exc}") from exc
    if not isinstance(raw, dict):
        raise ActualModelArtifactError("actual-model evidence root must be a JSON object")
    return raw


def _resolve_existing_evidence(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelArtifactError(f"cannot read existing evidence artifact: {exc}") from exc
    if existing == payload:
        return path
    raise ActualModelArtifactError(
        "run ID already exists with different evidence; use a distinct replicate_id"
    )
