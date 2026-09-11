from __future__ import annotations

import hashlib
import json
from typing import Mapping

import relaylm.v2_cognitive_ir_s3 as base
from relaylm.v2_cognitive_ir_actual_model import (
    S2Representation,
    build_s2_formation_messages,
    form_s2_representations as _historical_form_s2_representations,
)
from relaylm.v2_cognitive_ir_calibration import CALIBRATION_SEEDS
from relaylm.v2_cognitive_ir_calibration_v2 import CALIBRATION_V2_SEEDS
from relaylm.v2_cognitive_ir_p2_boundedness_qual_v2 import (
    P2_BOUNDEDNESS_HARD_MAX_CHARACTERS,
    P2_BOUNDEDNESS_HARD_MAX_WORDS,
    P2_BOUNDEDNESS_QUAL_V2_SEEDS,
    P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS,
    P2_BOUNDEDNESS_TARGET_MAX_WORDS,
    P2_BOUNDEDNESS_TARGET_MIN_WORDS,
    build_margin_p2_formation_messages,
    validate_p2_boundedness_qualification_v2,
)
from relaylm.v2_cognitive_ir_p2_termination_qual import (
    P2_TERMINATION_QUAL_SEEDS,
    S3_R4_LABEL as PRECOMMITTED_S3_R4_LABEL,
    S3_R4_PRECOMMITTED_SEEDS,
    validate_p2_termination_qualification,
)
from relaylm.v2_cognitive_ir_s2_selected import S2_SELECTED_SEED
from relaylm.v2_cognitive_ir_s3_r2 import HISTORICAL_S3_V1_SEEDS, S3_R2_SEEDS
from relaylm.v2_cognitive_ir_s3_r3 import S3_R3_SEEDS
from relaylm.v2_transfer_actual_model import ExperimentClient, ExperimentCompletion
from relaylm.v2_transfer_experiment import TransferFamily


S3_R4_PREREGISTRATION_SCHEMA = "relaylm2-cognitive-ir-s3-prereg-v4"
S3_R4_LABEL = "relaylm2-cognitive-ir-s3-semantic-invariance-v4"
S3_R4_MAX_OUTPUT_TOKENS = 1024
S3_R4_SEEDS: Mapping[str, tuple[int, ...]] = {
    "shared": (1813949056, 599436490, 759541357),
    "null": (1844644632, 1939834448, 1783561206),
    "mismatch": (1470423814, 1347260951, 1196431812),
    "shift": (1233805618, 2217769, 179280278),
}
S3_R4_P2_BUILDER = (
    "relaylm.v2_cognitive_ir_p2_boundedness_qual_v2."
    "build_margin_p2_formation_messages"
)
S3_R4_PREREGISTRATION_SHA256 = (
    "deb10b356f1cfe4fd18275b790f1a5bcb5972b1b841e874c26a8827ffd20dae4"
)


class S3R4BindingError(ValueError):
    """The #2580 S3-R4 preregistration cannot be bound exactly."""


