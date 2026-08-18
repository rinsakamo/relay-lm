from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from relaylm import __version__
from tools.release_identity import (
    ReleaseIdentityError,
    build_release_manifest,
    ensure_tag_available,
    expected_release_tag,
    parse_release_version,
    validate_ci_ref,
    validate_packaging_fix_successor,
    validate_release_tag,
)


def test_current_source_version_is_in_the_frozen_rel2_grammar() -> None:
    parsed = parse_release_version(__version__)

    assert parsed.kind == "dev"
    assert expected_release_tag(parsed) is None


@pytest.mark.parametrize(
    ("version", "kind", "serial"),
    [
        ("1.0.0.dev0", "dev", 0),
        ("1.0.0.dev7", "dev", 7),
        ("1.0.0rc1", "rc", 1),
        ("1.0.0rc12", "rc", 12),
        ("1.0.0", "final", None),
        ("1.0.1", "final", None),
    ],
)
def test_version_policy_accepts_only_canonical_dev_rc_and_final_forms(
    version: str,
    kind: str,
    serial: int | None,
) -> None:
    parsed = parse_release_version(version)

    assert parsed.kind == kind
    assert parsed.serial == serial


@pytest.mark.parametrize(
    "version",
    [
        "1.0",
        "v1.0.0",
        "1.0.0-rc1",
        "1.0.0rc0",
        "1.0.0a1",
        "1.0.0b1",
        "1.0.0.post1",
        "1.0.0+local",
        "01.0.0",
    ],
)
def test_version_policy_rejects_noncanonical_release_spellings(version: str) -> None:
    with pytest.raises(ReleaseIdentityError):
        parse_release_version(version)


def test_rc_and_final_tags_are_exact_v_prefixed_versions() -> None:
    assert expected_release_tag("1.0.0rc1") == "v1.0.0rc1"
    assert expected_release_tag("1.0.0") == "v1.0.0"
    validate_release_tag("1.0.0rc1", "v1.0.0rc1")

    with pytest.raises(ReleaseIdentityError):
        validate_release_tag("1.0.0rc1", "1.0.0rc1")
    with pytest.raises(ReleaseIdentityError):
        validate_release_tag("1.0.0.dev0", "v1.0.0.dev0")


def test_same_version_tag_reuse_is_rejected() -> None:
    assert ensure_tag_available("1.0.0rc1", ["v0.1.0"]) == "v1.0.0rc1"

    with pytest.raises(ReleaseIdentityError, match="already exists"):
        ensure_tag_available("1.0.0rc1", ["v1.0.0rc1"])


def test_tag_push_must_be_new_nonforced_and_match_the_version() -> None:
    validate_ci_ref(
        version="1.0.0rc1",
        event_name="push",
        ref_type="tag",
        ref_name="v1.0.0rc1",
        created=True,
        forced=False,
    )

    with pytest.raises(ReleaseIdentityError, match="force-updated"):
        validate_ci_ref(
            version="1.0.0rc1",
            event_name="push",
            ref_type="tag",
            ref_name="v1.0.0rc1",
            created=False,
            forced=True,
        )
    with pytest.raises(ReleaseIdentityError, match="exactly"):
        validate_ci_ref(
            version="1.0.0rc1",
            event_name="push",
            ref_type="tag",
            ref_name="v1.0.0rc2",
            created=True,
            forced=False,
        )


def test_packaging_only_fix_uses_the_next_patch_release_line() -> None:
    validate_packaging_fix_successor("1.0.0", "1.0.1rc1")
    validate_packaging_fix_successor("1.0.0", "1.0.1")

    with pytest.raises(ReleaseIdentityError):
        validate_packaging_fix_successor("1.0.0", "1.0.0rc2")
    with pytest.raises(ReleaseIdentityError):
        validate_packaging_fix_successor("1.0.0", "1.1.0")


def test_release_manifest_binds_version_tag_commit_and_artifact_hashes(tmp_path: Path) -> None:
    wheel = tmp_path / "relaylm-1.0.0rc1-py3-none-any.whl"
    sdist = tmp_path / "relaylm-1.0.0rc1.tar.gz"
    wheel.write_bytes(b"wheel-bytes")
    sdist.write_bytes(b"sdist-bytes")

    payload = build_release_manifest(
        version="1.0.0rc1",
        commit="a" * 40,
        artifacts=(wheel, sdist),
    )

    assert payload["version"] == "1.0.0rc1"
    assert payload["tag"] == "v1.0.0rc1"
    assert payload["commit"] == "a" * 40
    records = {item["filename"]: item["sha256"] for item in payload["artifacts"]}
    assert records[wheel.name] == hashlib.sha256(b"wheel-bytes").hexdigest()
    assert records[sdist.name] == hashlib.sha256(b"sdist-bytes").hexdigest()


def test_release_manifest_rejects_dev_identity() -> None:
    with pytest.raises(ReleaseIdentityError, match="rc or final"):
        build_release_manifest(
            version="1.0.0.dev0",
            commit="a" * 40,
            artifacts=(Path("relaylm-1.0.0.dev0-py3-none-any.whl"), Path("relaylm-1.0.0.dev0.tar.gz")),
        )
