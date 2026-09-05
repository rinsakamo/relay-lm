from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from relaylm.actual_model_vllm_launch_preflight import discover_vllm_supported_flags


class VLLMCapabilityProbeError(ValueError):
    """The provider-free vLLM capability probe contract is invalid."""


VLLMCapabilityProbeStatus = Literal[
    "CAPABILITY_READY",
    "NONZERO_EXIT",
    "EMPTY_HELP",
    "TIMEOUT",
    "SPAWN_ERROR",
]

_TRANSIENT_DIAGNOSTIC_LIMIT = 512


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise VLLMCapabilityProbeError("probe receipt must be canonical JSON") from exc


def _sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _sha256_json(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}"


def _validate_text_token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VLLMCapabilityProbeError(f"{name} must be a non-empty string")
    if any(char in value for char in "\r\n\x00"):
        raise VLLMCapabilityProbeError(f"{name} contains forbidden characters")
    return value


def _normalize_command(command: Sequence[str]) -> tuple[str, str, str]:
    if isinstance(command, (str, bytes)):
        raise VLLMCapabilityProbeError("capability command must be a token sequence")
    tokens = tuple(command)
    if len(tokens) != 3:
        raise VLLMCapabilityProbeError(
            "capability command must be exactly '<vllm> serve --help=all'"
        )
    executable = _validate_text_token(tokens[0], "capability executable")
    subcommand = _validate_text_token(tokens[1], "capability subcommand")
    help_flag = _validate_text_token(tokens[2], "capability help flag")
    executable_path = Path(executable)
    if not executable_path.is_absolute():
        raise VLLMCapabilityProbeError("capability executable must be an absolute path")
    if executable_path.name != "vllm":
        raise VLLMCapabilityProbeError("capability executable basename must be 'vllm'")
    if subcommand != "serve" or help_flag != "--help=all":
        raise VLLMCapabilityProbeError(
            "capability command must be exactly '<vllm> serve --help=all'"
        )
    return executable, subcommand, help_flag


def _normalize_environment_delta(
    environment: Mapping[str, str] | None,
) -> tuple[dict[str, str], tuple[str, ...]]:
    if environment is None:
        return {}, ()
    if not isinstance(environment, Mapping):
        raise TypeError("environment must be a mapping or None")
    normalized: dict[str, str] = {}
    for key, value in environment.items():
        key = _validate_text_token(key, "environment key")
        if not isinstance(value, str):
            raise VLLMCapabilityProbeError("environment values must be strings")
        if "\x00" in value:
            raise VLLMCapabilityProbeError("environment values must not contain NUL")
        normalized[key] = value
    return normalized, tuple(sorted(normalized))


