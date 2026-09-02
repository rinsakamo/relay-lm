from __future__ import annotations

from pathlib import Path

import pytest

import relaylm.actual_model_vllm_qualification_launcher as launcher
from relaylm.actual_model_vllm_launch_preflight import (
    RuntimeListenerEndpoint,
    VLLMHostPreflightError,
)
from relaylm.actual_model_vllm_qualification_launcher import (
    launch_vllm_qualification_runtime,
    prepare_vllm_qualification_launch,
)


SUPPORTED_FLAGS = {
    "--gpu-memory-utilization",
    "--max-model-len",
    "--port",
}


def _command(*extra: str) -> tuple[str, ...]:
    return (
        "vllm",
        "serve",
        "model",
        "--max-model-len",
        "4096",
        "--gpu-memory-utilization",
        "0.92",
        "--port",
        "8000",
        *extra,
    )


def _gpu_value(command: tuple[str, ...]) -> float:
    index = command.index("--gpu-memory-utilization")
    return float(command[index + 1])


def test_qualification_plan_wires_bounded_lower_reservation_into_final_argv(
    tmp_path: Path,
) -> None:
    rechecks: list[tuple[float, int]] = []

    plan = prepare_vllm_qualification_launch(
        command=_command(),
        supported_flags=SUPPORTED_FLAGS,
        requested_utilization=0.92,
        fallback_utilization=0.90,
        fresh_free_memory_bytes=10_980,
        total_memory_bytes=12_000,
        required_context_window=4096,
        capacity_recheck=lambda utilization, context: (
            rechecks.append((utilization, context)) or True
        ),
        run_id="qualification-a",
        native_root=tmp_path,
    )

    assert plan.admission.requested_utilization == 0.92
    assert plan.admission.selected_utilization == 0.90
    assert plan.admission.context_window == 4096
    assert plan.admission.changed is True
    assert plan.admission.reason == "mechanical_gpu_reservation_reduced_before_freeze"
    assert plan.admission.reattest_required is True
    assert rechecks == [(0.90, 4096)]
    assert _gpu_value(plan.launch.command) == 0.90
    max_len_index = plan.launch.command.index("--max-model-len")
    assert plan.launch.command[max_len_index + 1] == "4096"


def test_qualification_plan_keeps_requested_reservation_when_admissible(
    tmp_path: Path,
) -> None:
    rechecks: list[tuple[float, int]] = []

    plan = prepare_vllm_qualification_launch(
        command=_command(),
        supported_flags=SUPPORTED_FLAGS,
        requested_utilization=0.92,
        fallback_utilization=0.90,
        fresh_free_memory_bytes=11_500,
        total_memory_bytes=12_000,
        required_context_window=4096,
        capacity_recheck=lambda utilization, context: (
            rechecks.append((utilization, context)) or True
        ),
        run_id="qualification-requested",
        native_root=tmp_path,
    )

    assert plan.admission.selected_utilization == 0.92
    assert plan.admission.changed is False
    assert plan.admission.reason == "requested_gpu_reservation_admitted_before_freeze"
    assert rechecks == [(0.92, 4096)]
    assert _gpu_value(plan.launch.command) == 0.92


def test_qualification_plan_without_lower_fallback_fails_closed(
    tmp_path: Path,
) -> None:
    with pytest.raises(VLLMHostPreflightError, match="required context window"):
        prepare_vllm_qualification_launch(
            command=_command(),
            supported_flags=SUPPORTED_FLAGS,
            requested_utilization=0.92,
            fallback_utilization=None,
            fresh_free_memory_bytes=10_980,
            total_memory_bytes=12_000,
            required_context_window=4096,
            capacity_recheck=lambda _utilization, _context: True,
            run_id="qualification-no-fallback",
            native_root=tmp_path,
        )


def test_qualification_plan_fails_when_fixed_context_recheck_rejects_fallback(
    tmp_path: Path,
) -> None:
    rechecks: list[tuple[float, int]] = []

    with pytest.raises(VLLMHostPreflightError, match="required context window"):
        prepare_vllm_qualification_launch(
            command=_command(),
            supported_flags=SUPPORTED_FLAGS,
            requested_utilization=0.92,
            fallback_utilization=0.90,
            fresh_free_memory_bytes=10_980,
            total_memory_bytes=12_000,
            required_context_window=4096,
            capacity_recheck=lambda utilization, context: (
                rechecks.append((utilization, context)) or False
            ),
            run_id="qualification-recheck-reject",
            native_root=tmp_path,
        )

    assert rechecks == [(0.90, 4096)]


