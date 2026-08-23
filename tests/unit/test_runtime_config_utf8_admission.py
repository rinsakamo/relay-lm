from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from relaylm.cli import run_cli


@pytest.mark.parametrize("command", ["doctor", "serve"])
def test_cli_rejects_non_utf8_runtime_config_as_typed_parse_error(
    tmp_path: Path,
    command: str,
) -> None:
    config = tmp_path / "runtime.yaml"
    config.write_bytes(b"format_version: 1\nprovider:\n  model: \xff\n")
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        [command, "--config", str(config)],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    error = stderr.getvalue()
    assert "parse_error: config_path" in error
    assert "UTF-8" in error
