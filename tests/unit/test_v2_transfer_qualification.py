from __future__ import annotations

from dataclasses import replace

import pytest

from tools.v2_transfer_qualification import (
    FAIL_ACQUISITION,
    FAIL_CEILING,
    FAIL_FLOOR,
    FAIL_MECHANISM,
    ORIGIN_EVALUATOR_ORACLE,
    ORIGIN_MODEL_LEARNED,
    ORIGIN_NONE,
    PASS,
    PROTOCOL_INVALID,
    QUALIFICATION_VERSION,
    OracleProjectionResult,
    QualificationManifest,
    QualificationThresholds,
    SourceAcquisitionResult,
    TargetCompetenceResult,
    TransferQualificationError,
    classify_q1,
    classify_q2,
    classify_q3,
    manifest_digest,
    q3_effects,
    qualify_for_transfer,
    sha256_text,
)


def _manifest() -> QualificationManifest:
    semantics = "y[i] = (x[permutation[i]] + offsets[i]) mod modulus"
    return QualificationManifest(
        version=QUALIFICATION_VERSION,
        model_runtime_identity_digest="sha256:" + "1" * 64,
        task_family_identity_digest="sha256:" + "2" * 64,
        source_representation_semantics=semantics,
        source_representation_semantics_digest=sha256_text(semantics),
        target_evidence_levels=(0, 1, 2, 3),
        thresholds=QualificationThresholds(
            q1_min_families=8,
            q1_min_endpoint_rate=0.25,
            q1_max_endpoint_rate=0.90,
            q2_min_families=8,
            q2_min_exact_structure_rate=0.50,
            q2_min_behavioral_rate=0.75,
            q3_min_families_per_regime=8,
            q3_min_shared_gain=0.25,
            q3_min_interaction=0.20,
        ),
    )


def _q1(manifest: QualificationManifest) -> TargetCompetenceResult:
    return TargetCompetenceResult(
        manifest_digest=manifest_digest(manifest),
        evidence_ref="evidence:q1",
        complete=True,
        protocol_valid=True,
        structure_origin=ORIGIN_NONE,
        family_count=8,
        evidence_level_correct=(1, 2, 4, 5),
        endpoint_correct=5,
        replaced_seed_count=0,
    )


def _q2(manifest: QualificationManifest) -> SourceAcquisitionResult:
    return SourceAcquisitionResult(
        manifest_digest=manifest_digest(manifest),
        evidence_ref="evidence:q2",
        complete=True,
        protocol_valid=True,
        structure_origin=ORIGIN_MODEL_LEARNED,
        family_count=8,
        exact_structure_correct=5,
        behavioral_correct=7,
        oracle_truth_used=False,
        replaced_seed_count=0,
    )


def _q3(manifest: QualificationManifest) -> OracleProjectionResult:
    return OracleProjectionResult(
        manifest_digest=manifest_digest(manifest),
        evidence_ref="evidence:q3",
        complete=True,
        protocol_valid=True,
        structure_origin=ORIGIN_EVALUATOR_ORACLE,
        shared_family_count=8,
        shared_baseline_correct=2,
        shared_oracle_correct=6,
        null_family_count=8,
        null_baseline_correct=3,
        null_oracle_correct=3,
        matched_target_packets=True,
        target_rule_leakage_detected=False,
        replaced_seed_count=0,
    )


def test_manifest_binds_explicit_representation_semantics() -> None:
    manifest = _manifest()
    assert manifest.source_representation_semantics.startswith("y[i]")
    assert manifest.source_representation_semantics_digest == sha256_text(
        manifest.source_representation_semantics
    )
    with pytest.raises(TransferQualificationError, match="digest does not match"):
        replace(
            manifest,
            source_representation_semantics_digest="sha256:" + "0" * 64,
        )


def test_q1_requires_full_non_floor_non_ceiling_target_curve_without_structure() -> None:
    manifest = _manifest()
    assert classify_q1(manifest, _q1(manifest)) == PASS
    assert (
        classify_q1(
            manifest,
            replace(_q1(manifest), evidence_level_correct=(0, 0, 0, 0), endpoint_correct=0),
        )
        == FAIL_FLOOR
    )
    assert (
        classify_q1(
            manifest,
            replace(_q1(manifest), evidence_level_correct=(2, 4, 7, 8), endpoint_correct=8),
        )
        == FAIL_CEILING
    )
    assert (
        classify_q1(
            manifest,
            replace(_q1(manifest), structure_origin=ORIGIN_MODEL_LEARNED),
        )
        == PROTOCOL_INVALID
    )
    assert (
        classify_q1(
            manifest,
            replace(_q1(manifest), evidence_level_correct=(2, 4, 5), endpoint_correct=5),
        )
        == PROTOCOL_INVALID
    )
    with pytest.raises(TransferQualificationError, match="endpoint must equal"):
        replace(_q1(manifest), endpoint_correct=4)


