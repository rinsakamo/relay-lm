from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

import tools.relay_physical_run as runner
from tools.relay_physical_env import PhysicalEnvironmentIdentity


def _write_registry(root: Path, *, engine: str = "llama.cpp") -> None:
    path = root / ".ai" / "physical" / "llama_cpp_targets.json"
    path.parent.mkdir(parents=True)
    (root / ".ai" / "physical" / "python_environment_policy.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "python": {
                    "implementation": "CPython",
                    "major": 3,
                    "minor": 12,
                },
                "requirements": ["httpx>=0.28"],
            }
        ),
        encoding="utf-8",
    )
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "engine": engine,
                "resource_key": "llama-cpp:local-gpu",
                "targets": {
                    "demo": {
                        "branch": "v2",
                        "module": "tools.demo_target",
                        "description": "demo target",
                        "required_distributions": [],
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def _environment(root: Path, *, fingerprint: str = "fingerprint-a") -> PhysicalEnvironmentIdentity:
    python = str(Path(runner.sys.executable).absolute())
    return PhysicalEnvironmentIdentity(
        home=root / "physical-home",
        manifest_path=root / "physical-home" / "python-environment.json",
        python_executable=python,
        python_version=runner.sys.version,
        implementation="cpython",
        policy_sha256="policy-a",
        distribution_fingerprint=fingerprint,
    )


def test_all_registered_target_requirements_are_policy_constructible() -> None:
    targets = runner._load_targets(Path(__file__).parents[2])

    assert runner._missing_policy_distributions(
        Path(__file__).parents[2], targets
    ) == ()


def test_physical_policy_covers_no_isolation_build_requirements() -> None:
    root = Path(__file__).parents[2]
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    build_requirements = pyproject["build-system"]["requires"]
    assert isinstance(build_requirements, list)
    assert all(isinstance(item, str) and item for item in build_requirements)

    required_for_no_isolation = {"build"} | {
        runner._requirement_distribution_name(requirement)
        for requirement in build_requirements
    }
    policy = runner._load_policy(root)
    policy_requirements = policy["requirements"]
    assert isinstance(policy_requirements, list)
    guaranteed = {
        runner._requirement_distribution_name(requirement)
        for requirement in policy_requirements
    }

    assert required_for_no_isolation <= guaranteed


def _stub_prepare_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    fingerprint: str = "fingerprint-a",
) -> None:
    monkeypatch.setattr(
        runner,
        "_environment_identity",
        lambda root: _environment(tmp_path, fingerprint=fingerprint),
    )
    monkeypatch.setattr(runner, "_repo_identity", lambda root: ("a" * 40, "b" * 40))
    monkeypatch.setattr(runner, "_current_branch", lambda root: "infra/demo")
    monkeypatch.setattr(
        runner,
        "_remote_head",
        lambda root, branch, required: "c" * 40 if branch == "v2" else "a" * 40,
    )
    monkeypatch.setattr(runner, "_require_base_is_ancestor", lambda root, head: None)
    monkeypatch.setattr(runner, "_require_distributions", lambda names: None)
    monkeypatch.setattr(
        runner,
        "_module_origin",
        lambda module, root: str(root / "tools" / "demo_target.py"),
    )


def test_registry_rejects_non_llama_cpp_engine(tmp_path: Path) -> None:
    _write_registry(tmp_path, engine="other")
    with pytest.raises(runner.RelayPhysicalRunError, match="llama.cpp"):
        runner._load_targets(tmp_path)


def test_prepare_run_builds_persistent_python_module_command_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_registry(tmp_path)
    _stub_prepare_dependencies(tmp_path, monkeypatch)

    prepared = runner.prepare_run(
        repo_root=tmp_path,
        target_name="demo",
        target_args=("--sample", "1"),
    )

    assert prepared.command()[0] == _environment(tmp_path).python_executable
    assert prepared.command()[1:3] == ["-m", "tools.demo_target"]
    assert prepared.command()[3:] == ["--sample", "1"]
    assert prepared.environment_fingerprint == "fingerprint-a"


def test_prepare_run_rejects_remote_checkout_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_registry(tmp_path)
    monkeypatch.setattr(
        runner,
        "_environment_identity",
        lambda root: _environment(tmp_path),
    )
    monkeypatch.setattr(runner, "_repo_identity", lambda root: ("a" * 40, "b" * 40))
    monkeypatch.setattr(runner, "_current_branch", lambda root: "infra/demo")
    monkeypatch.setattr(
        runner,
        "_remote_head",
        lambda root, branch, required: "c" * 40 if branch == "v2" else "d" * 40,
    )
    monkeypatch.setattr(runner, "_require_base_is_ancestor", lambda root, head: None)

    with pytest.raises(
        runner.RelayPhysicalRunError, match="fresh remote branch head"
    ):
        runner.prepare_run(repo_root=tmp_path, target_name="demo")


def test_required_distribution_absence_blocks_before_queue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_registry(tmp_path)
    registry = json.loads(
        (tmp_path / ".ai" / "physical" / "llama_cpp_targets.json").read_text()
    )
    registry["targets"]["demo"]["required_distributions"] = ["build"]
    (tmp_path / ".ai" / "physical" / "llama_cpp_targets.json").write_text(
        json.dumps(registry), encoding="utf-8"
    )
    _stub_prepare_dependencies(tmp_path, monkeypatch)

    with pytest.raises(
        runner.RelayPhysicalRunError,
        match="not guaranteed by the persistent Python policy",
    ):
        runner.prepare_run(repo_root=tmp_path, target_name="demo")


def test_missing_runtime_distribution_blocks_before_queue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_registry(tmp_path)
    registry = json.loads(
        (tmp_path / ".ai" / "physical" / "llama_cpp_targets.json").read_text()
    )
    registry["targets"]["demo"]["required_distributions"] = ["httpx"]
    (tmp_path / ".ai" / "physical" / "llama_cpp_targets.json").write_text(
        json.dumps(registry), encoding="utf-8"
    )
    _stub_prepare_dependencies(tmp_path, monkeypatch)
    monkeypatch.setattr(
        runner,
        "_require_distributions",
        lambda names: (_ for _ in ()).throw(
            runner.RelayPhysicalRunError(
                "required runtime distributions are missing: httpx"
            )
        ),
    )

    with pytest.raises(
        runner.RelayPhysicalRunError,
        match="required runtime distributions are missing",
    ):
        runner.prepare_run(repo_root=tmp_path, target_name="demo")


def test_required_distribution_presence_passes_preparation_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_registry(tmp_path)
    registry = json.loads(
        (tmp_path / ".ai" / "physical" / "llama_cpp_targets.json").read_text()
    )
    registry["targets"]["demo"]["required_distributions"] = ["httpx"]
    (tmp_path / ".ai" / "physical" / "llama_cpp_targets.json").write_text(
        json.dumps(registry), encoding="utf-8"
    )
    _stub_prepare_dependencies(tmp_path, monkeypatch)
    checked: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        runner,
        "_require_distributions",
        lambda names: checked.append(tuple(names)),
    )

    prepared = runner.prepare_run(repo_root=tmp_path, target_name="demo")

    assert prepared.target.required_distributions == ("httpx",)
    assert checked == [("httpx",)]


