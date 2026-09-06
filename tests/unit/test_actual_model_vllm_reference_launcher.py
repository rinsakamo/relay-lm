from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import relaylm.actual_model_vllm_reference_launcher as reference_launcher
from relaylm.actual_model_vllm_launch_preflight import (
    RuntimeListenerEndpoint,
    VLLMHostPreflightError,
)
from relaylm.actual_model_vllm_qualification_launcher import (
    prepare_vllm_qualification_launch,
)
from relaylm.actual_model_vllm_reference_launcher import (
    launch_vllm_reference_runtime,
    prepare_vllm_reference_launch,
)


SUPPORTED_FLAGS = {
    "--gpu-memory-utilization",
    "--max-model-len",
    "--port",
}


def _reference_command(*extra: str) -> tuple[str, ...]:
    return (
        "/tmp/prepared/bin/vllm",
        "serve",
        "model",
        "--max-model-len",
        "auto",
        "--port",
        "8000",
        *extra,
    )


def _semantic_command_with_auto() -> tuple[str, ...]:
    return (
        "vllm",
        "serve",
        "model",
        "--max-model-len",
        "auto",
        "--gpu-memory-utilization",
        "0.92",
        "--port",
        "8000",
    )


def _gpu_value(command: tuple[str, ...]) -> float:
    index = command.index("--gpu-memory-utilization")
    return float(command[index + 1])


def test_reference_plan_derives_reservation_without_semantic_or_caller_choice(
    tmp_path: Path,
) -> None:
    signature = inspect.signature(prepare_vllm_reference_launch)
    for prohibited in (
        "required_context_window",
        "capacity_recheck",
        "requested_utilization",
        "fallback_utilization",
    ):
        assert prohibited not in signature.parameters

    plan = prepare_vllm_reference_launch(
        command=_reference_command(),
        supported_flags=SUPPORTED_FLAGS,
        fresh_free_memory_bytes=10_980,
        total_memory_bytes=12_000,
        run_id="reference-derived",
        native_root=tmp_path,
    )

    assert plan.admission.available_percent == 91
    assert plan.admission.headroom_percent_points == 1
    assert plan.admission.selected_utilization == 0.90
    assert plan.admission.reason == "fresh_reference_gpu_reservation_derived"
    assert plan.admission.reattest_required is True
    assert _gpu_value(plan.launch.command) == 0.90
    assert plan.launch.command.count("--gpu-memory-utilization") == 1
    max_len_index = plan.launch.command.index("--max-model-len")
    assert plan.launch.command[max_len_index + 1] == "auto"


@pytest.mark.parametrize(
    ("free_bytes", "total_bytes", "expected"),
    [
        (9_149, 10_000, 0.90),
        (9_200, 10_000, 0.91),
        (10_000, 10_000, 0.99),
    ],
)
def test_reference_plan_uses_two_decimal_floor_with_one_point_headroom(
    tmp_path: Path,
    free_bytes: int,
    total_bytes: int,
    expected: float,
) -> None:
    plan = prepare_vllm_reference_launch(
        command=_reference_command(),
        supported_flags=SUPPORTED_FLAGS,
        fresh_free_memory_bytes=free_bytes,
        total_memory_bytes=total_bytes,
        run_id="reference-headroom",
        native_root=tmp_path,
    )
    assert plan.admission.selected_utilization == expected
    assert _gpu_value(plan.launch.command) == expected


@pytest.mark.parametrize(
    ("free_bytes", "total_bytes", "match"),
    [
        (0, 10_000, "positive integer"),
        (10_001, 10_000, "cannot exceed"),
        (100, 10_000, "no positive reference reservation"),
    ],
)
def test_reference_plan_fails_closed_on_invalid_or_insufficient_fresh_memory(
    tmp_path: Path,
    free_bytes: int,
    total_bytes: int,
    match: str,
) -> None:
    with pytest.raises(VLLMHostPreflightError, match=match):
        prepare_vllm_reference_launch(
            command=_reference_command(),
            supported_flags=SUPPORTED_FLAGS,
            fresh_free_memory_bytes=free_bytes,
            total_memory_bytes=total_bytes,
            run_id="reference-invalid-memory",
            native_root=tmp_path,
        )


def test_reference_plan_rejects_caller_selected_gpu_reservation(
    tmp_path: Path,
) -> None:
    command = _reference_command("--gpu-memory-utilization", "0.90")
    with pytest.raises(VLLMHostPreflightError, match="producer owns"):
        prepare_vllm_reference_launch(
            command=command,
            supported_flags=SUPPORTED_FLAGS,
            fresh_free_memory_bytes=9_149,
            total_memory_bytes=10_000,
            run_id="reference-caller-reservation",
            native_root=tmp_path,
        )


