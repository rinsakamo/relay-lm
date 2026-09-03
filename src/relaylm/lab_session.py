from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence

from relaylm.actual_model_vllm_launch_preflight import (
    OwnedVLLMRuntime,
    RuntimeCleanupReceipt,
)


EXPLORATORY_EVIDENCE_CLASS = "EXPLORATORY_NON_CITABLE"
TrialOutcome = Literal["PASS", "FAIL", "INCONCLUSIVE"]
SessionState = Literal["OPEN", "STOPPED"]

_IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+\-]{0,127}\Z")
_STEP_RE = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_CODE_RE = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z")
_SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")


class LabSessionError(ValueError):
    """Raised when exploratory session state violates the LAB3 contract."""


@dataclass(frozen=True, slots=True)
class ExploratoryTrialRecord:
    """One explicitly non-citable exploratory or rehearsal trial."""

    session_id: str
    trial_id: str
    lab_environment_fingerprint: str
    condition_id: str
    required_steps: tuple[str, ...]
    completed_steps: tuple[str, ...]
    outcome: TrialOutcome
    detail_codes: tuple[str, ...] = ()
    evidence_class: str = EXPLORATORY_EVIDENCE_CLASS
    citable: bool = False
    qualification_authority: bool = False

    def __post_init__(self) -> None:
        _validate_identifier(self.session_id, "session_id")
        _validate_identifier(self.trial_id, "trial_id")
        _validate_lab_fingerprint(self.lab_environment_fingerprint)
        _validate_identifier(self.condition_id, "condition_id")
        _validate_steps(self.required_steps, "required_steps", require_non_empty=True)
        _validate_steps(self.completed_steps, "completed_steps")
        if not set(self.completed_steps).issubset(set(self.required_steps)):
            raise LabSessionError("completed_steps must be a subset of required_steps")
        if self.outcome not in {"PASS", "FAIL", "INCONCLUSIVE"}:
            raise LabSessionError("unsupported exploratory trial outcome")
        _validate_codes(self.detail_codes)
        if self.outcome == "PASS" and set(self.completed_steps) != set(
            self.required_steps
        ):
            raise LabSessionError(
                "PASS requires all declared required rehearsal steps to be complete"
            )
        if self.evidence_class != EXPLORATORY_EVIDENCE_CLASS:
            raise LabSessionError("exploratory evidence class cannot be changed")
        if self.citable is not False or self.qualification_authority is not False:
            raise LabSessionError("exploratory trial cannot become qualification evidence")

    @property
    def procedure_ready(self) -> bool:
        return self.outcome == "PASS"

    def to_mapping(self) -> dict[str, object]:
        return {
            "kind": "relaylm_exploratory_trial",
            "evidence_class": self.evidence_class,
            "citable": self.citable,
            "qualification_authority": self.qualification_authority,
            "session_id": self.session_id,
            "trial_id": self.trial_id,
            "lab_environment_fingerprint": self.lab_environment_fingerprint,
            "condition_id": self.condition_id,
            "required_steps": list(self.required_steps),
            "completed_steps": list(self.completed_steps),
            "outcome": self.outcome,
            "procedure_ready": self.procedure_ready,
            "detail_codes": list(self.detail_codes),
        }


@dataclass(frozen=True, slots=True)
class ExploratoryProcedureHint:
    """A successful rehearsal procedure hint, never qualification authority."""

    session_id: str
    trial_id: str
    lab_environment_fingerprint: str
    condition_id: str
    completed_steps: tuple[str, ...]
    evidence_class: str = EXPLORATORY_EVIDENCE_CLASS
    citable: bool = False
    qualification_authority: bool = False

    def __post_init__(self) -> None:
        _validate_identifier(self.session_id, "session_id")
        _validate_identifier(self.trial_id, "trial_id")
        _validate_lab_fingerprint(self.lab_environment_fingerprint)
        _validate_identifier(self.condition_id, "condition_id")
        _validate_steps(self.completed_steps, "completed_steps", require_non_empty=True)
        if self.evidence_class != EXPLORATORY_EVIDENCE_CLASS:
            raise LabSessionError("procedure hint must remain exploratory")
        if self.citable is not False or self.qualification_authority is not False:
            raise LabSessionError("procedure hint cannot become qualification authority")

    def to_mapping(self) -> dict[str, object]:
        return {
            "kind": "relaylm_exploratory_procedure_hint",
            "evidence_class": self.evidence_class,
            "citable": self.citable,
            "qualification_authority": self.qualification_authority,
            "session_id": self.session_id,
            "trial_id": self.trial_id,
            "lab_environment_fingerprint": self.lab_environment_fingerprint,
            "condition_id": self.condition_id,
            "completed_steps": list(self.completed_steps),
        }


