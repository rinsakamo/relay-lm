from __future__ import annotations

from relaylm.actual_model_vllm_launch_preflight import (
    HostProcess,
    RuntimeListenerEndpoint,
    RuntimeListenerObservation,
    RuntimeOwnershipAttestation,
    RuntimeOwnershipBoundary,
    RuntimeProcessIdentity,
    find_unowned_vllm_processes,
)


def _ownership() -> RuntimeOwnershipAttestation:
    endpoint = RuntimeListenerEndpoint(host="127.0.0.1", port=8000)
    root = RuntimeProcessIdentity(
        pid=900,
        ppid=800,
        pgid=901,
        session_id=902,
        start_time_ticks=1000,
        owner_nonce="owned-runtime",
    )
    engine_core = RuntimeProcessIdentity(
        pid=901,
        ppid=900,
        pgid=901,
        session_id=902,
        start_time_ticks=1001,
        owner_nonce="owned-runtime",
    )
    boundary = RuntimeOwnershipBoundary(
        run_id="qualification-live-owner",
        owner_nonce="owned-runtime",
        controller_pid=800,
        controller_pgid=800,
        controller_session_id=800,
        root=root,
        expected_listener=endpoint,
    )
    return RuntimeOwnershipAttestation(
        boundary=boundary,
        processes=(root, engine_core),
        listener=RuntimeListenerObservation(endpoint=endpoint, pids=(900,)),
    )


def test_live_owner_guard_accepts_current_owned_vllm_tree() -> None:
    ownership = _ownership()
    processes = (
        HostProcess(pid=900, argv=("vllm", "serve", "/models/gemma")),
        HostProcess(pid=901, argv=("VLLM::EngineCore",)),
    )

    assert find_unowned_vllm_processes(processes, ownership=ownership) == ()


def test_live_owner_guard_still_rejects_unowned_canonical_vllm_process() -> None:
    ownership = _ownership()
    processes = (
        HostProcess(pid=900, argv=("vllm", "serve", "/models/gemma")),
        HostProcess(pid=901, argv=("VLLM::EngineCore",)),
        HostProcess(pid=902, argv=("VLLM::EngineCore",)),
    )

    unowned = find_unowned_vllm_processes(processes, ownership=ownership)

    assert tuple(process.pid for process in unowned) == (902,)
