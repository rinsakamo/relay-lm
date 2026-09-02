from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import pytest

from relaylm.actual_model_vllm_profiler import (
    VLLMLaunchMemoryAdmission,
    VLLMTokenCapacityReference,
)


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


def _reference() -> VLLMTokenCapacityReference:
    return VLLMTokenCapacityReference(
        non_kv_memory_bytes=5_000_000,
        kv_cache_memory_bytes=4_000_001,
        kv_cache_capacity_tokens=4_000,
        kv_allocation_unit_bytes=1,
        kv_allocation_unit_tokens=1,
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


def test_successful_launch_envelope_becomes_stable_non_kv_reference() -> None:
    reference = VLLMTokenCapacityReference.from_successful_launch_envelope(
        startup_free_bytes=11_789_139_968,
        kv_cache_memory_bytes=1_539_740_672,
        kv_cache_capacity_tokens=4_457,
        kv_allocation_unit_bytes=1,
        kv_allocation_unit_tokens=1,
    )

    assert reference.non_kv_memory_bytes == 10_249_399_296
    assert reference.kv_cache_memory_bytes == 1_539_740_672
    assert reference.kv_cache_capacity_tokens == 4_457
    assert reference.kv_allocation_unit_bytes == 1
    assert reference.kv_allocation_unit_tokens == 1


def test_token_capacity_reference_uses_conservative_byte_per_token_ceiling() -> None:
    reference = _reference()

    assert reference.kv_bytes_per_token_upper_bound == 1001
    assert reference.required_kv_cache_memory_bytes(target_model_len=1) == 1001
    assert (
        reference.required_kv_cache_memory_bytes(target_model_len=3_000)
        == 3_003_000
    )
    assert (
        reference.required_total_memory_bytes(target_model_len=3_000)
        == 8_003_000
    )


def test_token_capacity_reference_is_monotonic() -> None:
    reference = _reference()

    smaller = reference.required_kv_cache_memory_bytes(target_model_len=2_000)
    larger = reference.required_kv_cache_memory_bytes(target_model_len=3_000)

    assert smaller < larger
    assert larger <= (
        reference.kv_bytes_per_token_upper_bound
        * reference.kv_cache_capacity_tokens
    )


def test_token_capacity_reference_refuses_extrapolation_beyond_attested_capacity() -> None:
    with pytest.raises(ValueError, match="attested KV token capacity"):
        _reference().required_kv_cache_memory_bytes(target_model_len=4_001)


def test_free_vram_jitter_above_requirement_does_not_change_launch_args() -> None:
    reference = _reference()
    low_free = VLLMLaunchMemoryAdmission.for_token_window(
        free_bytes=8_100_000,
        total_bytes=10_000_000,
        target_model_len=3_000,
        reference=reference,
    )
    high_free = VLLMLaunchMemoryAdmission.for_token_window(
        free_bytes=9_900_000,
        total_bytes=10_000_000,
        target_model_len=3_000,
        reference=reference,
    )

    assert low_free.required_memory_bytes == 8_003_000
    assert high_free.required_memory_bytes == 8_003_000
    assert low_free.gpu_memory_utilization == high_free.gpu_memory_utilization
    assert low_free.final_memory_args() == high_free.final_memory_args()


def test_final_runtime_uses_required_envelope_explicit_kv_and_selected_window() -> None:
    admission = VLLMLaunchMemoryAdmission.for_token_window(
        free_bytes=9_000_000,
        total_bytes=10_000_000,
        target_model_len=3_000,
        reference=_reference(),
    )

    assert admission.kv_cache_memory_bytes == 3_003_000
    assert admission.final_memory_args() == (
        "--gpu-memory-utilization",
        admission.gpu_memory_utilization,
        "--kv-cache-memory-bytes",
        "3003000",
        "--max-model-len",
        "3000",
    )
    assert "auto" not in admission.final_memory_args()


def test_startup_utilization_is_derived_from_required_memory_not_free_memory() -> None:
    admission = VLLMLaunchMemoryAdmission.for_token_window(
        free_bytes=9_000_000,
        total_bytes=10_000_000,
        target_model_len=3_000,
        reference=_reference(),
    )

    rendered = float(admission.gpu_memory_utilization)
    requested_by_pinned_vllm = math.ceil(admission.total_bytes * rendered)

    assert requested_by_pinned_vllm <= admission.required_memory_bytes
    assert admission.gpu_memory_utilization.startswith("0.800")


def test_launch_admission_accepts_exactly_required_free_memory() -> None:
    admission = VLLMLaunchMemoryAdmission.for_token_window(
        free_bytes=8_003_000,
        total_bytes=10_000_000,
        target_model_len=3_000,
        reference=_reference(),
    )

    assert admission.required_memory_bytes == admission.free_bytes


def test_launch_admission_fails_only_when_fresh_free_memory_is_below_requirement() -> None:
    with pytest.raises(ValueError, match="below the token-derived required memory"):
        VLLMLaunchMemoryAdmission.for_token_window(
            free_bytes=8_002_999,
            total_bytes=10_000_000,
            target_model_len=3_000,
            reference=_reference(),
        )


@pytest.mark.parametrize(
    ("non_kv_memory_bytes", "kv_cache_memory_bytes", "kv_cache_capacity_tokens"),
    [
        (0, 1, 1),
        (1, 0, 1),
        (1, 1, 0),
        (True, 1, 1),
        (1, 1.5, 1),
    ],
)
def test_token_capacity_reference_requires_positive_integer_evidence(
    non_kv_memory_bytes: object,
    kv_cache_memory_bytes: object,
    kv_cache_capacity_tokens: object,
) -> None:
    expected = (
        TypeError
        if any(
            isinstance(value, (bool, float))
            for value in (
                non_kv_memory_bytes,
                kv_cache_memory_bytes,
                kv_cache_capacity_tokens,
            )
        )
        else ValueError
    )
    with pytest.raises(expected):
        VLLMTokenCapacityReference(  # type: ignore[arg-type]
            non_kv_memory_bytes=non_kv_memory_bytes,
            kv_cache_memory_bytes=kv_cache_memory_bytes,
            kv_cache_capacity_tokens=kv_cache_capacity_tokens,
            kv_allocation_unit_bytes=1,
            kv_allocation_unit_tokens=1,
        )


@pytest.mark.parametrize(
    ("free_bytes", "total_bytes"),
    [
        (0, 10_000_000),
        (10_000_001, 10_000_000),
        (True, 10_000_000),
        (9_000_000.0, 10_000_000),
    ],
)
def test_launch_admission_requires_valid_fresh_capacity_evidence(
    free_bytes: object,
    total_bytes: object,
) -> None:
    expected = (
        TypeError
        if isinstance(free_bytes, (bool, float))
        or isinstance(total_bytes, (bool, float))
        else ValueError
    )
    with pytest.raises(expected):
        VLLMLaunchMemoryAdmission.for_token_window(  # type: ignore[arg-type]
            free_bytes=free_bytes,
            total_bytes=total_bytes,
            target_model_len=3_000,
            reference=_reference(),
        )
