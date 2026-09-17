from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from test_v1_external_qualification_campaign_prepare import _inputs, _prepare
from test_v1_external_qualification_llama_cpp_campaign import _strict_descriptor_mapping
from tools.v1_external_qualification_campaign_proof import prepare_static_proof
from tools.v1_external_qualification_llama_cpp_campaign import (
    CampaignCarriageError,
    CampaignDescriptor,
)


def _exact_rc_identity(axis: dict[str, object]) -> dict[str, object]:
    manifest = axis["manifest"]
    assert isinstance(manifest, dict)
    participants = manifest["participants"]
    assert isinstance(participants, list)
    participant = next(
        item
        for item in participants
        if isinstance(item, dict) and item.get("slot") == "relaylm_exact_rc"
    )
    identity = participant["identity"]
    assert isinstance(identity, dict)
    return identity


def _set_preserved_exact_rc_spelling(raw: dict[str, object], value: str) -> None:
    axes = raw["axes"]
    assert isinstance(axes, list)
    for axis in axes:
        assert isinstance(axis, dict)
        _exact_rc_identity(axis)["implementation"] = value


def _release_case(raw: dict[str, object], axis_id: str) -> dict[str, object]:
    freeze = raw["execution_freeze"]
    assert isinstance(freeze, dict)
    release_cases = freeze["release_cases"]
    assert isinstance(release_cases, list)
    release = next(
        item
        for item in release_cases
        if isinstance(item, dict) and item.get("axis_id") == axis_id
    )
    assert isinstance(release, dict)
    return release


def _set_matched_stale_case_fingerprint(
    raw: dict[str, object],
    *,
    fingerprint: str,
) -> None:
    axes = raw["axes"]
    assert isinstance(axes, list)
    for axis in axes:
        assert isinstance(axis, dict)
        axis_id = axis["axis_id"]
        assert isinstance(axis_id, str)
        material = axis["benchmark_material"]
        assert isinstance(material, dict)
        material["case_fingerprint"] = fingerprint
        release = _release_case(raw, axis_id)
        release_material = release["benchmark_material"]
        assert isinstance(release_material, dict)
        release_material["case_fingerprint"] = fingerprint


def test_prepare_accepts_preserved_exact_rc_spelling_and_canonicalizes(
    tmp_path: Path,
) -> None:
    stale, lifecycle_base = _inputs(tmp_path)
    _set_preserved_exact_rc_spelling(stale, "relaylm_exact_rc")

    prepared = _prepare(
        tmp_path,
        owner_id="owner-2965-preserved-exact-rc",
        stale=stale,
        lifecycle=lifecycle_base,
    )
    raw = prepared.to_mapping()
    CampaignDescriptor.from_mapping(raw)

    axes = raw["axes"]
    assert isinstance(axes, list)
    for axis in axes:
        assert isinstance(axis, dict)
        assert _exact_rc_identity(axis)["implementation"] == "relaylm"

    freeze = raw["execution_freeze"]
    assert isinstance(freeze, dict)
    release_cases = freeze["release_cases"]
    assert isinstance(release_cases, list)
    for release_case in release_cases:
        assert isinstance(release_case, dict)
        manifest = release_case["manifest"]
        assert isinstance(manifest, dict)
        participants = manifest["participants"]
        assert isinstance(participants, list)
        exact_rc = next(
            item
            for item in participants
            if isinstance(item, dict) and item.get("slot") == "relaylm_exact_rc"
        )
        identity = exact_rc["identity"]
        assert isinstance(identity, dict)
        assert identity["implementation"] == "relaylm"


def test_prepare_rejects_unknown_exact_rc_template_implementation(
    tmp_path: Path,
) -> None:
    stale, lifecycle_base = _inputs(tmp_path)
    axes = stale["axes"]
    assert isinstance(axes, list)
    first_axis = axes[0]
    assert isinstance(first_axis, dict)
    _exact_rc_identity(first_axis)["implementation"] = "RelayLMExactRC"

    with pytest.raises(
        CampaignCarriageError,
        match="relaylm_exact_rc participant must be RelayLM",
    ):
        _prepare(
            tmp_path,
            owner_id="owner-2965-reject-unknown-exact-rc",
            stale=stale,
            lifecycle=lifecycle_base,
        )


