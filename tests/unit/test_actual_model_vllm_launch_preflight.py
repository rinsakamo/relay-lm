from __future__ import annotations

import json
import sys
import subprocess
import time
from pathlib import Path

import pytest

import relaylm.actual_model_vllm_launch_preflight as launch_preflight
from relaylm.actual_model_vllm_launch_preflight import (
    AuthorityTransportError,
    ExecutionFreezeBoundary,
    FrozenExecutionIdentity,
    HostProcess,
    RuntimeListenerEndpoint,
    RuntimeListenerObservation,
    RuntimeOwnershipAttestation,
    RuntimeOwnershipBoundary,
    RuntimeOwnershipError,
    RuntimeProcessIdentity,
    acquire_current_authority,
    discover_vllm_supported_flags,
    launch_owned_vllm_runtime,
    VLLMHostPreflightError,
    negotiate_gpu_memory_utilization,
    negotiate_vllm_launch,
    prepare_vllm_runtime_paths,
    find_stale_vllm_processes,
    parse_process_snapshot,
    parse_listener_snapshot,
    snapshot_runtime_processes,
    snapshot_vllm_processes,
    wait_for_vllm_runtime_readiness,
)


def test_process_guard_does_not_self_match_detector_search_text() -> None:
    processes = parse_process_snapshot(
        "410\tawk /vllm|EngineCore|uvicorn/ {print}\n"
        "411\tpython -m relaylm.actual_model_vllm_launch_preflight\n"
    )

    assert find_stale_vllm_processes(processes) == ()


def test_process_guard_detects_canonical_vllm_serve_process() -> None:
    processes = parse_process_snapshot(
        "510\t/usr/bin/vllm serve /models/gemma --port 8000\n"
    )

    stale = find_stale_vllm_processes(processes)

    assert len(stale) == 1
    assert stale[0].pid == 510


def test_process_guard_detects_python_module_vllm_api_server() -> None:
    processes = parse_process_snapshot(
        "511\t/usr/bin/python -m vllm.entrypoints.openai.api_server /models/gemma --port 8000\n"
    )

    stale = find_stale_vllm_processes(processes)

    assert len(stale) == 1
    assert stale[0].pid == 511


def test_process_guard_detects_exact_vllm_engine_core_title() -> None:
    processes = parse_process_snapshot("512\tVLLM::EngineCore\n")

    stale = find_stale_vllm_processes(processes)

    assert len(stale) == 1
    assert stale[0].pid == 512


def test_process_guard_ignores_engine_core_substring_in_detector() -> None:
    processes = parse_process_snapshot(
        "513\tawk /EngineCore/ {print}\n"
    )

    assert find_stale_vllm_processes(processes) == ()


def test_process_guard_ignores_unrelated_python_with_vllm_word_in_argument() -> None:
    processes = parse_process_snapshot(
        "610\t/usr/bin/python worker.py --note vllm --mode offline\n"
    )

    assert find_stale_vllm_processes(processes) == ()


def test_process_snapshot_rejects_malformed_rows() -> None:
    with pytest.raises(VLLMHostPreflightError, match="process snapshot row"):
        parse_process_snapshot("not-a-pid python worker.py\n")


def test_snapshot_uses_structured_ps_without_shell_search_expression() -> None:
    calls: list[object] = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="710\t/usr/bin/python worker.py\n",
            stderr="",
        )

    processes = snapshot_vllm_processes(run=fake_run)

    assert len(processes) == 1
    assert processes[0].pid == 710
    assert calls == [
        (
            (("ps", "-eo", "pid=,args="),),
            {
                "check": True,
                "capture_output": True,
                "text": True,
            },
        )
    ]


def test_cli_returns_success_for_clean_host(monkeypatch, capsys) -> None:
    monkeypatch.setattr(launch_preflight, "snapshot_vllm_processes", lambda: ())

    assert launch_preflight.main([]) == 0
    assert capsys.readouterr().out == "vLLM process preflight: clean\n"


def test_cli_fails_closed_for_stale_host(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        launch_preflight,
        "snapshot_vllm_processes",
        lambda: (HostProcess(pid=810, argv=("vllm", "serve")),),
    )

    assert launch_preflight.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "stale vLLM process: pid=810\n"


