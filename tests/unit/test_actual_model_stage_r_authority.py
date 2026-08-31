from __future__ import annotations

import json
from pathlib import Path

import pytest

import relaylm.actual_model_stage_r as stage_r
from relaylm.actual_model_stage_r import StageRAuthorityError


_ROOT = Path(__file__).parents[2]
_AUTHORITY_PATH = (
    _ROOT
    / "evaluation"
    / "actual_model"
    / "screenings"
    / "stage-r0-vllm-current-v1.json"
)


def _common_args(operation: str) -> list[str]:
    return [
        "--operation",
        operation,
        "--condition",
        "reference_baseline",
        "--repo-root",
        str(_ROOT),
        "--snapshot-root",
        "/tmp/model",
        "--provider-base-url",
        "http://127.0.0.1:8000/v1",
        "--workspace-root",
        "/tmp/workspace",
        "--artifact-root",
        "/tmp/artifacts",
        "--model-runner",
        "v2",
    ]


def test_current_stage_r_authority_has_no_numeric_context_window() -> None:
    raw = json.loads(_AUTHORITY_PATH.read_text(encoding="utf-8"))

    assert raw == {
        "format_version": 1,
        "authority_id": "stage-r0-vllm-current-v1",
        "execution_template_path": (
            "evaluation/actual_model/screenings/stage-r0-vllm-reference-v3.json"
        ),
        "context_window_source": "fresh_external_capacity_evidence",
        "hardware_capability_source": "qualified_vllm_token_capacity_reference",
    }
    assert "effective_context_window" not in raw


def test_current_stage_r_rejects_stale_profiler_hardware_source(
    tmp_path: Path,
) -> None:
    path = tmp_path / "authority.json"
    path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "authority_id": "stage-r0-vllm-current-v1",
                "execution_template_path": (
                    "evaluation/actual_model/screenings/"
                    "stage-r0-vllm-reference-v3.json"
                ),
                "context_window_source": "fresh_external_capacity_evidence",
                "hardware_capability_source": "fresh_vllm_profiler_auto_kv",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        StageRAuthorityError,
        match="qualified vLLM token-capacity reference",
    ):
        stage_r.load_current_stage_r_authority(path)


def test_current_stage_r_rejects_origin_only_provider_base_url_before_delegation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    touched = False

    def forbidden(_: list[str]) -> int:
        nonlocal touched
        touched = True
        return 0

    monkeypatch.setattr(stage_r, "_host_main", forbidden)
    args = _common_args("capacity")
    args[args.index("--provider-base-url") + 1] = "http://127.0.0.1:8000"

    with pytest.raises(
        StageRAuthorityError,
        match="provider base URL.*\/v1",
    ):
        stage_r.main(args)

    assert touched is False


def test_current_stage_r_screening_requires_external_capacity_evidence() -> None:
    with pytest.raises(
        StageRAuthorityError,
        match="requires fresh external capacity evidence",
    ):
        stage_r.main(_common_args("screening"))


def test_current_stage_r_screening_always_binds_context_from_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegated: list[list[str]] = []
    monkeypatch.setattr(
        stage_r,
        "_host_main",
        lambda args: delegated.append(list(args)) or 0,
    )

    result = stage_r.main(
        _common_args("screening")
        + [
            "--capacity-evidence-id",
            "amcap-current",
            "--capacity-evidence-root",
            "/tmp/capacity",
        ]
    )

    assert result == 0
    assert len(delegated) == 1
    args = delegated[0]
    assert "--context-window-from-capacity-evidence" in args
    assert args[args.index("--capacity-evidence-id") + 1] == "amcap-current"
    assert args[args.index("--capacity-evidence-root") + 1] == "/tmp/capacity"
    assert args[args.index("--screening-plan") + 1] == (
        "evaluation/actual_model/screenings/stage-r0-vllm-reference-v3.json"
    )


def test_current_stage_r_capacity_does_not_consume_prior_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegated: list[list[str]] = []
    monkeypatch.setattr(
        stage_r,
        "_host_main",
        lambda args: delegated.append(list(args)) or 0,
    )

    result = stage_r.main(_common_args("capacity"))

    assert result == 0
    assert len(delegated) == 1
    args = delegated[0]
    assert "--capacity-evidence-id" not in args
    assert "--capacity-evidence-root" not in args
    assert "--context-window-from-capacity-evidence" not in args

    with pytest.raises(
        StageRAuthorityError,
        match="must not consume prior capacity evidence",
    ):
        stage_r.main(
            _common_args("capacity")
            + [
                "--capacity-evidence-id",
                "amcap-stale",
                "--capacity-evidence-root",
                "/tmp/capacity",
            ]
        )
