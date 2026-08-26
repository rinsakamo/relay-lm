from __future__ import annotations

import json
from pathlib import Path

from relaylm.actual_model_vllm_host import (
    CANONICAL_VLLM_SCREENING_PLAN_PATH,
    load_vllm_screening_plan,
)


_ROOT = Path(__file__).parents[2]


def test_current_stage_r_plan_declares_capacity_source_without_numeric_window() -> None:
    path = _ROOT / CANONICAL_VLLM_SCREENING_PLAN_PATH
    raw = json.loads(path.read_text(encoding="utf-8"))

    assert raw["format_version"] == 3
    assert raw["context_window_source"] == "capacity_evidence"
    assert "effective_context_window" not in raw

    plan = load_vllm_screening_plan(path)
    assert plan.format_version == 3
    assert plan.context_window_source == "capacity_evidence"
    assert plan.effective_context_window is None
