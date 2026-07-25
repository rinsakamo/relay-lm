from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from relaylm_ci_changed_matrix import (  # noqa: E402
    GROUPS,
    RUNTIME_TIMEOUTS,
    UI_KINDS,
    validate_matrix_coverage,
)


def _groups() -> dict[str, dict[str, object]]:
    return {workflow: dict(entries) for workflow, entries in GROUPS.items()}


def test_current_smoke_groups_have_exact_matrix_coverage() -> None:
    validate_matrix_coverage()


def test_runtime_group_without_timeout_fails_closed() -> None:
    runtime_timeouts = dict(RUNTIME_TIMEOUTS)
    runtime_timeouts.pop("subjective_mem_lifecycle")

    with pytest.raises(ValueError, match="runtime matrix coverage drift"):
        validate_matrix_coverage(runtime_timeouts=runtime_timeouts)


def test_unknown_runtime_timeout_fails_closed() -> None:
    runtime_timeouts = dict(RUNTIME_TIMEOUTS)
    runtime_timeouts["unknown_runtime_group"] = 30

    with pytest.raises(ValueError, match="unknown_runtime_group"):
        validate_matrix_coverage(runtime_timeouts=runtime_timeouts)


def test_ui_group_without_partition_fails_closed() -> None:
    ui_kinds = deepcopy(UI_KINDS)
    ui_kinds["mixed"].pop("lifecycle_visibility")

    with pytest.raises(ValueError, match="lifecycle_visibility"):
        validate_matrix_coverage(ui_kinds=ui_kinds)


def test_ui_group_in_multiple_partitions_fails_closed() -> None:
    ui_kinds = deepcopy(UI_KINDS)
    ui_kinds["python"]["lifecycle_visibility"] = 45

    with pytest.raises(ValueError, match="duplicates=.*lifecycle_visibility"):
        validate_matrix_coverage(ui_kinds=ui_kinds)


def test_unknown_ui_group_and_kind_fail_closed() -> None:
    ui_kinds = deepcopy(UI_KINDS)
    ui_kinds["other"] = {"unknown_ui_group": 30}

    with pytest.raises(ValueError, match="unknown_kinds=.*other"):
        validate_matrix_coverage(ui_kinds=ui_kinds)


@pytest.mark.parametrize(
    ("workflow", "group", "timeout"),
    [
        ("runtime", "subjective_mem_lifecycle", 0),
        ("runtime", "subjective_mem_lifecycle", True),
        ("ui", "lifecycle_visibility", -1),
    ],
)
def test_non_positive_or_boolean_timeouts_fail_closed(
    workflow: str,
    group: str,
    timeout: object,
) -> None:
    runtime_timeouts = dict(RUNTIME_TIMEOUTS)
    ui_kinds = deepcopy(UI_KINDS)
    if workflow == "runtime":
        runtime_timeouts[group] = timeout  # type: ignore[assignment]
    else:
        ui_kinds["mixed"][group] = timeout  # type: ignore[assignment]

    with pytest.raises(ValueError, match="invalid_timeouts"):
        validate_matrix_coverage(
            groups=_groups(),
            runtime_timeouts=runtime_timeouts,
            ui_kinds=ui_kinds,
        )