@pytest.mark.parametrize("fallback", [0.92, 0.93])
def test_qualification_plan_rejects_non_lower_fallback(
    tmp_path: Path,
    fallback: float,
) -> None:
    with pytest.raises(VLLMHostPreflightError, match="fallback GPU reservation"):
        prepare_vllm_qualification_launch(
            command=_command(),
            supported_flags=SUPPORTED_FLAGS,
            requested_utilization=0.92,
            fallback_utilization=fallback,
            fresh_free_memory_bytes=10_980,
            total_memory_bytes=12_000,
            required_context_window=4096,
            capacity_recheck=lambda _utilization, _context: True,
            run_id=f"qualification-invalid-{fallback}",
            native_root=tmp_path,
        )


def test_qualification_plan_rejects_duplicate_gpu_reservation_flags(
    tmp_path: Path,
) -> None:
    command = _command("--gpu-memory-utilization=0.92")

    with pytest.raises(VLLMHostPreflightError, match="exactly one"):
        prepare_vllm_qualification_launch(
            command=command,
            supported_flags=SUPPORTED_FLAGS,
            requested_utilization=0.92,
            fallback_utilization=0.90,
            fresh_free_memory_bytes=10_980,
            total_memory_bytes=12_000,
            required_context_window=4096,
            capacity_recheck=lambda _utilization, _context: True,
            run_id="qualification-duplicate",
            native_root=tmp_path,
        )


def test_qualification_plan_rejects_command_reservation_identity_drift(
    tmp_path: Path,
) -> None:
    command = tuple("0.91" if item == "0.92" else item for item in _command())

    with pytest.raises(VLLMHostPreflightError, match="does not match requested"):
        prepare_vllm_qualification_launch(
            command=command,
            supported_flags=SUPPORTED_FLAGS,
            requested_utilization=0.92,
            fallback_utilization=0.90,
            fresh_free_memory_bytes=10_980,
            total_memory_bytes=12_000,
            required_context_window=4096,
            capacity_recheck=lambda _utilization, _context: True,
            run_id="qualification-drift",
            native_root=tmp_path,
        )


def test_qualification_plan_rejects_context_window_identity_drift(
    tmp_path: Path,
) -> None:
    command = tuple("8192" if item == "4096" else item for item in _command())
    rechecks: list[tuple[float, int]] = []

    with pytest.raises(VLLMHostPreflightError, match="context window does not match"):
        prepare_vllm_qualification_launch(
            command=command,
            supported_flags=SUPPORTED_FLAGS,
            requested_utilization=0.92,
            fallback_utilization=0.90,
            fresh_free_memory_bytes=10_980,
            total_memory_bytes=12_000,
            required_context_window=4096,
            capacity_recheck=lambda utilization, context: (
                rechecks.append((utilization, context)) or True
            ),
            run_id="qualification-context-drift",
            native_root=tmp_path,
        )

    assert rechecks == []


def test_qualification_plan_rejects_duplicate_context_flags(tmp_path: Path) -> None:
    with pytest.raises(VLLMHostPreflightError, match="exactly one --max-model-len"):
        prepare_vllm_qualification_launch(
            command=_command("--max-model-len=4096"),
            supported_flags=SUPPORTED_FLAGS,
            requested_utilization=0.92,
            fallback_utilization=0.90,
            fresh_free_memory_bytes=10_980,
            total_memory_bytes=12_000,
            required_context_window=4096,
            capacity_recheck=lambda _utilization, _context: True,
            run_id="qualification-context-duplicate",
            native_root=tmp_path,
        )


def test_qualification_plan_preserves_other_semantic_launch_tokens(
    tmp_path: Path,
) -> None:
    command = _command()
    plan = prepare_vllm_qualification_launch(
        command=command,
        supported_flags=SUPPORTED_FLAGS,
        requested_utilization=0.92,
        fallback_utilization=0.90,
        fresh_free_memory_bytes=10_980,
        total_memory_bytes=12_000,
        required_context_window=4096,
        capacity_recheck=lambda _utilization, _context: True,
        run_id="qualification-preserve",
        native_root=tmp_path,
    )

    original_without_reservation = list(command)
    selected_without_reservation = list(plan.launch.command)
    original_index = original_without_reservation.index("--gpu-memory-utilization")
    selected_index = selected_without_reservation.index("--gpu-memory-utilization")
    del original_without_reservation[original_index : original_index + 2]
    del selected_without_reservation[selected_index : selected_index + 2]
    assert selected_without_reservation == original_without_reservation


