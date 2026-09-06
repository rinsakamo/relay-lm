from __future__ import annotations

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
_REFERENCE_GPU_HEADROOM_PERCENT_POINTS = 1
_UNIX_IPC_PATH_MAX_BYTES = 107
_VLLM_IPC_SUFFIX_BYTES = 37


@dataclass(frozen=True, slots=True)
class VLLMReferenceGPUAdmissionDecision:
    """Fresh physical GPU reservation for zero-semantic reference production."""

    selected_utilization: float
    fresh_free_memory_bytes: int
    total_memory_bytes: int
    available_percent: int
    headroom_percent_points: int = _REFERENCE_GPU_HEADROOM_PERCENT_POINTS
    reason: str = "fresh_reference_gpu_reservation_derived"
    reattest_required: bool = True

    def to_mapping(self) -> dict[str, object]:
        return {
            "selected_utilization": self.selected_utilization,
            "fresh_free_memory_bytes": self.fresh_free_memory_bytes,
            "total_memory_bytes": self.total_memory_bytes,
            "available_percent": self.available_percent,
            "headroom_percent_points": self.headroom_percent_points,
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
    fresh_free_memory_bytes: int,
    total_memory_bytes: int,
    run_id: str,
    requested_rpc_base_path: str | Path | None = None,
    native_root: str | Path = "/tmp",
    non_semantic_flags: Iterable[str] = ("--disable-log-requests",),
) -> VLLMReferenceLaunchPlan:
    """Prepare one window-independent launch-capability/reference condition.

    The caller supplies no semantic token window and no numeric GPU reservation.
    The producer requires the repository-authorized auto-fit model-length mode and
    derives exactly one mechanical GPU reservation from fresh free/total bytes.
    """

    _validate_direct_vllm_serve_command(command)
    _validate_reference_auto_fit_model_len(command)
    _reject_caller_gpu_memory_utilization(command)
    admission = _derive_reference_gpu_reservation(
        fresh_free_memory_bytes=fresh_free_memory_bytes,
        total_memory_bytes=total_memory_bytes,
    )
    rewritten_command = _append_gpu_memory_utilization(
        command=command,
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


def _reject_caller_gpu_memory_utilization(command: Sequence[str]) -> None:
    for token in command:
        if token == _GPU_MEMORY_FLAG or token.startswith(f"{_GPU_MEMORY_FLAG}="):
            raise VLLMHostPreflightError(
                "reference producer owns --gpu-memory-utilization; caller must omit it"
            )


def _derive_reference_gpu_reservation(
    *,
    fresh_free_memory_bytes: int,
    total_memory_bytes: int,
) -> VLLMReferenceGPUAdmissionDecision:
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

    available_percent = (fresh_free_memory_bytes * 100) // total_memory_bytes
    selected_percent = available_percent - _REFERENCE_GPU_HEADROOM_PERCENT_POINTS
    if selected_percent <= 0:
        raise VLLMHostPreflightError(
            "fresh GPU memory leaves no positive reference reservation after headroom"
        )

    return VLLMReferenceGPUAdmissionDecision(
        selected_utilization=selected_percent / 100,
        fresh_free_memory_bytes=fresh_free_memory_bytes,
        total_memory_bytes=total_memory_bytes,
        available_percent=available_percent,
    )


def _append_gpu_memory_utilization(
    *,
    command: Sequence[str],
    selected_utilization: float,
) -> tuple[str, ...]:
    return (
        *command,
        _GPU_MEMORY_FLAG,
        _render_utilization(selected_utilization),
    )


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
