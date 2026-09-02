from __future__ import annotations

from pathlib import Path

import pytest

from relaylm.actual_model_vllm_launch_preflight import VLLMHostPreflightError
from relaylm.actual_model_vllm_qualification_launcher import prepare_vllm_qualification_launch


SUPPORTED_FLAGS = {
    "--gpu-memory-utilization",
    "--max-model-len",
    "--port",
}


def _tail() -> tuple[str, ...]:
    return (
        "--max-model-len",
        "4096",
        "--gpu-memory-utilization",
        "0.92",
        "--port",
        "8000",
    )


def _prepare(command: tuple[str, ...], tmp_path: Path):
    return prepare_vllm_qualification_launch(
        command=command,
        supported_flags=SUPPORTED_FLAGS,
        requested_utilization=0.92,
        fallback_utilization=0.90,
        fresh_free_memory_bytes=11_500,
        total_memory_bytes=12_000,
        required_context_window=4096,
        capacity_recheck=lambda _utilization, _context: True,
        run_id="qualification-command-shape",
        native_root=tmp_path,
    )


@pytest.mark.parametrize(
    "malformed",
    [
        ("vllm", "model", *_tail()),
        ("python", "serve", "model", *_tail()),
        ("vllm", "run", "model", *_tail()),
        ("vllm", "serve"),
        ("vllm", "serve", *_tail()),
    ],
)
def test_malformed_direct_serve_topology_fails_before_launch_plan(
    malformed: tuple[str, ...],
    tmp_path: Path,
) -> None:
    with pytest.raises(VLLMHostPreflightError, match="vllm serve"):
        _prepare(malformed, tmp_path)


def test_direct_vllm_serve_model_topology_is_preserved(tmp_path: Path) -> None:
    command = ("vllm", "serve", "model", *_tail())

    plan = _prepare(command, tmp_path)

    assert plan.launch.command[:3] == ("vllm", "serve", "model")
