from __future__ import annotations

import hashlib
from typing import Mapping

import relaylm.v2_cognitive_ir_s3 as s3
from relaylm.v2_cognitive_ir_actual_model import build_s2_formation_messages
from relaylm import v2_cognitive_ir_p2_termination_qual as historical
from relaylm.v2_cognitive_ir_calibration import CALIBRATION_SEEDS
from relaylm.v2_cognitive_ir_calibration_v2 import CALIBRATION_V2_SEEDS
from relaylm.v2_cognitive_ir_s2_selected import S2_SELECTED_SEED
from relaylm.v2_cognitive_ir_s3_r2 import HISTORICAL_S3_V1_SEEDS, S3_R2_SEEDS
from relaylm.v2_cognitive_ir_s3_r3 import S3_R3_SEEDS
from relaylm.v2_transfer_experiment import TransferFamily


P2_BOUNDEDNESS_QUAL_V2_LABEL = "relaylm2-cognitive-ir-p2-boundedness-qual-v2"
P2_BOUNDEDNESS_QUAL_V2_SEEDS: Mapping[str, tuple[int, ...]] = {
    "shared": (1429064482, 638457751, 587511951),
    "null": (557367045, 1088885962, 452479792),
    "mismatch": (2085578331, 441803802, 1154804437),
    "shift": (534887107, 69996342, 304353334),
}
P2_BOUNDEDNESS_TARGET_MIN_WORDS = 60
P2_BOUNDEDNESS_TARGET_MAX_WORDS = 80
P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS = 550
P2_BOUNDEDNESS_HARD_MAX_WORDS = historical.P2_TERMINATION_QUAL_MAX_WORDS
P2_BOUNDEDNESS_HARD_MAX_CHARACTERS = historical.P2_TERMINATION_QUAL_MAX_CHARACTERS
P2_BOUNDEDNESS_MAX_OUTPUT_TOKENS = historical.P2_TERMINATION_QUAL_MAX_OUTPUT_TOKENS
P2_BOUNDEDNESS_TOTAL_SEMANTIC_CALLS = 12
P2_BOUNDEDNESS_TOTAL_INPUT_TOKEN_REQUESTS = 24
P2_BOUNDEDNESS_QUAL_V2_CLAIM = "NON_CITABLE_P2_BOUNDEDNESS_QUALIFICATION_V2"
P2_BOUNDEDNESS_QUAL_V2_INCOMPLETE = "P2_BOUNDEDNESS_QUALIFICATION_V2_INCOMPLETE"
P2_BOUNDEDNESS_QUAL_V2_CONTRACT = """Return one plain-text recap paragraph only.
Keep it deliberately short: aim for 60 to 80 words and no more than 550 Unicode characters.
Preserve supported conditions, recurring patterns, exceptions, and outcomes.
You may infer/generalize regularities when supported by the observations.
Do not include a heading, bullet list, special schema, or step-by-step derivation.
Do not fill the available output budget; stop after the recap paragraph."""


class P2BoundednessQualificationV2Error(ValueError):
    """The frozen #2571 P2 boundedness qualification contract was violated."""


def _derive_seed(label: str, regime: str, index: int) -> int:
    if regime not in s3.S3_REGIMES:
        raise P2BoundednessQualificationV2Error(f"unsupported regime: {regime}")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 3:
        raise P2BoundednessQualificationV2Error("seed index must be 0..2")
    raw = hashlib.sha256(f"{label}|{regime}|seed|{index}".encode("utf-8")).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def derive_p2_boundedness_qual_v2_seed(regime: str, index: int) -> int:
    return _derive_seed(P2_BOUNDEDNESS_QUAL_V2_LABEL, regime, index)


def _flatten(values: Mapping[str, tuple[int, ...]]) -> tuple[int, ...]:
    return tuple(seed for regime in s3.S3_REGIMES for seed in values[regime])


