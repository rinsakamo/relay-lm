from __future__ import annotations

import pytest

from relaylm.actual_model_vllm_launch import VLLMLaunchMemoryAdmission


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
