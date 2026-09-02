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


def test_missing_serve_subcommand_fails_before_launch_plan(tmp_path: Path) -> None:
    malformed = (
        "vllm",
        "model",
        "--max-model-len",
        "4096",
        "--gpu-memory-utilization",
        "0.92",
        "--port",
        "8000",
    )

    with pytest.raises(VLLMHostPreflightError, match="vllm serve"):
        prepare_vllm_qualification_launch(
            command=malformed,
            supported_flags=SUPPORTED_FLAGS,
            requested_utilization=0.92,
            fallback_utilization=0.90,
            fresh_free_memory_bytes=11_500,
            total_memory_bytes=12_000,
            required_context_window=4096,
            capacity_recheck=lambda _utilization, _context: True,
            run_id="qualification-missing-serve",
            native_root=tmp_path,
        )
