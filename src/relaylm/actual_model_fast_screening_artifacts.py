from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from relaylm.actual_model_fast_screening import (
    ScreeningCallOutcome,
    ScreeningCallTiming,
    ScreeningPhase,
)


FAST_SCREENING_TIMING_FORMAT_VERSION = 2
FAST_SCREENING_FAILURE_DIAGNOSTIC_FORMAT_VERSION = 1
FastScreeningExecutionMode = Literal["single_pass", "two_pass"]


class ActualModelFastScreeningArtifactError(ValueError):
    """Fast-screening timing evidence is malformed, ambiguous, or conflicting."""


@dataclass(frozen=True, slots=True)
class FastScreeningFailureDiagnostic:
    turn_index: int
    phase: ScreeningPhase
    exception_type: str
    exception_message: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.turn_index, bool) or not isinstance(self.turn_index, int):
            raise TypeError("failure diagnostic turn_index must be an integer")
        if self.turn_index <= 0:
            raise ValueError("failure diagnostic turn_index must be positive")
        if self.phase not in {"single_pass", "pass1", "pass2"}:
            raise ValueError(f"unsupported failure diagnostic phase: {self.phase}")
        if not isinstance(self.exception_type, str) or not self.exception_type.strip():
            raise ValueError("failure diagnostic exception_type must be non-empty")
        if self.exception_message is not None and (
            not isinstance(self.exception_message, str)
            or not self.exception_message.strip()
        ):
            raise ValueError(
                "failure diagnostic exception_message must be non-empty when present"
            )

    def to_mapping(self) -> dict[str, object]:
        return {
            "turn_index": self.turn_index,
            "phase": self.phase,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
        }


@dataclass(frozen=True, slots=True)
class FastScreeningFailureDiagnosticArtifact:
    run_id: str
    failures: tuple[FastScreeningFailureDiagnostic, ...]
    format_version: int = FAST_SCREENING_FAILURE_DIAGNOSTIC_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != FAST_SCREENING_FAILURE_DIAGNOSTIC_FORMAT_VERSION:
            raise ValueError(
                "unsupported fast-screening failure diagnostic format_version: "
                f"{self.format_version}"
            )
        _validate_canonical_stable_id(self.run_id, prefix="amr", label="run_id")
        if not self.failures or not all(
            isinstance(item, FastScreeningFailureDiagnostic) for item in self.failures
        ):
            raise ValueError("failure diagnostic artifact requires failure entries")

    @property
    def diagnostic_id(self) -> str:
        payload = json.dumps(
            self._identity_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"amfd-{hashlib.sha256(payload).hexdigest()}"

    def _identity_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "run_id": self.run_id,
            "failures": [item.to_mapping() for item in self.failures],
        }

    def to_mapping(self) -> dict[str, object]:
        return {"diagnostic_id": self.diagnostic_id, **self._identity_mapping()}

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        ) + "\n"