def test_launch_uses_selected_command_native_environment_and_owned_readiness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = prepare_vllm_qualification_launch(
        command=_command(),
        supported_flags=SUPPORTED_FLAGS,
        requested_utilization=0.92,
        fallback_utilization=0.90,
        fresh_free_memory_bytes=10_980,
        total_memory_bytes=12_000,
        required_context_window=4096,
        capacity_recheck=lambda _utilization, _context: True,
        run_id="qualification-launch",
        requested_rpc_base_path="/mnt/c/relay-rpc",
        native_root=tmp_path,
    )
    calls: dict[str, object] = {}

    class FakeRuntime:
        def cleanup(self) -> None:
            calls["cleanup"] = True

    runtime = FakeRuntime()
    ownership = object()

    def fake_launch(command, **kwargs):
        calls["command"] = tuple(command)
        calls["launch_kwargs"] = kwargs
        return runtime

    def fake_wait(observed_runtime, **kwargs):
        calls["wait_runtime"] = observed_runtime
        calls["wait_kwargs"] = kwargs
        return ownership

    monkeypatch.setattr(launcher, "_validate_vllm_unix_ipc_path", lambda _paths: None)
    monkeypatch.setattr(launcher, "launch_owned_vllm_runtime", fake_launch)
    monkeypatch.setattr(launcher, "wait_for_vllm_runtime_readiness", fake_wait)

    result = launch_vllm_qualification_runtime(
        plan,
        run_id="qualification-launch",
        expected_listener=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
        env={"EXTRA_SAFE_ENV": "1"},
        readiness_timeout=30.0,
        poll_interval=0.1,
    )

    assert result.plan == plan
    assert result.runtime is runtime
    assert result.ownership is ownership
    assert calls["command"] == plan.launch.command
    kwargs = calls["launch_kwargs"]
    assert kwargs["env"]["EXTRA_SAFE_ENV"] == "1"
    assert kwargs["env"]["VLLM_RPC_BASE_PATH"] == str(plan.runtime_paths.rpc_base_path)
    assert kwargs["env"]["TMPDIR"] == str(tmp_path.resolve())
    assert calls["wait_runtime"] is runtime
    assert calls["wait_kwargs"] == {"timeout": 30.0, "poll_interval": 0.1}
    assert "cleanup" not in calls


def test_short_unix_ipc_path_budget_is_admissible() -> None:
    rpc_base = Path("/tmp/relaylm-vllm-rpc-0123456789abcdef01234567")
    runtime_paths = launcher.VLLMRuntimePathPlan(
        rpc_base_path=rpc_base,
        tmpdir=Path("/tmp"),
        path_class="native_linux",
        rebased_from_drvfs=False,
        environment={
            "VLLM_RPC_BASE_PATH": str(rpc_base),
            "TMPDIR": "/tmp",
            "TMP": "/tmp",
            "TEMP": "/tmp",
        },
    )

    launcher._validate_vllm_unix_ipc_path(runtime_paths)


def test_launch_rejects_overlong_unix_ipc_path_before_provider_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    long_root = tmp_path / ("x" * 80)
    plan = prepare_vllm_qualification_launch(
        command=_command(),
        supported_flags=SUPPORTED_FLAGS,
        requested_utilization=0.92,
        fallback_utilization=0.90,
        fresh_free_memory_bytes=10_980,
        total_memory_bytes=12_000,
        required_context_window=4096,
        capacity_recheck=lambda _utilization, _context: True,
        run_id="qualification-overlong-ipc",
        native_root=long_root,
    )
    assert len(str(plan.runtime_paths.rpc_base_path).encode("utf-8")) + 37 > 107
    monkeypatch.setattr(
        launcher,
        "launch_owned_vllm_runtime",
        lambda *_args, **_kwargs: pytest.fail("provider launch must not occur"),
    )

    try:
        with pytest.raises(VLLMHostPreflightError, match="Unix IPC path"):
            launch_vllm_qualification_runtime(
                plan,
                run_id="qualification-overlong-ipc",
                expected_listener=RuntimeListenerEndpoint(
                    host="127.0.0.1", port=8000
                ),
            )
    finally:
        plan.runtime_paths.rpc_base_path.rmdir()


def test_launch_rejects_runtime_path_environment_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = prepare_vllm_qualification_launch(
        command=_command(),
        supported_flags=SUPPORTED_FLAGS,
        requested_utilization=0.92,
        fallback_utilization=0.90,
        fresh_free_memory_bytes=10_980,
        total_memory_bytes=12_000,
        required_context_window=4096,
        capacity_recheck=lambda _utilization, _context: True,
        run_id="qualification-env-conflict",
        native_root=tmp_path,
    )
    monkeypatch.setattr(
        launcher,
        "launch_owned_vllm_runtime",
        lambda *_args, **_kwargs: pytest.fail("launch must not occur"),
    )

    with pytest.raises(VLLMHostPreflightError, match="conflicts"):
        launch_vllm_qualification_runtime(
            plan,
            run_id="qualification-env-conflict",
            expected_listener=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
            env={"TMPDIR": "/different"},
        )