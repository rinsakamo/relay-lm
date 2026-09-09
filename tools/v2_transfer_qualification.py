from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re


QUALIFICATION_VERSION = "relaylm2-transfer-precondition-qualification-v1"
Q1_TARGET_COMPETENCE = "Q1_TARGET_COMPETENCE"
Q2_SOURCE_ACQUISITION = "Q2_SOURCE_ACQUISITION"
Q3_ORACLE_PROJECTION_UPPER_BOUND = "Q3_ORACLE_PROJECTION_UPPER_BOUND"

PASS = "PASS"
FAIL_FLOOR = "FAIL_FLOOR"
FAIL_CEILING = "FAIL_CEILING"
FAIL_ACQUISITION = "FAIL_ACQUISITION"
FAIL_MECHANISM = "FAIL_MECHANISM"
INCONCLUSIVE = "INCONCLUSIVE"
PROTOCOL_INVALID = "PROTOCOL_INVALID"

ORIGIN_NONE = "NONE"
ORIGIN_MODEL_LEARNED = "MODEL_LEARNED"
ORIGIN_EVALUATOR_ORACLE = "EVALUATOR_ORACLE"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class TransferQualificationError(ValueError):
    """The transfer-precondition qualification contract is invalid."""


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_text(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TransferQualificationError("text identity must be non-empty")
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise TransferQualificationError(f"{label} must be a sha256 digest")


def _require_rate(value: float, label: str, *, allow_zero: bool = True) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise TransferQualificationError(f"{label} must be a finite number")
    lower_ok = value >= 0 if allow_zero else value > 0
    if not lower_ok or value > 1:
        raise TransferQualificationError(f"{label} must be within the declared probability range")


def _require_nonnegative_int(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TransferQualificationError(f"{label} must be a non-negative integer")


def _validate_counts(correct: int, total: int, label: str) -> None:
    _require_nonnegative_int(correct, f"{label} correct")
    _require_nonnegative_int(total, f"{label} total")
    if correct > total:
        raise TransferQualificationError(f"{label} correct count exceeds total")


@dataclass(frozen=True, slots=True)
class QualificationThresholds:
    q1_min_families: int
    q1_min_endpoint_rate: float
    q1_max_endpoint_rate: float
    q2_min_families: int
    q2_min_exact_structure_rate: float
    q2_min_behavioral_rate: float
    q3_min_families_per_regime: int
    q3_min_shared_gain: float
    q3_min_interaction: float

    def __post_init__(self) -> None:
        for name in ("q1_min_families", "q2_min_families", "q3_min_families_per_regime"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise TransferQualificationError(f"{name} must be a positive integer")
        _require_rate(self.q1_min_endpoint_rate, "q1_min_endpoint_rate", allow_zero=False)
        _require_rate(self.q1_max_endpoint_rate, "q1_max_endpoint_rate")
        if self.q1_min_endpoint_rate >= self.q1_max_endpoint_rate:
            raise TransferQualificationError("Q1 floor threshold must be below ceiling threshold")
        _require_rate(self.q2_min_exact_structure_rate, "q2_min_exact_structure_rate", allow_zero=False)
        _require_rate(self.q2_min_behavioral_rate, "q2_min_behavioral_rate", allow_zero=False)
        _require_rate(self.q3_min_shared_gain, "q3_min_shared_gain", allow_zero=False)
        _require_rate(self.q3_min_interaction, "q3_min_interaction", allow_zero=False)


@dataclass(frozen=True, slots=True)
class QualificationManifest:
    version: str
    model_runtime_identity_digest: str
    task_family_identity_digest: str
    source_representation_semantics: str
    source_representation_semantics_digest: str
    target_evidence_levels: tuple[int, ...]
    thresholds: QualificationThresholds

    def __post_init__(self) -> None:
        if self.version != QUALIFICATION_VERSION:
            raise TransferQualificationError("qualification version drifted")
        _require_digest(self.model_runtime_identity_digest, "model/runtime identity")
        _require_digest(self.task_family_identity_digest, "task-family identity")
        if not isinstance(self.source_representation_semantics, str) or not self.source_representation_semantics.strip():
            raise TransferQualificationError("source representation semantics must be explicit")
        _require_digest(self.source_representation_semantics_digest, "source representation semantics identity")
        if self.source_representation_semantics_digest != sha256_text(self.source_representation_semantics):
            raise TransferQualificationError("source representation semantics digest does not match its text")
        if len(self.target_evidence_levels) < 2:
            raise TransferQualificationError("Q1 requires at least two target evidence levels")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in self.target_evidence_levels):
            raise TransferQualificationError("target evidence levels must be non-negative integers")
        if tuple(sorted(set(self.target_evidence_levels))) != self.target_evidence_levels:
            raise TransferQualificationError("target evidence levels must be unique and increasing")


def manifest_digest(manifest: QualificationManifest) -> str:
    return "sha256:" + hashlib.sha256(
        _canonical_json(asdict(manifest)).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class TargetCompetenceResult:
    manifest_digest: str
    evidence_ref: str
    complete: bool
    protocol_valid: bool
    structure_origin: str
    family_count: int
    evidence_level_correct: tuple[int, ...]
    endpoint_correct: int
    replaced_seed_count: int

    def __post_init__(self) -> None:
        _require_digest(self.manifest_digest, "Q1 manifest identity")
        if not isinstance(self.evidence_ref, str) or not self.evidence_ref.strip():
            raise TransferQualificationError("Q1 evidence reference must be non-empty")
        if not isinstance(self.complete, bool) or not isinstance(self.protocol_valid, bool):
            raise TransferQualificationError("Q1 completion/protocol flags must be boolean")
        if not isinstance(self.evidence_level_correct, tuple) or not self.evidence_level_correct:
            raise TransferQualificationError("Q1 adaptation curve must be a non-empty tuple")
        for index, correct in enumerate(self.evidence_level_correct):
            _validate_counts(correct, self.family_count, f"Q1 evidence level {index}")
        _validate_counts(self.endpoint_correct, self.family_count, "Q1 endpoint")
        if self.endpoint_correct != self.evidence_level_correct[-1]:
            raise TransferQualificationError("Q1 endpoint must equal the final adaptation-curve count")
        _require_nonnegative_int(self.replaced_seed_count, "Q1 replaced seed count")


@dataclass(frozen=True, slots=True)
class SourceAcquisitionResult:
    manifest_digest: str
    evidence_ref: str
    complete: bool
    protocol_valid: bool
    structure_origin: str
    family_count: int
    exact_structure_correct: int
    behavioral_correct: int
    oracle_truth_used: bool
    replaced_seed_count: int

    def __post_init__(self) -> None:
        _require_digest(self.manifest_digest, "Q2 manifest identity")
        if not isinstance(self.evidence_ref, str) or not self.evidence_ref.strip():
            raise TransferQualificationError("Q2 evidence reference must be non-empty")
        if not isinstance(self.complete, bool) or not isinstance(self.protocol_valid, bool):
            raise TransferQualificationError("Q2 completion/protocol flags must be boolean")
        if not isinstance(self.oracle_truth_used, bool):
            raise TransferQualificationError("Q2 oracle_truth_used must be boolean")
        _validate_counts(self.exact_structure_correct, self.family_count, "Q2 exact Structure")
        _validate_counts(self.behavioral_correct, self.family_count, "Q2 behavioral")
        _require_nonnegative_int(self.replaced_seed_count, "Q2 replaced seed count")


@dataclass(frozen=True, slots=True)
class OracleProjectionResult:
    manifest_digest: str
    evidence_ref: str
    complete: bool
    protocol_valid: bool
    structure_origin: str
    shared_family_count: int
    shared_baseline_correct: int
    shared_oracle_correct: int
    null_family_count: int
    null_baseline_correct: int
    null_oracle_correct: int
    matched_target_packets: bool
    target_rule_leakage_detected: bool
    replaced_seed_count: int

    def __post_init__(self) -> None:
        _require_digest(self.manifest_digest, "Q3 manifest identity")
        if not isinstance(self.evidence_ref, str) or not self.evidence_ref.strip():
            raise TransferQualificationError("Q3 evidence reference must be non-empty")
        if not isinstance(self.complete, bool) or not isinstance(self.protocol_valid, bool):
            raise TransferQualificationError("Q3 completion/protocol flags must be boolean")
        if not isinstance(self.matched_target_packets, bool) or not isinstance(self.target_rule_leakage_detected, bool):
            raise TransferQualificationError("Q3 matching/leakage flags must be boolean")
        _validate_counts(self.shared_baseline_correct, self.shared_family_count, "Q3 shared baseline")
        _validate_counts(self.shared_oracle_correct, self.shared_family_count, "Q3 shared oracle")
        _validate_counts(self.null_baseline_correct, self.null_family_count, "Q3 null baseline")
        _validate_counts(self.null_oracle_correct, self.null_family_count, "Q3 null oracle")
        _require_nonnegative_int(self.replaced_seed_count, "Q3 replaced seed count")


@dataclass(frozen=True, slots=True)
class TransferQualificationCertificate:
    version: str
    manifest_digest: str
    q1_evidence_ref: str
    q2_evidence_ref: str
    q3_evidence_ref: str


def _same_manifest(expected: str, observed: str) -> bool:
    return expected == observed


def classify_q1(manifest: QualificationManifest, result: TargetCompetenceResult) -> str:
    expected = manifest_digest(manifest)
    if not _same_manifest(expected, result.manifest_digest):
        return PROTOCOL_INVALID
    if result.structure_origin != ORIGIN_NONE or result.replaced_seed_count != 0:
        return PROTOCOL_INVALID
    if not result.protocol_valid:
        return PROTOCOL_INVALID
    if len(result.evidence_level_correct) != len(manifest.target_evidence_levels):
        return PROTOCOL_INVALID
    if not result.complete or result.family_count < manifest.thresholds.q1_min_families:
        return INCONCLUSIVE
    rate = result.endpoint_correct / result.family_count
    if rate < manifest.thresholds.q1_min_endpoint_rate:
        return FAIL_FLOOR
    if rate > manifest.thresholds.q1_max_endpoint_rate:
        return FAIL_CEILING
    return PASS


def classify_q2(manifest: QualificationManifest, result: SourceAcquisitionResult) -> str:
    expected = manifest_digest(manifest)
    if not _same_manifest(expected, result.manifest_digest):
        return PROTOCOL_INVALID
    if result.structure_origin != ORIGIN_MODEL_LEARNED or result.oracle_truth_used or result.replaced_seed_count != 0:
        return PROTOCOL_INVALID
    if not result.protocol_valid:
        return PROTOCOL_INVALID
    if not result.complete or result.family_count < manifest.thresholds.q2_min_families:
        return INCONCLUSIVE
    exact_rate = result.exact_structure_correct / result.family_count
    behavioral_rate = result.behavioral_correct / result.family_count
    if exact_rate < manifest.thresholds.q2_min_exact_structure_rate:
        return FAIL_ACQUISITION
    if behavioral_rate < manifest.thresholds.q2_min_behavioral_rate:
        return FAIL_ACQUISITION
    return PASS


def q3_effects(result: OracleProjectionResult) -> tuple[float, float, float]:
    if result.shared_family_count == 0 or result.null_family_count == 0:
        raise TransferQualificationError("Q3 effect requires non-empty shared and null regimes")
    shared_gain = (
        result.shared_oracle_correct - result.shared_baseline_correct
    ) / result.shared_family_count
    null_gain = (
        result.null_oracle_correct - result.null_baseline_correct
    ) / result.null_family_count
    return shared_gain, null_gain, shared_gain - null_gain


def classify_q3(manifest: QualificationManifest, result: OracleProjectionResult) -> str:
    expected = manifest_digest(manifest)
    if not _same_manifest(expected, result.manifest_digest):
        return PROTOCOL_INVALID
    if result.structure_origin != ORIGIN_EVALUATOR_ORACLE or result.replaced_seed_count != 0:
        return PROTOCOL_INVALID
    if not result.protocol_valid or not result.matched_target_packets or result.target_rule_leakage_detected:
        return PROTOCOL_INVALID
    minimum = manifest.thresholds.q3_min_families_per_regime
    if not result.complete or result.shared_family_count < minimum or result.null_family_count < minimum:
        return INCONCLUSIVE
    shared_gain, _null_gain, interaction = q3_effects(result)
    if shared_gain < manifest.thresholds.q3_min_shared_gain:
        return FAIL_MECHANISM
    if interaction < manifest.thresholds.q3_min_interaction:
        return FAIL_MECHANISM
    return PASS


def qualify_for_transfer(
    manifest: QualificationManifest,
    *,
    q1: TargetCompetenceResult,
    q2: SourceAcquisitionResult,
    q3: OracleProjectionResult,
) -> TransferQualificationCertificate:
    verdicts = (classify_q1(manifest, q1), classify_q2(manifest, q2), classify_q3(manifest, q3))
    if verdicts != (PASS, PASS, PASS):
        raise TransferQualificationError(
            "transfer prerequisites are not all PASS: " + ", ".join(verdicts)
        )
    refs = (q1.evidence_ref, q2.evidence_ref, q3.evidence_ref)
    if len(set(refs)) != 3:
        raise TransferQualificationError("Q1/Q2/Q3 must cite three distinct evidence products")
    return TransferQualificationCertificate(
        version=QUALIFICATION_VERSION,
        manifest_digest=manifest_digest(manifest),
        q1_evidence_ref=q1.evidence_ref,
        q2_evidence_ref=q2.evidence_ref,
        q3_evidence_ref=q3.evidence_ref,
    )