class ExploratoryLabSession:
    """LAB3 non-citable session for repeated probes on one owned warm runtime.

    This object deliberately does not launch a provider and does not produce any
    Qualification evidence. A caller may attach the existing
    ``OwnedVLLMRuntime`` returned by the current vLLM ownership boundary, run
    multiple named exploratory trials against that same runtime, and delegate
    final cleanup back to that existing owned-runtime primitive.
    """

    def __init__(
        self,
        *,
        session_id: str,
        lab_environment_fingerprint: str,
        runtime: OwnedVLLMRuntime | None = None,
    ) -> None:
        _validate_identifier(session_id, "session_id")
        _validate_lab_fingerprint(lab_environment_fingerprint)
        if runtime is not None and not isinstance(runtime, OwnedVLLMRuntime):
            raise TypeError("runtime must be OwnedVLLMRuntime or None")
        self.session_id = session_id
        self.lab_environment_fingerprint = lab_environment_fingerprint
        self.runtime = runtime
        self._state: SessionState = "OPEN"
        self._trials: list[ExploratoryTrialRecord] = []
        self._cleanup_receipt: RuntimeCleanupReceipt | None = None

    @property
    def trials(self) -> tuple[ExploratoryTrialRecord, ...]:
        return tuple(self._trials)

    def status(self) -> dict[str, object]:
        return {
            "kind": "relaylm_exploratory_lab_session",
            "evidence_class": EXPLORATORY_EVIDENCE_CLASS,
            "citable": False,
            "qualification_authority": False,
            "session_id": self.session_id,
            "lab_environment_fingerprint": self.lab_environment_fingerprint,
            "state": self._state,
            "runtime_attached": self.runtime is not None,
            "trial_count": len(self._trials),
        }

    def record_trial(
        self,
        *,
        trial_id: str,
        condition_id: str,
        required_steps: Sequence[str],
        completed_steps: Sequence[str],
        outcome: TrialOutcome,
        detail_codes: Sequence[str] = (),
    ) -> ExploratoryTrialRecord:
        if self._state != "OPEN":
            raise LabSessionError("cannot record a trial on a stopped exploratory session")
        _validate_identifier(trial_id, "trial_id")
        _validate_identifier(condition_id, "condition_id")
        if any(item.trial_id == trial_id for item in self._trials):
            raise LabSessionError("trial_id must be unique within one exploratory session")
        trial = ExploratoryTrialRecord(
            session_id=self.session_id,
            trial_id=trial_id,
            lab_environment_fingerprint=self.lab_environment_fingerprint,
            condition_id=condition_id,
            required_steps=tuple(required_steps),
            completed_steps=tuple(completed_steps),
            outcome=outcome,
            detail_codes=tuple(detail_codes),
        )
        self._trials.append(trial)
        return trial

    def procedure_hint(self, trial_id: str | None = None) -> ExploratoryProcedureHint:
        if trial_id is None:
            candidates = [item for item in self._trials if item.procedure_ready]
            if not candidates:
                raise LabSessionError("no successful rehearsal is available")
            trial = candidates[-1]
        else:
            _validate_identifier(trial_id, "trial_id")
            trial = next((item for item in self._trials if item.trial_id == trial_id), None)
            if trial is None:
                raise LabSessionError("trial_id does not exist in this exploratory session")
            if not trial.procedure_ready:
                raise LabSessionError("trial_id does not identify a successful rehearsal")
        return ExploratoryProcedureHint(
            session_id=self.session_id,
            trial_id=trial.trial_id,
            lab_environment_fingerprint=self.lab_environment_fingerprint,
            condition_id=trial.condition_id,
            completed_steps=trial.completed_steps,
        )

    def stop(self, **cleanup_kwargs: object) -> RuntimeCleanupReceipt | None:
        if self._state == "STOPPED":
            return self._cleanup_receipt
        if self.runtime is None:
            self._state = "STOPPED"
            return None
        receipt = self.runtime.cleanup(**cleanup_kwargs)
        if not isinstance(receipt, RuntimeCleanupReceipt):
            raise LabSessionError("owned runtime cleanup returned an invalid receipt")
        if not receipt.complete:
            raise LabSessionError("owned runtime cleanup did not complete")
        self._cleanup_receipt = receipt
        self._state = "STOPPED"
        return receipt

    def to_mapping(self) -> dict[str, object]:
        mapping = self.status()
        mapping["trials"] = [item.to_mapping() for item in self._trials]
        return mapping

    def save_notes(self, path: str | Path) -> Path:
        """Atomically persist bounded historical notes, never citable evidence."""

        destination = Path(path)
        payload = self.to_mapping()
        encoded = (
            json.dumps(
                payload,
                ensure_ascii=True,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("ascii")
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.parent / (
                f".{destination.name}.tmp-{secrets.token_hex(8)}"
            )
            try:
                temporary.write_bytes(encoded)
                os.replace(temporary, destination)
            finally:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass
        except OSError as exc:
            raise LabSessionError("cannot persist exploratory session notes") from exc
        return destination


def _validate_identifier(value: str, field: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise LabSessionError(
            f"{field} must be a bounded content-free identifier without free text"
        )


def _validate_lab_fingerprint(value: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise LabSessionError(
            "lab_environment_fingerprint must be one lowercase sha256 digest"
        )


def _validate_steps(
    values: tuple[str, ...],
    field: str,
    *,
    require_non_empty: bool = False,
) -> None:
    if not isinstance(values, tuple):
        raise LabSessionError(f"{field} must be a tuple")
    if require_non_empty and not values:
        raise LabSessionError(f"{field} must not be empty")
    if len(set(values)) != len(values):
        raise LabSessionError(f"{field} must not contain duplicates")
    for value in values:
        if not isinstance(value, str) or not _STEP_RE.fullmatch(value):
            raise LabSessionError(f"{field} must contain content-free step codes")


def _validate_codes(values: tuple[str, ...]) -> None:
    if len(set(values)) != len(values):
        raise LabSessionError("detail_codes must not contain duplicates")
    for value in values:
        if not isinstance(value, str) or not _CODE_RE.fullmatch(value):
            raise LabSessionError("detail_codes must contain uppercase content-free codes")
