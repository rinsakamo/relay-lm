from __future__ import annotations

import hashlib
from typing import Mapping

import relaylm.v2_cognitive_ir_s3 as s3
from relaylm.v2_cognitive_ir_actual_model import build_s2_formation_messages
from relaylm.v2_cognitive_ir_calibration import CALIBRATION_SEEDS
from relaylm.v2_cognitive_ir_calibration_v2 import CALIBRATION_V2_SEEDS
from relaylm.v2_cognitive_ir_s2_selected import S2_SELECTED_SEED
from relaylm.v2_cognitive_ir_s3_r2 import HISTORICAL_S3_V1_SEEDS, S3_R2_SEEDS
from relaylm.v2_cognitive_ir_s3_r3 import S3_R3_SEEDS
from relaylm.v2_transfer_experiment import TransferFamily


P2_TERMINATION_QUAL_LABEL = "relaylm2-cognitive-ir-p2-termination-qual-v1"
P2_TERMINATION_QUAL_SEEDS: Mapping[str, tuple[int, ...]] = {
    "shared": (961584193, 944521282, 1674448867),
    "null": (1501099255, 884619356, 1172443315),
    "mismatch": (1461365599, 1125953772, 2074907614),
    "shift": (137041362, 281452170, 9745268),
}
P2_TERMINATION_QUAL_MAX_WORDS = 120
P2_TERMINATION_QUAL_MAX_CHARACTERS = 800
P2_TERMINATION_QUAL_MAX_OUTPUT_TOKENS = 1024
P2_TERMINATION_QUAL_TOTAL_SEMANTIC_CALLS = 12
P2_TERMINATION_QUAL_TOTAL_INPUT_TOKEN_REQUESTS = 24
P2_TERMINATION_QUAL_CLAIM = "NON_CITABLE_P2_TERMINATION_QUALIFICATION"
P2_TERMINATION_QUAL_INCOMPLETE = "P2_TERMINATION_QUALIFICATION_INCOMPLETE"
P2_TERMINATION_QUAL_CONTRACT = """Return one plain-text recap paragraph only.
Use no more than 120 words and no more than 800 Unicode characters.
Preserve supported conditions, recurring patterns, exceptions, and outcomes.
You may infer/generalize regularities when supported by the observations.
Do not include a heading, bullet list, special schema, or step-by-step derivation.
Stop after the recap paragraph."""

S3_R4_LABEL = "relaylm2-cognitive-ir-s3-semantic-invariance-v4"
S3_R4_PRECOMMITTED_SEEDS: Mapping[str, tuple[int, ...]] = {
    "shared": (1813949056, 599436490, 759541357),
    "null": (1844644632, 1939834448, 1783561206),
    "mismatch": (1470423814, 1347260951, 1196431812),
    "shift": (1233805618, 2217769, 179280278),
}


class P2TerminationQualificationError(ValueError):
    """The frozen #2530 P2 termination qualification contract was violated."""


def _derive_seed(label: str, regime: str, index: int) -> int:
    if regime not in s3.S3_REGIMES:
        raise P2TerminationQualificationError(f"unsupported regime: {regime}")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 3:
        raise P2TerminationQualificationError("seed index must be 0..2")
    raw = hashlib.sha256(f"{label}|{regime}|seed|{index}".encode("utf-8")).digest()
    return int.from_bytes(raw[:4], "big") & 0x7FFFFFFF


def derive_p2_termination_qual_seed(regime: str, index: int) -> int:
    return _derive_seed(P2_TERMINATION_QUAL_LABEL, regime, index)


def derive_s3_r4_precommitted_seed(regime: str, index: int) -> int:
    return _derive_seed(S3_R4_LABEL, regime, index)


def _flatten(values: Mapping[str, tuple[int, ...]]) -> tuple[int, ...]:
    return tuple(seed for regime in s3.S3_REGIMES for seed in values[regime])


def validate_p2_termination_qualification() -> None:
    expected_qual = {
        regime: tuple(derive_p2_termination_qual_seed(regime, index) for index in range(3))
        for regime in s3.S3_REGIMES
    }
    if expected_qual != dict(P2_TERMINATION_QUAL_SEEDS):
        raise P2TerminationQualificationError("qualification seeds drifted from #2530")
    expected_r4 = {
        regime: tuple(derive_s3_r4_precommitted_seed(regime, index) for index in range(3))
        for regime in s3.S3_REGIMES
    }
    if expected_r4 != dict(S3_R4_PRECOMMITTED_SEEDS):
        raise P2TerminationQualificationError("precommitted R4 seeds drifted from #2530")

    qual = set(_flatten(P2_TERMINATION_QUAL_SEEDS))
    r4 = set(_flatten(S3_R4_PRECOMMITTED_SEEDS))
    if len(qual) != 12 or len(r4) != 12 or qual & r4:
        raise P2TerminationQualificationError("qualification/R4 seeds are not unique and disjoint")
    historical = {
        *(seed for values in HISTORICAL_S3_V1_SEEDS.values() for seed in values),
        *(seed for values in S3_R2_SEEDS.values() for seed in values),
        *(seed for values in S3_R3_SEEDS.values() for seed in values),
    }
    forbidden = {
        2211,
        2522,
        2530,
        2533,
        S2_SELECTED_SEED,
        *CALIBRATION_SEEDS,
        *CALIBRATION_V2_SEEDS,
        *historical,
    }
    overlap = sorted((qual | r4) & forbidden)
    if overlap:
        raise P2TerminationQualificationError(f"qualification/R4 seeds overlap prior evidence: {overlap}")
    if tuple(s3.S3_REGIMES) != ("shared", "null", "mismatch", "shift"):
        raise P2TerminationQualificationError("qualification regime order drifted")
    if P2_TERMINATION_QUAL_MAX_OUTPUT_TOKENS != 1024:
        raise P2TerminationQualificationError("qualification hard output ceiling drifted")
    if (
        P2_TERMINATION_QUAL_TOTAL_SEMANTIC_CALLS,
        P2_TERMINATION_QUAL_TOTAL_INPUT_TOKEN_REQUESTS,
    ) != (12, 24):
        raise P2TerminationQualificationError("qualification call ledger drifted")


def qualification_call_plan() -> tuple[str, ...]:
    validate_p2_termination_qualification()
    return tuple(
        f"{regime}:{index}:{P2_TERMINATION_QUAL_SEEDS[regime][index]}:form-p2"
        for regime in s3.S3_REGIMES
        for index in range(3)
    )


def generate_qualification_family(regime: str, index: int) -> TransferFamily:
    """Generate one qualification family without leaving historical S3 globals mutated."""

    validate_p2_termination_qualification()
    original_label = s3.S3_LABEL
    original_seeds = s3.S3_SEEDS
    try:
        s3.S3_LABEL = P2_TERMINATION_QUAL_LABEL
        s3.S3_SEEDS = P2_TERMINATION_QUAL_SEEDS
        return s3.generate_s3_family(regime, index)
    finally:
        s3.S3_LABEL = original_label
        s3.S3_SEEDS = original_seeds


def build_bounded_p2_formation_messages(
    family: TransferFamily,
) -> tuple[dict[str, str], ...]:
    """Add the frozen finite text envelope while preserving legacy source semantics."""

    legacy = build_s2_formation_messages("P2_ORDINARY_SUMMARY", family)
    return (
        {"role": "system", "content": legacy[0]["content"] + "\n" + P2_TERMINATION_QUAL_CONTRACT},
        dict(legacy[1]),
    )
