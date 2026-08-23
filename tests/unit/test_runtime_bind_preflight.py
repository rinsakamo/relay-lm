from __future__ import annotations

from io import StringIO
from pathlib import Path

from relaylm.cli import run_cli


def _character(root: Path) -> Path:
    root.mkdir()
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: bind-preflight-test\n  name: Bind Preflight Test\n",
        encoding="utf-8",
    )
    (root / "SOUL.md").write_text("A valid test identity.\n", encoding="utf-8")
    return root


def test_doctor_rejects_obviously_malformed_bind_host_before_startup(
    tmp_path: Path,
) -> None:
    character = _character(tmp_path / "character")
    config = tmp_path / "runtime.yaml"
    config.write_text(
        "\n".join(
            [
                "format_version: 1",
                "character:",
                f"  directory: {character}",
                "provider:",
                "  adapter: openai_compatible",
                "  base_url: http://127.0.0.1:1234/v1",
                "  model: test-model",
                "server:",
                "  host: invalid bind host /",
                "  port: 8090",
                "",
            ]
        ),
        encoding="utf-8",
    )
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        ["doctor", "--config", str(config), "--json"],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    assert "invalid_value: server.host" in stderr.getvalue()
    assert "bind" in stderr.getvalue().lower()


def test_doctor_rejects_obviously_malformed_provider_host_before_startup(
    tmp_path: Path,
) -> None:
    character = _character(tmp_path / "character")
    config = tmp_path / "runtime.yaml"
    config.write_text(
        "\n".join(
            [
                "format_version: 1",
                "character:",
                f"  directory: {character}",
                "provider:",
                "  adapter: openai_compatible",
                "  base_url: http://invalid host/v1",
                "  model: test-model",
                "server:",
                "  host: 127.0.0.1",
                "  port: 8090",
                "",
            ]
        ),
        encoding="utf-8",
    )
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        ["doctor", "--config", str(config), "--json"],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    assert "provider_invalid: provider.base_url" in stderr.getvalue()
    assert "host" in stderr.getvalue().lower()
