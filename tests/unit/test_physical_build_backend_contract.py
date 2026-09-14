from __future__ import annotations

from pathlib import Path
import tomllib

import tools.relay_physical_run as runner


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
INSTALLED_LLAMA_CPP_TARGET = "v1:installed-llama-cpp"


def test_installed_llama_cpp_target_covers_no_isolation_build_requirements() -> None:
    pyproject = tomllib.loads(
        (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    build_system = pyproject["build-system"]
    build_requirements = build_system["requires"]
    assert isinstance(build_requirements, list)
    assert all(isinstance(item, str) and item for item in build_requirements)

    required_for_no_isolation = {"build"} | {
        runner._requirement_distribution_name(requirement)
        for requirement in build_requirements
    }
    target = runner._load_targets(REPOSITORY_ROOT)[INSTALLED_LLAMA_CPP_TARGET]
    declared = {
        runner._normalize_distribution_name(name)
        for name in target.required_distributions
    }

    assert required_for_no_isolation <= declared
