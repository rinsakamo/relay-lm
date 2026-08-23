from __future__ import annotations

from io import StringIO

import pytest

from relaylm.cli import run_cli
from relaylm.runtime_config import RUNTIME_CONFIG_PATH_ENV


@pytest.mark.parametrize("command", ["doctor", "serve"])
@pytest.mark.parametrize("source", ["cli", "env"])
def test_operator_maps_config_home_expansion_failure_to_typed_discovery_error(
    command: str,
    source: str,
) -> None:
    selected = "~relaylm-rq16-user-that-must-not-exist/runtime.yaml"
    argv = [command]
    environ: dict[str, str] = {}
    if source == "cli":
        argv.extend(["--config", selected])
    else:
        environ[RUNTIME_CONFIG_PATH_ENV] = selected
    stdout = StringIO()
    stderr = StringIO()

    code = run_cli(
        argv,
        environ=environ,
        stdout=stdout,
        stderr=stderr,
        serve_runner=lambda app, *, host, port: None,
    )

    assert code == 2
    assert stdout.getvalue() == ""
    error = stderr.getvalue()
    assert "discovery_error: config_path" in error
    assert "home" in error.lower()
    assert selected not in error
