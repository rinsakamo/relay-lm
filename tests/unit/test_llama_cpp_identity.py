from __future__ import annotations

import pytest

from tools.llama_cpp_identity import (
    LlamaCppIdentityError,
    parse_cli_build_identity,
    parse_props_build_info,
    verify_cli_against_props,
    verify_props_build_info,
)


REVISION = "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"


def test_real_2956_cli_representation_matches_props() -> None:
    observed = parse_cli_build_identity(
        "version: 0.4.0-dev (build 10874, commit e2d2c0d6a)"
    )
    assert observed.build_number == 10874
    assert observed.commit == "e2d2c0d6a"
    assert verify_cli_against_props(
        cli_output="version: 0.4.0-dev (build 10874, commit e2d2c0d6a)",
        expected_build_info="b10874-e2d2c0d6a",
        upstream_revision=REVISION,
    ) == observed


def test_cli_identity_accepts_stderr_and_ignores_formatting() -> None:
    output = "warning\nversion: 0.4.0-dev (build 10874, commit E2D2C0D6A)\n"
    assert parse_cli_build_identity(output).source == "cli"


@pytest.mark.parametrize(
    "value",
    [
        "b10874-123456",
        "build 10874, commit e2d2c0d6a",
    ],
)
def test_identity_rejects_structurally_wrong_values(value: str) -> None:
    with pytest.raises(LlamaCppIdentityError):
        parse_props_build_info(value)


def test_cli_identity_rejects_build_or_commit_drift() -> None:
    with pytest.raises(LlamaCppIdentityError, match="build number"):
        verify_cli_against_props(
            cli_output="version: 0.4.0-dev (build 10873, commit e2d2c0d6a)",
            expected_build_info="b10874-e2d2c0d6a",
            upstream_revision=REVISION,
        )
    with pytest.raises(LlamaCppIdentityError, match="commit"):
        verify_cli_against_props(
            cli_output="version: 0.4.0-dev (build 10874, commit deadbee)",
            expected_build_info="b10874-e2d2c0d6a",
            upstream_revision=REVISION,
        )


def test_live_props_requires_exact_frozen_build() -> None:
    assert verify_props_build_info(
        actual_build_info="b10874-e2d2c0d6a",
        expected_build_info="b10874-e2d2c0d6a",
        upstream_revision=REVISION,
    ).source == "/props"
    with pytest.raises(LlamaCppIdentityError):
        verify_props_build_info(
            actual_build_info="b10874-e2d2c0d6b",
            expected_build_info="b10874-e2d2c0d6a",
            upstream_revision=REVISION,
        )
