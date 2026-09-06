from __future__ import annotations

import math
import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from relaylm.actual_model_vllm_launch_preflight import (
    OwnedVLLMRuntime,
    RuntimeListenerEndpoint,
    RuntimeOwnershipAttestation,
    VLLMHostPreflightError,
    VLLMLaunchPlan,
    VLLMRuntimePathPlan,
    launch_owned_vllm_runtime,
    negotiate_vllm_launch,
    prepare_vllm_runtime_paths,
    wait_for_vllm_runtime_readiness,
)


_GPU_MEMORY_FLAG = "--gpu-memory-utilization"
_MAX_MODEL_LEN_FLAG = "--max-model-len"
_AUTO_MODEL_LEN = "auto"
_UNIX_IPC_PATH_MAX_BYTES = 107
_VLLM_IPC_SUFFIX_BYTES = 37


@dataclass(frozen=True, slots=True)
class VLLMReferenceGPUAdmissionDecision:
    """Mechanical GPU-reservation feasibility for reference production.

    Unlike semantic Stage R admission, this decision carries no declared token
    window and performs no context-capacity recheck. The producer is measuring
    the launch class through the runtime's repository-authorized auto-fit mode.
    """

    requested_utilization: float
    selected_utilization: float
    fresh_free_memory_bytes: int
    total_memory_bytes: int
    changed: bool
    reason: str
    reattest_required: bool = True

    def to_mapping(self) -> dict[str, object]:
        return {
            "requested_utilization": self.requested_utilization,
            "selected_utilization": self.selected_utilization,
            "fresh_free_memory_bytes": self.fresh_free_memory_bytes,
            "total_memory_bytes": self.total_memory_bytes,
            "changed": self.changed,
            "reason": self.reason,
            "reattest_required": self.reattest_required,
        }


@dataclass(frozen=True, slots=True)
class VLLMReferenceLaunchPlan:
    """One zero-semantic auto-fit launch plan for reference production."""

    admission: VLLMReferenceGPUAdmissionDecision
    launch: VLLMLaunchPlan
    runtime_paths: VLLMRuntimePathPlan

    def to_mapping(self) -> dict[str, object]:
        return {
            "admission": self.admission.to_mapping(),
            "launch": self.launch.to_mapping(),
            "runtime_paths": self.runtime_paths.to_mapping(),
        }


@dataclass(frozen=True, slots=True)
class VLLMReferenceRuntime:
    """Serving owned runtime produced from one reference launch plan."""

    plan: VLLMReferenceLaunchPlan
    runtime: OwnedVLLMRuntime
    ownership: RuntimeOwnershipAttestation


def prepare_vllm_reference_launch(
    *,
    command: Sequence[str],
    supported_flags: Iterable[str],
    requested_utilization: float,
    fallback_utilization: float | None,
    fresh_free_memory_bytes: int,
    total_memory_bytes: int,
    run_id: str,
    requested_rpc_base_path: str | Path | None = None,
    native_root: str | Path = "/tmp",
    non_semantic_flags: Iterable[str] = ("--disable-log-requests",),
) -> VLLMReferenceLaunchPlan:
    """Prepare one window-independent launch-capability/reference condition.

    This surface is intentionally separate from
    ``prepare_vllm_qualification_launch``. It requires the repository-authorized
    auto-fit max-model-length representation and never accepts or derives a
    semantic target context window. GPU reservation selection is purely
    mechanical: a candidate must fit inside the freshly observed free/total
    memory fraction. Capacity is measured by the launched profiler/final runtime.
    """

    _validate_direct_vllm_serve_command(command)
    _validate_reference_auto_fit_model_len(command)
    candidates = _reservation_candidates(
        requested_utilization=requested_utilization,
        fallback_utilization=fallback_utilization,
    )
    admission = _select_reference_gpu_reservation(
        requested_utilization=requested_utilization,
        fresh_free_memory_bytes=fresh_free_memory_bytes,
        total_memory_bytes=total_memory_bytes,
        candidate_utilizations=candidates,
    )
    rewritten_command = _rewrite_gpu_memory_utilization(
        command=command,
        expected_requested_utilization=requested_utilization,
        selected_utilization=admission.selected_utilization,
    )
    launch = negotiate_vllm_launch(
        command=rewritten_command,
        supported_flags=supported_flags,
        non_semantic_flags=non_semantic_flags,
    )
    runtime_paths = prepare_vllm_runtime_paths(
        run_id=run_id,
        requested_rpc_base_path=requested_rpc_base_path,
        native_root=native_root,
    )
    return VLLMReferenceLaunchPlan(
        admission=admission,
        launch=launch,
        runtime_paths=runtime_paths,
    )