@dataclass(frozen=True, slots=True)
class FastScreeningTurnTiming:
    turn_index: int
    response_provider_ms: float
    response_outcome: ScreeningCallOutcome
    first_visible_provider_ms: float | None
    extraction_provider_ms: float | None
    extraction_outcome: ScreeningCallOutcome | None

    def __post_init__(self) -> None:
        if isinstance(self.turn_index, bool) or not isinstance(self.turn_index, int):
            raise TypeError("turn_index must be an integer")
        if self.turn_index <= 0:
            raise ValueError("turn_index must be positive")
        _validate_non_negative_finite(self.response_provider_ms, "response_provider_ms")
        _validate_call_outcome(self.response_outcome, "response_outcome")
        if self.first_visible_provider_ms is not None:
            _validate_non_negative_finite(
                self.first_visible_provider_ms,
                "first_visible_provider_ms",
            )
            if self.first_visible_provider_ms > self.response_provider_ms:
                raise ValueError(
                    "first_visible_provider_ms cannot exceed response_provider_ms"
                )
        if self.extraction_provider_ms is None:
            if self.extraction_outcome is not None:
                raise ValueError(
                    "extraction_outcome requires extraction_provider_ms"
                )
        else:
            _validate_non_negative_finite(
                self.extraction_provider_ms,
                "extraction_provider_ms",
            )
            if self.extraction_outcome is None:
                raise ValueError(
                    "extraction_provider_ms requires extraction_outcome"
                )
            _validate_call_outcome(self.extraction_outcome, "extraction_outcome")

    @property
    def provider_total_ms(self) -> float:
        return self.response_provider_ms + (self.extraction_provider_ms or 0.0)

    def to_mapping(self) -> dict[str, object]:
        return {
            "turn_index": self.turn_index,
            "response_provider_ms": self.response_provider_ms,
            "response_outcome": self.response_outcome,
            "first_visible_provider_ms": self.first_visible_provider_ms,
            "extraction_provider_ms": self.extraction_provider_ms,
            "extraction_outcome": self.extraction_outcome,
            "provider_total_ms": self.provider_total_ms,
        }


@dataclass(frozen=True, slots=True)
class FastScreeningTimingArtifact:
    screening_id: str
    condition_id: str
    replicate_id: str
    scenario_id: str
    execution_id: str
    run_id: str
    execution_mode: FastScreeningExecutionMode
    scenario_elapsed_ms: float
    turns: tuple[FastScreeningTurnTiming, ...]
    format_version: int = FAST_SCREENING_TIMING_FORMAT_VERSION
    failure_diagnostics: tuple[FastScreeningFailureDiagnostic, ...] = field(
        default_factory=tuple,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if self.format_version != FAST_SCREENING_TIMING_FORMAT_VERSION:
            raise ValueError(
                f"unsupported fast-screening timing format_version: {self.format_version}"
            )
        for name in (
            "screening_id",
            "condition_id",
            "replicate_id",
            "scenario_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        _validate_canonical_stable_id(
            self.execution_id,
            prefix="amx",
            label="execution_id",
        )
        _validate_canonical_stable_id(self.run_id, prefix="amr", label="run_id")
        if self.execution_mode not in {"single_pass", "two_pass"}:
            raise ValueError(f"unsupported execution_mode: {self.execution_mode}")
        _validate_non_negative_finite(self.scenario_elapsed_ms, "scenario_elapsed_ms")
        if not self.turns:
            raise ValueError("timing artifact must contain at least one turn")
        expected = tuple(range(1, len(self.turns) + 1))
        observed = tuple(turn.turn_index for turn in self.turns)
        if observed != expected:
            raise ValueError("timing artifact turn indexes must be contiguous from 1")
        if any(turn.response_outcome != "completed" for turn in self.turns):
            raise ValueError(
                "citable completed execution timing requires completed response calls"
            )
        if self.execution_mode == "single_pass" and any(
            turn.extraction_provider_ms is not None
            or turn.extraction_outcome is not None
            for turn in self.turns
        ):
            raise ValueError("single_pass timing must not carry extraction timing")
        if not all(
            isinstance(item, FastScreeningFailureDiagnostic)
            for item in self.failure_diagnostics
        ):
            raise TypeError(
                "failure_diagnostics must contain FastScreeningFailureDiagnostic values"
            )
        if any(item.turn_index > len(self.turns) for item in self.failure_diagnostics):
            raise ValueError("failure diagnostic turn_index exceeds timing turn count")
        provider_total_ms = sum(turn.provider_total_ms for turn in self.turns)
        if self.scenario_elapsed_ms + 1e-6 < provider_total_ms:
            raise ActualModelFastScreeningArtifactError(
                "scenario elapsed time cannot be below provider call total"
            )

    @property
    def timing_id(self) -> str:
        payload = json.dumps(
            self._identity_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"amt-{hashlib.sha256(payload).hexdigest()}"

    def _identity_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "screening_id": self.screening_id,
            "condition_id": self.condition_id,
            "replicate_id": self.replicate_id,
            "scenario_id": self.scenario_id,
            "execution_id": self.execution_id,
            "run_id": self.run_id,
            "execution_mode": self.execution_mode,
            "clock": "monotonic_ns",
            "scenario_elapsed_ms": self.scenario_elapsed_ms,
            "turns": [turn.to_mapping() for turn in self.turns],
        }

    def to_mapping(self) -> dict[str, object]:
        return {"timing_id": self.timing_id, **self._identity_mapping()}

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        ) + "\n"


