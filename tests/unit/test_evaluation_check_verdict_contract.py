from __future__ import annotations

import pytest

from relaylm.evaluation import EvaluationCheck


def test_evaluation_check_rejects_truthy_non_boolean_verdict() -> None:
    with pytest.raises(TypeError, match="passed must be a bool"):
        EvaluationCheck(
            check_id="synthetic_false_positive",
            boundary="evaluation",
            passed="false",  # type: ignore[arg-type]
            expected=False,
            observed=False,
        )
