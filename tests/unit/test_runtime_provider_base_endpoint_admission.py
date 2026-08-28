from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from relaylm.cli import run_cli


def _character(root: Path) -> Path:
    root.mkdir()
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: provider-base-test\n  name: Provider Base Test\n",
        encoding="utf-8",
    )
    (root / "SOUL.md").write_text("A valid test identity.\n", encoding="utf-8")
    return root


@pytest.mark.parametrize("command", ["doctor", "serve"])
@pytest.mark.parametrize("trailing_slash", [False, True])
def test_operator_rejects_provider_chat_completion_route_as_base_endpoint(
    tmp_path: Path,
    command: str,
    trailing_slash: bool,
) -> None:
    character = _character(tmp_path / "character")
    base_url = "http://127.0.0.1:1234/v1/chat/completions"
    if trailing_slash:
        base_url += "/"
    config = tmp_path / "runtime.yaml"
    config.write_text(
        "\n".join(
            [
                "format_version: 1",
                "profiles:",
                "  - name: provider-base-test",
                f"    root: {character}",
                "provider:",
                "  adapter: openai_compatible",
                f"  base_url: {base_url}",
                "  model: test-model",
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
    assert "provider_invalid: provider.base_url" in error
    assert "base endpoint" in error
