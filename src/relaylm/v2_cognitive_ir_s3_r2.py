from __future__ import annotations

import hashlib
from typing import Mapping

import relaylm.v2_cognitive_ir_s3 as base
from relaylm.v2_cognitive_ir_calibration import CALIBRATION_SEEDS
from relaylm.v2_cognitive_ir_calibration_v2 import CALIBRATION_V2_SEEDS
from relaylm.v2_cognitive_ir_s2_selected import S2_SELECTED_SEED


S3_R2_PREREGISTRATION_SCHEMA = "relaylm2-cognitive-ir-s3-prereg-v2"
S3_R2_PREREGISTRATION_SHA256 = (
    "d3e19d59c2c6481178b942d462e4fca0a1ace02ed8deea1ae3c22f68c59f2166"
)
S3_R2_LABEL = "relaylm2-cognitive-ir-s3-semantic-invariance-v2"
S3_R2_SEEDS: Mapping[str, tuple[int, ...]] = {
    "shared": (900332946, 4686252, 1045955583),
    "null": (2143918802, 448647733, 1569754577),
    "mismatch": (1206244949, 1165112526, 1584962688),
    "shift": (236371850, 1062068690, 225652850),
}
HISTORICAL_S3_V1_SEEDS: Mapping[str, tuple[int, ...]] = {
    "shared": (408671368, 1152794703, 2087212991),
    "null": (292304948, 865761977, 509247258),
    "mismatch": (1201776179, 630460040, 1118062807),
    "shift": (5662972, 445070522, 1853464615),
}


class S3R2BindingError(ValueError):
    """The #2491 replacement preregistration cannot be bound exactly."""


def derive_s3_r2_seed(regime: str, index: int) -> int:
    if regime not in base.S3_REGIMES:
        raise S3R2BindingError(f"unsupported S3-R2 regime: {regime}")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 3:
        raise S3R2BindingError("S3-R2 seed index must be 0..2")
    raw = hashlib.sha256(
        f"{S3_R2_LABEL}|{regime}|seed|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def validate_s3_r2_preregistration() -> None:
    derived = {
        regime: tuple(derive_s3_r2_seed(regime, index) for index in range(3))
        for regime in base.S3_REGIMES
    }
    if derived != dict(S3_R2_SEEDS):
        raise S3R2BindingError("derived S3-R2 seeds drifted from #2491")

    flattened = tuple(
        seed for regime in base.S3_REGIMES for seed in S3_R2_SEEDS[regime]
    )
    if len(set(flattened)) != 12:
        raise S3R2BindingError("S3-R2 seeds are not unique")

    historical = {
        seed
        for regime in base.S3_REGIMES
        for seed in HISTORICAL_S3_V1_SEEDS[regime]
    }
    forbidden = {
        2211,
        S2_SELECTED_SEED,
        *CALIBRATION_SEEDS,
        *CALIBRATION_V2_SEEDS,
        *historical,
    }
    overlap = sorted(set(flattened) & forbidden)
    if overlap:
        raise S3R2BindingError(
            f"S3-R2 seeds overlap historical evidence: {overlap}"
        )

    if tuple(base.S3_REGIMES) != ("shared", "null", "mismatch", "shift"):
        raise S3R2BindingError("S3-R2 regime order drifted")
    if dict(base.S3_SHARD_CALLS) != {
        "shared": 123,
        "null": 123,
        "mismatch": 123,
        "shift": 129,
    }:
        raise S3R2BindingError("S3-R2 shard ledger drifted")
    if base.S3_TOTAL_SEMANTIC_CALLS != 498:
        raise S3R2BindingError("S3-R2 semantic-call total drifted")
    if base.S3_TOTAL_INPUT_TOKEN_REQUESTS != 996:
        raise S3R2BindingError("S3-R2 input-token ledger drifted")
    if (
        base.S3_SURFACE_EFFECT_MAX,
        base.S3_SEMANTIC_EFFECT_MIN,
        base.S3_EFFECT_MARGIN_MIN,
    ) != (0.15, 0.20, 0.15):
        raise S3R2BindingError("S3-R2 discriminator thresholds drifted")


def activate_s3_r2_preregistration() -> None:
    """Activate #2491 only inside the dedicated fresh S3-R2 child process.

    The historical base module remains the immutable #2461/#2478 campaign on
    normal import.  The one-command WSL route launches a fresh child whose
    first action is this exact replacement binding, before the physical
    transaction module imports its preregistration identity.
    """

    validate_s3_r2_preregistration()
    base.S3_PREREGISTRATION_SCHEMA = S3_R2_PREREGISTRATION_SCHEMA
    base.S3_PREREGISTRATION_SHA256 = S3_R2_PREREGISTRATION_SHA256
    base.S3_LABEL = S3_R2_LABEL
    base.S3_SEEDS = S3_R2_SEEDS
    base.validate_frozen_seeds()
