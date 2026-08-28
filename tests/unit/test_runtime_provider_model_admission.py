from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from relaylm.cli import run_cli


def _character(root: Path) -> Path:
    root.mkdir()
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: model-admission\n  name: Model Admission\n",
        encoding="utf-8",
    )
    (root / "SOUL.md").write_text("A valid test identity.\n", encoding="utf-8")
    return root


@pytest.mark.parametrize("command", ["doctor", "serve"])
@pytest.mark.parametrize(
    "model",
    [
        "model\nforged-status: ok",
        "model\x1b[2J",
        "model\x7fforged-status-ok",
    ],
)
def test_operator_rejects_provider_model_with_ascii_control_before_success(
    tmp_path: Path,
    command: str,
    model: str,
) -> None:
    character = _character(tmp_path / "character")
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        [
            command,
            "--profile-name",
            "model-admission",
            "--profile-root",
            str(character),
            "--provider-base-url",
            "http://127.0.0.1:1234/v1",
            "--provider-model",
            model,
        ],
        environ={},
        stdout=stdout,
        stderr=stderr,
        serve_runner=lambda app, *, host, port: None,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    error = stderr.getvalue()
    assert "provider_invalid: provider.model" in error
    assert "control" in error.lower()
    assert model not in error