def test_unsupported_observability_flag_is_omitted_before_launch() -> None:
    supported = discover_vllm_supported_flags(
        """
        --max-model-len INTEGER\n
        --gpu-memory-utilization FLOAT\n
        """
    )

    plan = negotiate_vllm_launch(
        command=(
            "vllm",
            "serve",
            "model",
            "--max-model-len",
            "4096",
            "--gpu-memory-utilization",
            "0.90",
            "--disable-log-requests",
        ),
        supported_flags=supported,
    )

    assert plan.command == (
        "vllm",
        "serve",
        "model",
        "--max-model-len",
        "4096",
        "--gpu-memory-utilization",
        "0.90",
    )
    assert plan.omitted_flags == ("--disable-log-requests",)


def test_unsupported_semantic_flag_fails_closed() -> None:
    with pytest.raises(VLLMHostPreflightError, match="semantic vLLM flag"):
        negotiate_vllm_launch(
            command=("vllm", "serve", "model", "--max-model-len", "4096"),
            supported_flags=(),
        )


def test_drvfs_rpc_path_is_rebased_to_fresh_native_run_path(tmp_path) -> None:
    plan = prepare_vllm_runtime_paths(
        run_id="memconflict-run-1",
        requested_rpc_base_path="/mnt/c/Users/rinsa/relay-rpc",
        native_root=tmp_path,
    )

    assert plan.path_class == "native_linux"
    assert plan.rebased_from_drvfs is True
    assert str(plan.rpc_base_path).startswith(str(tmp_path))
    assert "/mnt/c/" not in str(plan.rpc_base_path)
    assert plan.environment["VLLM_RPC_BASE_PATH"] == str(plan.rpc_base_path)
    assert plan.environment["TMPDIR"] == str(tmp_path)
    assert plan.environment["TMP"] == str(tmp_path)
    assert plan.environment["TEMP"] == str(tmp_path)


def test_native_rpc_path_is_not_reused_for_a_second_launch(tmp_path) -> None:
    prepare_vllm_runtime_paths(run_id="same-run", native_root=tmp_path)

    with pytest.raises(VLLMHostPreflightError, match="fresh native vLLM RPC path"):
        prepare_vllm_runtime_paths(run_id="same-run", native_root=tmp_path)


def test_gpu_reservation_can_reduce_without_reducing_declared_context() -> None:
    rechecks: list[tuple[float, int]] = []

    decision = negotiate_gpu_memory_utilization(
        requested_utilization=0.92,
        fresh_free_memory_bytes=10_980,
        total_memory_bytes=12_000,
        required_context_window=4096,
        candidate_utilizations=(0.92, 0.90),
        capacity_recheck=lambda utilization, context_window: (
            rechecks.append((utilization, context_window)) or True
        ),
    )

    assert decision.selected_utilization == 0.90
    assert decision.context_window == 4096
    assert decision.changed is True
    assert decision.reattest_required is True
    assert rechecks == [(0.90, 4096)]


def test_gpu_admission_does_not_make_a_lower_context_candidate() -> None:
    with pytest.raises(VLLMHostPreflightError, match="required context window"):
        negotiate_gpu_memory_utilization(
            requested_utilization=0.92,
            fresh_free_memory_bytes=10_980,
            total_memory_bytes=12_000,
            required_context_window=4096,
            candidate_utilizations=(0.92,),
            capacity_recheck=lambda utilization, context_window: True,
        )


def test_gpu_admission_requires_fresh_capacity_recheck() -> None:
    with pytest.raises(VLLMHostPreflightError, match="fresh capacity recheck"):
        negotiate_gpu_memory_utilization(
            requested_utilization=0.90,
            fresh_free_memory_bytes=11_000,
            total_memory_bytes=12_000,
            required_context_window=4096,
            candidate_utilizations=(0.90,),
        )


def test_authority_transport_failure_cannot_promote_stale_authority() -> None:
    def unavailable() -> dict[str, object]:
        raise AuthorityTransportError("sandbox DNS unavailable")

    result = acquire_current_authority(
        sources=(("sandbox", unavailable),),
        stale_authority={"repository_head": "old"},
    )

    assert result.status == "AUTHORITY_TRANSPORT_UNAVAILABLE"
    assert result.authority is None
    assert result.source is None