def launch_vllm_reference_runtime(
    plan: VLLMReferenceLaunchPlan,
    *,
    run_id: str,
    expected_listener: RuntimeListenerEndpoint,
    owner_nonce: str | None = None,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
    stdout: object | None = None,
    stderr: object | None = None,
    readiness_timeout: float = 120.0,
    poll_interval: float = 0.05,
) -> VLLMReferenceRuntime:
    """Launch the exact reference plan and require owned readiness."""

    if not isinstance(plan, VLLMReferenceLaunchPlan):
        raise TypeError("plan must be VLLMReferenceLaunchPlan")
    merged_env = _merge_runtime_environment(
        runtime_environment=plan.runtime_paths.environment,
        caller_environment=env,
    )
    _validate_vllm_unix_ipc_path(plan.runtime_paths)
    runtime = launch_owned_vllm_runtime(
        plan.launch.command,
        run_id=run_id,
        expected_listener=expected_listener,
        owner_nonce=owner_nonce,
        env=merged_env,
        cwd=cwd,
        stdout=stdout,
        stderr=stderr,
    )
    try:
        ownership = wait_for_vllm_runtime_readiness(
            runtime,
            timeout=readiness_timeout,
            poll_interval=poll_interval,
        )
    except Exception:
        runtime.cleanup()
        raise
    return VLLMReferenceRuntime(
        plan=plan,
        runtime=runtime,
        ownership=ownership,
    )


def _validate_direct_vllm_serve_command(command: Sequence[str]) -> None:
    if isinstance(command, (str, bytes)) or not command:
        raise TypeError("vLLM command must be a non-empty sequence")
    if not all(isinstance(item, str) and item for item in command):
        raise VLLMHostPreflightError("vLLM command must contain non-empty strings")
    if len(command) < 3:
        raise VLLMHostPreflightError(
            "reference launch requires direct 'vllm serve <model>' command"
        )
    if Path(command[0]).name != "vllm" or command[1] != "serve":
        raise VLLMHostPreflightError(
            "reference launch requires direct 'vllm serve <model>' command"
        )
    if command[2].startswith("-"):
        raise VLLMHostPreflightError(
            "reference launch requires a non-option model after 'vllm serve'"
        )


def _validate_reference_auto_fit_model_len(command: Sequence[str]) -> None:
    values: list[str] = []
    index = 0
    while index < len(command):
        token = command[index]
        if token == _MAX_MODEL_LEN_FLAG:
            if index + 1 >= len(command) or command[index + 1].startswith("--"):
                raise VLLMHostPreflightError(
                    "--max-model-len requires one auto-fit value"
                )
            values.append(command[index + 1])
            index += 2
            continue
        if token.startswith(f"{_MAX_MODEL_LEN_FLAG}="):
            values.append(token.split("=", 1)[1])
        index += 1

    if len(values) != 1:
        raise VLLMHostPreflightError(
            "reference launch requires exactly one --max-model-len"
        )
    if values[0] != _AUTO_MODEL_LEN:
        raise VLLMHostPreflightError(
            "reference launch requires --max-model-len auto"
        )


def _reservation_candidates(
    *,
    requested_utilization: float,
    fallback_utilization: float | None,
) -> tuple[float, ...]:
    _validate_utilization(requested_utilization, "requested_utilization")
    if fallback_utilization is None:
        return (float(requested_utilization),)
    _validate_utilization(fallback_utilization, "fallback_utilization")
    if fallback_utilization == requested_utilization:
        raise VLLMHostPreflightError(
            "fallback GPU reservation must differ from requested reservation"
        )
    if fallback_utilization > requested_utilization:
        raise VLLMHostPreflightError(
            "fallback GPU reservation cannot exceed requested reservation"
        )
    return (float(requested_utilization), float(fallback_utilization))


