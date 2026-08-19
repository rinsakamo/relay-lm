from __future__ import annotations

import pytest

from relaylm.cognitive import CognitionExecutionMode


def test_cognition_execution_mode_is_closed_release_vocabulary() -> None:
    assert tuple(mode.value for mode in CognitionExecutionMode) == (
        "single_pass",
        "two_pass",
        "shadow_two_pass",
        "auto",
    )

    with pytest.raises(ValueError):
        CognitionExecutionMode("selective_two_pass")