def test_alternate_live_authority_can_converge_before_freeze() -> None:
    def unavailable() -> dict[str, object]:
        raise AuthorityTransportError("sandbox DNS unavailable")

    current = {"repository_head": "40f7dde8ffa9693fd045e6d63b0e8a6bb4ea7e63"}
    result = acquire_current_authority(
        sources=(("sandbox", unavailable), ("host-api", lambda: current)),
    )

    assert result.status == "CURRENT_AUTHORITY_CONFIRMED"
    assert result.authority == current
    assert result.source == "host-api"


def test_execution_freezes_once_and_rejects_post_freeze_correction() -> None:
    authority = acquire_current_authority(
        sources=(("host-api", lambda: {"repository_head": "current"}),)
    )
    boundary = ExecutionFreezeBoundary()
    boundary.confirm_authority(authority)
    boundary.mark_admission_ready()
    ownership = RuntimeOwnershipAttestation(
        boundary=RuntimeOwnershipBoundary(
            run_id="run-1",
            owner_nonce="nonce-1",
            controller_pid=1,
            controller_pgid=10,
            controller_session_id=20,
            root=RuntimeProcessIdentity(
                pid=2,
                ppid=1,
                pgid=11,
                session_id=21,
                start_time_ticks=30,
                owner_nonce="nonce-1",
            ),
            expected_listener=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
        ),
        processes=(
            RuntimeProcessIdentity(
                pid=2,
                ppid=1,
                pgid=11,
                session_id=21,
                start_time_ticks=30,
                owner_nonce="nonce-1",
            ),
        ),
        listener=RuntimeListenerObservation(
            endpoint=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
            pids=(2,),
        ),
    )
    boundary.attest_runtime_ownership(ownership)
    boundary.mark_startup_ready()
    boundary.record_preflight_correction("omit_legacy_flag")
    identity = FrozenExecutionIdentity.from_mapping({"condition": "declared-v1"})

    boundary.freeze(identity)
    boundary.begin_semantic_request()

    assert boundary.freeze_count == 1
    assert boundary.phase == "SEMANTIC_EXECUTION"
    with pytest.raises(VLLMHostPreflightError, match="after execution freeze"):
        boundary.record_preflight_correction("change-context")
    with pytest.raises(VLLMHostPreflightError, match="only once"):
        boundary.freeze(identity)
    marker = boundary.freeze_marker()
    assert marker["phase"] == "SEMANTIC_EXECUTION"
    assert marker["freeze_count"] == 1
    assert marker["authority"]["status"] == "CURRENT_AUTHORITY_CONFIRMED"
    assert marker["runtime_ownership"]["status"] == "PROVEN"


def test_authority_cannot_be_reconfirmed_after_startup() -> None:
    authority = acquire_current_authority(
        sources=(("host-api", lambda: {"repository_head": "current"}),)
    )
    boundary = ExecutionFreezeBoundary()
    boundary.confirm_authority(authority)
    boundary.mark_admission_ready()
    ownership = RuntimeOwnershipAttestation(
        boundary=RuntimeOwnershipBoundary(
            run_id="reconfirm-run",
            owner_nonce="reconfirm-owner",
            controller_pid=1,
            controller_pgid=10,
            controller_session_id=20,
            root=RuntimeProcessIdentity(
                pid=2,
                ppid=1,
                pgid=11,
                session_id=21,
                start_time_ticks=30,
                owner_nonce="reconfirm-owner",
            ),
            expected_listener=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
        ),
        processes=(
            RuntimeProcessIdentity(
                pid=2,
                ppid=1,
                pgid=11,
                session_id=21,
                start_time_ticks=30,
                owner_nonce="reconfirm-owner",
            ),
        ),
        listener=RuntimeListenerObservation(
            endpoint=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
            pids=(2,),
        ),
    )
    boundary.attest_runtime_ownership(ownership)
    boundary.mark_startup_ready()

    with pytest.raises(VLLMHostPreflightError, match="only during PREFLIGHT"):
        boundary.confirm_authority(authority)


def test_startup_readiness_requires_runtime_ownership_attestation() -> None:
    authority = acquire_current_authority(
        sources=(("host-api", lambda: {"repository_head": "current"}),)
    )
    boundary = ExecutionFreezeBoundary()
    boundary.confirm_authority(authority)
    boundary.mark_admission_ready()

    with pytest.raises(RuntimeOwnershipError, match="PROCESS_OWNERSHIP_UNPROVEN"):
        boundary.mark_startup_ready()


