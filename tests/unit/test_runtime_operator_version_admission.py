from __future__ import annotations

from io import StringIO

from relaylm.cli import RELAYLM_VERSION, run_cli


def test_version_standalone_preserves_success_output() -> None:
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        ["--version"],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 0
    assert stdout.getvalue() == f"relaylm {RELAYLM_VERSION}\n"
    assert stderr.getvalue() == ""


def test_version_rejects_trailing_unsupported_argv_before_success() -> None:
    stdout = StringIO()
    stderr = StringIO()
    forged = "--unknown\nforged-status: ok\x1b[2J"

    code = run_cli(
        ["--version", forged],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    error = stderr.getvalue()
    assert "relaylm: error:" in error
    assert "--unknown" in error
    assert forged not in error
    assert "\x1b" not in error
    assert error.count("\n") == 2
    assert "\\x1b" in error
