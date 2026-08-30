from __future__ import annotations

import hashlib
import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest

from tools.release_candidate import (
    ReleaseCandidateError,
    discover_candidate_artifacts,
    inspect_candidate_artifacts,
    validate_candidate_source,
    validate_candidate_version,
    verify_release_manifest,
    verify_runtime_evidence,
)


def test_candidate_gate_accepts_only_rc_or_final_versions() -> None:
    assert validate_candidate_version("1.0.0rc1") == "v1.0.0rc1"
    assert validate_candidate_version("1.0.0") == "v1.0.0"

    with pytest.raises(ReleaseCandidateError, match="rc or final"):
        validate_candidate_version("1.0.0.dev0")


def test_candidate_commit_must_equal_fresh_v1_head() -> None:
    sha = "a" * 40
    validate_candidate_source(candidate_commit=sha, current_v1_commit=sha)

    with pytest.raises(ReleaseCandidateError, match="freshly fetched current v1"):
        validate_candidate_source(candidate_commit=sha, current_v1_commit="b" * 40)


def test_candidate_artifacts_require_exact_version_pair(tmp_path: Path) -> None:
    (tmp_path / "relaylm-1.0.0rc1-py3-none-any.whl").write_bytes(b"wheel")
    (tmp_path / "relaylm-1.0.0rc1.tar.gz").write_bytes(b"sdist")

    artifacts = discover_candidate_artifacts(tmp_path, "1.0.0rc1")
    assert artifacts.wheel.name.endswith(".whl")
    assert artifacts.sdist.name.endswith(".tar.gz")

    (tmp_path / "relaylm-1.0.0rc1-extra.whl").write_bytes(b"other")
    with pytest.raises(ReleaseCandidateError, match="exactly one"):
        discover_candidate_artifacts(tmp_path, "1.0.0rc1")


def test_candidate_artifact_inspection_and_manifest_hash_binding(tmp_path: Path) -> None:
    version = "1.0.0rc1"
    wheel = tmp_path / f"relaylm-{version}-py3-none-any.whl"
    sdist = tmp_path / f"relaylm-{version}.tar.gz"
    _write_wheel(wheel, version)
    _write_sdist(sdist, version)

    inspect_candidate_artifacts(tmp_path, version)
    commit = "c" * 40
    records = [
        {"filename": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in sorted((wheel, sdist), key=lambda item: item.name)
    ]
    manifest = tmp_path / "release-identity.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "package": "relaylm",
                "version": version,
                "release_kind": "rc",
                "tag": f"v{version}",
                "commit": commit,
                "artifacts": records,
            }
        ),
        encoding="utf-8",
    )
    verify_release_manifest(
        manifest_path=manifest,
        artifacts_directory=tmp_path,
        version=version,
        commit=commit,
    )

    wheel.write_bytes(wheel.read_bytes() + b"changed")
    with pytest.raises(ReleaseCandidateError, match="hashes"):
        verify_release_manifest(
            manifest_path=manifest,
            artifacts_directory=tmp_path,
            version=version,
            commit=commit,
        )


def test_runtime_evidence_requires_doctor_ok_and_native_eval_pass(tmp_path: Path) -> None:
    doctor = tmp_path / "doctor.json"
    evaluation = tmp_path / "evaluation.json"
    doctor.write_text('{"status":"ok"}', encoding="utf-8")
    evaluation.write_text('{"suite":"relaylm-native","status":"pass"}', encoding="utf-8")

    verify_runtime_evidence(doctor_path=doctor, evaluation_path=evaluation)

    evaluation.write_text('{"suite":"relaylm-native","status":"fail"}', encoding="utf-8")
    with pytest.raises(ReleaseCandidateError, match="did not pass"):
        verify_runtime_evidence(doctor_path=doctor, evaluation_path=evaluation)


def test_candidate_workflow_uses_current_profile_and_starter_operator_path() -> None:
    workflow = Path(".github/workflows/v1-release-candidate.yml").read_text(encoding="utf-8")

    assert "profiles:" in workflow
    assert "materialize_starter_package" in workflow
    assert 'materialize_starter_package("relm"' in workflow
    assert 'materialize_starter_package("fact-summarizer"' in workflow
    assert "character:\n            directory:" not in workflow


def _metadata(version: str) -> bytes:
    return (
        "Metadata-Version: 2.4\n"
        "Name: relaylm\n"
        f"Version: {version}\n"
        "Requires-Python: >=3.12\n\n"
    ).encode()


def _write_wheel(path: Path, version: str) -> None:
    dist_info = f"relaylm-{version}.dist-info"
    with zipfile.ZipFile(path, "w") as archive:
        for name in (
            "relaylm/__init__.py",
            "relaylm/_version.py",
            "relaylm/cli.py",
            "relaylm/evaluation.py",
        ):
            archive.writestr(name, "")
        archive.writestr(f"{dist_info}/METADATA", _metadata(version))
        archive.writestr(
            f"{dist_info}/entry_points.txt",
            "[console_scripts]\nrelaylm = relaylm.cli:main\nrelaylm-eval = relaylm.evaluation:main\n",
        )


def _write_sdist(path: Path, version: str) -> None:
    root = f"relaylm-{version}"
    files = {
        "pyproject.toml": b"",
        "README.md": b"",
        "LICENSE": b"",
        "src/relaylm/__init__.py": b"",
        "src/relaylm/_version.py": b"",
        "src/relaylm/cli.py": b"",
        "src/relaylm/evaluation.py": b"",
        "PKG-INFO": _metadata(version),
    }
    with tarfile.open(path, "w:gz") as archive:
        for relative, data in files.items():
            info = tarfile.TarInfo(f"{root}/{relative}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
