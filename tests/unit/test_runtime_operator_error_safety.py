from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from relaylm.cli import run_cli


@pytest.mark.parametrize("command", ["doctor", "serve"])
def test_runtime_errors_escape_control_characters_in_user_supplied_metadata(
    tmp_path: Path,
    command: str,
) -> None:
    config_path = str(tmp_path / "missing") + "\nforged-error: ok\x1b[2J"
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        [command, "--config", config_path],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    error = stderr.getvalue()
    assert "\x1b" not in error
    assert "\nforged-error: ok" not in error
    assert r"\x0aforged-error: ok\x1b[2J" in error
    assert error.count("\n") == 1
