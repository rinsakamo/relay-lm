"""Shared structural llama.cpp binary identity grammar for qualification paths."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


class LlamaCppIdentityError(ValueError):
    """The frozen llama.cpp build identity could not be proven."""


_PROPS_RE = re.compile(r"^b(?P<build>\d+)-(?P<commit>[0-9a-fA-F]{7,40})$")
_CLI_RE = re.compile(
    r"\bbuild\s+(?P<build>\d+)\s*,\s*commit\s+(?P<commit>[0-9a-fA-F]{7,40})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class LlamaCppBuildIdentity:
    build_number: int
    commit: str
    source: str


def parse_props_build_info(value: str) -> LlamaCppBuildIdentity:
    match = _PROPS_RE.fullmatch(value.strip())
    if match is None:
        raise LlamaCppIdentityError(
            "canonical llama.cpp /props build_info must be b<build>-<commit>"
        )
    return LlamaCppBuildIdentity(
        build_number=int(match.group("build")),
        commit=match.group("commit").lower(),
        source="/props",
    )


def parse_cli_build_identity(output: str) -> LlamaCppBuildIdentity:
    match = _CLI_RE.search(output)
    if match is None:
        raise LlamaCppIdentityError(
            "llama-server --version output has no structural build/commit identity"
        )
    return LlamaCppBuildIdentity(
        build_number=int(match.group("build")),
        commit=match.group("commit").lower(),
        source="cli",
    )


def verify_cli_against_props(
    *,
    cli_output: str,
    expected_build_info: str,
    upstream_revision: str,
) -> LlamaCppBuildIdentity:
    expected = parse_props_build_info(expected_build_info)
    observed = parse_cli_build_identity(cli_output)
    if observed.build_number != expected.build_number:
        raise LlamaCppIdentityError(
            "llama-server CLI build number does not match canonical /props build_info"
        )
    revision = upstream_revision.lower()
    if observed.commit != revision[: len(observed.commit)]:
        raise LlamaCppIdentityError(
            "llama-server CLI commit does not match frozen upstream revision"
        )
    if expected.commit != revision[: len(expected.commit)]:
        raise LlamaCppIdentityError(
            "canonical /props build_info commit does not match frozen upstream revision"
        )
    if observed.commit != expected.commit[: len(observed.commit)]:
        raise LlamaCppIdentityError(
            "llama-server CLI commit does not match canonical /props build_info"
        )
    return observed


def probe_cli_identity(
    binary: Path,
    *,
    expected_build_info: str,
    upstream_revision: str,
) -> tuple[LlamaCppBuildIdentity, str]:
    """Probe stdout and stderr together; actual llama.cpp builds vary by stream."""

    completed = subprocess.run(
        [str(binary), "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    combined = "\n".join(
        value.strip()
        for value in (completed.stdout, completed.stderr)
        if value and value.strip()
    )
    if completed.returncode != 0:
        raise LlamaCppIdentityError(
            f"llama-server --version failed with exit code {completed.returncode}"
        )
    return (
        verify_cli_against_props(
            cli_output=combined,
            expected_build_info=expected_build_info,
            upstream_revision=upstream_revision,
        ),
        combined,
    )


def verify_props_build_info(
    *,
    actual_build_info: str,
    expected_build_info: str,
    upstream_revision: str,
) -> LlamaCppBuildIdentity:
    """Retain the exact live /props assertion after server startup."""

    expected = parse_props_build_info(expected_build_info)
    actual = parse_props_build_info(actual_build_info)
    if actual != LlamaCppBuildIdentity(
        build_number=expected.build_number,
        commit=expected.commit,
        source="/props",
    ):
        raise LlamaCppIdentityError("live /props build_info drifted from the frozen plan")
    if expected.commit != upstream_revision.lower()[: len(expected.commit)]:
        raise LlamaCppIdentityError(
            "live /props build_info commit does not match frozen upstream revision"
        )
    return actual