def derive_s3_r4_seed(regime: str, index: int) -> int:
    if regime not in base.S3_REGIMES:
        raise S3R4BindingError(f"unsupported S3-R4 regime: {regime}")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 3:
        raise S3R4BindingError("S3-R4 seed index must be 0..2")
    raw = hashlib.sha256(
        f"{S3_R4_LABEL}|{regime}|seed|{index}".encode("utf-8")
    ).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def _spec_payload() -> dict[str, object]:
    return {
        "schema": S3_R4_PREREGISTRATION_SCHEMA,
        "label": S3_R4_LABEL,
        "seeds": {key: list(value) for key, value in S3_R4_SEEDS.items()},
        "max_output_tokens": S3_R4_MAX_OUTPUT_TOKENS,
        "regimes": list(base.S3_REGIMES),
        "shard_calls": dict(base.S3_SHARD_CALLS),
        "total_semantic_calls": base.S3_TOTAL_SEMANTIC_CALLS,
        "total_input_token_requests": base.S3_TOTAL_INPUT_TOKEN_REQUESTS,
        "surface_effect_max": base.S3_SURFACE_EFFECT_MAX,
        "semantic_effect_min": base.S3_SEMANTIC_EFFECT_MIN,
        "effect_margin_min": base.S3_EFFECT_MARGIN_MIN,
        "p2_builder": S3_R4_P2_BUILDER,
        "p2_target_margin": {
            "min_words": P2_BOUNDEDNESS_TARGET_MIN_WORDS,
            "max_words": P2_BOUNDEDNESS_TARGET_MAX_WORDS,
            "max_unicode_characters": P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS,
        },
        "p2_hard_admission": {
            "max_words": P2_BOUNDEDNESS_HARD_MAX_WORDS,
            "max_unicode_characters": P2_BOUNDEDNESS_HARD_MAX_CHARACTERS,
        },
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


def _flatten(values: Mapping[str, tuple[int, ...]]) -> set[int]:
    return {seed for seeds in values.values() for seed in seeds}


def validate_s3_r4_preregistration() -> None:
    validate_p2_termination_qualification()
    validate_p2_boundedness_qualification_v2()

    if S3_R4_LABEL != PRECOMMITTED_S3_R4_LABEL:
        raise S3R4BindingError("S3-R4 label drifted from the #2530 precommit")
    if dict(S3_R4_SEEDS) != dict(S3_R4_PRECOMMITTED_SEEDS):
        raise S3R4BindingError("S3-R4 seeds drifted from the #2530 precommit")

    derived = {
        regime: tuple(derive_s3_r4_seed(regime, index) for index in range(3))
        for regime in base.S3_REGIMES
    }
    if derived != dict(S3_R4_SEEDS):
        raise S3R4BindingError("derived S3-R4 seeds drifted from the precommit")

    fresh = _flatten(S3_R4_SEEDS)
    if len(fresh) != 12:
        raise S3R4BindingError("S3-R4 seeds are not unique")

    historical = {
        *_flatten(HISTORICAL_S3_V1_SEEDS),
        *_flatten(S3_R2_SEEDS),
        *_flatten(S3_R3_SEEDS),
        *_flatten(P2_TERMINATION_QUAL_SEEDS),
        *_flatten(P2_BOUNDEDNESS_QUAL_V2_SEEDS),
        *CALIBRATION_SEEDS,
        *CALIBRATION_V2_SEEDS,
        S2_SELECTED_SEED,
        2211,
        2530,
        2533,
        2538,
        2571,
        2572,
        2577,
        2580,
    }
    overlap = sorted(fresh & historical)
    if overlap:
        raise S3R4BindingError(f"S3-R4 seeds overlap prior/precommitted evidence: {overlap}")

    if tuple(base.S3_REGIMES) != ("shared", "null", "mismatch", "shift"):
        raise S3R4BindingError("S3-R4 regime order drifted")
    if dict(base.S3_SHARD_CALLS) != {
        "shared": 123,
        "null": 123,
        "mismatch": 123,
        "shift": 129,
    }:
        raise S3R4BindingError("S3-R4 shard ledger drifted")
    if (
        base.S3_TOTAL_SEMANTIC_CALLS,
        base.S3_TOTAL_INPUT_TOKEN_REQUESTS,
    ) != (498, 996):
        raise S3R4BindingError("S3-R4 campaign call ledger drifted")
    if (
        base.S3_SURFACE_EFFECT_MAX,
        base.S3_SEMANTIC_EFFECT_MIN,
        base.S3_EFFECT_MARGIN_MIN,
    ) != (0.15, 0.20, 0.15):
        raise S3R4BindingError("S3-R4 discriminator thresholds drifted")
    if (
        P2_BOUNDEDNESS_TARGET_MIN_WORDS,
        P2_BOUNDEDNESS_TARGET_MAX_WORDS,
        P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS,
    ) != (60, 80, 550):
        raise S3R4BindingError("S3-R4 P2 target margin drifted")
    if (
        P2_BOUNDEDNESS_HARD_MAX_WORDS,
        P2_BOUNDEDNESS_HARD_MAX_CHARACTERS,
        S3_R4_MAX_OUTPUT_TOKENS,
    ) != (120, 800, 1024):
        raise S3R4BindingError("S3-R4 P2 hard envelope/output ceiling drifted")
    if _spec_sha256() != S3_R4_PREREGISTRATION_SHA256:
        raise S3R4BindingError("S3-R4 preregistration spec hash drifted")


class _R4FormationClient:
    """Substitute only the already-qualified P2 prompt while checking P3/P4 drift."""

    def __init__(self, inner: ExperimentClient, family: TransferFamily) -> None:
        self.inner = inner
        self.family = family
        self.index = 0

    def complete(
        self,
        messages: tuple[dict[str, str], ...],
    ) -> ExperimentCompletion:
        if self.index >= 3:
            raise S3R4BindingError("R4 formation attempted an undeclared fourth call")
        kinds = (
            "P2_ORDINARY_SUMMARY",
            "P3_SEMANTIC_CACHE",
            "P4_MEMORY_PLUS_STRUCTURE",
        )
        kind = kinds[self.index]
        expected = build_s2_formation_messages(kind, self.family)
        if messages != expected:
            raise S3R4BindingError(f"R4 inherited {kind} formation messages drifted")

        outgoing = (
            build_margin_p2_formation_messages(self.family)
            if kind == "P2_ORDINARY_SUMMARY"
            else messages
        )
        self.index += 1
        return self.inner.complete(outgoing)


def form_s2_representations_r4(
    client: ExperimentClient,
    family: TransferFamily,
) -> dict[str, S2Representation]:
    scoped = _R4FormationClient(client, family)
    representations = _historical_form_s2_representations(scoped, family)
    if scoped.index != 3:
        raise S3R4BindingError("R4 representation formation did not consume exactly three calls")
    return representations


def activate_s3_r4_preregistration() -> None:
    """Activate R4 only inside its dedicated campaign process."""

    validate_s3_r4_preregistration()
    base.S3_PREREGISTRATION_SCHEMA = S3_R4_PREREGISTRATION_SCHEMA
    base.S3_PREREGISTRATION_SHA256 = S3_R4_PREREGISTRATION_SHA256
    base.S3_LABEL = S3_R4_LABEL
    base.S3_SEEDS = S3_R4_SEEDS
    base.form_s2_representations = form_s2_representations_r4
    base.validate_frozen_seeds()
