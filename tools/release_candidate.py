#!/usr/bin/env python3
"""Mechanical validation helpers for an exact RelayLM release candidate artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
import zipfile
from dataclasses import dataclass
from email.parser import BytesParser
from pathlib import Path
from typing import Mapping, Sequence

from tools.release_identity import (
    ReleaseIdentityError,
    expected_release_tag,
    parse_release_version,
)


_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_FORBIDDEN_ROOTS = (
    "tests/",
    "docs/",
    "examples/",
    "evaluation/",
    ".github/",
    "constraints/",
)


class ReleaseCandidateError(ValueError):
    """Raised when candidate mechanics do not preserve exact artifact authority."""


@dataclass(frozen=True, slots=True)
class CandidateArtifacts:
    wheel: Path
    sdist: Path


def validate_candidate_version(version: str) -> str:
    parsed = parse_release_version(version)
    if parsed.kind not in {"rc", "final"}:
        raise ReleaseCandidateError("release-candidate gate requires an rc or final package version")
    tag = expected_release_tag(parsed)
    assert tag is not None
    return tag


def validate_candidate_source(*, candidate_commit: str, current_v1_commit: str) -> None:
    if _COMMIT_RE.fullmatch(candidate_commit) is None:
        raise ReleaseCandidateError("candidate commit must be a lowercase 40-hex SHA")
    if _COMMIT_RE.fullmatch(current_v1_commit) is None:
        raise ReleaseCandidateError("current v1 commit must be a lowercase 40-hex SHA")
    if candidate_commit != current_v1_commit:
        raise ReleaseCandidateError("candidate commit must equal the freshly fetched current v1 HEAD")


def discover_candidate_artifacts(directory: Path, version: str) -> CandidateArtifacts:
    validate_candidate_version(version)
    wheels = sorted(directory.glob(f"relaylm-{version}-*.whl"))
    sdists = sorted(directory.glob(f"relaylm-{version}.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ReleaseCandidateError(
            "candidate directory must contain exactly one version-matching wheel and one sdist"
        )
    return CandidateArtifacts(wheel=wheels[0], sdist=sdists[0])


def inspect_candidate_artifacts(directory: Path, version: str) -> CandidateArtifacts:
    artifacts = discover_candidate_artifacts(directory, version)
    _inspect_wheel(artifacts.wheel, version)
    _inspect_sdist(artifacts.sdist, version)
    return artifacts


def verify_release_manifest(
    *,
    manifest_path: Path,
    artifacts_directory: Path,
    version: str,
    commit: str,
) -> None:
    tag = validate_candidate_version(version)
    validate_candidate_source(candidate_commit=commit, current_v1_commit=commit)
    artifacts = inspect_candidate_artifacts(artifacts_directory, version)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_header = {
        "schema_version": 1,
        "package": "relaylm",
        "version": version,
        "release_kind": parse_release_version(version).kind,
        "tag": tag,
        "commit": commit,
    }
    for key, expected in expected_header.items():
        if payload.get(key) != expected:
            raise ReleaseCandidateError(f"manifest {key!r} does not match candidate authority")

    records = payload.get("artifacts")
    if not isinstance(records, list) or len(records) != 2:
        raise ReleaseCandidateError("manifest must record exactly the candidate wheel and sdist")
    expected_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (artifacts.wheel, artifacts.sdist)
    }
    observed: dict[str, str] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise ReleaseCandidateError("manifest artifact record must be an object")
        filename = record.get("filename")
        sha256 = record.get("sha256")
        if not isinstance(filename, str) or not isinstance(sha256, str):
            raise ReleaseCandidateError("manifest artifact record is incomplete")
        observed[filename] = sha256
    if observed != expected_hashes:
        raise ReleaseCandidateError("manifest artifact hashes do not match the exact candidate bytes")


def verify_runtime_evidence(*, doctor_path: Path, evaluation_path: Path) -> None:
    doctor = json.loads(doctor_path.read_text(encoding="utf-8"))
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    if doctor.get("status") != "ok":
        raise ReleaseCandidateError("installed candidate doctor did not report status=ok")
    if evaluation.get("status") != "pass" or evaluation.get("suite") != "relaylm-native":
        raise ReleaseCandidateError("installed candidate native evaluation did not pass")


def _inspect_wheel(path: Path, version: str) -> None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        required = {
            "relaylm/__init__.py",
            "relaylm/_version.py",
            "relaylm/cli.py",
            "relaylm/evaluation.py",
        }
        if not required <= names:
            raise ReleaseCandidateError(f"wheel is missing required files: {sorted(required - names)}")
        if any(name.startswith(_FORBIDDEN_ROOTS) for name in names):
            raise ReleaseCandidateError("wheel contains repository-only roots")
        metadata_name = next(
            (name for name in names if name.endswith(".dist-info/METADATA")), None
        )
        entry_points_name = next(
            (name for name in names if name.endswith(".dist-info/entry_points.txt")), None
        )
        if metadata_name is None or entry_points_name is None:
            raise ReleaseCandidateError("wheel metadata or entrypoints are missing")
        metadata = BytesParser().parsebytes(archive.read(metadata_name))
        if metadata["Name"] != "relaylm" or metadata["Version"] != version:
            raise ReleaseCandidateError("wheel metadata does not match candidate package/version")
        if metadata["Requires-Python"] != ">=3.12":
            raise ReleaseCandidateError("wheel Python support declaration changed unexpectedly")
        entry_points = archive.read(entry_points_name).decode("utf-8")
        for expected in (
            "relaylm = relaylm.cli:main",
            "relaylm-eval = relaylm.evaluation:main",
        ):
            if expected not in entry_points:
                raise ReleaseCandidateError(f"wheel entrypoint is missing: {expected}")


def _inspect_sdist(path: Path, version: str) -> None:
    root = f"relaylm-{version}/"
    with tarfile.open(path, "r:gz") as archive:
        names = set(archive.getnames())
        required = {
            root + "pyproject.toml",
            root + "README.md",
            root + "LICENSE",
            root + "src/relaylm/__init__.py",
            root + "src/relaylm/_version.py",
            root + "src/relaylm/cli.py",
            root + "src/relaylm/evaluation.py",
        }
        if not required <= names:
            raise ReleaseCandidateError(f"sdist is missing required files: {sorted(required - names)}")
        if any(
            name.startswith(root + forbidden)
            for name in names
            for forbidden in _FORBIDDEN_ROOTS
        ):
            raise ReleaseCandidateError("sdist contains repository-only roots")
        pkg_info_name = next((name for name in names if name == root + "PKG-INFO"), None)
        if pkg_info_name is None:
            raise ReleaseCandidateError("sdist PKG-INFO is missing")
        member = archive.extractfile(pkg_info_name)
        if member is None:
            raise ReleaseCandidateError("sdist PKG-INFO cannot be read")
        metadata = BytesParser().parsebytes(member.read())
        if metadata["Name"] != "relaylm" or metadata["Version"] != version:
            raise ReleaseCandidateError("sdist metadata does not match candidate package/version")
        if metadata["Requires-Python"] != ">=3.12":
            raise ReleaseCandidateError("sdist Python support declaration changed unexpectedly")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate RelayLM exact candidate mechanics")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_version = subparsers.add_parser("check-version")
    check_version.add_argument("version")

    check_source = subparsers.add_parser("check-source")
    check_source.add_argument("--candidate", required=True)
    check_source.add_argument("--current-v1", required=True)

    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("--version", required=True)
    inspect.add_argument("--artifacts", required=True, type=Path)

    manifest = subparsers.add_parser("verify-manifest")
    manifest.add_argument("--version", required=True)
    manifest.add_argument("--commit", required=True)
    manifest.add_argument("--manifest", required=True, type=Path)
    manifest.add_argument("--artifacts", required=True, type=Path)

    runtime = subparsers.add_parser("verify-runtime")
    runtime.add_argument("--doctor", required=True, type=Path)
    runtime.add_argument("--evaluation", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "check-version":
            validate_candidate_version(args.version)
        elif args.command == "check-source":
            validate_candidate_source(
                candidate_commit=args.candidate,
                current_v1_commit=args.current_v1,
            )
        elif args.command == "inspect":
            inspect_candidate_artifacts(args.artifacts, args.version)
        elif args.command == "verify-manifest":
            verify_release_manifest(
                manifest_path=args.manifest,
                artifacts_directory=args.artifacts,
                version=args.version,
                commit=args.commit,
            )
        elif args.command == "verify-runtime":
            verify_runtime_evidence(doctor_path=args.doctor, evaluation_path=args.evaluation)
        else:  # pragma: no cover - argparse owns validation
            raise AssertionError(args.command)
    except (ReleaseCandidateError, ReleaseIdentityError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"release candidate error: {exc}", file=__import__("sys").stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