def test_owned_runtime_gets_distinct_boundary_and_listener_is_owned() -> None:
    runtime = launch_owned_vllm_runtime(
        (sys.executable, "-c", "import time; time.sleep(30)"),
        run_id="ownership-positive",
        expected_listener=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
        owner_nonce="owner-positive",
    )
    try:
        listener = RuntimeListenerObservation(
            endpoint=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
            pids=(runtime.boundary.root.pid,),
        )
        attestation = runtime.attest_startup(
            process_snapshot=snapshot_runtime_processes,
            listener_snapshot=lambda: (listener,),
        )
        assert attestation.boundary.root.pgid != attestation.boundary.controller_pgid
        assert (
            attestation.boundary.root.session_id
            != attestation.boundary.controller_session_id
        )
        assert attestation.listener.pids == (runtime.boundary.root.pid,)
    finally:
        runtime.cleanup()


def test_non_isolated_child_is_rejected_and_cleaned_up() -> None:
    with pytest.raises(RuntimeOwnershipError, match="PROCESS_OWNERSHIP_UNPROVEN"):
        launch_owned_vllm_runtime(
            (sys.executable, "-c", "import time; time.sleep(30)"),
            run_id="ownership-negative",
            expected_listener=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
            owner_nonce="owner-negative",
            start_new_session=False,
        )


def test_stale_listener_cannot_satisfy_readiness() -> None:
    runtime = launch_owned_vllm_runtime(
        (sys.executable, "-c", "import time; time.sleep(30)"),
        run_id="stale-listener",
        expected_listener=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
        owner_nonce="owner-stale",
    )
    try:
        stale = RuntimeListenerObservation(
            endpoint=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
            pids=(runtime.boundary.controller_pid,),
        )
        with pytest.raises(RuntimeOwnershipError, match="PROCESS_OWNERSHIP_UNPROVEN"):
            wait_for_vllm_runtime_readiness(
                runtime,
                timeout=0.01,
                poll_interval=0,
                process_snapshot=snapshot_runtime_processes,
                listener_snapshot=lambda: (stale,),
            )
    finally:
        runtime.cleanup()


def test_listener_with_owned_and_unrelated_pids_is_ambiguous() -> None:
    runtime = launch_owned_vllm_runtime(
        (sys.executable, "-c", "import time; time.sleep(30)"),
        run_id="mixed-listener",
        expected_listener=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
        owner_nonce="owner-mixed",
    )
    try:
        mixed = RuntimeListenerObservation(
            endpoint=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
            pids=(runtime.boundary.root.pid, runtime.boundary.controller_pid),
        )
        with pytest.raises(RuntimeOwnershipError, match="PROCESS_OWNERSHIP_UNPROVEN"):
            runtime.attest_startup(
                process_snapshot=snapshot_runtime_processes,
                listener_snapshot=lambda: (mixed,),
            )
    finally:
        runtime.cleanup()


def test_runtime_root_boundary_drift_cannot_satisfy_readiness() -> None:
    runtime = launch_owned_vllm_runtime(
        (sys.executable, "-c", "import time; time.sleep(30)"),
        run_id="boundary-drift",
        expected_listener=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
        owner_nonce="owner-drift",
    )
    try:
        root = runtime.boundary.root
        drifted = RuntimeProcessIdentity(
            pid=root.pid,
            ppid=root.ppid,
            pgid=runtime.boundary.controller_pgid,
            session_id=root.session_id,
            start_time_ticks=root.start_time_ticks,
            owner_nonce="owner-drift",
        )
        listener = RuntimeListenerObservation(
            endpoint=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
            pids=(root.pid,),
        )
        with pytest.raises(RuntimeOwnershipError, match="PROCESS_OWNERSHIP_UNPROVEN"):
            runtime.attest_startup(
                process_snapshot=lambda: (drifted,),
                listener_snapshot=lambda: (listener,),
            )
    finally:
        runtime.cleanup()