def bind_fast_screening_timing_artifact(
    *,
    screening_id: str,
    condition_id: str,
    replicate_id: str,
    scenario_id: str,
    execution_id: str,
    run_id: str,
    execution_mode: FastScreeningExecutionMode,
    turn_count: int,
    scenario_elapsed_ms: float,
    calls: tuple[ScreeningCallTiming, ...],
) -> FastScreeningTimingArtifact:
    if isinstance(turn_count, bool) or not isinstance(turn_count, int):
        raise TypeError("turn_count must be an integer")
    if turn_count <= 0:
        raise ValueError("turn_count must be positive")
    if not isinstance(calls, tuple) or not all(
        isinstance(call, ScreeningCallTiming) for call in calls
    ):
        raise TypeError("calls must be a tuple of ScreeningCallTiming values")
    if execution_mode not in {"single_pass", "two_pass"}:
        raise ValueError(f"unsupported execution_mode: {execution_mode}")

    turns: list[FastScreeningTurnTiming] = []
    diagnostics: list[FastScreeningFailureDiagnostic] = []
    offset = 0
    for turn_index in range(1, turn_count + 1):
        if offset >= len(calls):
            _raise_phase_sequence_error(
                execution_mode=execution_mode,
                turn_count=turn_count,
                calls=calls,
            )
        response = calls[offset]
        expected_response_phase = (
            "single_pass" if execution_mode == "single_pass" else "pass1"
        )
        if response.phase != expected_response_phase:
            _raise_phase_sequence_error(
                execution_mode=execution_mode,
                turn_count=turn_count,
                calls=calls,
            )
        if response.outcome != "completed":
            raise ActualModelFastScreeningArtifactError(
                "completed scenario timing cannot contain a failed response call"
            )
        offset += 1

        extraction = None
        if execution_mode == "two_pass" and offset < len(calls):
            next_call = calls[offset]
            if next_call.phase == "pass2":
                extraction = next_call
                offset += 1
            elif next_call.phase != "pass1":
                _raise_phase_sequence_error(
                    execution_mode=execution_mode,
                    turn_count=turn_count,
                    calls=calls,
                )

        if (
            extraction is not None
            and extraction.outcome == "failed"
            and extraction.failure_exception_type is not None
        ):
            diagnostics.append(
                FastScreeningFailureDiagnostic(
                    turn_index=turn_index,
                    phase="pass2",
                    exception_type=extraction.failure_exception_type,
                    exception_message=extraction.failure_exception_message,
                )
            )
        turns.append(
            FastScreeningTurnTiming(
                turn_index=turn_index,
                response_provider_ms=response.duration_ms,
                response_outcome=response.outcome,
                first_visible_provider_ms=response.first_visible_ms,
                extraction_provider_ms=(
                    extraction.duration_ms if extraction is not None else None
                ),
                extraction_outcome=(
                    extraction.outcome if extraction is not None else None
                ),
            )
        )

    if offset != len(calls):
        _raise_phase_sequence_error(
            execution_mode=execution_mode,
            turn_count=turn_count,
            calls=calls,
        )

    return FastScreeningTimingArtifact(
        screening_id=screening_id,
        condition_id=condition_id,
        replicate_id=replicate_id,
        scenario_id=scenario_id,
        execution_id=execution_id,
        run_id=run_id,
        execution_mode=execution_mode,
        scenario_elapsed_ms=scenario_elapsed_ms,
        turns=tuple(turns),
        failure_diagnostics=tuple(diagnostics),
    )


