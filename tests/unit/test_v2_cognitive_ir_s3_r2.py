from __future__ import annotations

import relaylm.v2_cognitive_ir_s3 as base
from relaylm.v2_cognitive_ir_s3_r2 import (
    HISTORICAL_S3_V1_SEEDS,
    S3_R2_LABEL,
    S3_R2_PREREGISTRATION_SCHEMA,
    S3_R2_PREREGISTRATION_SHA256,
    S3_R2_SEEDS,
    activate_s3_r2_preregistration,
    derive_s3_r2_seed,
    validate_s3_r2_preregistration,
)
import tools.v2_cognitive_ir_s3_llama_cpp_wsl as wsl


def test_s3_r2_frozen_identity_seeds_and_route() -> None:
    validate_s3_r2_preregistration()
    assert S3_R2_PREREGISTRATION_SCHEMA == "relaylm2-cognitive-ir-s3-prereg-v2"
    assert S3_R2_PREREGISTRATION_SHA256 == (
        "d3e19d59c2c6481178b942d462e4fca0a1ace02ed8deea1ae3c22f68c59f2166"
    )
    assert S3_R2_LABEL == "relaylm2-cognitive-ir-s3-semantic-invariance-v2"
    assert {
        regime: tuple(derive_s3_r2_seed(regime, index) for index in range(3))
        for regime in base.S3_REGIMES
    } == dict(S3_R2_SEEDS)

    fresh = {seed for values in S3_R2_SEEDS.values() for seed in values}
    historical = {
        seed for values in HISTORICAL_S3_V1_SEEDS.values() for seed in values
    }
    assert len(fresh) == 12
    assert fresh.isdisjoint(historical)
    assert wsl.INNER_TRANSACTION_MODULE == (
        "tools.v2_cognitive_ir_s3_r2_llama_cpp_transaction"
    )


def test_s3_r2_activation_changes_only_campaign_identity_and_families() -> None:
    original = (
        base.S3_PREREGISTRATION_SCHEMA,
        base.S3_PREREGISTRATION_SHA256,
        base.S3_LABEL,
        base.S3_SEEDS,
    )
    scientific_shape = (
        tuple(base.S3_REGIMES),
        dict(base.S3_SHARD_CALLS),
        base.S3_TOTAL_SEMANTIC_CALLS,
        base.S3_TOTAL_INPUT_TOKEN_REQUESTS,
        tuple(base.S3_SURFACE_VARIANTS),
        tuple(base.S3_SEMANTIC_INTERVENTIONS),
        base.S3_SURFACE_EFFECT_MAX,
        base.S3_SEMANTIC_EFFECT_MIN,
        base.S3_EFFECT_MARGIN_MIN,
    )
    try:
        activate_s3_r2_preregistration()
        assert base.S3_PREREGISTRATION_SCHEMA == S3_R2_PREREGISTRATION_SCHEMA
        assert base.S3_PREREGISTRATION_SHA256 == S3_R2_PREREGISTRATION_SHA256
        assert base.S3_LABEL == S3_R2_LABEL
        assert dict(base.S3_SEEDS) == dict(S3_R2_SEEDS)
        base.validate_frozen_seeds()
        assert len(base.s3_campaign_plan()) == 498
        assert (
            tuple(base.S3_REGIMES),
            dict(base.S3_SHARD_CALLS),
            base.S3_TOTAL_SEMANTIC_CALLS,
            base.S3_TOTAL_INPUT_TOKEN_REQUESTS,
            tuple(base.S3_SURFACE_VARIANTS),
            tuple(base.S3_SEMANTIC_INTERVENTIONS),
            base.S3_SURFACE_EFFECT_MAX,
            base.S3_SEMANTIC_EFFECT_MIN,
            base.S3_EFFECT_MARGIN_MIN,
        ) == scientific_shape
    finally:
        (
            base.S3_PREREGISTRATION_SCHEMA,
            base.S3_PREREGISTRATION_SHA256,
            base.S3_LABEL,
            base.S3_SEEDS,
        ) = original
