from __future__ import annotations

import hashlib
import json
from typing import Mapping

import relaylm.v2_cognitive_ir_s3 as base
from relaylm.v2_cognitive_ir_calibration import CALIBRATION_SEEDS
from relaylm.v2_cognitive_ir_calibration_v2 import CALIBRATION_V2_SEEDS
from relaylm.v2_cognitive_ir_s2_selected import S2_SELECTED_SEED
from relaylm.v2_cognitive_ir_s3_r2 import HISTORICAL_S3_V1_SEEDS, S3_R2_SEEDS


S3_R3_PREREGISTRATION_SCHEMA = "relaylm2-cognitive-ir-s3-prereg-v3"
S3_R3_LABEL = "relaylm2-cognitive-ir-s3-semantic-invariance-v3"
S3_R3_MAX_OUTPUT_TOKENS = 1024
S3_R3_SEEDS: Mapping[str, tuple[int, ...]] = {
    "shared": (410645929, 1746379332, 553311797),
    "null": (37598355, 516261911, 867582011),
    "mismatch": (970643640, 1824424633, 1573930240),
    "shift": (1371833688, 1071883363, 1464302864),
}
S3_R3_PREREGISTRATION_SHA256 = (
    "a0b137f023c260eb9da479f5722708f6cf6f955198e4234203753831e9278ed1"
)


class S3R3BindingError(ValueError):
    """The #2517/#2518 S3-R3 preregistration cannot be bound exactly."""


def derive_s3_r3_seed(regime: str, index: int) -> int:
    if regime not in base.S3_REGIMES:
        raise S3R3BindingError(f"unsupported S3-R3 regime: {regime}")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 3:
        raise S3R3BindingError("S3-R3 seed index must be 0..2")
    raw = hashlib.sha256(
        f"{S3_R3_LABEL}|{regime}|seed|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def _spec_payload() -> dict[str, object]:
    return {
        "schema": S3_R3_PREREGISTRATION_SCHEMA,
        "label": S3_R3_LABEL,
        "seeds": {key: list(value) for key, value in S3_R3_SEEDS.items()},
        "max_output_tokens": S3_R3_MAX_OUTPUT_TOKENS,
        "regimes": list(base.S3_REGIMES),
        "shard_calls": dict(base.S3_SHARD_CALLS),
        "total_semantic_calls": base.S3_TOTAL_SEMANTIC_CALLS,
        "total_input_token_requests": base.S3_TOTAL_INPUT_TOKEN_REQUESTS,
        "surface_effect_max": base.S3_SURFACE_EFFECT_MAX,
        "semantic_effect_min": base.S3_SEMANTIC_EFFECT_MIN,
        "effect_margin_min": base.S3_EFFECT_MARGIN_MIN,
    }


def _spec_sha256() -> str:
    canonical = json.dumps(
        _spec_payload(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_s3_r3_preregistration() -> None:
    derived = {
        regime: tuple(derive_s3_r3_seed(regime, index) for index in range(3))
        for regime in base.S3_REGIMES
    }
    if derived != dict(S3_R3_SEEDS):
        raise S3R3BindingError("derived S3-R3 seeds drifted from #2517")

    flattened = tuple(
        seed for regime in base.S3_REGIMES for seed in S3_R3_SEEDS[regime]
    )
    if len(set(flattened)) != 12:
        raise S3R3BindingError("S3-R3 seeds are not unique")

    forbidden = {
        2211,
        2518,
        S2_SELECTED_SEED,
        *CALIBRATION_SEEDS,
        *CALIBRATION_V2_SEEDS,
        *(seed for values in HISTORICAL_S3_V1_SEEDS.values() for seed in values),
        *(seed for values in S3_R2_SEEDS.values() for seed in values),
    }
    overlap = sorted(set(flattened) & forbidden)
    if overlap:
        raise S3R3BindingError(f"S3-R3 seeds overlap prior evidence: {overlap}")

    if tuple(base.S3_REGIMES) != ("shared", "null", "mismatch", "shift"):
        raise S3R3BindingError("S3-R3 regime order drifted")
    if dict(base.S3_SHARD_CALLS) != {
        "shared": 123,
        "null": 123,
        "mismatch": 123,
        "shift": 129,
    }:
        raise S3R3BindingError("S3-R3 shard ledger drifted")
    if base.S3_TOTAL_SEMANTIC_CALLS != 498:
        raise S3R3BindingError("S3-R3 semantic-call total drifted")
    if base.S3_TOTAL_INPUT_TOKEN_REQUESTS != 996:
        raise S3R3BindingError("S3-R3 input-token ledger drifted")
    if (
        base.S3_SURFACE_EFFECT_MAX,
        base.S3_SEMANTIC_EFFECT_MIN,
        base.S3_EFFECT_MARGIN_MIN,
    ) != (0.15, 0.20, 0.15):
        raise S3R3BindingError("S3-R3 discriminator thresholds drifted")
    if _spec_sha256() != S3_R3_PREREGISTRATION_SHA256:
        raise S3R3BindingError("S3-R3 preregistration spec hash drifted")


def activate_s3_r3_preregistration() -> None:
    """Activate the fresh R3 campaign only in its dedicated child process."""

    validate_s3_r3_preregistration()
    base.S3_PREREGISTRATION_SCHEMA = S3_R3_PREREGISTRATION_SCHEMA
    base.S3_PREREGISTRATION_SHA256 = S3_R3_PREREGISTRATION_SHA256
    base.S3_LABEL = S3_R3_LABEL
    base.S3_SEEDS = S3_R3_SEEDS
    base.validate_frozen_seeds()
