from __future__ import annotations

import pytest

from relaylm.actual_model_vllm_profiler import (
    VLLMKVAllocationDemand,
    VLLMTokenCapacityReference,
)


def _page_reference() -> VLLMTokenCapacityReference:
    return VLLMTokenCapacityReference(
        non_kv_memory_bytes=5_000_000,
        kv_cache_memory_bytes=4_096_000,
        kv_cache_capacity_tokens=4_096,
        kv_pool_block_bytes=64_000,
        kv_allocation_demands=(
            VLLMKVAllocationDemand(multiplicity=1, tokens_per_block=64),
        ),
    )


def test_fixed_window_kv_requirement_is_conservative_in_allocation_units() -> None:
    reference = _page_reference()

    # Continuous byte/token arithmetic asks for exactly 3_000_000 bytes.
    # Whole-block allocation needs ceil(3000 / 64) * 64_000 = 3_008_000.
    assert reference.kv_bytes_per_token_upper_bound == 1_000
    assert reference.required_kv_pool_blocks(target_model_len=3_000) == 47
    assert reference.required_kv_cache_memory_bytes(target_model_len=3_000) == 3_008_000


def test_allocation_geometry_does_not_remove_no_extrapolation_boundary() -> None:
    with pytest.raises(ValueError, match="attested KV token capacity"):
        _page_reference().required_kv_cache_memory_bytes(target_model_len=4_097)


def test_inconsistent_allocation_geometry_fails_closed() -> None:
    with pytest.raises(ValueError, match="allocation geometry"):
        VLLMTokenCapacityReference(
            non_kv_memory_bytes=5_000_000,
            kv_cache_memory_bytes=60_000,
            kv_cache_capacity_tokens=4_096,
            kv_pool_block_bytes=64_000,
            kv_allocation_demands=(
                VLLMKVAllocationDemand(multiplicity=1, tokens_per_block=64),
            ),
        )


def test_heterogeneous_group_widths_are_representable_without_scalar_collapse() -> None:
    reference = VLLMTokenCapacityReference(
        non_kv_memory_bytes=5_000_000,
        kv_cache_memory_bytes=10_000_000,
        kv_cache_capacity_tokens=4_096,
        kv_pool_block_bytes=10_000,
        kv_allocation_demands=(
            VLLMKVAllocationDemand(
                multiplicity=5,
                tokens_per_block=16,
                fixed_blocks_per_request=1,
            ),
            VLLMKVAllocationDemand(
                multiplicity=1,
                tokens_per_block=64,
            ),
        ),
    )

    assert reference.required_kv_pool_blocks(target_model_len=3_000) == 992


def test_equivalent_duplicate_demand_terms_are_canonicalized() -> None:
    reference = VLLMTokenCapacityReference(
        non_kv_memory_bytes=5_000_000,
        kv_cache_memory_bytes=10_000_000,
        kv_cache_capacity_tokens=4_096,
        kv_pool_block_bytes=10_000,
        kv_allocation_demands=(
            VLLMKVAllocationDemand(multiplicity=1, tokens_per_block=64),
            VLLMKVAllocationDemand(
                multiplicity=2,
                tokens_per_block=16,
                fixed_blocks_per_request=1,
            ),
            VLLMKVAllocationDemand(
                multiplicity=3,
                tokens_per_block=16,
                fixed_blocks_per_request=1,
            ),
        ),
    )

    assert reference.kv_allocation_demands == (
        VLLMKVAllocationDemand(
            multiplicity=5,
            tokens_per_block=16,
            fixed_blocks_per_request=1,
        ),
        VLLMKVAllocationDemand(multiplicity=1, tokens_per_block=64),
    )


def test_allocation_demand_validation_is_strict() -> None:
    with pytest.raises(ValueError):
        VLLMKVAllocationDemand(multiplicity=0, tokens_per_block=16)
    with pytest.raises(ValueError):
        VLLMKVAllocationDemand(multiplicity=1, tokens_per_block=0)
    with pytest.raises(ValueError):
        VLLMKVAllocationDemand(
            multiplicity=1,
            tokens_per_block=16,
            fixed_blocks_per_request=-1,
        )


def test_reference_requires_non_empty_allocation_demands() -> None:
    with pytest.raises(ValueError, match="non-empty tuple"):
        VLLMTokenCapacityReference(
            non_kv_memory_bytes=5_000_000,
            kv_cache_memory_bytes=10_000_000,
            kv_cache_capacity_tokens=4_096,
            kv_pool_block_bytes=10_000,
            kv_allocation_demands=(),
        )
