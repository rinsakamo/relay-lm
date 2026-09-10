from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

import tools.v1_llama_cpp_controller_preflight as preflight


def test_import_module_without_main_never_calls_main() -> None:
    calls = 0

    def fake_main() -> int:
        nonlocal calls
        calls += 1
        return 0

    module = SimpleNamespace(main=fake_main)

    def importer(name: str):
        assert name == "relaylm.example_transaction"
        return module

    observed = preflight.import_module_without_main(
        "relaylm.example_transaction",
        importer=importer,
    )

    assert observed is module
    assert calls == 0


def test_missing_runtime_import_is_pre_wrapper_block() -> None:
    def importer(name: str):
        raise ModuleNotFoundError(f"No module named {name!r}")

    with pytest.raises(
        preflight.LlamaCppControllerPreflightError,
        match="module import failed before wrapper consumption",
    ):
        preflight.import_module_without_main("httpx", importer=importer)


def test_one_shot_command_uses_selected_preflight_interpreter() -> None:
    executable = "/tmp/relaylm-preflight/venv/bin/python3"

    assert preflight.one_shot_command(
        "tools.v1_stage_r_llama_cpp_epistemic_formation_wsl",
        executable=executable,
    ) == [
        executable,
        "-m",
        "tools.v1_stage_r_llama_cpp_epistemic_formation_wsl",
    ]


def test_base_interpreter_is_rejected_before_wrapper(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setattr(sys, "prefix", "/usr")
    monkeypatch.setattr(sys, "base_prefix", "/usr")

    with pytest.raises(
        preflight.LlamaCppControllerPreflightError,
        match="prepared virtual environment",
    ):
        preflight._require_repo_external_venv(repo_root)


def test_virtual_environment_inside_repo_is_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    environment = repo_root / ".venv"
    environment.mkdir()
    monkeypatch.setattr(sys, "prefix", str(environment))
    monkeypatch.setattr(sys, "base_prefix", "/usr")

    with pytest.raises(
        preflight.LlamaCppControllerPreflightError,
        match="outside the repository",
    ):
        preflight._require_repo_external_venv(repo_root)


def test_cli_blocked_result_spends_no_one_shot_counts(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    def fail_validation(**kwargs):
        raise preflight.LlamaCppControllerPreflightError("missing runtime closure")

    monkeypatch.setattr(preflight, "validate_controller_environment", fail_validation)

    result = preflight.main(
        [
            "--repo-root",
            str(tmp_path),
            "--expected-head",
            "a" * 40,
            "--expected-tree",
            "b" * 40,
            "--inner-module",
            "relaylm.actual_model_stage_r_llama_cpp_epistemic_formation_transaction",
            "--wrapper-module",
            "tools.v1_stage_r_llama_cpp_epistemic_formation_wsl",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert result == 2
    assert payload["classification"] == preflight.BLOCKED_CLASSIFICATION
    assert payload["controller_restartable"] is True
    assert payload["wrapper_consumed"] is False
    assert payload["server_calls"] == 0
    assert payload["host_calls"] == 0
    assert payload["provider_calls"] == 0
    assert payload["semantic_calls"] == 0


def test_project_python_floor_tracks_current_pyproject() -> None:
    repo_root = Path(preflight.__file__).resolve().parents[1]

    assert preflight._project_python_floor(repo_root) == (3, 12)
