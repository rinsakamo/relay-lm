from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from relaylm.cli import run_cli


def _character(root: Path) -> Path:
    root.mkdir()
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: utf8-test\n  name: UTF8 Test\n",
        encoding="utf-8",
    )
    (root / "SOUL.md").write_text("A valid test identity.\n", encoding="utf-8")
    return root


def _runtime_config(path: Path, character: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "format_version: 1",
                "profiles:",
                "  - name: utf8-test",
                f"    root: {character}",
                "provider:",
                "  adapter: openai_compatible",
                "  base_url: http://127.0.0.1:1234/v1",
                "  model: test-model",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize("command", ["doctor", "serve"])
@pytest.mark.parametrize(
    "relative_path",
    [
        "config.yaml",
        "SOUL.md",
        "memory/events.jsonl",
        "memory/MEMORY.md",
    ],
)
def test_operator_maps_package_utf8_decode_failure_to_typed_preflight_error(
    tmp_path: Path,
    command: str,
    relative_path: str,
) -> None:
    character = _character(tmp_path / "character")
    target = character / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"\xff")
    config = _runtime_config(tmp_path / "runtime.yaml", character)
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
    assert "character_invalid: profiles[0].root" in error
    assert "invalid or unreadable" in error
    assert "UnicodeDecodeError" not in error
    assert str(target) not in error
