#!/usr/bin/env python3
"""RelayLM v1 release-identity policy and provenance helpers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


_VERSION_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:(?P<rc>rc[1-9]\d*)|(?P<dev>\.dev(?:0|[1-9]\d*)))?$"
)
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class ReleaseIdentityError(ValueError):
    """Raised when release identity violates the frozen REL2 policy."""


@dataclass(frozen=True, slots=True)
class ReleaseVersion:
    text: str
    major: int
    minor: int
    patch: int
    kind: str
    serial: int | None

    @property
    def core(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)


def parse_release_version(value: str) -> ReleaseVersion:
    match = _VERSION_RE.fullmatch(value)
    if match is None:
        raise ReleaseIdentityError(
            "version must be canonical X.Y.Z, X.Y.ZrcN (N>=1), or X.Y.Z.devN"
        )

    rc = match.group("rc")
    dev = match.group("dev")
    if rc is not None:
        kind = "rc"
        serial = int(rc[2:])
    elif dev is not None:
        kind = "dev"
        serial = int(dev[4:])
    else:
        kind = "final"
        serial = None

    return ReleaseVersion(
        text=value,
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
        kind=kind,
        serial=serial,
    )


def expected_release_tag(version: ReleaseVersion | str) -> str | None:
    parsed = parse_release_version(version) if isinstance(version, str) else version
    if parsed.kind == "dev":
        return None
    return f"v{parsed.text}"


def validate_release_tag(version: ReleaseVersion | str, tag: str) -> None:
    parsed = parse_release_version(version) if isinstance(version, str) else version
    expected = expected_release_tag(parsed)
    if expected is None:
        raise ReleaseIdentityError("development versions must not have release tags")
    if tag != expected:
        raise ReleaseIdentityError(f"release tag must be exactly {expected!r}")


def ensure_tag_available(
    version: ReleaseVersion | str,
    existing_tags: Iterable[str],
) -> str:
    parsed = parse_release_version(version) if isinstance(version, str) else version
    tag = expected_release_tag(parsed)
    if tag is None:
        raise ReleaseIdentityError("development versions are not releasable identities")
    if tag in set(existing_tags):
        raise ReleaseIdentityError(
            f"release tag {tag!r} already exists; same-version overwrite/reissue is forbidden"
        )
    return tag


def validate_packaging_fix_successor(
    previous_final: ReleaseVersion | str,
    proposed: ReleaseVersion | str,
) -> None:
    previous = (
        parse_release_version(previous_final)
        if isinstance(previous_final, str)
        else previous_final
    )
    candidate = parse_release_version(proposed) if isinstance(proposed, str) else proposed
    if previous.kind != "final":
        raise ReleaseIdentityError("packaging-fix predecessor must be a final release")
    expected_core = (previous.major, previous.minor, previous.patch + 1)
    if candidate.core != expected_core or candidate.kind not in {"rc", "final"}:
        raise ReleaseIdentityError(
            "a packaging-only fix after a final release must use the next patch release line"
        )


def validate_ci_ref(
    *,
    version: ReleaseVersion | str,
    event_name: str,
    ref_type: str,
    ref_name: str,
    created: bool = False,
    forced: bool = False,
) -> None:
    parsed = parse_release_version(version) if isinstance(version, str) else version
    if ref_type != "tag":
        return

    validate_release_tag(parsed, ref_name)
    if event_name == "push":
        if forced:
            raise ReleaseIdentityError("release tags must never be force-updated")
        if not created:
            raise ReleaseIdentityError(
                "a release-tag push must create a new immutable tag, not rewrite an existing one"
            )


def build_release_manifest(
    *,
    version: ReleaseVersion | str,
    commit: str,
    artifacts: Sequence[Path],
) -> dict[str, object]:
    parsed = parse_release_version(version) if isinstance(version, str) else version
    tag = expected_release_tag(parsed)
    if tag is None:
        raise ReleaseIdentityError("release manifest requires an rc or final version")
    if _COMMIT_RE.fullmatch(commit) is None:
        raise ReleaseIdentityError("release commit must be a lowercase 40-hex commit SHA")
    if len(artifacts) != 2:
        raise ReleaseIdentityError("release manifest requires exactly one wheel and one sdist")

    expected_sdist = f"relaylm-{parsed.text}.tar.gz"
    expected_wheel_prefix = f"relaylm-{parsed.text}-"
    names = [path.name for path in artifacts]
    if expected_sdist not in names:
        raise ReleaseIdentityError(f"missing expected sdist {expected_sdist!r}")
    wheels = [name for name in names if name.startswith(expected_wheel_prefix) and name.endswith(".whl")]
    if len(wheels) != 1:
        raise ReleaseIdentityError("release manifest requires exactly one version-matching wheel")

    records: list[dict[str, str]] = []
    for path in sorted(artifacts, key=lambda item: item.name):
        if not path.is_file():
            raise ReleaseIdentityError(f"artifact does not exist: {path}")
        records.append(
            {
                "filename": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    return {
        "schema_version": 1,
        "package": "relaylm",
        "version": parsed.text,
        "release_kind": parsed.kind,
        "tag": tag,
        "commit": commit,
        "artifacts": records,
    }


def _parse_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def _git_tags() -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "tag", "--list"],
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate RelayLM release identity")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_version = subparsers.add_parser("check-version")
    check_version.add_argument("version")

    check_tag = subparsers.add_parser("check-tag")
    check_tag.add_argument("version")
    check_tag.add_argument("tag")

    ci = subparsers.add_parser("ci")
    ci.add_argument("--version", required=True)
    ci.add_argument("--event-name", required=True)
    ci.add_argument("--ref-type", required=True)
    ci.add_argument("--ref-name", required=True)
    ci.add_argument("--created", default="false")
    ci.add_argument("--forced", default="false")

    tag_available = subparsers.add_parser("assert-tag-absent")
    tag_available.add_argument("version")

    manifest = subparsers.add_parser("manifest")
    manifest.add_argument("--version", required=True)
    manifest.add_argument("--commit", required=True)
    manifest.add_argument("artifacts", nargs=2, type=Path)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "check-version":
            parse_release_version(args.version)
        elif args.command == "check-tag":
            validate_release_tag(args.version, args.tag)
        elif args.command == "ci":
            validate_ci_ref(
                version=args.version,
                event_name=args.event_name,
                ref_type=args.ref_type,
                ref_name=args.ref_name,
                created=_parse_bool(args.created),
                forced=_parse_bool(args.forced),
            )
        elif args.command == "assert-tag-absent":
            ensure_tag_available(args.version, _git_tags())
        elif args.command == "manifest":
            payload = build_release_manifest(
                version=args.version,
                commit=args.commit,
                artifacts=args.artifacts,
            )
            print(json.dumps(payload, sort_keys=True, indent=2))
        else:  # pragma: no cover - argparse owns command validation
            raise AssertionError(args.command)
    except (ReleaseIdentityError, subprocess.CalledProcessError) as exc:
        print(f"release identity error: {exc}", file=__import__("sys").stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
