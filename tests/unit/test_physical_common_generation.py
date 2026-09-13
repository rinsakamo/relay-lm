from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools.physical_common_generation import (
    COMMON_PHYSICAL_SURFACE,
    CommonGenerationError,
    aggregate_identity,
    assert_generation_id_consistent,
    build_certificate,
    git_blob_oid,
    validate_certificate,
    verify_checkout,
)

ORIGIN = "1" * 40
TREE = "2" * 40
PREDECESSOR = "3" * 40


def _write_surface(root: Path) -> None:
    for index, relative in enumerate(COMMON_PHYSICAL_SURFACE):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"surface-{index}\n".encode())


def _certificate(root: Path) -> dict[str, object]:
    _write_surface(root)
    return build_certificate(
        root,
        generation_id="relay-common-physical-g1",
        origin_commit=ORIGIN,
        origin_tree=TREE,
        promotion_owner=2750,
        predecessor_issue=2731,
        predecessor_commit=PREDECESSOR,
    )


def _reaggregate(cert: dict[str, object]) -> None:
    surface = cert["surface"]
    assert isinstance(surface, list)
    cert["aggregate_identity"] = aggregate_identity(
        (entry["path"], entry["git_blob_oid"]) for entry in surface
    )


def test_git_blob_oid_matches_git_object_framing() -> None:
    assert git_blob_oid(b"test content\n") == "d670460b4b4aece5915caf5c68d12f560a9fe3e4"


def test_round_trip_and_checkout_verification(tmp_path: Path) -> None:
    cert = _certificate(tmp_path)
    identity = verify_checkout(
        tmp_path,
        cert,
        expected_generation_id="relay-common-physical-g1",
        expected_aggregate_identity=cert["aggregate_identity"],
    )
    assert identity["generation_id"] == "relay-common-physical-g1"
    assert identity["origin_commit"] == ORIGIN


def test_schema_version_bool_is_rejected(tmp_path: Path) -> None:
    cert = _certificate(tmp_path)
    cert["schema_version"] = True
    with pytest.raises(CommonGenerationError, match="must be an integer"):
        validate_certificate(cert)


def test_unknown_root_key_is_rejected(tmp_path: Path) -> None:
    cert = _certificate(tmp_path)
    cert["extra"] = "not-authority"
    with pytest.raises(CommonGenerationError, match="keys mismatch"):
        validate_certificate(cert)


def test_surface_must_be_sorted_and_unique(tmp_path: Path) -> None:
    cert = _certificate(tmp_path)
    surface = cert["surface"]
    assert isinstance(surface, list)
    surface[0], surface[1] = surface[1], surface[0]
    with pytest.raises(CommonGenerationError, match="strictly path-sorted"):
        validate_certificate(cert)


def test_path_traversal_is_rejected(tmp_path: Path) -> None:
    cert = _certificate(tmp_path)
    surface = cert["surface"]
    assert isinstance(surface, list)
    surface[0]["path"] = "../escape"
    surface.sort(key=lambda item: item["path"])
    with pytest.raises(CommonGenerationError, match="normalized repository-relative"):
        validate_certificate(cert)


def test_aggregate_tamper_is_rejected(tmp_path: Path) -> None:
    cert = _certificate(tmp_path)
    cert["aggregate_identity"] = "sha256:" + "0" * 64
    with pytest.raises(CommonGenerationError, match="aggregate_identity mismatch"):
        validate_certificate(cert)


def test_checkout_drift_is_rejected(tmp_path: Path) -> None:
    cert = _certificate(tmp_path)
    changed = tmp_path / COMMON_PHYSICAL_SURFACE[-1]
    changed.write_text("changed\n", encoding="utf-8")
    with pytest.raises(CommonGenerationError, match="certified surface drift"):
        verify_checkout(tmp_path, cert)


