from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import secrets
import shlex
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable, Mapping
from typing import Callable, Literal, Sequence


class VLLMHostPreflightError(ValueError):
    """The bounded vLLM host-preflight process snapshot is not admissible."""


class RuntimeOwnershipError(VLLMHostPreflightError):
    """A runtime process/listener boundary cannot be proven safely."""

    def __init__(self, message: str, *, code: str = "PROCESS_OWNERSHIP_UNPROVEN") -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


RUNTIME_OWNER_NONCE_ENV = "RELAYLM_RUNTIME_OWNER_NONCE"
RUNTIME_OWNER_RUN_ID_ENV = "RELAYLM_RUNTIME_RUN_ID"


class AuthorityTransportError(RuntimeError):
    """A live repository/Issue authority source could not be reached."""


AuthorityStatus = Literal[
    "CURRENT_AUTHORITY_CONFIRMED",
    "AUTHORITY_TRANSPORT_UNAVAILABLE",
    "AUTHORITY_CONTRADICTORY",
]


@dataclass(frozen=True, slots=True)
class AuthorityAcquisition:
    """A content-free result of trying only explicitly live authority sources."""

    status: AuthorityStatus
    authority: dict[str, object] | None
    source: str | None
    attempts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {
            "CURRENT_AUTHORITY_CONFIRMED",
            "AUTHORITY_TRANSPORT_UNAVAILABLE",
            "AUTHORITY_CONTRADICTORY",
        }:
            raise VLLMHostPreflightError("unsupported authority acquisition status")
        if self.authority is not None and not isinstance(self.authority, dict):
            raise TypeError("authority must be a mapping or None")
        if self.status == "CURRENT_AUTHORITY_CONFIRMED":
            if self.authority is None or self.source is None:
                raise VLLMHostPreflightError(
                    "confirmed authority requires a live source and authority"
                )
        elif self.authority is not None or self.source is not None:
            raise VLLMHostPreflightError(
                "unconfirmed authority must not expose a promoted authority"
            )

    def to_mapping(self) -> dict[str, object]:
        return {
            "status": self.status,
            "authority": dict(self.authority) if self.authority is not None else None,
            "source": self.source,
            "attempts": list(self.attempts),
        }