def write_fast_screening_timing_artifact(
    *,
    artifact: FastScreeningTimingArtifact,
    artifact_root: str | Path,
) -> Path:
    if not isinstance(artifact, FastScreeningTimingArtifact):
        raise TypeError("artifact must be FastScreeningTimingArtifact")
    directory = Path(artifact_root) / "screening_timing"
    path = directory / f"{artifact.run_id}.json"
    payload = artifact.to_json()
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ActualModelFastScreeningArtifactError(
            f"cannot create timing evidence directory: {exc}"
        ) from exc

    resolved_path = path
    if path.exists():
        resolved_path = _resolve_existing(path=path, payload=payload)
    else:
        temporary = directory / (
            f".{artifact.run_id}.{artifact.timing_id}.{os.getpid()}.tmp"
        )
        try:
            with temporary.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                resolved_path = _resolve_existing(path=path, payload=payload)
        except OSError as exc:
            raise ActualModelFastScreeningArtifactError(
                f"cannot write timing evidence: {exc}"
            ) from exc
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    if artifact.failure_diagnostics:
        _write_failure_diagnostic_sidecar(
            artifact=FastScreeningFailureDiagnosticArtifact(
                run_id=artifact.run_id,
                failures=artifact.failure_diagnostics,
            ),
            artifact_root=artifact_root,
        )
    return resolved_path


def _write_failure_diagnostic_sidecar(
    *,
    artifact: FastScreeningFailureDiagnosticArtifact,
    artifact_root: str | Path,
) -> Path:
    directory = Path(artifact_root) / "screening_failure_diagnostics"
    path = directory / f"{artifact.run_id}.json"
    payload = artifact.to_json()
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ActualModelFastScreeningArtifactError(
            f"cannot create screening failure diagnostic directory: {exc}"
        ) from exc
    if path.exists():
        return _resolve_existing(path=path, payload=payload)

    temporary = directory / (
        f".{artifact.run_id}.{artifact.diagnostic_id}.{os.getpid()}.tmp"
    )
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
        raise ActualModelFastScreeningArtifactError(
            f"cannot write screening failure diagnostic evidence: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def _resolve_existing(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelFastScreeningArtifactError(
            f"cannot read existing timing evidence: {exc}"
        ) from exc
    if existing == payload:
        return path
    raise ActualModelFastScreeningArtifactError(
        "conflicting timing evidence already exists for this run_id; "
        "use a distinct replicate_id"
    )


def _raise_phase_sequence_error(
    *,
    execution_mode: FastScreeningExecutionMode,
    turn_count: int,
    calls: tuple[ScreeningCallTiming, ...],
) -> None:
    if execution_mode == "single_pass":
        expected = ("single_pass",) * turn_count
    else:
        expected = "one pass1 per turn with an optional immediate pass2 provider call"
    observed = tuple(call.phase for call in calls)
    raise ActualModelFastScreeningArtifactError(
        "screening timing phase sequence does not match execution topology: "
        f"expected {expected}, observed {observed}"
    )


def _validate_call_outcome(value: str, label: str) -> None:
    if value not in {"completed", "failed"}:
        raise ValueError(f"{label} must be completed or failed")


def _validate_canonical_stable_id(value: str, *, prefix: str, label: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    expected_prefix = f"{prefix}-"
    digest = value.removeprefix(expected_prefix)
    if (
        not value.startswith(expected_prefix)
        or len(digest) != 64
        or any(char not in "0123456789abcdef" for char in digest)
    ):
        raise ValueError(
            f"{label} must be canonical {prefix}-<64 lowercase hex> identity"
        )


def _validate_non_negative_finite(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric")
    if not math.isfinite(float(value)) or value < 0:
        raise ValueError(f"{label} must be finite and non-negative")