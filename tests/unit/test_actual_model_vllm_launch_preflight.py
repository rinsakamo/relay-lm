from __future__ import annotations

import subprocess

import pytest

import relaylm.actual_model_vllm_launch_preflight as launch_preflight
from relaylm.actual_model_vllm_launch_preflight import (
    AuthorityTransportError,
    ExecutionFreezeBoundary,
    FrozenExecutionIdentity,
    HostProcess,
    acquire_current_authority,
    discover_vllm_supported_flags,
    VLLMHostPreflightError,
    negotiate_gpu_memory_utilization,
    negotiate_vllm_launch,
    prepare_vllm_runtime_paths,
    find_stale_vllm_processes,
    parse_process_snapshot,
    snapshot_vllm_processes,
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


def test_authority_cannot_be_reconfirmed_after_startup() -> None:
    authority = acquire_current_authority(
        sources=(("host-api", lambda: {"repository_head": "current"}),)
    )
    boundary = ExecutionFreezeBoundary()
    boundary.confirm_authority(authority)
    boundary.mark_admission_ready()
    boundary.mark_startup_ready()

    with pytest.raises(VLLMHostPreflightError, match="only during PREFLIGHT"):
        boundary.confirm_authority(authority)