def test_wrapper_exit_keeps_descendant_attributable_and_cleanup_owned(
    tmp_path: Path,
) -> None:
    child_pid_path = tmp_path / "child.pid"
    code = (
        "import os, time\n"
        f"path = {str(child_pid_path)!r}\n"
        "if os.fork(): os._exit(0)\n"
        "with open(path, 'w', encoding='ascii') as handle: handle.write(str(os.getpid()))\n"
        "time.sleep(30)\n"
    )
    runtime = launch_owned_vllm_runtime(
        (sys.executable, "-c", code),
        run_id="wrapper-exit",
        expected_listener=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
        owner_nonce="owner-wrapper",
    )
    try:
        deadline = time.monotonic() + 2
        while not child_pid_path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert child_pid_path.exists()
        child_pid = int(child_pid_path.read_text(encoding="ascii"))
        listener = RuntimeListenerObservation(
            endpoint=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
            pids=(child_pid,),
        )
        attestation = runtime.attest_startup(
            process_snapshot=snapshot_runtime_processes,
            listener_snapshot=lambda: (listener,),
        )
        assert runtime.boundary.root.pid not in {item.pid for item in attestation.processes}
        assert child_pid in {item.pid for item in attestation.processes}
        receipt = runtime.cleanup()
        assert receipt.complete is True
        assert child_pid in receipt.graceful_signal_pids
        assert runtime.cleanup() == receipt
    finally:
        runtime.cleanup()


def test_cleanup_does_not_kill_unrelated_sibling() -> None:
    runtime = launch_owned_vllm_runtime(
        (sys.executable, "-c", "import time; time.sleep(30)"),
        run_id="sibling-safe",
        expected_listener=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
        owner_nonce="owner-sibling",
    )
    sibling = subprocess.Popen((sys.executable, "-c", "import time; time.sleep(30)"))
    try:
        receipt = runtime.cleanup()
        assert receipt.complete is True
        assert sibling.poll() is None
    finally:
        runtime.cleanup()
        sibling.terminate()
        sibling.wait(timeout=2)


def test_partial_cleanup_is_idempotent_and_content_free(tmp_path: Path) -> None:
    runtime = launch_owned_vllm_runtime(
        (sys.executable, "-c", "import time; time.sleep(30)"),
        run_id="partial-startup",
        expected_listener=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
        owner_nonce="owner-partial",
    )
    receipt = runtime.cleanup(receipt_root=tmp_path)
    repeated = runtime.cleanup(receipt_root=tmp_path)

    assert receipt.complete is True
    assert repeated == receipt
    encoded = json.dumps(receipt.to_mapping(), sort_keys=True)
    assert "import time" not in encoded
    assert "owner-partial" in encoded
    assert set(receipt.to_mapping()["controller"]) == {"pid", "pgid", "session_id"}
    receipt_files = tuple(tmp_path.glob("runtime-cleanup-*.json"))
    assert len(receipt_files) == 1
    assert json.loads(receipt_files[0].read_text(encoding="ascii")) == receipt.to_mapping()
    assert not tuple(tmp_path.glob(".*.tmp-*"))


def test_cleanup_skips_pid_reuse_instead_of_signalling_new_process() -> None:
    runtime = launch_owned_vllm_runtime(
        (sys.executable, "-c", "import time; time.sleep(30)"),
        run_id="pid-reuse",
        expected_listener=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
        owner_nonce="owner-reuse",
    )
    signals: list[tuple[int, int]] = []
    original = runtime.boundary.root
    reused = RuntimeProcessIdentity(
        pid=original.pid,
        ppid=original.ppid,
        pgid=original.pgid,
        session_id=original.session_id,
        start_time_ticks=original.start_time_ticks + 1,
        owner_nonce="owner-reuse",
    )
    try:
        receipt = runtime.cleanup(
            process_snapshot=lambda: (reused,),
            listener_snapshot=lambda: (),
            signal_process=lambda pid, signum: signals.append((pid, signum)),
        )
        assert signals == []
        assert receipt.complete is False
        assert receipt.failure_code == "PROCESS_OWNERSHIP_UNPROVEN"
    finally:
        runtime.process.kill()
        runtime.process.wait(timeout=2)


def test_listener_snapshot_parser_preserves_listener_pids() -> None:
    listeners = parse_listener_snapshot(
        'LISTEN 0 4096 127.0.0.1:8000 0.0.0.0:* users:(("python",pid=42,fd=3))\n'
    )

    assert listeners == (
        RuntimeListenerObservation(
            endpoint=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
            pids=(42,),
        ),
    )
