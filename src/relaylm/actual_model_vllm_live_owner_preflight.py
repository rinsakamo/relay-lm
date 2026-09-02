from __future__ import annotations

from collections.abc import Sequence

from .actual_model_vllm_launch_preflight import (
    HostProcess,
    RuntimeOwnershipAttestation,
    find_stale_vllm_processes,
)


def find_unowned_vllm_processes(
    processes: Sequence[HostProcess],
    *,
    ownership: RuntimeOwnershipAttestation,
) -> tuple[HostProcess, ...]:
    """Return canonical vLLM processes not proven owned by the live runtime.

    ``find_stale_vllm_processes`` remains the strict pre-launch cleanliness guard.
    This function is for the post-launch/pre-semantic phase, after a
    ``RuntimeOwnershipAttestation`` has positively proved the transaction-owned
    process tree and expected listener. Only PIDs in that proof are exempted;
    any additional canonical vLLM process remains an unowned conflict.
    """

    if not isinstance(ownership, RuntimeOwnershipAttestation):
        raise TypeError("ownership must be RuntimeOwnershipAttestation")

    owned_pids = frozenset(ownership.owned_pids)
    return tuple(
        process
        for process in find_stale_vllm_processes(processes)
        if process.pid not in owned_pids
    )