def test_prepare_rederives_matched_stale_benchmark_material_case_fingerprint(
    tmp_path: Path,
) -> None:
    stale, lifecycle_base = _inputs(tmp_path)
    stale_fingerprint = "sha256:" + "0" * 64
    _set_matched_stale_case_fingerprint(
        stale,
        fingerprint=stale_fingerprint,
    )

    prepared = _prepare(
        tmp_path,
        owner_id="owner-2965-rederive-benchmark-material",
        stale=stale,
        lifecycle=lifecycle_base,
    )
    raw = prepared.to_mapping()
    CampaignDescriptor.from_mapping(raw)

    axes = raw["axes"]
    assert isinstance(axes, list)
    for axis in axes:
        assert isinstance(axis, dict)
        axis_id = axis["axis_id"]
        assert isinstance(axis_id, str)
        material = axis["benchmark_material"]
        assert isinstance(material, dict)
        assert material["case_fingerprint"] != stale_fingerprint
        release = _release_case(raw, axis_id)
        assert release["benchmark_material"] == material


def test_prepare_rejects_source_axis_release_case_mismatch(tmp_path: Path) -> None:
    stale, lifecycle_base = _inputs(tmp_path)
    axes = stale["axes"]
    assert isinstance(axes, list)
    first_axis = axes[0]
    assert isinstance(first_axis, dict)
    axis_id = first_axis["axis_id"]
    assert isinstance(axis_id, str)
    release = _release_case(stale, axis_id)
    release_case = release["case"]
    assert isinstance(release_case, dict)
    release_case["adapter_case_ref"] = str(release_case["adapter_case_ref"]) + "-mismatch"

    with pytest.raises(
        CampaignCarriageError,
        match="case differs from execution freeze",
    ):
        _prepare(
            tmp_path,
            owner_id="owner-2965-reject-case-mismatch",
            stale=stale,
            lifecycle=lifecycle_base,
        )


def test_prepare_rejects_source_axis_release_material_mismatch(tmp_path: Path) -> None:
    stale, lifecycle_base = _inputs(tmp_path)
    axes = stale["axes"]
    assert isinstance(axes, list)
    first_axis = axes[0]
    assert isinstance(first_axis, dict)
    axis_id = first_axis["axis_id"]
    assert isinstance(axis_id, str)
    release = _release_case(stale, axis_id)
    release_material = release["benchmark_material"]
    assert isinstance(release_material, dict)
    release_material["case_fingerprint"] = "sha256:" + "1" * 64

    with pytest.raises(
        CampaignCarriageError,
        match="benchmark_material differs from execution freeze",
    ):
        _prepare(
            tmp_path,
            owner_id="owner-2965-reject-material-mismatch",
            stale=stale,
            lifecycle=lifecycle_base,
        )


def test_static_proof_accepts_preserved_hindsight_and_exact_rc_spellings(
    tmp_path: Path,
) -> None:
    raw = _strict_descriptor_mapping(tmp_path)

    freeze = raw["execution_freeze"]
    assert isinstance(freeze, dict)
    comparator = freeze["comparator"]
    assert isinstance(comparator, dict)
    comparator["implementation"] = "Hindsight"

    axes = raw["axes"]
    assert isinstance(axes, list)
    for axis in axes:
        assert isinstance(axis, dict)
        manifest = axis["manifest"]
        assert isinstance(manifest, dict)
        participants = manifest["participants"]
        assert isinstance(participants, list)
        serious = next(
            item
            for item in participants
            if isinstance(item, dict) and item.get("slot") == "serious_comparator"
        )
        serious_identity = serious["identity"]
        assert isinstance(serious_identity, dict)
        serious_identity["implementation"] = "Hindsight"
        _exact_rc_identity(axis)["implementation"] = "relaylm_exact_rc"

    _set_matched_stale_case_fingerprint(
        raw,
        fingerprint="sha256:" + "2" * 64,
    )

    source = tmp_path / "preserved-source.json"
    source.write_text(json.dumps(raw, sort_keys=True) + "\n", encoding="utf-8")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    owner_id = "owner-2965-proof-preserved-identities"
    plan = tmp_path / "fresh-plan.json"

    receipt = prepare_static_proof(
        repo_root=tmp_path,
        source_path=source,
        source_sha256=source_sha,
        plan_path=plan,
        owner_root=tmp_path / owner_id,
        owner_id=owner_id,
        repository_head="a" * 40,
        repository_tree="b" * 40,
    )

    assert receipt["status"] == "FRESH_OWNER_STATIC_PROOF_PASS"
    prepared = json.loads(plan.read_text(encoding="utf-8"))
    CampaignDescriptor.from_mapping(prepared)
    prepared_axes = prepared["axes"]
    assert isinstance(prepared_axes, list)
    for axis in prepared_axes:
        assert isinstance(axis, dict)
        assert _exact_rc_identity(axis)["implementation"] == "relaylm"
