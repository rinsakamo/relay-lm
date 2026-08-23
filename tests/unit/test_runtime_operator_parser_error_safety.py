from __future__ import annotations

from io import StringIO

from relaylm.cli import run_cli


def test_argument_parser_errors_escape_control_characters_in_user_tokens() -> None:
    unsafe_argument = "--unknown\nforged-error: ok\x1b[2J"
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        ["doctor", unsafe_argument],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    error = stderr.getvalue()
    assert "\x1b" not in error
    assert "\nforged-error: ok" not in error
    assert r"--unknown\x0aforged-error: ok\x1b[2J" in error