def test_q2_separates_learned_acquisition_from_oracle_truth() -> None:
    manifest = _manifest()
    assert classify_q2(manifest, _q2(manifest)) == PASS
    assert (
        classify_q2(
            manifest,
            replace(_q2(manifest), exact_structure_correct=3),
        )
        == FAIL_ACQUISITION
    )
    assert (
        classify_q2(
            manifest,
            replace(_q2(manifest), behavioral_correct=5),
        )
        == FAIL_ACQUISITION
    )
    assert (
        classify_q2(
            manifest,
            replace(_q2(manifest), oracle_truth_used=True),
        )
        == PROTOCOL_INVALID
    )
    assert (
        classify_q2(
            manifest,
            replace(_q2(manifest), structure_origin=ORIGIN_EVALUATOR_ORACLE),
        )
        == PROTOCOL_INVALID
    )


def test_q3_requires_relation_specific_oracle_mechanism_effect() -> None:
    manifest = _manifest()
    q3 = _q3(manifest)
    assert q3_effects(q3) == (0.5, 0.0, 0.5)
    assert classify_q3(manifest, q3) == PASS
    assert (
        classify_q3(
            manifest,
            replace(q3, shared_oracle_correct=3),
        )
        == FAIL_MECHANISM
    )
    assert (
        classify_q3(
            manifest,
            replace(q3, null_oracle_correct=6),
        )
        == FAIL_MECHANISM
    )
    assert (
        classify_q3(
            manifest,
            replace(q3, matched_target_packets=False),
        )
        == PROTOCOL_INVALID
    )
    assert (
        classify_q3(
            manifest,
            replace(q3, target_rule_leakage_detected=True),
        )
        == PROTOCOL_INVALID
    )


def test_seed_replacement_invalidates_every_gate() -> None:
    manifest = _manifest()
    assert classify_q1(manifest, replace(_q1(manifest), replaced_seed_count=1)) == PROTOCOL_INVALID
    assert classify_q2(manifest, replace(_q2(manifest), replaced_seed_count=1)) == PROTOCOL_INVALID
    assert classify_q3(manifest, replace(_q3(manifest), replaced_seed_count=1)) == PROTOCOL_INVALID


def test_transfer_certificate_requires_three_passes_under_one_manifest() -> None:
    manifest = _manifest()
    certificate = qualify_for_transfer(
        manifest,
        q1=_q1(manifest),
        q2=_q2(manifest),
        q3=_q3(manifest),
    )
    assert certificate.version == QUALIFICATION_VERSION
    assert certificate.manifest_digest == manifest_digest(manifest)
    assert (
        certificate.q1_evidence_ref,
        certificate.q2_evidence_ref,
        certificate.q3_evidence_ref,
    ) == ("evidence:q1", "evidence:q2", "evidence:q3")


def test_transfer_certificate_rejects_failed_or_mismatched_gate() -> None:
    manifest = _manifest()
    with pytest.raises(TransferQualificationError, match="not all PASS"):
        qualify_for_transfer(
            manifest,
            q1=replace(
                _q1(manifest),
                evidence_level_correct=(0, 0, 0, 0),
                endpoint_correct=0,
            ),
            q2=_q2(manifest),
            q3=_q3(manifest),
        )

    other = replace(
        manifest,
        task_family_identity_digest="sha256:" + "3" * 64,
    )
    with pytest.raises(TransferQualificationError, match="not all PASS"):
        qualify_for_transfer(
            manifest,
            q1=_q1(manifest),
            q2=replace(_q2(manifest), manifest_digest=manifest_digest(other)),
            q3=_q3(manifest),
        )


def test_transfer_certificate_requires_distinct_evidence_products() -> None:
    manifest = _manifest()
    with pytest.raises(TransferQualificationError, match="three distinct evidence"):
        qualify_for_transfer(
            manifest,
            q1=_q1(manifest),
            q2=replace(_q2(manifest), evidence_ref="evidence:q1"),
            q3=_q3(manifest),
        )