def test_final_gate_blocks_if_protected_branch_advanced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = runner.TargetSpec(
        name="demo",
        module="tools.demo_target",
        branch="v2",
        description="demo",
        required_distributions=(),
    )
    prepared = runner.PreparedRun(
        target=target,
        repo_root=tmp_path,
        head="a" * 40,
        tree="b" * 40,
        checkout_branch="infra/demo",
        base_remote_head="c" * 40,
        checkout_remote_head="a" * 40,
        python_executable=_environment(tmp_path).python_executable,
        environment_manifest=str(_environment(tmp_path).manifest_path),
        environment_policy_sha256="policy-a",
        environment_fingerprint="fingerprint-a",
        module_origin=str(tmp_path / "tools" / "demo_target.py"),
        target_args=(),
    )
    monkeypatch.setattr(
        runner,
        "_environment_identity",
        lambda root: _environment(tmp_path),
    )
    monkeypatch.setattr(runner, "_repo_identity", lambda root: ("a" * 40, "b" * 40))
    monkeypatch.setattr(
        runner,
        "_remote_head",
        lambda root, branch, required: "e" * 40 if branch == "v2" else "a" * 40,
    )
    monkeypatch.setattr(runner, "_require_distributions", lambda names: None)
    monkeypatch.setattr(
        runner,
        "_module_origin",
        lambda module, root: str(root / "tools" / "demo_target.py"),
    )

    with pytest.raises(runner.RelayPhysicalRunError, match="advanced while waiting"):
        runner.final_pre_invoke_gate(prepared)


