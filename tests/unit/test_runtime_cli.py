from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest

from relaylm import __version__
from relaylm.cli import run_cli
from relaylm.runtime_config import RuntimeConfigErrorCode
from relaylm.runtime_preflight import RuntimePreflightError


def _character(root: Path) -> Path:
    root.mkdir()
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: cli-test\n  name: CLI Test\n",
        encoding="utf-8",
    )
    (root / "SOUL.md").write_text("A valid test identity.\n", encoding="utf-8")
    return root


def _runtime_config(path: Path, character: Path, *, host: str = "127.0.0.1") -> Path:
    path.write_text(
        "\n".join(
            [
                "format_version: 1",
                "profiles:",
                "  - name: cli-test",
                f"    root: {character}",
                "provider:",
                "  adapter: openai_compatible",
                "  base_url: http://127.0.0.1:1234/v1",
                "  model: test-model",
                "server:",
                f"  host: {host}",
                "  port: 8090",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_version_is_available_without_runtime_configuration() -> None:
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(["--version"], environ={}, stdout=stdout, stderr=stderr)

    assert code == 0
    assert stdout.getvalue().strip() == f"relaylm {__version__}"
    assert stderr.getvalue() == ""


def test_doctor_json_is_non_secret_and_reports_effective_sources(tmp_path: Path) -> None:
    character = _character(tmp_path / "character")
    config = _runtime_config(tmp_path / "runtime.yaml", character)
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        ["doctor", "--config", str(config), "--json"],
        environ={"RELAYLM_PROVIDER_API_KEY": "never-print-this"},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 0
    report = json.loads(stdout.getvalue())
    assert report["status"] == "ok"
    assert report["checks"] == {
        "configuration": "ok",
        "persistence": "ok",
        "profiles": "ok",
        "provider": "ok",
        "runtime_assembly": "ok",
    }
    assert report["effective_config"]["values"]["provider.model"] == {
        "value": "test-model",
        "source": "config_file",
    }
    assert report["effective_config"]["values"]["profiles.0.name"] == {
        "value": "cli-test",
        "source": "config_file",
    }
    rendered = stdout.getvalue() + stderr.getvalue()
    assert "never-print-this" not in rendered
    assert report["effective_config"]["secrets"]["provider.api_key"]["configured"] is True


def test_doctor_fails_profile_validation_without_mutating_package(tmp_path: Path) -> None:
    character = _character(tmp_path / "character")
    (character / "SOUL.md").write_text("", encoding="utf-8")
    config = _runtime_config(tmp_path / "runtime.yaml", character)
    before = sorted(
        (p.relative_to(character), p.read_bytes())
        for p in character.rglob("*")
        if p.is_file()
    )
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        ["doctor", "--config", str(config)],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    after = sorted(
        (p.relative_to(character), p.read_bytes())
        for p in character.rglob("*")
        if p.is_file()
    )
    assert code == 2
    assert before == after
    assert stdout.getvalue() == ""
    assert "character_invalid" in stderr.getvalue()
    assert "SOUL" not in stderr.getvalue()


def test_doctor_rejects_non_http_provider_url_before_network_use(tmp_path: Path) -> None:
    character = _character(tmp_path / "character")
    config = _runtime_config(tmp_path / "runtime.yaml", character)
    text = config.read_text(encoding="utf-8").replace(
        "http://127.0.0.1:1234/v1", "file:///tmp/provider"
    )
    config.write_text(text, encoding="utf-8")
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        ["doctor", "--config", str(config)],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    assert "provider_invalid" in stderr.getvalue()
    assert "http or https" in stderr.getvalue()


def test_doctor_maps_malformed_provider_url_to_typed_preflight_failure(
    tmp_path: Path,
) -> None:
    character = _character(tmp_path / "character")
    config = _runtime_config(tmp_path / "runtime.yaml", character)
    text = config.read_text(encoding="utf-8").replace(
        "http://127.0.0.1:1234/v1", "http://[::1"
    )
    config.write_text(text, encoding="utf-8")
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        ["doctor", "--config", str(config)],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    assert "provider_invalid: provider.base_url" in stderr.getvalue()


@pytest.mark.parametrize(
    "base_url",
    [
        "http://:1234/v1",
        "http://127.0.0.1:not-a-port/v1",
        "http://127.0.0.1:70000/v1",
    ],
)
def test_doctor_rejects_provider_url_with_invalid_host_or_port(
    tmp_path: Path,
    base_url: str,
) -> None:
    character = _character(tmp_path / "character")
    config = _runtime_config(tmp_path / "runtime.yaml", character)
    text = config.read_text(encoding="utf-8").replace(
        "http://127.0.0.1:1234/v1", base_url
    )
    config.write_text(text, encoding="utf-8")
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        ["doctor", "--config", str(config)],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    assert "provider_invalid: provider.base_url" in stderr.getvalue()


@pytest.mark.parametrize(
    "base_url",
    [
        "http://127.0.0.1:1234/v1?api-version=test",
        "http://127.0.0.1:1234/v1#fragment",
        "http://127.0.0.1:1234/v1?",
        "http://127.0.0.1:1234/v1#",
    ],
)
def test_doctor_rejects_provider_url_that_is_not_a_base_endpoint(
    tmp_path: Path,
    base_url: str,
) -> None:
    character = _character(tmp_path / "character")
    config = _runtime_config(tmp_path / "runtime.yaml", character)
    text = config.read_text(encoding="utf-8").replace(
        "http://127.0.0.1:1234/v1", base_url
    )
    config.write_text(text, encoding="utf-8")
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        ["doctor", "--config", str(config)],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    assert "provider_invalid: provider.base_url" in stderr.getvalue()


def test_named_cli_overrides_win_and_serve_uses_preflighted_runtime(tmp_path: Path) -> None:
    character = _character(tmp_path / "character")
    config = _runtime_config(tmp_path / "runtime.yaml", character)
    stdout = StringIO()
    stderr = StringIO()
    calls: list[tuple[object, str, int]] = []

    def serve_runner(app: object, *, host: str, port: int) -> None:
        calls.append((app, host, port))

    code = run_cli(
        [
            "serve",
            "--config",
            str(config),
            "--provider-model",
            "cli-model",
            "--host",
            "127.0.0.2",
            "--port",
            "9001",
        ],
        environ={"RELAYLM_PROVIDER_MODEL": "env-model"},
        stdout=stdout,
        stderr=stderr,
        serve_runner=serve_runner,
    )

    assert code == 0
    assert len(calls) == 1
    _, host, port = calls[0]
    assert host == "127.0.0.2"
    assert port == 9001
    summary = stdout.getvalue()
    assert "profile: cli-test" in summary
    assert "physical_model=cli-model" in summary
    assert "127.0.0.2:9001" in summary
    assert stderr.getvalue() == ""


def test_cli_has_no_generic_set_override() -> None:
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        ["doctor", "--set", "provider.model=unsafe"],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert "unrecognized arguments: --set" in stderr.getvalue()


def test_cli_maps_typed_preflight_failure_to_exit_two(monkeypatch: pytest.MonkeyPatch) -> None:
    import relaylm.cli as cli

    def fail(*args: object, **kwargs: object) -> object:
        raise RuntimePreflightError(
            RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE,
            field="runtime.cognitive_budget.token_counter.capability",
            message="configured capability is unavailable",
        )

    monkeypatch.setattr(cli, "prepare_runtime", fail)
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        [
            "doctor",
            "--profile-name",
            "relm",
            "--profile-root",
            "/tmp/character",
            "--provider-base-url",
            "http://127.0.0.1:1234/v1",
            "--provider-model",
            "model",
        ],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    assert "capability_unavailable" in stderr.getvalue()
