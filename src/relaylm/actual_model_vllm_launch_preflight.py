from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable, Mapping
from typing import Callable, Literal, Sequence


class VLLMHostPreflightError(ValueError):
    """The bounded vLLM host-preflight process snapshot is not admissible."""


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


class ExecutionFreezeBoundary:
    """State machine separating recoverable startup work from semantic calls."""

    def __init__(self) -> None:
        self._phase = "PREFLIGHT"
        self._authority: AuthorityAcquisition | None = None
        self._identity: FrozenExecutionIdentity | None = None
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

    def mark_startup_ready(self) -> None:
        if self._phase != "ADMISSION":
            raise VLLMHostPreflightError(
                "startup readiness requires completed GPU admission"
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
