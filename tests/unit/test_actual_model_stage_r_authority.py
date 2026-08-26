from __future__ import annotations

import json
from pathlib import Path


_ROOT = Path(__file__).parents[2]
_AUTHORITY_PATH = (
    _ROOT
    / "evaluation"
    / "actual_model"
    / "screenings"
    / "stage-r0-vllm-current-v1.json"
)


def test_current_stage_r_authority_has_no_numeric_context_window() -> None:
    raw = json.loads(_AUTHORITY_PATH.read_text(encoding="utf-8"))

    assert raw == {
        "format_version": 1,
        "authority_id": "stage-r0-vllm-current-v1",
        "execution_template_path": (
            "evaluation/actual_model/screenings/stage-r0-vllm-reference-v2.json"
        ),
        "context_window_source": "fresh_external_capacity_evidence",
        "hardware_capability_source": "fresh_vllm_profiler_auto_kv",
    }
    assert "effective_context_window" not in raw
