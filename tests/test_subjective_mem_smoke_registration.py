"""Regression coverage for the consolidated Subjective MEM lifecycle boundary."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from relaylm_ci_changed_matrix import RUNTIME_TIMEOUTS, _matrix
from relaylm_ci_consolidated_smoke import COMMANDS, changed_outputs
from relaylm.subjective_mem_reformation import _timestamp


def test_subjective_mem_forget_runtime_change_selects_lifecycle_group() -> None:
    selected = changed_outputs(
        "runtime", ["relaylm/subjective_mem_forget_runtime.py"], False
    )
    assert selected["subjective_mem_lifecycle"] is True
    assert sum(selected.values()) == 1


def test_subjective_mem_pin_runtime_change_selects_lifecycle_group() -> None:
    selected = changed_outputs(
        "runtime", ["relaylm/subjective_mem_pin_runtime.py"], False
    )
    assert selected["subjective_mem_lifecycle"] is True
    assert sum(selected.values()) == 1


def test_subjective_mem_lifecycle_group_is_emitted_in_runtime_matrix() -> None:
    selected = changed_outputs(
        "runtime", ["relaylm/subjective_mem_pin_runtime.py"], False
    )
    matrix = _matrix(selected, RUNTIME_TIMEOUTS)
    assert matrix == {
        "include": [
            {
                "group": "subjective_mem_lifecycle",
                "name": "subjective-mem-lifecycle",
                "timeout": 45,
            }
        ]
    }


def test_subjective_mem_lifecycle_group_runs_regression_and_process_smokes() -> None:
    commands = COMMANDS["runtime"]["subjective_mem_lifecycle"]
    assert [
        "-m",
        "pytest",
        "-q",
        "tests/test_subjective_mem_runtime.py",
        "tests/test_subjective_mem_commit_runtime.py",
        "tests/test_subjective_mem_lifecycle_runtime.py",
        "tests/test_subjective_mem_forget_runtime.py",
        "tests/test_subjective_mem_pin_runtime.py",
    ] in commands
    assert ["scripts/relaylm_lc1a_subjective_mem_correct_smoke.py"] in commands
    assert ["scripts/relaylm_subjective_mem_forget_smoke.py"] in commands
    assert ["scripts/relaylm_subjective_mem_pin_unpin_smoke.py"] in commands


def test_subjective_mem_create_has_one_direct_owner_without_core_bypass() -> None:
    runtime = REPO_ROOT / "relaylm/subjective_mem_runtime.py"
    private_core_name = "_" + "subjective_mem_runtime_core"
    private_core = REPO_ROOT / "relaylm" / f"{private_core_name}.py"
    source = runtime.read_text(encoding="utf-8")

    assert not private_core.exists()
    assert private_core_name not in source
    assert "ContextVar" not in source
    assert "_core._preflight_new_identity" not in source
    assert source.count("check_subjective_mem_reformation_locked") == 2

    references = []
    for root_name in ("relaylm", "scripts", "tests"):
        for path in sorted((REPO_ROOT / root_name).rglob("*.py")):
            if private_core_name in path.read_text(encoding="utf-8"):
                references.append(path.relative_to(REPO_ROOT).as_posix())
    assert references == []


def test_reformation_module_is_the_only_semantic_evaluator_owner() -> None:
    canonical = (
        REPO_ROOT / "relaylm/subjective_mem_reformation.py"
    ).read_text(encoding="utf-8")
    forget_runtime = (
        REPO_ROOT / "relaylm/subjective_mem_forget_runtime.py"
    ).read_text(encoding="utf-8")

    assert canonical.count("def _evaluate_subjective_mem_reformation_locked(") == 1
    assert canonical.count("def check_subjective_mem_reformation(") == 1
    assert canonical.count("def check_subjective_mem_reformation_locked(") == 1
    assert "def check_subjective_mem_reformation(" not in forget_runtime
    assert "class SubjectiveMemReformationCheck" not in forget_runtime
    assert "_valid_tombstone_state" not in forget_runtime
    assert "_valid_tombstone_lineage" not in forget_runtime
    assert "subjective_mem_forget_runtime import" not in canonical


def test_reformation_lineage_timestamp_requires_aware_iso_datetime() -> None:
    assert _timestamp("2026-07-24T01:00:00+00:00") is True
    assert _timestamp("2026-07-24T01:00:00") is False
    assert _timestamp("T") is False