def test_final_gate_blocks_if_persistent_environment_drifted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = runner.TargetSpec(
        name="demo",
        module="tools.demo_target",
        branch="v2",
        description="demo",
        required_distributions=(),
    )
    prepared = runner.PreparedRun(
        target=target,
        repo_root=tmp_path,
        head="a" * 40,
        tree="b" * 40,
        checkout_branch="infra/demo",
        base_remote_head="c" * 40,
        checkout_remote_head="a" * 40,
        python_executable=_environment(tmp_path).python_executable,
        environment_manifest=str(_environment(tmp_path).manifest_path),
        environment_policy_sha256="policy-a",
        environment_fingerprint="fingerprint-a",
        module_origin=str(tmp_path / "tools" / "demo_target.py"),
        target_args=(),
    )
    monkeypatch.setattr(
        runner,
        "_environment_identity",
        lambda root: _environment(tmp_path, fingerprint="fingerprint-b"),
    )

    with pytest.raises(
        runner.RelayPhysicalRunError, match="distributions drifted"
    ):
        runner.final_pre_invoke_gate(prepared)


def test_final_gate_accepts_present_required_distribution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = runner.TargetSpec(
        name="demo",
        module="tools.demo_target",
        branch="v2",
        description="demo",
        required_distributions=("httpx",),
    )
    environment = _environment(tmp_path)
    prepared = runner.PreparedRun(
        target=target,
        repo_root=tmp_path,
        head="a" * 40,
        tree="b" * 40,
        checkout_branch="infra/demo",
        base_remote_head="c" * 40,
        checkout_remote_head="a" * 40,
        python_executable=environment.python_executable,
        environment_manifest=str(environment.manifest_path),
        environment_policy_sha256="policy-a",
        environment_fingerprint="fingerprint-a",
        module_origin=str(tmp_path / "tools" / "demo_target.py"),
        target_args=(),
    )
    checked: list[tuple[str, ...]] = []
    monkeypatch.setattr(runner, "_environment_identity", lambda root: environment)
    monkeypatch.setattr(runner, "_repo_identity", lambda root: ("a" * 40, "b" * 40))
    monkeypatch.setattr(
        runner,
        "_remote_head",
        lambda root, branch, required: "c" * 40 if branch == "v2" else "a" * 40,
    )
    monkeypatch.setattr(
        runner,
        "_require_distributions",
        lambda names: checked.append(tuple(names)),
    )
    monkeypatch.setattr(
        runner,
        "_module_origin",
        lambda module, root: str(root / "tools" / "demo_target.py"),
    )

    runner.final_pre_invoke_gate(prepared)

    assert checked == [("httpx",)]


def test_child_pythonpath_is_exact_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTHONPATH", "/foreign/path")
    runner._prepare_child_environment(tmp_path)
    assert runner.os.environ["PYTHONPATH"] == runner.os.pathsep.join(
        (str(tmp_path), str(tmp_path / "src"))
    )
    assert runner.os.environ["PYTHONNOUSERSITE"] == "1"
