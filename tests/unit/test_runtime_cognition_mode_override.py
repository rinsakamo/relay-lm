from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest

from relaylm.cli import run_cli
from relaylm.cognitive import CognitionExecutionMode
from relaylm.runtime_config import ConfigSource, RuntimeConfigErrorCode
from relaylm.runtime_config_loader import (
    RuntimeConfigOverrides,
    RuntimeConfigResolutionError,
    resolve_runtime_config,
)


def _write_runtime(path: Path, character: Path, *, mode: str = "auto") -> Path:
    path.write_text(
        f"""\
format_version: 1
character:
  directory: {character}
provider:
  adapter: openai_compatible
  base_url: http://127.0.0.1:1234/v1
  model: test-model
runtime:
  cognition:
    mode: {mode}
""",
        encoding="utf-8",
    )
    return path


def _character(root: Path) -> Path:
    root.mkdir()
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: mode-test\n  name: Mode Test\n",
        encoding="utf-8",
    )
    (root / "SOUL.md").write_text("A valid mode test identity.\n", encoding="utf-8")
    return root


def _required_env() -> dict[str, str]:
    return {
        "RELAYLM_CHARACTER_DIR": "/characters/relm",
        "RELAYLM_PROVIDER_BASE_URL": "http://127.0.0.1:1234/v1",
        "RELAYLM_PROVIDER_MODEL": "model-id",
    }


def test_cognition_mode_environment_override_has_env_provenance() -> None:
    environ = _required_env()
    environ["RELAYLM_COGNITION_MODE"] = "single_pass"

    resolved = resolve_runtime_config(environ=environ)

    assert resolved.config.runtime.cognition.mode is CognitionExecutionMode.SINGLE_PASS
    assert resolved.source_for("runtime.cognition.mode") is ConfigSource.ENV


def test_cognition_mode_cli_override_beats_environment_and_file(tmp_path: Path) -> None:
    path = _write_runtime(tmp_path / "runtime.yaml", Path("/characters/relm"))

    resolved = resolve_runtime_config(
        config_path=path,
        overrides=RuntimeConfigOverrides(cognition_mode="single_pass"),
        environ={"RELAYLM_COGNITION_MODE": "two_pass"},
    )

    assert resolved.config.runtime.cognition.mode is CognitionExecutionMode.SINGLE_PASS
    assert resolved.source_for("runtime.cognition.mode") is ConfigSource.CLI


def test_invalid_cognition_mode_environment_override_fails_closed() -> None:
    environ = _required_env()
    environ["RELAYLM_COGNITION_MODE"] = "sometimes"

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(environ=environ)

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_VALUE
    assert caught.value.field == "runtime.cognition.mode"


def test_doctor_accepts_named_cognition_mode_cli_override(tmp_path: Path) -> None:
    character = _character(tmp_path / "character")
    config = _write_runtime(tmp_path / "runtime.yaml", character, mode="two_pass")
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        [
            "doctor",
            "--config",
            str(config),
            "--cognition-mode",
            "single_pass",
            "--json",
        ],
        environ={"RELAYLM_COGNITION_MODE": "two_pass"},
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 0
    assert stderr.getvalue() == ""
    report = json.loads(stdout.getvalue())
    assert report["effective_config"]["values"]["runtime.cognition.mode"] == {
        "value": "single_pass",
        "source": "cli",
    }