def test_generation_id_collision_is_rejected(tmp_path: Path) -> None:
    cert = _certificate(tmp_path)
    other = copy.deepcopy(cert)
    surface = other["surface"]
    assert isinstance(surface, list)
    surface[0]["git_blob_oid"] = "f" * 40
    _reaggregate(other)
    with pytest.raises(CommonGenerationError, match="generation id collision"):
        assert_generation_id_consistent([cert, other])


def test_same_generation_and_identity_is_not_a_collision(tmp_path: Path) -> None:
    cert = _certificate(tmp_path)
    assert_generation_id_consistent([cert, copy.deepcopy(cert)])


@pytest.mark.parametrize("field", ["promotion_owner", "predecessor_issue"])
def test_provenance_issue_numbers_are_generic_positive_integers(tmp_path: Path, field: str) -> None:
    cert = _certificate(tmp_path)
    provenance = cert["provenance"]
    assert isinstance(provenance, dict)
    provenance[field] = 9999
    validate_certificate(cert)
    provenance[field] = 0
    with pytest.raises(CommonGenerationError, match="positive integer"):
        validate_certificate(cert)
    provenance[field] = True
    with pytest.raises(CommonGenerationError, match="must be an integer"):
        validate_certificate(cert)


def test_build_certificate_carries_generic_provenance(tmp_path: Path) -> None:
    _write_surface(tmp_path)
    cert = build_certificate(
        tmp_path,
        generation_id="relay-common-physical-g2",
        origin_commit=ORIGIN,
        origin_tree=TREE,
        promotion_owner=9001,
        predecessor_issue=8999,
        predecessor_commit=PREDECESSOR,
    )
    assert cert["provenance"]["promotion_owner"] == 9001
    assert cert["provenance"]["predecessor_issue"] == 8999


def test_branch_local_and_science_surfaces_are_excluded() -> None:
    excluded = {
        ".ai/authority/physical_execution_queue.yaml",
        ".ai/physical/llama_cpp_targets.json",
        ".ai/physical/common_generation.json",
        "tools/physical_common_generation.py",
    }
    assert excluded.isdisjoint(COMMON_PHYSICAL_SURFACE)
    assert not any("tools/v1_" in path or "tools/v2_" in path for path in COMMON_PHYSICAL_SURFACE)


def test_surface_is_stable_sorted_and_has_expected_size() -> None:
    assert COMMON_PHYSICAL_SURFACE == tuple(sorted(COMMON_PHYSICAL_SURFACE))
    assert len(COMMON_PHYSICAL_SURFACE) == 13
    assert len(set(COMMON_PHYSICAL_SURFACE)) == 13


def test_checked_in_certificate_matches_declared_surface() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    certificate_path = repo_root / ".ai/physical/common_generation.json"
    cert = validate_certificate(json.loads(certificate_path.read_text(encoding="utf-8")))
    assert tuple(entry["path"] for entry in cert["surface"]) == COMMON_PHYSICAL_SURFACE
    assert cert["generation_id"] == "relay-common-physical-g2"
    assert cert["aggregate_identity"] == (
        "sha256:bb983011905bdd8b5393c2c3459b691289f5ced9a41561bb8dc7f642fa330b87"
    )
    assert cert["provenance"]["origin_commit"] == "3bd301b35fe45b1984d732b2439cdd38a849a46b"
    assert cert["provenance"]["origin_tree"] == "1149a660cd63ec686637f07286776bd8c998b035"
    assert cert["provenance"]["promotion_owner"] == 2799
    assert cert["provenance"]["predecessor_issue"] == 2750
    assert cert["provenance"]["predecessor_commit"] == "8451050fc0c52e090f2e1c2c6c5d2b8121ca159f"


def test_checked_in_certificate_verifies_checkout() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    certificate_path = repo_root / ".ai/physical/common_generation.json"
    cert = validate_certificate(json.loads(certificate_path.read_text(encoding="utf-8")))
    identity = verify_checkout(repo_root, cert)
    assert identity["generation_id"] == "relay-common-physical-g2"