def acquire_current_authority(
    *,
    sources: Sequence[tuple[str, Callable[[], Mapping[str, object]]]],
    stale_authority: Mapping[str, object] | None = None,
) -> AuthorityAcquisition:
    """Try bounded live sources without ever promoting a stale fallback.

    ``stale_authority`` is accepted only to make accidental fallback explicit to
    callers; it is intentionally ignored.  A source that cannot be reached is
    infrastructure evidence, not permission to use a remembered ref or Issue.
    """

    del stale_authority
    observations: list[tuple[str, dict[str, object], str]] = []
    attempts: list[str] = []
    for source_name, source in sources:
        if not isinstance(source_name, str) or not source_name.strip():
            raise VLLMHostPreflightError("authority source names must be non-empty")
        if not callable(source):
            raise TypeError("authority sources must be callable")
        try:
            raw = source()
            if not isinstance(raw, Mapping):
                raise TypeError("live authority source must return a mapping")
            encoded = json.dumps(
                dict(raw),
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            normalized = json.loads(encoded)
            if not isinstance(normalized, dict):
                raise TypeError("live authority source must return an object")
        except Exception as exc:
            attempts.append(f"{source_name}:unavailable:{type(exc).__name__}")
            continue
        attempts.append(f"{source_name}:ok")
        observations.append((source_name, normalized, encoded))

    if not observations:
        return AuthorityAcquisition(
            status="AUTHORITY_TRANSPORT_UNAVAILABLE",
            authority=None,
            source=None,
            attempts=tuple(attempts),
        )
    first_name, first_authority, first_encoded = observations[0]
    if any(encoded != first_encoded for _, _, encoded in observations[1:]):
        return AuthorityAcquisition(
            status="AUTHORITY_CONTRADICTORY",
            authority=None,
            source=None,
            attempts=tuple(attempts),
        )
    return AuthorityAcquisition(
        status="CURRENT_AUTHORITY_CONFIRMED",
        authority=first_authority,
        source=first_name,
        attempts=tuple(attempts),
    )


@dataclass(frozen=True, slots=True)
class FrozenExecutionIdentity:
    """Content-addressed identity captured at the pre-semantic freeze point."""

    payload: dict[str, object]
    fingerprint: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "FrozenExecutionIdentity":
        if not isinstance(value, Mapping) or not value:
            raise VLLMHostPreflightError("frozen execution identity must be a non-empty mapping")
        try:
            encoded = json.dumps(
                dict(value),
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            payload = json.loads(encoded.decode("utf-8"))
        except (TypeError, ValueError, UnicodeError) as exc:
            raise VLLMHostPreflightError(
                "frozen execution identity must be JSON-serializable"
            ) from exc
        if not isinstance(payload, dict):
            raise VLLMHostPreflightError("frozen execution identity must be an object")
        return cls(
            payload=payload,
            fingerprint=f"sha256:{hashlib.sha256(encoded).hexdigest()}",
        )

    def to_mapping(self) -> dict[str, object]:
        return json.loads(
            json.dumps(
                self.payload,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )


@dataclass(frozen=True, slots=True)
class RuntimeListenerEndpoint:
    """The content-free endpoint a transaction expects its runtime to own."""

    host: str
    port: int

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or not self.host.strip():
            raise RuntimeOwnershipError("listener host must be non-empty")
        if any(char in self.host for char in "\r\n\x00"):
            raise RuntimeOwnershipError("listener host contains forbidden characters")
        if isinstance(self.port, bool) or not isinstance(self.port, int):
            raise RuntimeOwnershipError("listener port must be an integer")
        if self.port < 1 or self.port > 65535:
            raise RuntimeOwnershipError("listener port must be in 1..65535")

    def to_mapping(self) -> dict[str, object]:
        return {"host": self.host, "port": self.port}


@dataclass(frozen=True, slots=True)
class RuntimeListenerObservation:
    """One local listening socket and the kernel-reported owning PIDs."""

    endpoint: RuntimeListenerEndpoint
    pids: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.endpoint, RuntimeListenerEndpoint):
            raise TypeError("listener endpoint must be RuntimeListenerEndpoint")
        if not isinstance(self.pids, tuple) or not self.pids:
            raise RuntimeOwnershipError("listener observation must contain owner PIDs")
        if len(set(self.pids)) != len(self.pids):
            raise RuntimeOwnershipError("listener owner PIDs must be unique")
        if any(isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0 for pid in self.pids):
            raise RuntimeOwnershipError("listener owner PIDs must be positive integers")

    def to_mapping(self) -> dict[str, object]:
        return {"endpoint": self.endpoint.to_mapping(), "pids": list(self.pids)}


@dataclass(frozen=True, slots=True)
class RuntimeProcessIdentity:
    """Kernel process identity used for PID-reuse-safe ownership decisions."""

    pid: int
    ppid: int
    pgid: int
    session_id: int
    start_time_ticks: int
    owner_nonce: str | None

    def __post_init__(self) -> None:
        for name in ("pid", "ppid", "pgid", "session_id", "start_time_ticks"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise RuntimeOwnershipError(f"process {name} must be an integer")
            if name == "start_time_ticks":
                if value <= 0:
                    raise RuntimeOwnershipError("process start_time_ticks must be positive")
            elif name == "ppid":
                if value < 0:
                    raise RuntimeOwnershipError(f"process {name} must be non-negative")
            elif value <= 0:
                raise RuntimeOwnershipError(f"process {name} must be positive")
        if self.owner_nonce is not None:
            if not isinstance(self.owner_nonce, str) or not self.owner_nonce.strip():
                raise RuntimeOwnershipError("process owner_nonce must be non-empty or null")
            if any(char in self.owner_nonce for char in "\r\n\x00"):
                raise RuntimeOwnershipError("process owner_nonce contains forbidden characters")

    def to_mapping(self) -> dict[str, object]:
        return {
            "pid": self.pid,
            "ppid": self.ppid,
            "pgid": self.pgid,
            "session_id": self.session_id,
            "start_time_ticks": self.start_time_ticks,
            "owner_nonce": self.owner_nonce,
        }


@dataclass(frozen=True, slots=True)
class RuntimeOwnershipBoundary:
    """The transaction-owned root and the controller/runtime boundary."""

    run_id: str
    owner_nonce: str
    controller_pid: int
    controller_pgid: int
    controller_session_id: int
    root: RuntimeProcessIdentity
    expected_listener: RuntimeListenerEndpoint

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise RuntimeOwnershipError("runtime run_id must be non-empty")
        if any(char in self.run_id for char in "\r\n\x00"):
            raise RuntimeOwnershipError("runtime run_id contains forbidden characters")
        if not isinstance(self.owner_nonce, str) or not self.owner_nonce.strip():
            raise RuntimeOwnershipError("runtime owner_nonce must be non-empty")
        if any(char in self.owner_nonce for char in "\r\n\x00"):
            raise RuntimeOwnershipError("runtime owner_nonce contains forbidden characters")
        for name in ("controller_pid", "controller_pgid", "controller_session_id"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise RuntimeOwnershipError(f"{name} must be a positive integer")
        if not isinstance(self.root, RuntimeProcessIdentity):
            raise TypeError("runtime root must be RuntimeProcessIdentity")
        if self.root.owner_nonce != self.owner_nonce:
            raise RuntimeOwnershipError("runtime root owner nonce does not match boundary")
        if not isinstance(self.expected_listener, RuntimeListenerEndpoint):
            raise TypeError("expected_listener must be RuntimeListenerEndpoint")
        if self.root.pgid == self.controller_pgid:
            raise RuntimeOwnershipError("runtime root shares the controller process group")
        if self.root.session_id == self.controller_session_id:
            raise RuntimeOwnershipError("runtime root shares the controller session")

    @property
    def root_pid(self) -> int:
        return self.root.pid

    @property
    def root_pgid(self) -> int:
        return self.root.pgid

    @property
    def root_session_id(self) -> int:
        return self.root.session_id

    def to_mapping(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "owner_nonce": self.owner_nonce,
            "controller": {
                "pid": self.controller_pid,
                "pgid": self.controller_pgid,
                "session_id": self.controller_session_id,
            },
            "runtime_root": self.root.to_mapping(),
            "expected_listener": self.expected_listener.to_mapping(),
        }


@dataclass(frozen=True, slots=True)
class RuntimeOwnershipAttestation:
    """Positive proof that the expected listener is held by this transaction."""

    boundary: RuntimeOwnershipBoundary
    processes: tuple[RuntimeProcessIdentity, ...]
    listener: RuntimeListenerObservation
    status: Literal["PROVEN"] = "PROVEN"

    def __post_init__(self) -> None:
        if not isinstance(self.boundary, RuntimeOwnershipBoundary):
            raise TypeError("ownership boundary must be RuntimeOwnershipBoundary")
        if self.status != "PROVEN":
            raise RuntimeOwnershipError("unsupported ownership attestation status")
        if not isinstance(self.processes, tuple) or not self.processes:
            raise RuntimeOwnershipError("ownership attestation requires owned processes")
        for process in self.processes:
            if not isinstance(process, RuntimeProcessIdentity):
                raise TypeError("ownership processes must be RuntimeProcessIdentity values")
            if process.owner_nonce != self.boundary.owner_nonce:
                raise RuntimeOwnershipError("owned process nonce does not match boundary")
        if len({item.pid for item in self.processes}) != len(self.processes):
            raise RuntimeOwnershipError("owned process PIDs must be unique")
        if not isinstance(self.listener, RuntimeListenerObservation):
            raise TypeError("ownership listener must be RuntimeListenerObservation")
        if self.listener.endpoint != self.boundary.expected_listener:
            raise RuntimeOwnershipError("attested listener endpoint does not match expected endpoint")
        owned_pids = {item.pid for item in self.processes}
        if not set(self.listener.pids).issubset(owned_pids):
            raise RuntimeOwnershipError("attested listener has an unowned process owner")

    @property
    def owned_pids(self) -> tuple[int, ...]:
        return tuple(item.pid for item in self.processes)

    def to_mapping(self) -> dict[str, object]:
        return {
            "status": self.status,
            "boundary": self.boundary.to_mapping(),
            "owned_processes": [item.to_mapping() for item in self.processes],
            "listener": self.listener.to_mapping(),
        }


CleanupListenerDisposition = Literal[
    "removed",
    "absent",
    "not_owned_preserved",
    "ownership_unavailable",
    "owned_listener_remaining",
]


@dataclass(frozen=True, slots=True)
class RuntimeCleanupReceipt:
    """Content-free, auditable result of exclusive runtime cleanup."""

    run_id: str
    owner_nonce: str
    controller_pid: int
    controller_pgid: int
    controller_session_id: int
    root_pid: int
    root_pgid: int
    root_session_id: int
    expected_listener: RuntimeListenerEndpoint
    graceful_signal_pids: tuple[int, ...]
    escalated_signal_pids: tuple[int, ...]
    remaining_owned_pids: tuple[int, ...]
    listener_disposition: CleanupListenerDisposition
    complete: bool
    idempotent: bool = True
    failure_code: str | None = None

    def __post_init__(self) -> None:
        for name in ("run_id", "owner_nonce"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise RuntimeOwnershipError(f"cleanup {name} must be non-empty")
        for name in (
            "controller_pid",
            "controller_pgid",
            "controller_session_id",
            "root_pid",
            "root_pgid",
            "root_session_id",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise RuntimeOwnershipError(f"cleanup {name} must be positive")
        if not isinstance(self.expected_listener, RuntimeListenerEndpoint):
            raise TypeError("cleanup expected_listener must be RuntimeListenerEndpoint")
        for name in (
            "graceful_signal_pids",
            "escalated_signal_pids",
            "remaining_owned_pids",
        ):
            pids = getattr(self, name)
            if not isinstance(pids, tuple) or len(set(pids)) != len(pids):
                raise RuntimeOwnershipError(f"cleanup {name} must contain unique PID tuples")
            if any(isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0 for pid in pids):
                raise RuntimeOwnershipError(f"cleanup {name} must contain positive PIDs")
        if self.listener_disposition not in {
            "removed",
            "absent",
            "not_owned_preserved",
            "ownership_unavailable",
            "owned_listener_remaining",
        }:
            raise RuntimeOwnershipError("unsupported cleanup listener disposition")
        if not isinstance(self.complete, bool) or not isinstance(self.idempotent, bool):
            raise RuntimeOwnershipError("cleanup completion flags must be boolean")
        if self.failure_code is not None:
            if not isinstance(self.failure_code, str) or not re.fullmatch(
                r"[A-Z][A-Z0-9_]*", self.failure_code
            ):
                raise RuntimeOwnershipError("cleanup failure_code must be a content-free code")

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": 1,
            "run_id": self.run_id,
            "owner_nonce": self.owner_nonce,
            "controller": {
                "pid": self.controller_pid,
                "pgid": self.controller_pgid,
                "session_id": self.controller_session_id,
            },
            "runtime_root": {
                "pid": self.root_pid,
                "pgid": self.root_pgid,
                "session_id": self.root_session_id,
            },
            "expected_listener": self.expected_listener.to_mapping(),
            "graceful_signal_pids": list(self.graceful_signal_pids),
            "escalated_signal_pids": list(self.escalated_signal_pids),
            "remaining_owned_pids": list(self.remaining_owned_pids),
            "listener_disposition": self.listener_disposition,
            "complete": self.complete,
            "idempotent": self.idempotent,
            "failure_code": self.failure_code,
        }


def write_runtime_cleanup_receipt(
    receipt: RuntimeCleanupReceipt,
    *,
    artifact_root: str | Path,
) -> Path:
    """Atomically persist only the content-free cleanup receipt mapping."""

    if not isinstance(receipt, RuntimeCleanupReceipt):
        raise TypeError("receipt must be RuntimeCleanupReceipt")
    root = Path(artifact_root)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeOwnershipError(
            "cannot create cleanup receipt directory",
            code="CLEANUP_RECEIPT_WRITE_FAILED",
        ) from exc
    encoded = (
        json.dumps(
            receipt.to_mapping(),
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")
    digest = hashlib.sha256(encoded).hexdigest()
    path = root / f"runtime-cleanup-{digest}.json"
    try:
        if path.exists():
            if path.read_bytes() != encoded:
                raise RuntimeOwnershipError(
                    "cleanup receipt path contains different content",
                    code="CLEANUP_RECEIPT_CONFLICT",
                )
            return path
        temporary = root / f".{path.name}.tmp-{secrets.token_hex(8)}"
        try:
            temporary.write_bytes(encoded)
            os.replace(temporary, path)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    except RuntimeOwnershipError:
        raise
    except OSError as exc:
        raise RuntimeOwnershipError(
            "cannot persist cleanup receipt",
            code="CLEANUP_RECEIPT_WRITE_FAILED",
        ) from exc
    return path


class ExecutionFreezeBoundary:
    """State machine separating recoverable startup work from semantic calls."""

    def __init__(self) -> None:
        self._phase = "PREFLIGHT"
        self._authority: AuthorityAcquisition | None = None
        self._identity: FrozenExecutionIdentity | None = None
        self._ownership: RuntimeOwnershipAttestation | None = None
        self._freeze_count = 0
        self._semantic_request_count = 0
        self._corrections: list[str] = []

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def authority(self) -> AuthorityAcquisition | None:
        return self._authority

    @property
    def frozen_identity(self) -> FrozenExecutionIdentity | None:
        return self._identity

    @property
    def runtime_ownership(self) -> RuntimeOwnershipAttestation | None:
        return self._ownership

    @property
    def freeze_count(self) -> int:
        return self._freeze_count

    @property
    def semantic_request_count(self) -> int:
        return self._semantic_request_count

    @property
    def corrections(self) -> tuple[str, ...]:
        return tuple(self._corrections)

    def confirm_authority(self, result: AuthorityAcquisition) -> None:
        if self._phase != "PREFLIGHT":
            raise VLLMHostPreflightError(
                "live authority can be confirmed only during PREFLIGHT"
            )
        if not isinstance(result, AuthorityAcquisition):
            raise TypeError("authority result must be AuthorityAcquisition")
        if result.status != "CURRENT_AUTHORITY_CONFIRMED":
            raise VLLMHostPreflightError(
                f"cannot enter execution with {result.status}; current authority is required"
            )
        self._authority = result
        self._phase = "AUTHORITY_READY"

    def mark_admission_ready(self) -> None:
        if self._phase != "AUTHORITY_READY":
            raise VLLMHostPreflightError(
                "GPU admission readiness requires confirmed current authority"
            )
        self._phase = "ADMISSION"

    def attest_runtime_ownership(self, attestation: RuntimeOwnershipAttestation) -> None:
        if self._phase != "ADMISSION":
            raise RuntimeOwnershipError(
                "runtime ownership must be attested after admission and before startup readiness",
            )
        if not isinstance(attestation, RuntimeOwnershipAttestation):
            raise TypeError("runtime ownership must be RuntimeOwnershipAttestation")
        if attestation.status != "PROVEN":
            raise RuntimeOwnershipError("runtime ownership attestation is not proven")
        if self._ownership is not None:
            raise RuntimeOwnershipError("runtime ownership may be attested only once")
        self._ownership = attestation

    def mark_startup_ready(self) -> None:
        if self._phase != "ADMISSION":
            raise VLLMHostPreflightError(
                "startup readiness requires completed GPU admission"
            )
        if self._ownership is None:
            raise RuntimeOwnershipError(
                "runtime process and listener ownership must be proven before startup readiness",
            )
        self._phase = "STARTUP_READY"

    def record_preflight_correction(self, correction: str) -> None:
        self._require_pre_freeze("record a preflight correction")
        if not isinstance(correction, str) or not correction.strip():
            raise VLLMHostPreflightError("preflight correction must be non-empty")
        self._corrections.append(correction)

    def freeze(self, identity: FrozenExecutionIdentity) -> None:
        if self._freeze_count:
            raise VLLMHostPreflightError(
                "execution freeze may occur only once for a run"
            )
        if self._phase != "STARTUP_READY":
            raise VLLMHostPreflightError(
                "execution can freeze only after startup readiness"
            )
        if not isinstance(identity, FrozenExecutionIdentity):
            raise TypeError("freeze identity must be FrozenExecutionIdentity")
        self._identity = identity
        self._freeze_count = 1
        self._phase = "EXECUTION_FROZEN"

    def begin_semantic_request(self) -> None:
        if self._identity is None:
            raise VLLMHostPreflightError(
                "semantic request is forbidden before execution freeze"
            )
        if self._phase == "EXECUTION_FROZEN":
            self._phase = "SEMANTIC_EXECUTION"
        elif self._phase != "SEMANTIC_EXECUTION":
            raise VLLMHostPreflightError(
                "semantic request is not valid in the current execution phase"
            )
        self._semantic_request_count += 1

    def freeze_marker(self) -> dict[str, object]:
        """Return the immutable pre-semantic marker after a successful freeze."""

        if self._identity is None or self._authority is None:
            raise VLLMHostPreflightError(
                "freeze marker is unavailable before execution freeze"
            )
        return {
            "phase": self._phase,
            "freeze_count": self._freeze_count,
            "identity": self._identity.to_mapping(),
            "identity_fingerprint": self._identity.fingerprint,
            "authority": self._authority.to_mapping(),
            "runtime_ownership": self._ownership.to_mapping(),
            "preflight_corrections": list(self._corrections),
        }

    def _require_pre_freeze(self, action: str) -> None:
        if self._phase in {"EXECUTION_FROZEN", "SEMANTIC_EXECUTION"}:
            raise VLLMHostPreflightError(
                f"cannot {action} after execution freeze"
            )


@dataclass(frozen=True, slots=True)
class VLLMLaunchPlan:
    """Exact launch argv after capability-gated preflight negotiation."""

    command: tuple[str, ...]
    supported_flags: tuple[str, ...]
    omitted_flags: tuple[str, ...]

    def to_mapping(self) -> dict[str, object]:
        return {
            "command": list(self.command),
            "supported_flags": list(self.supported_flags),
            "omitted_flags": list(self.omitted_flags),
        }


def discover_vllm_supported_flags(help_text: str) -> frozenset[str]:
    """Extract option names from the current vLLM help surface."""

    if not isinstance(help_text, str):
        raise TypeError("vLLM help text must be a string")
    return frozenset(
        re.findall(r"(?<![A-Za-z0-9_-])--[A-Za-z0-9][A-Za-z0-9-]*", help_text)
    )


def negotiate_vllm_launch(
    *,
    command: Sequence[str],
    supported_flags: Iterable[str],
    non_semantic_flags: Iterable[str] = ("--disable-log-requests",),
) -> VLLMLaunchPlan:
    """Reject unknown semantic options and drop only known legacy observability flags."""

    if isinstance(command, (str, bytes)) or not command:
        raise TypeError("vLLM command must be a non-empty sequence")
    if not all(isinstance(item, str) and item for item in command):
        raise VLLMHostPreflightError("vLLM command must contain non-empty strings")
    supported = frozenset(supported_flags)
    legacy = frozenset(non_semantic_flags)
    if not all(
        isinstance(item, str) and item.startswith("--") for item in supported | legacy
    ):
        raise VLLMHostPreflightError("vLLM option names must start with '--'")

    final: list[str] = []
    omitted: list[str] = []
    for token in command:
        if not token.startswith("--"):
            final.append(token)
            continue
        flag = token.split("=", 1)[0]
        if flag in supported:
            final.append(token)
        elif flag in legacy:
            omitted.append(flag)
        else:
            raise VLLMHostPreflightError(
                f"unsupported semantic vLLM flag before launch: {flag}"
            )
    return VLLMLaunchPlan(
        command=tuple(final),
        supported_flags=tuple(sorted(supported)),
        omitted_flags=tuple(omitted),
    )


@dataclass(frozen=True, slots=True)
class VLLMRuntimePathPlan:
    """Native Linux process/IPC paths kept separate from evidence placement."""

    rpc_base_path: Path
    tmpdir: Path
    path_class: Literal["native_linux"]
    rebased_from_drvfs: bool
    environment: dict[str, str]

    def to_mapping(self) -> dict[str, object]:
        return {
            "rpc_base_path": str(self.rpc_base_path),
            "tmpdir": str(self.tmpdir),
            "path_class": self.path_class,
            "rebased_from_drvfs": self.rebased_from_drvfs,
            "environment": dict(self.environment),
        }


def prepare_vllm_runtime_paths(
    *,
    run_id: str,
    requested_rpc_base_path: str | Path | None = None,
    native_root: str | Path = "/tmp",
) -> VLLMRuntimePathPlan:
    """Create a fresh native run path and prevent drvfs IPC placement."""

    if not isinstance(run_id, str) or not run_id.strip():
        raise VLLMHostPreflightError("vLLM run_id must be non-empty")
    root = Path(native_root)
    if _is_drvfs_path(root):
        raise VLLMHostPreflightError(
            "vLLM native_root must be on a native Linux filesystem"
        )
    try:
        root.mkdir(parents=True, exist_ok=True)
        if root.is_symlink():
            raise VLLMHostPreflightError("vLLM native_root must not be a symlink")
        root = root.resolve()
    except OSError as exc:
        raise VLLMHostPreflightError(
            f"cannot prepare native vLLM runtime root: {exc}"
        ) from exc

    requested = (
        None if requested_rpc_base_path is None else str(requested_rpc_base_path)
    )
    rebased = requested is not None and _is_drvfs_path(Path(requested))
    digest = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:24]
    rpc_path = root / f"relaylm-vllm-rpc-{digest}"
    try:
        rpc_path.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        raise VLLMHostPreflightError(
            f"cannot prepare fresh native vLLM RPC path: {exc}"
        ) from exc
    environment = {
        "VLLM_RPC_BASE_PATH": str(rpc_path),
        "TMPDIR": str(root),
        "TMP": str(root),
        "TEMP": str(root),
    }
    return VLLMRuntimePathPlan(
        rpc_base_path=rpc_path,
        tmpdir=root,
        path_class="native_linux",
        rebased_from_drvfs=rebased,
        environment=environment,
    )


def _is_drvfs_path(path: str | Path) -> bool:
    text = os.fspath(path)
    if re.match(r"^[A-Za-z]:[\\/]", text):
        return True
    parts = Path(text).parts
    return (
        len(parts) >= 3
        and parts[0] == "/"
        and parts[1] == "mnt"
        and len(parts[2]) == 1
        and parts[2].isalpha()
    )


@dataclass(frozen=True, slots=True)
class GPUAdmissionDecision:
    """A pre-freeze mechanical reservation decision with context unchanged."""

    requested_utilization: float
    selected_utilization: float
    fresh_free_memory_bytes: int
    total_memory_bytes: int
    context_window: int
    changed: bool
    reason: str
    reattest_required: bool = True

    def to_mapping(self) -> dict[str, object]:
        return {
            "requested_utilization": self.requested_utilization,
            "selected_utilization": self.selected_utilization,
            "fresh_free_memory_bytes": self.fresh_free_memory_bytes,
            "total_memory_bytes": self.total_memory_bytes,
            "context_window": self.context_window,
            "changed": self.changed,
            "reason": self.reason,
            "reattest_required": self.reattest_required,
        }


def negotiate_gpu_memory_utilization(
    *,
    requested_utilization: float,
    fresh_free_memory_bytes: int,
    total_memory_bytes: int,
    required_context_window: int,
    candidate_utilizations: Iterable[float],
    capacity_recheck: Callable[[float, int], bool] | None = None,
) -> GPUAdmissionDecision:
    """Choose only a lower mechanical reservation while keeping context fixed."""

    _validate_utilization(requested_utilization, "requested_utilization")
    for value, label in (
        (fresh_free_memory_bytes, "fresh_free_memory_bytes"),
        (total_memory_bytes, "total_memory_bytes"),
        (required_context_window, "required_context_window"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise VLLMHostPreflightError(f"{label} must be a positive integer")
    if fresh_free_memory_bytes > total_memory_bytes:
        raise VLLMHostPreflightError(
            "fresh_free_memory_bytes cannot exceed total_memory_bytes"
        )
    if capacity_recheck is None:
        raise VLLMHostPreflightError(
            "GPU admission requires a fresh capacity recheck for the declared context"
        )

    candidates: list[float] = []
    for value in candidate_utilizations:
        _validate_utilization(value, "candidate_utilization")
        if value > requested_utilization:
            raise VLLMHostPreflightError(
                "GPU admission cannot increase the requested reservation"
            )
        if value not in candidates:
            candidates.append(value)
    if not candidates:
        raise VLLMHostPreflightError("GPU admission requires at least one candidate")

    available_fraction = fresh_free_memory_bytes / total_memory_bytes
    for candidate in sorted(candidates, reverse=True):
        if candidate > available_fraction:
            continue
        try:
            preserves_condition = capacity_recheck(candidate, required_context_window)
        except Exception as exc:
            raise VLLMHostPreflightError(
                "GPU capacity recheck failed before execution freeze"
            ) from exc
        if not preserves_condition:
            continue
        return GPUAdmissionDecision(
            requested_utilization=requested_utilization,
            selected_utilization=candidate,
            fresh_free_memory_bytes=fresh_free_memory_bytes,
            total_memory_bytes=total_memory_bytes,
            context_window=required_context_window,
            changed=candidate != requested_utilization,
            reason=(
                "mechanical_gpu_reservation_reduced_before_freeze"
                if candidate != requested_utilization
                else "requested_gpu_reservation_admitted_before_freeze"
            ),
        )

    raise VLLMHostPreflightError(
        "required context window cannot be admitted without changing the declared condition"
    )


def _validate_utilization(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VLLMHostPreflightError(f"{label} must be a number")
    if not math.isfinite(float(value)) or value <= 0 or value > 1:
        raise VLLMHostPreflightError(f"{label} must be finite and in (0, 1]")


@dataclass(frozen=True, slots=True)
class HostProcess:
    pid: int
    argv: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.pid, bool) or not isinstance(self.pid, int) or self.pid <= 0:
            raise VLLMHostPreflightError("process pid must be a positive integer")
        if not self.argv or not all(isinstance(item, str) and item for item in self.argv):
            raise VLLMHostPreflightError("process argv must contain non-empty strings")


RunProcessSnapshot = Callable[..., subprocess.CompletedProcess[str]]


def parse_process_snapshot(snapshot_text: str) -> tuple[HostProcess, ...]:
    if not isinstance(snapshot_text, str):
        raise TypeError("snapshot_text must be a string")

    processes: list[HostProcess] = []
    seen_pids: set[int] = set()
    for line_number, raw_line in enumerate(snapshot_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split(maxsplit=1)
        if len(fields) != 2:
            raise VLLMHostPreflightError(
                f"process snapshot row {line_number} must contain pid and argv"
            )
        pid_text, command_text = fields
        try:
            pid = int(pid_text, 10)
        except ValueError as exc:
            raise VLLMHostPreflightError(
                f"process snapshot row {line_number} has invalid pid"
            ) from exc
        if pid <= 0 or pid in seen_pids:
            raise VLLMHostPreflightError(
                f"process snapshot row {line_number} has invalid or duplicate pid"
            )
        try:
            argv = tuple(shlex.split(command_text, posix=True))
        except ValueError as exc:
            raise VLLMHostPreflightError(
                f"process snapshot row {line_number} has malformed argv"
            ) from exc
        if not argv:
            raise VLLMHostPreflightError(
                f"process snapshot row {line_number} has empty argv"
            )
        processes.append(HostProcess(pid=pid, argv=argv))
        seen_pids.add(pid)
    return tuple(processes)


def _executable_name(value: str) -> str:
    return Path(value).name


def _is_canonical_vllm_process(process: HostProcess) -> bool:
    argv = process.argv
    if argv[0] == "VLLM::EngineCore":
        return True

    executable = _executable_name(argv[0])
    if executable == "vllm" and len(argv) >= 2 and argv[1] == "serve":
        return True

    if executable.startswith("python"):
        for index, value in enumerate(argv[:-1]):
            if value == "-m" and argv[index + 1] == "vllm.entrypoints.openai.api_server":
                return True
    return False


def find_stale_vllm_processes(
    processes: Sequence[HostProcess],
) -> tuple[HostProcess, ...]:
    if not isinstance(processes, Sequence):
        raise TypeError("processes must be a sequence")
    stale: list[HostProcess] = []
    for process in processes:
        if not isinstance(process, HostProcess):
            raise TypeError("processes must contain HostProcess values")
        if _is_canonical_vllm_process(process):
            stale.append(process)
    return tuple(stale)


def snapshot_vllm_processes(
    *,
    run: RunProcessSnapshot = subprocess.run,
) -> tuple[HostProcess, ...]:
    try:
        completed = run(
            ("ps", "-eo", "pid=,args="),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise VLLMHostPreflightError("failed to acquire process snapshot") from exc
    if not isinstance(completed.stdout, str):
        raise VLLMHostPreflightError("process snapshot stdout must be text")
    return parse_process_snapshot(completed.stdout)


RuntimeProcessSnapshot = Callable[[], Sequence[RuntimeProcessIdentity]]
RuntimeListenerSnapshot = Callable[[], Sequence[RuntimeListenerObservation]]
RuntimeSignal = Callable[[int, int], None]


def snapshot_runtime_processes(
    *,
    proc_root: str | Path = "/proc",
) -> tuple[RuntimeProcessIdentity, ...]:
    """Read kernel process identity without relying on command-name matching.

    The owner nonce is read only from the process environment and is used as an
    internal transaction marker.  No command line, environment payload, or
    process output is emitted as ownership evidence.
    """

    root = Path(proc_root)
    try:
        entries = tuple(root.iterdir())
    except OSError as exc:
        raise RuntimeOwnershipError(
            "cannot inspect the process namespace",
            code="PROCESS_SNAPSHOT_UNAVAILABLE",
        ) from exc

    processes: list[RuntimeProcessIdentity] = []
    for entry in entries:
        if not entry.name.isdecimal():
            continue
        identity = _read_runtime_process_identity(entry, owner_nonce=None)
        if identity is not None:
            processes.append(identity)
    return tuple(sorted(processes, key=lambda item: item.pid))


def parse_listener_snapshot(snapshot_text: str) -> tuple[RuntimeListenerObservation, ...]:
    """Parse content-free ``ss`` listener rows, retaining endpoint and PIDs only."""

    if not isinstance(snapshot_text, str):
        raise TypeError("listener snapshot text must be a string")
    listeners: list[RuntimeListenerObservation] = []
    for line_number, raw_line in enumerate(snapshot_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split()
        if fields and fields[0].lower() in {"netid", "state"}:
            continue
        endpoint: RuntimeListenerEndpoint | None = None
        for field in fields:
            parsed = _parse_listener_address(field)
            if parsed is not None:
                endpoint = parsed
                break
        if endpoint is None:
            raise RuntimeOwnershipError(
                f"listener snapshot row {line_number} has no parseable endpoint",
                code="LISTENER_SNAPSHOT_UNAVAILABLE",
            )
        pids = tuple(dict.fromkeys(int(value) for value in re.findall(r"pid=(\d+)", line)))
        if not pids:
            raise RuntimeOwnershipError(
                f"listener snapshot row {line_number} has no kernel owner PID",
                code="PROCESS_OWNERSHIP_UNPROVEN",
            )
        listeners.append(RuntimeListenerObservation(endpoint=endpoint, pids=pids))
    return tuple(listeners)


def snapshot_runtime_listeners(
    *,
    run: RunProcessSnapshot = subprocess.run,
) -> tuple[RuntimeListenerObservation, ...]:
    """Snapshot listening sockets through ``ss`` without a shell search."""

    try:
        completed = run(
            ("ss", "-H", "-ltnp"),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeOwnershipError(
            "failed to acquire listener snapshot",
            code="LISTENER_SNAPSHOT_UNAVAILABLE",
        ) from exc
    if not isinstance(completed.stdout, str):
        raise RuntimeOwnershipError(
            "listener snapshot stdout must be text",
            code="LISTENER_SNAPSHOT_UNAVAILABLE",
        )
    return parse_listener_snapshot(completed.stdout)


class OwnedVLLMRuntime:
    """A directly launched runtime with an auditable, nonce-scoped boundary."""

    def __init__(
        self,
        *,
        process: subprocess.Popen[object],
        boundary: RuntimeOwnershipBoundary,
    ) -> None:
        self.process = process
        self.boundary = boundary
        self._attestation: RuntimeOwnershipAttestation | None = None
        self._cleanup_receipt: RuntimeCleanupReceipt | None = None

    @property
    def attestation(self) -> RuntimeOwnershipAttestation | None:
        return self._attestation

    def attest_startup(
        self,
        *,
        process_snapshot: RuntimeProcessSnapshot | None = None,
        listener_snapshot: RuntimeListenerSnapshot | None = None,
    ) -> RuntimeOwnershipAttestation:
        attestation = attest_vllm_runtime_ownership(
            self.boundary,
            process_snapshot=process_snapshot,
            listener_snapshot=listener_snapshot,
        )
        self._attestation = attestation
        return attestation

    def cleanup(
        self,
        *,
        graceful_timeout: float = 2.0,
        escalation_timeout: float = 2.0,
        poll_interval: float = 0.05,
        process_snapshot: RuntimeProcessSnapshot | None = None,
        listener_snapshot: RuntimeListenerSnapshot | None = None,
        signal_process: RuntimeSignal = os.kill,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        receipt_root: str | Path | None = None,
    ) -> RuntimeCleanupReceipt:
        """Stop only nonce-owned PIDs, then verify process/listener disappearance."""

        if self._cleanup_receipt is not None and self._cleanup_receipt.complete:
            if receipt_root is not None:
                write_runtime_cleanup_receipt(
                    self._cleanup_receipt,
                    artifact_root=receipt_root,
                )
            return self._cleanup_receipt
        _validate_timeout(graceful_timeout, "graceful_timeout")
        _validate_timeout(escalation_timeout, "escalation_timeout")
        _validate_timeout(poll_interval, "poll_interval")
        process_snapshot = process_snapshot or snapshot_runtime_processes
        listener_snapshot = listener_snapshot or snapshot_runtime_listeners

        graceful: list[int] = []
        escalated: list[int] = []
        failure_code: str | None = None
        try:
            owned = _owned_processes(self.boundary, process_snapshot())
        except RuntimeOwnershipError as exc:
            return self._store_cleanup_receipt(
                RuntimeCleanupReceipt(
                    run_id=self.boundary.run_id,
                    owner_nonce=self.boundary.owner_nonce,
                    controller_pid=self.boundary.controller_pid,
                    controller_pgid=self.boundary.controller_pgid,
                    controller_session_id=self.boundary.controller_session_id,
                    root_pid=self.boundary.root_pid,
                    root_pgid=self.boundary.root_pgid,
                    root_session_id=self.boundary.root_session_id,
                    expected_listener=self.boundary.expected_listener,
                    graceful_signal_pids=(),
                    escalated_signal_pids=(),
                    remaining_owned_pids=(),
                    listener_disposition="ownership_unavailable",
                    complete=False,
                    failure_code=exc.code,
                ),
                receipt_root=receipt_root,
            )

        known_owned_pids = {item.pid for item in owned}
        graceful.extend(
            _signal_owned_processes(
                self.boundary,
                owned,
                signum=signal.SIGTERM,
                signal_process=signal_process,
                process_snapshot=process_snapshot,
            )
        )
        _wait_for_owned_processes(
            boundary=self.boundary,
            process_snapshot=process_snapshot,
            timeout=graceful_timeout,
            poll_interval=poll_interval,
            clock=clock,
            sleep=sleep,
        )

        try:
            owned_after_graceful = _owned_processes(self.boundary, process_snapshot())
        except RuntimeOwnershipError as exc:
            failure_code = exc.code
            owned_after_graceful = ()
        if owned_after_graceful:
            known_owned_pids.update(item.pid for item in owned_after_graceful)
            escalated.extend(
                _signal_owned_processes(
                    self.boundary,
                    owned_after_graceful,
                    signum=signal.SIGKILL,
                    signal_process=signal_process,
                    process_snapshot=process_snapshot,
                )
            )
            _wait_for_owned_processes(
                boundary=self.boundary,
                process_snapshot=process_snapshot,
                timeout=escalation_timeout,
                poll_interval=poll_interval,
                clock=clock,
                sleep=sleep,
            )

        try:
            remaining = _owned_processes(self.boundary, process_snapshot())
        except RuntimeOwnershipError as exc:
            failure_code = failure_code or exc.code
            remaining = ()
        remaining_pids = tuple(item.pid for item in remaining)
        known_owned_pids.update(remaining_pids)

        listener_disposition, listener_failure = _cleanup_listener_disposition(
            boundary=self.boundary,
            listener_snapshot=listener_snapshot,
            previously_owned_pids=known_owned_pids | set(graceful) | set(escalated),
        )
        failure_code = failure_code or listener_failure
        complete = (
            not remaining_pids
            and listener_disposition in {"removed", "absent"}
            and failure_code is None
        )
        receipt = RuntimeCleanupReceipt(
            run_id=self.boundary.run_id,
            owner_nonce=self.boundary.owner_nonce,
            controller_pid=self.boundary.controller_pid,
            controller_pgid=self.boundary.controller_pgid,
            controller_session_id=self.boundary.controller_session_id,
            root_pid=self.boundary.root_pid,
            root_pgid=self.boundary.root_pgid,
            root_session_id=self.boundary.root_session_id,
            expected_listener=self.boundary.expected_listener,
            graceful_signal_pids=tuple(dict.fromkeys(graceful)),
            escalated_signal_pids=tuple(dict.fromkeys(escalated)),
            remaining_owned_pids=remaining_pids,
            listener_disposition=listener_disposition,
            complete=complete,
            failure_code=failure_code,
        )
        return self._store_cleanup_receipt(receipt, receipt_root=receipt_root)

    def _store_cleanup_receipt(
        self,
        receipt: RuntimeCleanupReceipt,
        *,
        receipt_root: str | Path | None = None,
    ) -> RuntimeCleanupReceipt:
        if receipt_root is not None:
            write_runtime_cleanup_receipt(receipt, artifact_root=receipt_root)
        if receipt.complete:
            self._cleanup_receipt = receipt
        return receipt


def launch_owned_vllm_runtime(
    command: Sequence[str],
    *,
    run_id: str,
    expected_listener: RuntimeListenerEndpoint,
    owner_nonce: str | None = None,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
    start_new_session: bool = True,
    popen_factory: Callable[..., subprocess.Popen[object]] = subprocess.Popen,
    stdout: object | None = None,
    stderr: object | None = None,
) -> OwnedVLLMRuntime:
    """Launch a direct child in a fresh session and attach a unique owner nonce.

    ``start_new_session`` is an implementation detail of the current POSIX
    boundary.  The acceptance contract is the resulting auditable ownership,
    not the spelling of the launcher or a shell utility.
    """

    _validate_direct_command(command)
    if not isinstance(expected_listener, RuntimeListenerEndpoint):
        raise TypeError("expected_listener must be RuntimeListenerEndpoint")
    if not isinstance(start_new_session, bool):
        raise TypeError("start_new_session must be boolean")
    if not callable(popen_factory):
        raise TypeError("popen_factory must be callable")
    resolved_nonce = secrets.token_hex(16) if owner_nonce is None else owner_nonce
    _validate_owner_nonce(resolved_nonce)
    _validate_run_id(run_id)
    child_env = os.environ.copy()
    if env is not None:
        for key, value in env.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise RuntimeOwnershipError("runtime environment must contain strings")
        child_env.update(env)
    child_env[RUNTIME_OWNER_NONCE_ENV] = resolved_nonce
    child_env[RUNTIME_OWNER_RUN_ID_ENV] = run_id

    kwargs: dict[str, object] = {
        "env": child_env,
        "shell": False,
        "start_new_session": start_new_session,
    }
    if cwd is not None:
        kwargs["cwd"] = os.fspath(cwd)
    if stdout is not None:
        kwargs["stdout"] = stdout
    if stderr is not None:
        kwargs["stderr"] = stderr
    try:
        process = popen_factory(tuple(command), **kwargs)
    except OSError as exc:
        raise RuntimeOwnershipError(
            "runtime launch failed",
            code="RUNTIME_LAUNCH_FAILED",
        ) from exc

    controller_pid = os.getpid()
    controller_pgid = os.getpgrp()
    try:
        controller_session_id = os.getsid(0)
    except OSError as exc:
        _cleanup_unproven_launch(process, resolved_nonce)
        raise RuntimeOwnershipError(
            "controller session identity is unavailable",
            code="PROCESS_OWNERSHIP_UNPROVEN",
        ) from exc

    root = _read_runtime_process_identity(
        Path("/proc") / str(process.pid),
        owner_nonce=resolved_nonce,
    )
    if root is None or (
        root.pgid == controller_pgid or root.session_id == controller_session_id
    ):
        _cleanup_unproven_launch(process, resolved_nonce)
        raise RuntimeOwnershipError(
            "runtime root is not in a distinct owned process/session boundary",
        )
    boundary = RuntimeOwnershipBoundary(
        run_id=run_id,
        owner_nonce=resolved_nonce,
        controller_pid=controller_pid,
        controller_pgid=controller_pgid,
        controller_session_id=controller_session_id,
        root=root,
        expected_listener=expected_listener,
    )
    return OwnedVLLMRuntime(process=process, boundary=boundary)


def attest_vllm_runtime_ownership(
    boundary: RuntimeOwnershipBoundary,
    *,
    process_snapshot: RuntimeProcessSnapshot | None = None,
    listener_snapshot: RuntimeListenerSnapshot | None = None,
) -> RuntimeOwnershipAttestation:
    """Prove current owned processes and endpoint listener before startup ready."""

    if not isinstance(boundary, RuntimeOwnershipBoundary):
        raise TypeError("boundary must be RuntimeOwnershipBoundary")
    process_snapshot = process_snapshot or snapshot_runtime_processes
    listener_snapshot = listener_snapshot or snapshot_runtime_listeners
    try:
        processes = _owned_processes(boundary, process_snapshot())
    except RuntimeOwnershipError:
        raise
    if not processes:
        raise RuntimeOwnershipError("no live process carries the transaction owner nonce")

    try:
        listeners = tuple(listener_snapshot())
    except RuntimeOwnershipError:
        raise
    except Exception as exc:
        raise RuntimeOwnershipError(
            "listener snapshot failed",
            code="LISTENER_SNAPSHOT_UNAVAILABLE",
        ) from exc
    matching = tuple(
        item for item in listeners if _listener_matches(boundary.expected_listener, item.endpoint)
    )
    if not matching:
        raise RuntimeOwnershipError(
            "expected runtime listener is not ready",
            code="RUNTIME_NOT_READY",
        )
    if len(matching) != 1:
        raise RuntimeOwnershipError("expected listener has an ambiguous socket owner")
    listener = matching[0]
    owned_pids = {item.pid for item in processes}
    if not set(listener.pids).issubset(owned_pids):
        raise RuntimeOwnershipError("expected listener is held by an unrelated process")
    return RuntimeOwnershipAttestation(
        boundary=boundary,
        processes=processes,
        listener=listener,
    )


def wait_for_vllm_runtime_readiness(
    runtime: OwnedVLLMRuntime,
    *,
    timeout: float = 10.0,
    poll_interval: float = 0.05,
    process_snapshot: RuntimeProcessSnapshot | None = None,
    listener_snapshot: RuntimeListenerSnapshot | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> RuntimeOwnershipAttestation:
    """Poll only for a listener owned by ``runtime``; stale listeners fail closed."""

    if not isinstance(runtime, OwnedVLLMRuntime):
        raise TypeError("runtime must be OwnedVLLMRuntime")
    _validate_timeout(timeout, "timeout")
    _validate_timeout(poll_interval, "poll_interval")
    process_snapshot = process_snapshot or snapshot_runtime_processes
    listener_snapshot = listener_snapshot or snapshot_runtime_listeners
    deadline = clock() + timeout
    while True:
        try:
            return runtime.attest_startup(
                process_snapshot=process_snapshot,
                listener_snapshot=listener_snapshot,
            )
        except RuntimeOwnershipError as exc:
            if exc.code != "RUNTIME_NOT_READY":
                raise
            if clock() >= deadline:
                raise RuntimeOwnershipError(
                    "expected runtime listener did not become ready",
                    code="RUNTIME_NOT_READY",
                ) from exc
            sleep(min(poll_interval, max(0.0, deadline - clock())))


def _read_runtime_process_identity(
    entry: Path,
    *,
    owner_nonce: str | None,
) -> RuntimeProcessIdentity | None:
    try:
        stat_text = (entry / "stat").read_text(encoding="utf-8")
        closing = stat_text.rfind(")")
        if closing < 0:
            return None
        fields = stat_text[closing + 2 :].split()
        if len(fields) < 20:
            return None
        state = fields[0]
        if state == "Z":
            return None
        pid = int(entry.name, 10)
        ppid = int(fields[1], 10)
        pgid = int(fields[2], 10)
        session_id = int(fields[3], 10)
        start_time_ticks = int(fields[19], 10)
    except (OSError, UnicodeError, ValueError):
        return None
    observed_nonce = _read_runtime_owner_nonce(entry)
    if owner_nonce is not None and observed_nonce != owner_nonce:
        return None
    try:
        return RuntimeProcessIdentity(
            pid=pid,
            ppid=ppid,
            pgid=pgid,
            session_id=session_id,
            start_time_ticks=start_time_ticks,
            owner_nonce=observed_nonce,
        )
    except RuntimeOwnershipError:
        # Kernel/system entries such as PID 1/2 can expose zero process-group
        # fields in a container namespace.  They are not runtime evidence;
        # an owned entry that cannot be represented simply disappears from
        # the snapshot and therefore fails closed at attestation/cleanup.
        return None


def _read_runtime_owner_nonce(entry: Path) -> str | None:
    try:
        environment = (entry / "environ").read_bytes().split(b"\x00")
    except (OSError, UnicodeError):
        return None
    prefix = f"{RUNTIME_OWNER_NONCE_ENV}=".encode("utf-8")
    for item in environment:
        if item.startswith(prefix):
            try:
                value = item[len(prefix) :].decode("utf-8")
            except UnicodeError:
                return None
            return value if value else None
    return None


def _owned_processes(
    boundary: RuntimeOwnershipBoundary,
    processes: Sequence[RuntimeProcessIdentity],
) -> tuple[RuntimeProcessIdentity, ...]:
    if not isinstance(processes, Sequence):
        raise RuntimeOwnershipError(
            "process snapshot must be a sequence",
            code="PROCESS_SNAPSHOT_UNAVAILABLE",
        )
    owned: list[RuntimeProcessIdentity] = []
    seen: set[int] = set()
    for process in processes:
        if not isinstance(process, RuntimeProcessIdentity):
            raise RuntimeOwnershipError(
                "process snapshot contains an invalid identity",
                code="PROCESS_SNAPSHOT_UNAVAILABLE",
            )
        if process.owner_nonce != boundary.owner_nonce:
            continue
        if process.pid in seen:
            raise RuntimeOwnershipError(
                "process snapshot contains duplicate owner PID",
                code="PROCESS_SNAPSHOT_UNAVAILABLE",
            )
        if process.pid == boundary.root_pid and process.start_time_ticks != boundary.root.start_time_ticks:
            raise RuntimeOwnershipError(
                "runtime root PID was reused with a different start-time identity",
                code="PROCESS_OWNERSHIP_UNPROVEN",
            )
        if process.pid == boundary.root_pid and (
            process.pgid != boundary.root.pgid
            or process.session_id != boundary.root.session_id
        ):
            raise RuntimeOwnershipError(
                "runtime root process/session boundary drifted",
                code="PROCESS_OWNERSHIP_UNPROVEN",
            )
        owned.append(process)
        seen.add(process.pid)
    return tuple(sorted(owned, key=lambda item: item.pid))


def _signal_owned_processes(
    boundary: RuntimeOwnershipBoundary,
    candidates: Sequence[RuntimeProcessIdentity],
    *,
    signum: int,
    signal_process: RuntimeSignal,
    process_snapshot: RuntimeProcessSnapshot,
) -> tuple[int, ...]:
    try:
        current = {
            item.pid: item
            for item in _owned_processes(boundary, process_snapshot())
        }
    except RuntimeOwnershipError:
        return ()
    signalled: list[int] = []
    for candidate in candidates:
        live = current.get(candidate.pid)
        if live is None or live.start_time_ticks != candidate.start_time_ticks:
            continue
        try:
            _send_process_signal(
                live,
                signum=signum,
                signal_process=signal_process,
            )
        except (ProcessLookupError, PermissionError, OSError):
            continue
        signalled.append(live.pid)
    return tuple(signalled)


def _send_process_signal(
    process: RuntimeProcessIdentity,
    *,
    signum: int,
    signal_process: RuntimeSignal,
) -> None:
    pidfd_open = getattr(os, "pidfd_open", None)
    pidfd_send_signal = getattr(signal, "pidfd_send_signal", None)
    if callable(pidfd_open) and callable(pidfd_send_signal) and signal_process is os.kill:
        fd = pidfd_open(process.pid)
        try:
            pidfd_send_signal(fd, signum)
        finally:
            os.close(fd)
        return
    signal_process(process.pid, signum)


def _wait_for_owned_processes(
    *,
    boundary: RuntimeOwnershipBoundary,
    process_snapshot: RuntimeProcessSnapshot,
    timeout: float,
    poll_interval: float,
    clock: Callable[[], float],
    sleep: Callable[[float], None],
) -> None:
    deadline = clock() + timeout
    while True:
        try:
            if not _owned_processes(boundary, process_snapshot()):
                return
        except RuntimeOwnershipError:
            return
        if clock() >= deadline:
            return
        sleep(min(poll_interval, max(0.0, deadline - clock())))


def _cleanup_listener_disposition(
    *,
    boundary: RuntimeOwnershipBoundary,
    listener_snapshot: RuntimeListenerSnapshot,
    previously_owned_pids: set[int],
) -> tuple[CleanupListenerDisposition, str | None]:
    try:
        listeners = tuple(listener_snapshot())
    except RuntimeOwnershipError as exc:
        return "ownership_unavailable", exc.code
    except Exception:
        return "ownership_unavailable", "LISTENER_SNAPSHOT_UNAVAILABLE"
    matching = tuple(
        item for item in listeners if _listener_matches(boundary.expected_listener, item.endpoint)
    )
    if not matching:
        return "absent", None
    if len(matching) != 1:
        return "ownership_unavailable", "PROCESS_OWNERSHIP_UNPROVEN"
    listener = matching[0]
    if set(listener.pids).issubset(previously_owned_pids):
        return "owned_listener_remaining", "OWNED_LISTENER_REMAINS"
    return "not_owned_preserved", "UNRELATED_LISTENER_PRESERVED"


def _listener_matches(
    expected: RuntimeListenerEndpoint,
    observed: RuntimeListenerEndpoint,
) -> bool:
    if expected.port != observed.port:
        return False
    expected_host = expected.host.strip().lower()
    observed_host = observed.host.strip().lower()
    if expected_host == observed_host:
        return True
    if observed_host in {"*", "0.0.0.0", "::", "[::]"}:
        return True
    if expected_host == "localhost" and observed_host in {"127.0.0.1", "::1", "[::1]"}:
        return True
    return False


def _parse_listener_address(value: str) -> RuntimeListenerEndpoint | None:
    if value.startswith("["):
        closing = value.find("]:")
        if closing < 0:
            return None
        host = value[1:closing]
        port_text = value[closing + 2 :]
    else:
        if ":" not in value:
            return None
        host, port_text = value.rsplit(":", 1)
    if not port_text.isdecimal() or not host:
        return None
    try:
        return RuntimeListenerEndpoint(host=host, port=int(port_text, 10))
    except RuntimeOwnershipError:
        return None


def _validate_direct_command(command: Sequence[str]) -> None:
    if isinstance(command, (str, bytes)) or not command:
        raise TypeError("runtime command must be a non-empty direct sequence")
    if not all(isinstance(item, str) and item for item in command):
        raise RuntimeOwnershipError("runtime command must contain non-empty strings")


def _validate_owner_nonce(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeOwnershipError("runtime owner_nonce must be non-empty")
    if any(char in value for char in "\r\n\x00"):
        raise RuntimeOwnershipError("runtime owner_nonce contains forbidden characters")


def _validate_run_id(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeOwnershipError("runtime run_id must be non-empty")
    if any(char in value for char in "\r\n\x00"):
        raise RuntimeOwnershipError("runtime run_id contains forbidden characters")


def _validate_timeout(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a number")
    if not math.isfinite(float(value)) or value < 0:
        raise ValueError(f"{label} must be finite and non-negative")


def _cleanup_unproven_launch(process: subprocess.Popen[object], owner_nonce: str) -> None:
    """Use only the direct child handle or nonce-matched descendants on launch failure."""

    try:
        process.terminate()
        process.wait(timeout=0.5)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
            process.wait(timeout=0.5)
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        processes = snapshot_runtime_processes()
    except RuntimeOwnershipError:
        return
    for item in processes:
        if item.owner_nonce != owner_nonce:
            continue
        try:
            _send_process_signal(item, signum=signal.SIGKILL, signal_process=os.kill)
        except (ProcessLookupError, PermissionError, OSError):
            pass


def _build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description=(
            "Fail closed when a canonical stale vLLM process is present "
            "before a bounded actual-model launch transaction."
        )
    )


def main(argv: list[str] | None = None) -> int:
    _build_parser().parse_args(argv)
    try:
        stale = find_stale_vllm_processes(snapshot_vllm_processes())
    except VLLMHostPreflightError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if stale:
        for process in stale:
            print(f"stale vLLM process: pid={process.pid}", file=sys.stderr)
        return 2

    print("vLLM process preflight: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