def _validate_timeout(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VLLMCapabilityProbeError("timeout_seconds must be numeric")
    timeout = float(value)
    if not math.isfinite(timeout) or timeout <= 0:
        raise VLLMCapabilityProbeError("timeout_seconds must be finite and positive")
    return timeout


def _optional_int(value: object, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise VLLMCapabilityProbeError(f"{name} must be an integer or null")
    return value


def _required_nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise VLLMCapabilityProbeError(f"{name} must be a non-negative integer")
    return value


def _bounded_transient_diagnostic(
    *,
    status: VLLMCapabilityProbeStatus,
    stdout: str,
    stderr: str,
    source: str | None = None,
) -> str | None:
    if status == "CAPABILITY_READY":
        return None
    candidate = source
    if candidate is None:
        candidate = stderr if stderr.strip() else stdout
    if not candidate:
        return None
    printable = "".join(
        char if char.isprintable() or char.isspace() else " " for char in candidate
    )
    normalized = " ".join(printable.split())
    if not normalized:
        return None
    return normalized[:_TRANSIENT_DIAGNOSTIC_LIMIT]


@dataclass(frozen=True, slots=True)
class VLLMCapabilityProbeResult:
    """Durable-content-free probe result with optional transient local diagnostics."""

    status: VLLMCapabilityProbeStatus
    command: tuple[str, str, str]
    command_digest: str
    environment_keys: tuple[str, ...]
    environment_key_digest: str
    returncode: int | None
    stdout_digest: str
    stderr_digest: str
    stdout_bytes: int
    stderr_bytes: int
    help_digest: str | None
    supported_flags: tuple[str, ...]
    supported_flags_digest: str | None
    timed_out: bool
    cleanup_complete: bool
    failure_type: str | None
    transient_diagnostic: str | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if self.status not in {
            "CAPABILITY_READY",
            "NONZERO_EXIT",
            "EMPTY_HELP",
            "TIMEOUT",
            "SPAWN_ERROR",
        }:
            raise VLLMCapabilityProbeError("unsupported capability probe status")
        if self.command_digest != _sha256_json(list(self.command)):
            raise VLLMCapabilityProbeError("capability command digest mismatch")
        if self.environment_key_digest != _sha256_json(list(self.environment_keys)):
            raise VLLMCapabilityProbeError("capability environment-key digest mismatch")
        if self.supported_flags:
            expected_flags_digest = _sha256_json(list(self.supported_flags))
            if self.supported_flags_digest != expected_flags_digest:
                raise VLLMCapabilityProbeError("supported-flags digest mismatch")
        elif self.supported_flags_digest is not None:
            raise VLLMCapabilityProbeError("empty supported flags must not carry a digest")
        if self.status == "CAPABILITY_READY":
            if self.returncode != 0 or not self.help_digest or not self.supported_flags_digest:
                raise VLLMCapabilityProbeError("ready capability probe is incomplete")
            if not self.supported_flags:
                raise VLLMCapabilityProbeError("ready capability probe requires supported flags")
            if self.transient_diagnostic is not None:
                raise VLLMCapabilityProbeError("ready capability probe must not carry a diagnostic")
        elif self.supported_flags:
            raise VLLMCapabilityProbeError("non-ready capability probe must not expose flags")
        if self.status == "TIMEOUT" and not self.timed_out:
            raise VLLMCapabilityProbeError("timeout status requires timed_out")
        if self.status == "SPAWN_ERROR" and self.returncode is not None:
            raise VLLMCapabilityProbeError("spawn error must not expose a returncode")
        if self.stdout_bytes < 0 or self.stderr_bytes < 0:
            raise VLLMCapabilityProbeError("probe byte counts must be non-negative")
        if self.transient_diagnostic is not None:
            if not isinstance(self.transient_diagnostic, str):
                raise TypeError("transient_diagnostic must be a string or None")
            if not self.transient_diagnostic:
                raise VLLMCapabilityProbeError("transient diagnostic must not be empty")
            if len(self.transient_diagnostic) > _TRANSIENT_DIAGNOSTIC_LIMIT:
                raise VLLMCapabilityProbeError("transient diagnostic exceeds bound")
            if " ".join(self.transient_diagnostic.split()) != self.transient_diagnostic:
                raise VLLMCapabilityProbeError("transient diagnostic must be normalized")

    @property
    def receipt_id(self) -> str:
        return _sha256_json(self.to_mapping(include_id=False))

    def to_mapping(self, *, include_id: bool = True) -> dict[str, object]:
        mapping: dict[str, object] = {
            "format_version": 1,
            "kind": "vllm_capability_probe",
            "status": self.status,
            "command": list(self.command),
            "command_digest": self.command_digest,
            "environment_keys": list(self.environment_keys),
            "environment_key_digest": self.environment_key_digest,
            "returncode": self.returncode,
            "stdout_digest": self.stdout_digest,
            "stderr_digest": self.stderr_digest,
            "stdout_bytes": self.stdout_bytes,
            "stderr_bytes": self.stderr_bytes,
            "help_digest": self.help_digest,
            "supported_flags": list(self.supported_flags),
            "supported_flags_digest": self.supported_flags_digest,
            "timed_out": self.timed_out,
            "cleanup_complete": self.cleanup_complete,
            "failure_type": self.failure_type,
        }
        if include_id:
            mapping["receipt_id"] = self.receipt_id
        return mapping

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "VLLMCapabilityProbeResult":
        if not isinstance(value, Mapping):
            raise TypeError("probe receipt must be a mapping")
        if value.get("format_version") != 1 or value.get("kind") != "vllm_capability_probe":
            raise VLLMCapabilityProbeError("unsupported capability probe receipt")
        command = value.get("command")
        environment_keys = value.get("environment_keys")
        supported_flags = value.get("supported_flags")
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            raise VLLMCapabilityProbeError("receipt command must be a string list")
        if not isinstance(environment_keys, list) or not all(
            isinstance(item, str) for item in environment_keys
        ):
            raise VLLMCapabilityProbeError("receipt environment_keys must be a string list")
        if not isinstance(supported_flags, list) or not all(
            isinstance(item, str) for item in supported_flags
        ):
            raise VLLMCapabilityProbeError("receipt supported_flags must be a string list")
        result = cls(
            status=value.get("status"),  # type: ignore[arg-type]
            command=_normalize_command(command),
            command_digest=str(value.get("command_digest")),
            environment_keys=tuple(environment_keys),
            environment_key_digest=str(value.get("environment_key_digest")),
            returncode=_optional_int(value.get("returncode"), "returncode"),
            stdout_digest=str(value.get("stdout_digest")),
            stderr_digest=str(value.get("stderr_digest")),
            stdout_bytes=_required_nonnegative_int(value.get("stdout_bytes"), "stdout_bytes"),
            stderr_bytes=_required_nonnegative_int(value.get("stderr_bytes"), "stderr_bytes"),
            help_digest=value.get("help_digest") if isinstance(value.get("help_digest"), str) else None,
            supported_flags=tuple(supported_flags),
            supported_flags_digest=(
                value.get("supported_flags_digest")
                if isinstance(value.get("supported_flags_digest"), str)
                else None
            ),
            timed_out=value.get("timed_out") is True,
            cleanup_complete=value.get("cleanup_complete") is True,
            failure_type=value.get("failure_type") if isinstance(value.get("failure_type"), str) else None,
        )
        receipt_id = value.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id:
            raise VLLMCapabilityProbeError("capability probe receipt id is required")
        if receipt_id != result.receipt_id:
            raise VLLMCapabilityProbeError("capability probe receipt id mismatch")
        return result


def _decode_stream(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _result(
    *,
    status: VLLMCapabilityProbeStatus,
    command: tuple[str, str, str],
    environment_keys: tuple[str, ...],
    returncode: int | None,
    stdout: str,
    stderr: str,
    help_text: str | None = None,
    supported_flags: Sequence[str] = (),
    timed_out: bool = False,
    cleanup_complete: bool = True,
    failure_type: str | None = None,
    transient_diagnostic_source: str | None = None,
) -> VLLMCapabilityProbeResult:
    flags = tuple(sorted(set(supported_flags)))
    return VLLMCapabilityProbeResult(
        status=status,
        command=command,
        command_digest=_sha256_json(list(command)),
        environment_keys=environment_keys,
        environment_key_digest=_sha256_json(list(environment_keys)),
        returncode=returncode,
        stdout_digest=_sha256_text(stdout),
        stderr_digest=_sha256_text(stderr),
        stdout_bytes=len(stdout.encode("utf-8")),
        stderr_bytes=len(stderr.encode("utf-8")),
        help_digest=_sha256_text(help_text) if help_text is not None else None,
        supported_flags=flags,
        supported_flags_digest=_sha256_json(list(flags)) if flags else None,
        timed_out=timed_out,
        cleanup_complete=cleanup_complete,
        failure_type=failure_type,
        transient_diagnostic=_bounded_transient_diagnostic(
            status=status,
            stdout=stdout,
            stderr=stderr,
            source=transient_diagnostic_source,
        ),
    )


def _cleanup_timed_out_probe(
    process: subprocess.Popen[object],
    *,
    cleanup_timeout: float,
) -> tuple[str, str, bool]:
    stdout = ""
    stderr = ""
    try:
        process.terminate()
        try:
            tail_stdout, tail_stderr = process.communicate(timeout=cleanup_timeout)
        except subprocess.TimeoutExpired as exc:
            stdout += _decode_stream(exc.stdout)
            stderr += _decode_stream(exc.stderr)
            process.kill()
            try:
                tail_stdout, tail_stderr = process.communicate(timeout=cleanup_timeout)
            except subprocess.TimeoutExpired as kill_exc:
                stdout += _decode_stream(kill_exc.stdout)
                stderr += _decode_stream(kill_exc.stderr)
                return stdout, stderr, process.poll() is not None
        stdout += _decode_stream(tail_stdout)
        stderr += _decode_stream(tail_stderr)
    except (OSError, subprocess.SubprocessError):
        return stdout, stderr, process.poll() is not None
    return stdout, stderr, process.poll() is not None


def probe_vllm_capability_surface(
    command: Sequence[str],
    *,
    environment: Mapping[str, str] | None = None,
    timeout_seconds: float = 30.0,
    popen_factory: Callable[..., subprocess.Popen[object]] = subprocess.Popen,
    cleanup_timeout_seconds: float = 2.0,
) -> VLLMCapabilityProbeResult:
    """Run exactly one direct provider-free ``vllm serve --help=all`` probe.

    The caller chooses the exploratory environment candidate. This function owns
    direct execution, bounded cleanup, classification, help parsing, durable
    content-free identity, and one bounded transient local diagnostic. It never
    treats a probe failure as semantic/model-quality evidence and never mutates
    the caller's process environment.
    """

    normalized_command = _normalize_command(command)
    environment_delta, environment_keys = _normalize_environment_delta(environment)
    timeout = _validate_timeout(timeout_seconds)
    cleanup_timeout = _validate_timeout(cleanup_timeout_seconds)
    child_environment = os.environ.copy()
    child_environment.update(environment_delta)

    try:
        process = popen_factory(
            normalized_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=child_environment,
            shell=False,
            text=True,
        )
    except OSError as exc:
        return _result(
            status="SPAWN_ERROR",
            command=normalized_command,
            environment_keys=environment_keys,
            returncode=None,
            stdout="",
            stderr="",
            failure_type=type(exc).__name__,
            transient_diagnostic_source=str(exc),
        )

    try:
        stdout_raw, stderr_raw = process.communicate(timeout=timeout)
        stdout = _decode_stream(stdout_raw)
        stderr = _decode_stream(stderr_raw)
    except subprocess.TimeoutExpired as exc:
        stdout = _decode_stream(exc.stdout)
        stderr = _decode_stream(exc.stderr)
        tail_stdout, tail_stderr, cleanup_complete = _cleanup_timed_out_probe(
            process,
            cleanup_timeout=cleanup_timeout,
        )
        stdout += tail_stdout
        stderr += tail_stderr
        return _result(
            status="TIMEOUT",
            command=normalized_command,
            environment_keys=environment_keys,
            returncode=process.poll(),
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
            cleanup_complete=cleanup_complete,
            failure_type="TimeoutExpired",
        )

    returncode = process.returncode
    if returncode != 0:
        return _result(
            status="NONZERO_EXIT",
            command=normalized_command,
            environment_keys=environment_keys,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            failure_type="NonZeroExit",
        )

    help_text = stdout.strip()
    if not help_text:
        return _result(
            status="EMPTY_HELP",
            command=normalized_command,
            environment_keys=environment_keys,
            returncode=0,
            stdout=stdout,
            stderr=stderr,
            help_text="",
            failure_type="EmptyHelpSurface",
        )

    supported_flags = discover_vllm_supported_flags(help_text)
    if not supported_flags:
        return _result(
            status="EMPTY_HELP",
            command=normalized_command,
            environment_keys=environment_keys,
            returncode=0,
            stdout=stdout,
            stderr=stderr,
            help_text=help_text,
            failure_type="NoSupportedFlags",
        )
    return _result(
        status="CAPABILITY_READY",
        command=normalized_command,
        environment_keys=environment_keys,
        returncode=0,
        stdout=stdout,
        stderr=stderr,
        help_text=help_text,
        supported_flags=supported_flags,
    )


def write_vllm_capability_probe_receipt(
    result: VLLMCapabilityProbeResult,
    *,
    artifact_root: str | Path,
) -> Path:
    """Atomically persist one content-free probe receipt outside repository policy."""

    if not isinstance(result, VLLMCapabilityProbeResult):
        raise TypeError("result must be VLLMCapabilityProbeResult")
    root = Path(artifact_root)
    if not root.is_dir():
        raise VLLMCapabilityProbeError("artifact_root must be an existing directory")
    destination = root / "vllm-capability-probe.json"
    if destination.exists():
        raise VLLMCapabilityProbeError("capability probe receipt already exists")
    temporary = root / f".{destination.name}.tmp-{os.getpid()}"
    payload = _canonical_json(result.to_mapping()) + b"\n"
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return destination


def load_vllm_capability_probe_receipt(path: str | Path) -> VLLMCapabilityProbeResult:
    """Strictly reload and content-address one persisted capability probe receipt."""

    candidate = Path(path)
    try:
        raw = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VLLMCapabilityProbeError("failed to load capability probe receipt") from exc
    if not isinstance(raw, Mapping):
        raise VLLMCapabilityProbeError("capability probe receipt must be an object")
    return VLLMCapabilityProbeResult.from_mapping(raw)
