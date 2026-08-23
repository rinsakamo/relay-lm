from __future__ import annotations

import json
import os
from pathlib import Path

from relaylm.actual_model_execution import (
    ActualModelScenarioExecutionResult,
    _stable_execution_id,
)


class ActualModelExecutionArtifactError(RuntimeError):
    """An execution artifact violated immutable actual-model evidence rules."""


def write_actual_model_execution_result(
    *,
    result: ActualModelScenarioExecutionResult,
    artifact_root: str | Path,
) -> Path:
    """Persist one complete execution result as an immutable citable JSON artifact."""

    expected_execution_id = _stable_execution_id(
        plan=result.plan,
        run_id=result.run_id,
    )
    if result.execution_id != expected_execution_id:
        raise ActualModelExecutionArtifactError(
            "execution_id does not match execution evidence"
        )

    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{result.execution_id}.json"
    payload = result.to_json() + "\n"

    if path.exists():
        return _resolve_existing_execution(path=path, payload=payload)

    temporary = root / f".{result.execution_id}.{os.getpid()}.tmp"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return _resolve_existing_execution(path=path, payload=payload)
    except OSError as exc:
        raise ActualModelExecutionArtifactError(
            f"cannot persist actual-model execution artifact: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def load_actual_model_execution_mapping(path: str | Path) -> dict[str, object]:
    """Load one execution artifact without reconstructing runtime/provider objects."""

    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActualModelExecutionArtifactError(
            f"cannot load actual-model execution artifact: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise ActualModelExecutionArtifactError(
            "actual-model execution artifact root must be a JSON object"
        )
    return raw


def _resolve_existing_execution(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelExecutionArtifactError(
            f"cannot read existing actual-model execution artifact: {exc}"
        ) from exc
    if existing == payload:
        return path
    raise ActualModelExecutionArtifactError(
        "execution ID already exists with different evidence; use a distinct replicate_id"
    )
