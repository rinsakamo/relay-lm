from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from relaylm.cli import run_cli


def _character(root: Path) -> Path:
    root.mkdir()
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: summary-safety\n  name: Summary Safety\n",
        encoding="utf-8",
    )
    (root / "SOUL.md").write_text("A valid test identity.\n", encoding="utf-8")
    return root


@pytest.mark.parametrize("command", ["doctor", "serve"])
def test_human_operator_summary_escapes_control_characters_in_metadata(
    tmp_path: Path,
    command: str,
) -> None:
    character = _character(tmp_path / "character\nforged-status: ok\x1b[2J")
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        [
            command,
            "--profile-name",
            "summary-safety",
            "--profile-root",
            str(character),
            "--provider-base-url",
            "http://127.0.0.1:1234/v1",
            "--provider-model",
            "model-safe",
        ],
        environ={},
        stdout=stdout,
        stderr=stderr,
        serve_runner=lambda app, *, host, port: None,
    )

    assert code == 0
    summary = stdout.getvalue()
    assert "\x1b" not in summary
    assert "\nforged-status: ok" not in summary
    assert r"character\x0aforged-status: ok\x1b[2J" in summary
    assert stderr.getvalue() == ""