def validate_p2_boundedness_qualification_v2() -> None:
    historical.validate_p2_termination_qualification()
    expected = {
        regime: tuple(derive_p2_boundedness_qual_v2_seed(regime, index) for index in range(3))
        for regime in s3.S3_REGIMES
    }
    if expected != dict(P2_BOUNDEDNESS_QUAL_V2_SEEDS):
        raise P2BoundednessQualificationV2Error("boundedness qualification seeds drifted from #2571")

    seeds = set(_flatten(P2_BOUNDEDNESS_QUAL_V2_SEEDS))
    if len(seeds) != 12:
        raise P2BoundednessQualificationV2Error("boundedness qualification seeds are not unique")
    historical_seeds = {
        *(seed for values in HISTORICAL_S3_V1_SEEDS.values() for seed in values),
        *(seed for values in S3_R2_SEEDS.values() for seed in values),
        *(seed for values in S3_R3_SEEDS.values() for seed in values),
        *(seed for values in historical.P2_TERMINATION_QUAL_SEEDS.values() for seed in values),
        *(seed for values in historical.S3_R4_PRECOMMITTED_SEEDS.values() for seed in values),
    }
    forbidden = {
        2211,
        2538,
        2571,
        2572,
        S2_SELECTED_SEED,
        *CALIBRATION_SEEDS,
        *CALIBRATION_V2_SEEDS,
        *historical_seeds,
    }
    overlap = sorted(seeds & forbidden)
    if overlap:
        raise P2BoundednessQualificationV2Error(
            f"boundedness qualification seeds overlap prior/precommitted evidence: {overlap}"
        )
    if tuple(s3.S3_REGIMES) != ("shared", "null", "mismatch", "shift"):
        raise P2BoundednessQualificationV2Error("qualification regime order drifted")
    if not (
        P2_BOUNDEDNESS_TARGET_MIN_WORDS
        < P2_BOUNDEDNESS_TARGET_MAX_WORDS
        < P2_BOUNDEDNESS_HARD_MAX_WORDS
    ):
        raise P2BoundednessQualificationV2Error("word target margin must remain inside hard envelope")
    if not P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS < P2_BOUNDEDNESS_HARD_MAX_CHARACTERS:
        raise P2BoundednessQualificationV2Error("character target margin must remain inside hard envelope")
    if (
        P2_BOUNDEDNESS_HARD_MAX_WORDS,
        P2_BOUNDEDNESS_HARD_MAX_CHARACTERS,
        P2_BOUNDEDNESS_MAX_OUTPUT_TOKENS,
    ) != (120, 800, 1024):
        raise P2BoundednessQualificationV2Error("hard envelope/output ceiling drifted")
    if (
        P2_BOUNDEDNESS_TOTAL_SEMANTIC_CALLS,
        P2_BOUNDEDNESS_TOTAL_INPUT_TOKEN_REQUESTS,
    ) != (12, 24):
        raise P2BoundednessQualificationV2Error("qualification call ledger drifted")


def qualification_call_plan_v2() -> tuple[str, ...]:
    validate_p2_boundedness_qualification_v2()
    return tuple(
        f"{regime}:{index}:{P2_BOUNDEDNESS_QUAL_V2_SEEDS[regime][index]}:form-p2"
        for regime in s3.S3_REGIMES
        for index in range(3)
    )


def generate_qualification_family_v2(regime: str, index: int) -> TransferFamily:
    """Generate a fresh qualification family without mutating historical globals afterward."""

    validate_p2_boundedness_qualification_v2()
    original_label = s3.S3_LABEL
    original_seeds = s3.S3_SEEDS
    try:
        s3.S3_LABEL = P2_BOUNDEDNESS_QUAL_V2_LABEL
        s3.S3_SEEDS = P2_BOUNDEDNESS_QUAL_V2_SEEDS
        return s3.generate_s3_family(regime, index)
    finally:
        s3.S3_LABEL = original_label
        s3.S3_SEEDS = original_seeds


def build_margin_p2_formation_messages(
    family: TransferFamily,
) -> tuple[dict[str, str], ...]:
    """Add only the #2571 target margin while preserving legacy P2 source semantics."""

    legacy = build_s2_formation_messages("P2_ORDINARY_SUMMARY", family)
    return (
        {"role": "system", "content": legacy[0]["content"] + "\n" + P2_BOUNDEDNESS_QUAL_V2_CONTRACT},
        dict(legacy[1]),
    )
