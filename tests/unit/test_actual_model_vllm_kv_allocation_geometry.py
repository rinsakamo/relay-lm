from __future__ import annotations

import pytest

from relaylm.actual_model_vllm_profiler import VLLMTokenCapacityReference


def _page_reference() -> VLLMTokenCapacityReference:
    return VLLMTokenCapacityReference(
        non_kv_memory_bytes=5_000_000,
        kv_cache_memory_bytes=4_000_000,
        kv_cache_capacity_tokens=4_000,
        kv_allocation_unit_bytes=64_000,
        kv_allocation_unit_tokens=64,
        kv_allocation_guard_units=1,
    )


def test_fixed_window_kv_requirement_is_conservative_in_allocation_units() -> None:
    reference = _page_reference()
    assert reference.kv_bytes_per_token_upper_bound == 1_000
    assert reference.required_kv_cache_memory_bytes(target_model_len=3_000) == 3_072_000


def test_allocation_geometry_does_not_remove_no_extrapolation_boundary() -> None:
    with pytest.raises(ValueError, match="attested KV token capacity"):
        _page_reference().required_kv_cache_memory_bytes(target_model_len=4_001)