@pytest.mark.parametrize(
    "command",
    [
        (
            "/tmp/prepared/bin/vllm",
            "serve",
            "model",
            "--port",
            "8000",
        ),
        (
            "/tmp/prepared/bin/vllm",
            "serve",
            "model",
            "--max-model-len",
            "4096",
            "--port",
            "8000",
        ),
        _reference_command("--max-model-len=auto"),
    ],
)
def test_reference_plan_rejects_missing_numeric_or_duplicate_auto_fit(
    tmp_path: Path,
    command: tuple[str, ...],
) -> None:
    with pytest.raises(VLLMHostPreflightError, match="max-model-len"):
        prepare_vllm_reference_launch(
            command=command,
            supported_flags=SUPPORTED_FLAGS,
            fresh_free_memory_bytes=9_500,
            total_memory_bytes=10_000,
            run_id="reference-invalid-auto",
            native_root=tmp_path,
        )


def test_reference_plan_accepts_equal_form_auto_fit_without_lexical_gate(
    tmp_path: Path,
) -> None:
    command = (
        "/tmp/prepared/bin/vllm",
        "serve",
        "model",
        "--max-model-len=auto",
        "--port",
        "8000",
    )
    plan = prepare_vllm_reference_launch(
        command=command,
        supported_flags=SUPPORTED_FLAGS,
        fresh_free_memory_bytes=9_500,
        total_memory_bytes=10_000,
        run_id="reference-equal-form",
        native_root=tmp_path,
    )

    assert "--max-model-len=auto" in plan.launch.command
    assert _gpu_value(plan.launch.command) == 0.94


def test_reference_plan_fails_closed_on_unsupported_required_flag(
    tmp_path: Path,
) -> None:
    with pytest.raises(VLLMHostPreflightError, match="unsupported"):
        prepare_vllm_reference_launch(
            command=_reference_command("--kv-cache-memory-bytes", "123456"),
            supported_flags=SUPPORTED_FLAGS,
            fresh_free_memory_bytes=9_500,
            total_memory_bytes=10_000,
            run_id="reference-unsupported",
            native_root=tmp_path,
        )


def test_semantic_qualification_launcher_still_rejects_auto_fit(
    tmp_path: Path,
) -> None:
    with pytest.raises(VLLMHostPreflightError, match="must be an integer"):
        prepare_vllm_qualification_launch(
            command=_semantic_command_with_auto(),
            supported_flags=SUPPORTED_FLAGS,
            requested_utilization=0.92,
            fallback_utilization=None,
            fresh_free_memory_bytes=11_500,
            total_memory_bytes=12_000,
            required_context_window=4096,
            capacity_recheck=lambda _utilization, _context: True,
            run_id="semantic-still-fixed",
            native_root=tmp_path,
        )


def test_reference_launch_uses_owned_runtime_and_native_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = prepare_vllm_reference_launch(
        command=_reference_command(),
        supported_flags=SUPPORTED_FLAGS,
        fresh_free_memory_bytes=9_149,
        total_memory_bytes=10_000,
        run_id="reference-launch",
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

    monkeypatch.setattr(reference_launcher, "_validate_vllm_unix_ipc_path", lambda _paths: None)
    monkeypatch.setattr(reference_launcher, "launch_owned_vllm_runtime", fake_launch)
    monkeypatch.setattr(reference_launcher, "wait_for_vllm_runtime_readiness", fake_wait)

    result = launch_vllm_reference_runtime(
        plan,
        run_id="reference-launch",
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


def test_reference_launch_cleans_owned_runtime_on_readiness_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = prepare_vllm_reference_launch(
        command=_reference_command(),
        supported_flags=SUPPORTED_FLAGS,
        fresh_free_memory_bytes=9_500,
        total_memory_bytes=10_000,
        run_id="reference-cleanup",
        native_root=tmp_path,
    )
    calls: dict[str, object] = {}

    class FakeRuntime:
        def cleanup(self) -> None:
            calls["cleanup"] = True

    runtime = FakeRuntime()
    monkeypatch.setattr(reference_launcher, "_validate_vllm_unix_ipc_path", lambda _paths: None)
    monkeypatch.setattr(
        reference_launcher,
        "launch_owned_vllm_runtime",
        lambda *_args, **_kwargs: runtime,
    )

    def fail_readiness(*_args, **_kwargs):
        raise RuntimeError("not ready")

    monkeypatch.setattr(
        reference_launcher,
        "wait_for_vllm_runtime_readiness",
        fail_readiness,
    )

    with pytest.raises(RuntimeError, match="not ready"):
        launch_vllm_reference_runtime(
            plan,
            run_id="reference-cleanup",
            expected_listener=RuntimeListenerEndpoint(host="127.0.0.1", port=8000),
        )

    assert calls["cleanup"] is True
