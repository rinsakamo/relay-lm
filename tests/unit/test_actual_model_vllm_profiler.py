from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from relaylm.actual_model_vllm_profiler import VLLMLaunchMemoryAdmission


def _run_parser(tmp_path: Path, log_text: str) -> subprocess.CompletedProcess[str]:
    log_path = tmp_path / "profiler.log"
    log_path.write_text(log_text, encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "relaylm.actual_model_vllm_profiler",
            "--log",
            str(log_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_profiler_cli_parses_observed_backtick_recommendation(tmp_path: Path) -> None:
    result = _run_parser(
        tmp_path,
        "INFO To fully utilize available GPU memory, use `--kv-cache-memory=1493352960`.\n",
    )

    assert result.returncode == 0
    assert result.stdout == "1493352960\n"
    assert result.stderr == ""


def test_profiler_cli_parses_documented_bytes_form(tmp_path: Path) -> None:
    result = _run_parser(
        tmp_path,
        "INFO To fully utilize available GPU memory, use --kv-cache-memory-bytes=1618644685\n",
    )

    assert result.returncode == 0
    assert result.stdout == "1618644685\n"


def test_profiler_cli_selects_fully_utilize_role_from_pinned_vllm_message(
    tmp_path: Path,
) -> None:
    result = _run_parser(
        tmp_path,
        (
            "INFO Replace gpu_memory_utilization config with "
            "`--kv-cache-memory=1400000000` (1.30 GiB) to fit into requested "
            "memory, or `--kv-cache-memory=1500000000` (1.40 GiB) to fully "
            "utilize gpu memory. Current kv cache memory in use is 1.20 GiB.\n"
        ),
    )

    assert result.returncode == 0
    assert result.stdout == "1500000000\n"
    assert result.stderr == ""


def test_profiler_cli_rejects_requested_limit_without_fully_utilize_role(
    tmp_path: Path,
) -> None:
    result = _run_parser(
        tmp_path,
        "INFO `--kv-cache-memory=1400000000` (1.30 GiB) to fit into requested memory.\n",
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "not found" in result.stderr


def test_profiler_cli_allows_repeated_identical_recommendation(tmp_path: Path) -> None:
    result = _run_parser(
        tmp_path,
        "\n".join(
            [
                "INFO To fully utilize available GPU memory, use `--kv-cache-memory=1493352960`.",
                "INFO To fully utilize available GPU memory, use `--kv-cache-memory-bytes=1493352960`.",
            ]
        ),
    )

    assert result.returncode == 0
    assert result.stdout == "1493352960\n"


def test_profiler_cli_rejects_conflicting_recommendations(tmp_path: Path) -> None:
    result = _run_parser(
        tmp_path,
        "\n".join(
            [
                "INFO To fully utilize available GPU memory, use `--kv-cache-memory=1493352960`.",
                "INFO To fully utilize available GPU memory, use --kv-cache-memory-bytes=1493352961.",
            ]
        ),
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "conflicting" in result.stderr


def test_profiler_cli_rejects_missing_recommendation(tmp_path: Path) -> None:
    result = _run_parser(tmp_path, "INFO CUDA graph capture complete\n")

    assert result.returncode == 2
    assert result.stdout == ""
    assert "not found" in result.stderr


def test_launch_admission_floors_fresh_free_ratio_to_three_decimals() -> None:
    admission = VLLMLaunchMemoryAdmission.from_fresh_bytes(
        free_bytes=9_149,
        total_bytes=10_000,
    )

    assert admission.gpu_memory_utilization == "0.914"


def test_profiler_and_final_runtime_share_one_explicit_admission() -> None:
    admission = VLLMLaunchMemoryAdmission.from_fresh_bytes(
        free_bytes=7_509,
        total_bytes=10_000,
    )

    assert admission.profiler_memory_args() == (
        "--gpu-memory-utilization",
        "0.750",
        "--max-model-len",
        "auto",
    )
    assert admission.final_memory_args(kv_cache_memory_bytes=123_456_789) == (
        "--gpu-memory-utilization",
        "0.750",
        "--kv-cache-memory-bytes",
        "123456789",
        "--max-model-len",
        "auto",
    )


@pytest.mark.parametrize(
    ("free_bytes", "total_bytes"),
    [
        (0, 10_000),
        (10_001, 10_000),
        (1, 10_000),
        (10_000, 10_000),
    ],
)
def test_launch_admission_rejects_invalid_or_unusable_fresh_capacity(
    free_bytes: int,
    total_bytes: int,
) -> None:
    with pytest.raises(ValueError):
        VLLMLaunchMemoryAdmission.from_fresh_bytes(
            free_bytes=free_bytes,
            total_bytes=total_bytes,
        )


@pytest.mark.parametrize(
    ("free_bytes", "total_bytes"),
    [
        (True, 10_000),
        (9_000, False),
        (9_000.0, 10_000),
    ],
)
def test_launch_admission_requires_integer_byte_evidence(
    free_bytes: object,
    total_bytes: object,
) -> None:
    with pytest.raises(TypeError):
        VLLMLaunchMemoryAdmission.from_fresh_bytes(  # type: ignore[arg-type]
            free_bytes=free_bytes,
            total_bytes=total_bytes,
        )


@pytest.mark.parametrize("kv_cache_memory_bytes", [0, -1, True, 1.5])
def test_final_launch_requires_positive_integer_explicit_kv(
    kv_cache_memory_bytes: object,
) -> None:
    admission = VLLMLaunchMemoryAdmission.from_fresh_bytes(
        free_bytes=7_509,
        total_bytes=10_000,
    )

    expected = TypeError if isinstance(kv_cache_memory_bytes, (bool, float)) else ValueError
    with pytest.raises(expected):
        admission.final_memory_args(  # type: ignore[arg-type]
            kv_cache_memory_bytes=kv_cache_memory_bytes,
        )
