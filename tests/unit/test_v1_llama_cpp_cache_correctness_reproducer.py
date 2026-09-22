from __future__ import annotations

from pathlib import Path

import tools.relay_physical_run as runner
import tools.v1_installed_llama_cpp_cache_on_experiment as experiment
import tools.v1_llama_cpp_cache_correctness_reproducer as reproducer


REPO_ROOT = Path(__file__).parents[2]


def test_cache_correctness_reproducer_is_a_distinct_physical_target() -> None:
    targets = runner._load_targets(REPO_ROOT)

    historical = targets[experiment.EXPERIMENT_TARGET_NAME]
    current = targets[reproducer.REPRODUCER_TARGET_NAME]

    assert historical.module == "tools.v1_installed_llama_cpp_cache_on_experiment"
    assert current.module == "tools.v1_llama_cpp_cache_correctness_reproducer"
    assert current.branch == "v1"
    assert current.required_distributions == ("build", "httpx")


def test_reproducer_delegates_to_cache_treatment_with_fresh_target_identity(
    monkeypatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_run(argv, *, target_name):
        observed["argv"] = argv
        observed["target_name"] = target_name
        return 17

    monkeypatch.setattr(experiment, "run_cache_on_experiment", fake_run)

    assert reproducer.main(["--repo-root", "."]) == 17
    assert observed == {
        "argv": ["--repo-root", "."],
        "target_name": reproducer.REPRODUCER_TARGET_NAME,
    }
