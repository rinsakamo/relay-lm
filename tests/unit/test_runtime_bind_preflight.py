from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from relaylm.cli import run_cli


def _character(root: Path) -> Path:
    root.mkdir()
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: bind-preflight-test\n  name: Bind Preflight Test\n",
        encoding="utf-8",
    )
    (root / "SOUL.md").write_text("A valid test identity.\n", encoding="utf-8")
    return root


def _profile_args(root: Path) -> list[str]:
    return ["--profile-name", "bind-preflight-test", "--profile-root", str(root)]


def test_doctor_rejects_obviously_malformed_bind_host_before_startup(
    tmp_path: Path,
) -> None:
    character = _character(tmp_path / "character")
    config = tmp_path / "runtime.yaml"
    config.write_text(
        "\n".join(
            [
                "format_version: 1",
                "profiles:",
                "  - name: bind-preflight-test",
                f"    root: {character}",
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


@pytest.mark.parametrize("host", ["local\x1bhost", "local\x7fhost"])
def test_doctor_rejects_bind_host_with_ascii_control_before_startup(
    tmp_path: Path,
    host: str,
) -> None:
    character = _character(tmp_path / "character")
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        [
            "doctor",
            *_profile_args(character),
            "--provider-base-url",
            "http://127.0.0.1:1234/v1",
            "--provider-model",
            "test-model",
            "--host",
            host,
            "--json",
        ],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    assert "invalid_value: server.host" in stderr.getvalue()
    assert "control" in stderr.getvalue().lower()


@pytest.mark.parametrize("host", ["127.0.0.1:8090", "localhost:8090"])
def test_doctor_rejects_bind_host_with_embedded_port_before_startup(
    tmp_path: Path,
    host: str,
) -> None:
    character = _character(tmp_path / "character")
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        [
            "doctor",
            *_profile_args(character),
            "--provider-base-url",
            "http://127.0.0.1:1234/v1",
            "--provider-model",
            "test-model",
            "--host",
            host,
            "--json",
        ],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    assert "invalid_value: server.host" in stderr.getvalue()
    assert "port" in stderr.getvalue().lower()


def test_doctor_preserves_valid_ipv6_bind_host(
    tmp_path: Path,
) -> None:
    character = _character(tmp_path / "character")
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        [
            "doctor",
            *_profile_args(character),
            "--provider-base-url",
            "http://127.0.0.1:1234/v1",
            "--provider-model",
            "test-model",
            "--host",
            "::1",
            "--json",
        ],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 0
    assert stderr.getvalue() == ""
    assert '"server.host":{"source":"cli","value":"::1"}' in stdout.getvalue()


def test_doctor_rejects_obviously_malformed_provider_host_before_startup(
    tmp_path: Path,
) -> None:
    character = _character(tmp_path / "character")
    config = tmp_path / "runtime.yaml"
    config.write_text(
        "\n".join(
            [
                "format_version: 1",
                "profiles:",
                "  - name: bind-preflight-test",
                f"    root: {character}",
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


@pytest.mark.parametrize(
    "base_url",
    ["http://127.0.0.1:0/v1", "http://[::1]:0/v1"],
)
def test_doctor_rejects_provider_url_port_zero_before_startup(
    tmp_path: Path,
    base_url: str,
) -> None:
    character = _character(tmp_path / "character")
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        [
            "doctor",
            *_profile_args(character),
            "--provider-base-url",
            base_url,
            "--provider-model",
            "test-model",
            "--json",
        ],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    assert "provider_invalid: provider.base_url" in stderr.getvalue()
    assert "port" in stderr.getvalue().lower()


@pytest.mark.parametrize(
    "base_url",
    [
        " http://127.0.0.1:1234/v1",
        "http://127.0.0.1:1234/v1 ",
        "http://127.0.0.1:1234/v1\t",
    ],
)
def test_doctor_rejects_provider_url_literal_whitespace_before_startup(
    tmp_path: Path,
    base_url: str,
) -> None:
    character = _character(tmp_path / "character")
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        [
            "doctor",
            *_profile_args(character),
            "--provider-base-url",
            base_url,
            "--provider-model",
            "test-model",
            "--json",
        ],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    assert "provider_invalid: provider.base_url" in stderr.getvalue()
    assert "whitespace" in stderr.getvalue().lower()