def _select_reference_gpu_reservation(
    *,
    requested_utilization: float,
    fresh_free_memory_bytes: int,
    total_memory_bytes: int,
    candidate_utilizations: Iterable[float],
) -> VLLMReferenceGPUAdmissionDecision:
    _validate_utilization(requested_utilization, "requested_utilization")
    for value, label in (
        (fresh_free_memory_bytes, "fresh_free_memory_bytes"),
        (total_memory_bytes, "total_memory_bytes"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise VLLMHostPreflightError(f"{label} must be a positive integer")
    if fresh_free_memory_bytes > total_memory_bytes:
        raise VLLMHostPreflightError(
            "fresh_free_memory_bytes cannot exceed total_memory_bytes"
        )

    candidates: list[float] = []
    for value in candidate_utilizations:
        _validate_utilization(value, "candidate_utilization")
        if value > requested_utilization:
            raise VLLMHostPreflightError(
                "reference launch cannot increase the requested GPU reservation"
            )
        if value not in candidates:
            candidates.append(float(value))
    if not candidates:
        raise VLLMHostPreflightError(
            "reference launch requires at least one GPU reservation candidate"
        )

    available_fraction = fresh_free_memory_bytes / total_memory_bytes
    for candidate in sorted(candidates, reverse=True):
        if candidate > available_fraction:
            continue
        return VLLMReferenceGPUAdmissionDecision(
            requested_utilization=float(requested_utilization),
            selected_utilization=candidate,
            fresh_free_memory_bytes=fresh_free_memory_bytes,
            total_memory_bytes=total_memory_bytes,
            changed=candidate != float(requested_utilization),
            reason=(
                "reference_gpu_reservation_reduced_before_measurement"
                if candidate != float(requested_utilization)
                else "requested_reference_gpu_reservation_admitted"
            ),
        )

    raise VLLMHostPreflightError(
        "reference launch GPU reservation is not currently available"
    )


def _rewrite_gpu_memory_utilization(
    *,
    command: Sequence[str],
    expected_requested_utilization: float,
    selected_utilization: float,
) -> tuple[str, ...]:
    rewritten = list(command)
    occurrences: list[tuple[int, int | None, float]] = []
    index = 0
    while index < len(command):
        token = command[index]
        if token == _GPU_MEMORY_FLAG:
            if index + 1 >= len(command) or command[index + 1].startswith("--"):
                raise VLLMHostPreflightError(
                    "--gpu-memory-utilization requires one numeric value"
                )
            value_index = index + 1
            value = _parse_utilization(command[value_index])
            occurrences.append((index, value_index, value))
            index += 2
            continue
        if token.startswith(f"{_GPU_MEMORY_FLAG}="):
            value = _parse_utilization(token.split("=", 1)[1])
            occurrences.append((index, None, value))
        index += 1

    if len(occurrences) != 1:
        raise VLLMHostPreflightError(
            "reference launch requires exactly one --gpu-memory-utilization"
        )
    flag_index, value_index, observed = occurrences[0]
    if observed != float(expected_requested_utilization):
        raise VLLMHostPreflightError(
            "command GPU reservation does not match requested reservation"
        )

    rendered = _render_utilization(selected_utilization)
    if value_index is None:
        rewritten[flag_index] = f"{_GPU_MEMORY_FLAG}={rendered}"
    else:
        rewritten[value_index] = rendered
    return tuple(rewritten)


def _validate_utilization(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VLLMHostPreflightError(f"{label} must be a number")
    if not math.isfinite(float(value)) or value <= 0 or value > 1:
        raise VLLMHostPreflightError(f"{label} must be finite and in (0, 1]")


def _parse_utilization(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise VLLMHostPreflightError(
            "--gpu-memory-utilization must be numeric"
        ) from exc
    if not math.isfinite(parsed) or parsed <= 0 or parsed > 1:
        raise VLLMHostPreflightError(
            "--gpu-memory-utilization must be finite and in (0, 1]"
        )
    return parsed


def _render_utilization(value: float) -> str:
    return format(float(value), ".12g")


def _validate_vllm_unix_ipc_path(runtime_paths: VLLMRuntimePathPlan) -> None:
    if not isinstance(runtime_paths, VLLMRuntimePathPlan):
        raise TypeError("runtime_paths must be VLLMRuntimePathPlan")
    rpc_base_bytes = len(os.fsencode(runtime_paths.rpc_base_path))
    endpoint_bytes = rpc_base_bytes + _VLLM_IPC_SUFFIX_BYTES
    if endpoint_bytes > _UNIX_IPC_PATH_MAX_BYTES:
        raise VLLMHostPreflightError(
            "vLLM Unix IPC path exceeds the conservative host socket budget "
            "before provider launch "
            f"(rpc_base_bytes={rpc_base_bytes}, "
            f"reserved_suffix_bytes={_VLLM_IPC_SUFFIX_BYTES}, "
            f"max_bytes={_UNIX_IPC_PATH_MAX_BYTES})"
        )


def _merge_runtime_environment(
    *,
    runtime_environment: Mapping[str, str],
    caller_environment: Mapping[str, str] | None,
) -> dict[str, str]:
    merged = dict(caller_environment or {})
    for key, value in runtime_environment.items():
        existing = merged.get(key)
        if existing is not None and existing != value:
            raise VLLMHostPreflightError(
                f"caller environment conflicts with reference runtime path: {key}"
            )
        merged[key] = value
    return merged
