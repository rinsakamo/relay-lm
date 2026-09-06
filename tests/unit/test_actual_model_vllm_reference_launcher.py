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
        "--gpu-memory-utilization",
        "0.92",
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


def test_reference_plan_accepts_auto_fit_without_semantic_window_recheck(
    tmp_path: Path,
) -> None:
    signature = inspect.signature(prepare_vllm_reference_launch)
    assert "required_context_window" not in signature.parameters
    assert "capacity_recheck" not in signature.parameters

    plan = prepare_vllm_reference_launch(
        command=_reference_command(),
        supported_flags=SUPPORTED_FLAGS,
        requested_utilization=0.92,
        fallback_utilization=0.90,
        fresh_free_memory_bytes=10_980,
        total_memory_bytes=12_000,
        run_id="reference-auto",
        native_root=tmp_path,
    )

    assert plan.admission.requested_utilization == 0.92
    assert plan.admission.selected_utilization == 0.90
    assert plan.admission.changed is True
    assert plan.admission.reason == "reference_gpu_reservation_reduced_before_measurement"
    assert plan.admission.reattest_required is True
    assert _gpu_value(plan.launch.command) == 0.90
    max_len_index = plan.launch.command.index("--max-model-len")
    assert plan.launch.command[max_len_index + 1] == "auto"


def test_reference_plan_keeps_requested_reservation_when_freshly_available(
    tmp_path: Path,
) -> None:
    plan = prepare_vllm_reference_launch(
        command=_reference_command(),
        supported_flags=SUPPORTED_FLAGS,
        requested_utilization=0.92,
        fallback_utilization=None,
        fresh_free_memory_bytes=11_500,
        total_memory_bytes=12_000,
        run_id="reference-requested",
        native_root=tmp_path,
    )

    assert plan.admission.selected_utilization == 0.92
    assert plan.admission.changed is False
    assert plan.admission.reason == "requested_reference_gpu_reservation_admitted"


def test_reference_plan_fails_when_declared_reservation_is_not_available(
    tmp_path: Path,
) -> None:
    with pytest.raises(VLLMHostPreflightError, match="not currently available"):
        prepare_vllm_reference_launch(
            command=_reference_command(),
            supported_flags=SUPPORTED_FLAGS,
            requested_utilization=0.92,
            fallback_utilization=None,
            fresh_free_memory_bytes=10_980,
            total_memory_bytes=12_000,
            run_id="reference-unavailable",
            native_root=tmp_path,
        )


@pytest.mark.parametrize(
    "command",
    [
        (
            "/tmp/prepared/bin/vllm",
            "serve",
            "model",
            "--gpu-memory-utilization",
            "0.92",
            "--port",
            "8000",
        ),
        (
            "/tmp/prepared/bin/vllm",
            "serve",
            "model",
            "--max-model-len",
            "4096",
            "--gpu-memory-utilization",
            "0.92",
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
            requested_utilization=0.92,
            fallback_utilization=None,
            fresh_free_memory_bytes=11_500,
            total_memory_bytes=12_000,
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
        "--gpu-memory-utilization=0.92",
        "--port",
        "8000",
    )
    plan = prepare_vllm_reference_launch(
        command=command,
        supported_flags=SUPPORTED_FLAGS,
        requested_utilization=0.92,
        fallback_utilization=None,
        fresh_free_memory_bytes=11_500,
        total_memory_bytes=12_000,
        run_id="reference-equal-form",
        native_root=tmp_path,
    )

    assert "--max-model-len=auto" in plan.launch.command
    assert "--gpu-memory-utilization=0.92" in plan.launch.command


def test_reference_plan_fails_closed_on_unsupported_required_flag(
    tmp_path: Path,
) -> None:
    with pytest.raises(VLLMHostPreflightError, match="unsupported"):
        prepare_vllm_reference_launch(
            command=_reference_command("--kv-cache-memory-bytes", "123456"),
            supported_flags=SUPPORTED_FLAGS,
            requested_utilization=0.92,
            fallback_utilization=None,
            fresh_free_memory_bytes=11_500,
            total_memory_bytes=12_000,
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
        requested_utilization=0.92,
        fallback_utilization=0.90,
        fresh_free_memory_bytes=10_980,
        total_memory_bytes=12_000,
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
        requested_utilization=0.92,
        fallback_utilization=None,
        fresh_free_memory_bytes=11_500,
        total_memory_bytes=12_000,
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
