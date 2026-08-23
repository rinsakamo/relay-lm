from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from relaylm.cli import run_cli


@pytest.mark.parametrize("command", ["doctor", "serve"])
def test_operator_duplicate_yaml_key_error_does_not_echo_key_content(
    tmp_path: Path,
    command: str,
) -> None:
    sensitive_key = "never-print-this-secret"
    config = tmp_path / "runtime.yaml"
    config.write_text(
        "\n".join(
            [
                "format_version: 1",
                f'"{sensitive_key}": first',
                f'"{sensitive_key}": second',
                "",
            ]
        ),
        encoding="utf-8",
    )
    stdout = StringIO()
    stderr = StringIO()
    serve_calls: list[object] = []

    code = run_cli(
        [command, "--config", str(config)],
        environ={},
        stdout=stdout,
        stderr=stderr,
        serve_runner=lambda app, *, host, port: serve_calls.append(app),
    )

    assert code == 2
    assert stdout.getvalue() == ""
    assert serve_calls == []
    error = stderr.getvalue()
    assert "parse_error: config_path" in error
    assert "duplicate YAML key is not allowed" in error
    assert sensitive_key not in error
