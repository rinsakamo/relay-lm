from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from relaylm.cli import run_cli


def _character(root: Path) -> Path:
    root.mkdir()
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: backend-summary\n  name: Backend Summary\n",
        encoding="utf-8",
    )
    (root / "SOUL.md").write_text("A valid test identity.\n", encoding="utf-8")
    return root


def _runtime_config(path: Path, character: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "format_version: 1",
                "character:",
                f"  directory: {character}",
                "provider:",
                "  adapter: openai_compatible",
                "  backend: vllm",
                "  base_url: http://127.0.0.1:1234/v1",
                "  model: test-model",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize("command", ["doctor", "serve"])
def test_human_operator_summary_reports_canonical_provider_backend(
    tmp_path: Path,
    command: str,
) -> None:
    character = _character(tmp_path / "character")
    config = _runtime_config(tmp_path / "runtime.yaml", character)
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        [command, "--config", str(config)],
        environ={},
        stdout=stdout,
        stderr=stderr,
        serve_runner=lambda app, *, host, port: None,
    )

    assert code == 0
    assert "provider: openai_compatible backend=vllm model=test-model" in stdout.getvalue()
    assert stderr.getvalue() == ""
