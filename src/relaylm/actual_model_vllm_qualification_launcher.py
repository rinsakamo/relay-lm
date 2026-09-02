from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from relaylm.actual_model_vllm_launch_preflight import (
    GPUAdmissionDecision,
    OwnedVLLMRuntime,
    RuntimeListenerEndpoint,
    RuntimeOwnershipAttestation,
    VLLMHostPreflightError,
    VLLMLaunchPlan,
    VLLMRuntimePathPlan,
    launch_owned_vllm_runtime,
    negotiate_gpu_memory_utilization,
    negotiate_vllm_launch,
    prepare_vllm_runtime_paths,
    wait_for_vllm_runtime_readiness,
)


_GPU_MEMORY_FLAG = "--gpu-memory-utilization"
_MAX_MODEL_LEN_FLAG = "--max-model-len"
_UNIX_IPC_PATH_MAX_BYTES = 107
_VLLM_IPC_SUFFIX_BYTES = 37
CapacityRecheck = Callable[[float, int], bool]


@dataclass(frozen=True, slots=True)
class VLLMQualificationLaunchPlan:
    """One bounded pre-freeze launch plan for actual-model qualification."""

    admission: GPUAdmissionDecision
    launch: VLLMLaunchPlan
    runtime_paths: VLLMRuntimePathPlan

    def to_mapping(self) -> dict[str, object]:
        return {
            "admission": self.admission.to_mapping(),
            "launch": self.launch.to_mapping(),
            "runtime_paths": self.runtime_paths.to_mapping(),
        }


@dataclass(frozen=True, slots=True)
class VLLMQualificationRuntime:
    """Serving owned runtime produced from one qualification launch plan."""

    plan: VLLMQualificationLaunchPlan
    runtime: OwnedVLLMRuntime
    ownership: RuntimeOwnershipAttestation


def prepare_vllm_qualification_launch(
    *,
    command: Sequence[str],
    supported_flags: Iterable[str],
    requested_utilization: float,
    fallback_utilization: float | None,
    fresh_free_memory_bytes: int,
    total_memory_bytes: int,
    required_context_window: int,
    capacity_recheck: CapacityRecheck,
    run_id: str,
    requested_rpc_base_path: str | Path | None = None,
    native_root: str | Path = "/tmp",
    non_semantic_flags: Iterable[str] = ("--disable-log-requests",),
) -> VLLMQualificationLaunchPlan:
    """Compose #2045 admission, argv negotiation and native-path preparation.

    The caller supplies at most one lower reservation candidate.  This function
    never searches reservation values and never changes the declared context.
    A serving-runtime capacity attestation is still required after launch and
    before any execution freeze.
    """

    _validate_declared_context_window(
        command=command,
        required_context_window=required_context_window,
    )
    if fallback_utilization is not None:
        if fallback_utilization == requested_utilization:
            raise VLLMHostPreflightError(
                "fallback GPU reservation must differ from requested reservation"
            )
        if fallback_utilization > requested_utilization:
            raise VLLMHostPreflightError(
                "fallback GPU reservation cannot exceed requested reservation"
            )
        candidates = (requested_utilization, fallback_utilization)
    else:
        candidates = (requested_utilization,)

    admission = negotiate_gpu_memory_utilization(
        requested_utilization=requested_utilization,
        fresh_free_memory_bytes=fresh_free_memory_bytes,
        total_memory_bytes=total_memory_bytes,
        required_context_window=required_context_window,
        candidate_utilizations=candidates,
        capacity_recheck=capacity_recheck,
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
    return VLLMQualificationLaunchPlan(
        admission=admission,
        launch=launch,
        runtime_paths=runtime_paths,
    )


def launch_vllm_qualification_runtime(
    plan: VLLMQualificationLaunchPlan,
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
) -> VLLMQualificationRuntime:
    """Launch the exact selected plan and require #2051 owned readiness.

    This is deliberately not an execution-freeze operation.  The caller must
    still collect fresh serving-runtime capacity evidence and construct the live
    launch admission attestation before semantic execution can freeze.
    """

    if not isinstance(plan, VLLMQualificationLaunchPlan):
        raise TypeError("plan must be VLLMQualificationLaunchPlan")
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
    return VLLMQualificationRuntime(
        plan=plan,
        runtime=runtime,
        ownership=ownership,
    )


def _validate_vllm_unix_ipc_path(runtime_paths: VLLMRuntimePathPlan) -> None:
    """Reject RPC bases that cannot fit the pinned vLLM V2 Unix IPC suffix."""

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


def _validate_declared_context_window(
    *,
    command: Sequence[str],
    required_context_window: int,
) -> None:
    if isinstance(command, (str, bytes)) or not command:
        raise TypeError("vLLM command must be a non-empty sequence")
    if not all(isinstance(item, str) and item for item in command):
        raise VLLMHostPreflightError("vLLM command must contain non-empty strings")
    if isinstance(required_context_window, bool) or not isinstance(
        required_context_window, int
    ):
        raise VLLMHostPreflightError("required context window must be an integer")
    if required_context_window <= 0:
        raise VLLMHostPreflightError("required context window must be positive")

    values: list[int] = []
    index = 0
    while index < len(command):
        token = command[index]
        if token == _MAX_MODEL_LEN_FLAG:
            if index + 1 >= len(command) or command[index + 1].startswith("--"):
                raise VLLMHostPreflightError("--max-model-len requires one integer value")
            values.append(_parse_context_window(command[index + 1]))
            index += 2
            continue
        if token.startswith(f"{_MAX_MODEL_LEN_FLAG}="):
            values.append(_parse_context_window(token.split("=", 1)[1]))
        index += 1

    if len(values) != 1:
        raise VLLMHostPreflightError(
            "qualification launch requires exactly one --max-model-len"
        )
    if values[0] != required_context_window:
        raise VLLMHostPreflightError(
            "command context window does not match required context window"
        )


def _rewrite_gpu_memory_utilization(
    *,
    command: Sequence[str],
    expected_requested_utilization: float,
    selected_utilization: float,
) -> tuple[str, ...]:
    if isinstance(command, (str, bytes)) or not command:
        raise TypeError("vLLM command must be a non-empty sequence")
    if not all(isinstance(item, str) and item for item in command):
        raise VLLMHostPreflightError("vLLM command must contain non-empty strings")

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
            "qualification launch requires exactly one --gpu-memory-utilization"
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


def _parse_context_window(value: str) -> int:
    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise VLLMHostPreflightError("--max-model-len must be an integer") from exc
    if parsed <= 0:
        raise VLLMHostPreflightError("--max-model-len must be positive")
    return parsed


def _parse_utilization(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise VLLMHostPreflightError(
            "--gpu-memory-utilization must be numeric"
        ) from exc
    if parsed <= 0 or parsed > 1:
        raise VLLMHostPreflightError(
            "--gpu-memory-utilization must be in (0, 1]"
        )
    return parsed


def _render_utilization(value: float) -> str:
    return format(float(value), ".12g")


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
                f"caller environment conflicts with qualification runtime path: {key}"
            )
        merged[key] = value
    return merged