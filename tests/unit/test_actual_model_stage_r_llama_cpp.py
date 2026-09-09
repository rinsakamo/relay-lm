from __future__ import annotations

import json
from pathlib import Path

import pytest

import relaylm.actual_model_stage_r_llama_cpp as host


CORE = "sha256:" + "a" * 64
HEAD = "b" * 40
TREE = "c" * 40


def _argv(tmp_path: Path) -> list[str]:
    return [
        "--repo-root",
        str(tmp_path / "repo"),
        "--provider-base-url",
        "http://127.0.0.1:1234/v1",
        "--request-model",
        "gemma-local",
        "--artifact-path",
        str(tmp_path / "gemma.gguf"),
        "--llama-upstream-revision",
        "d" * 40,
        "--llama-version",
        "0.4.0-dev",
        "--expected-build-number",
        "10874",
        "--expected-context-window",
        "4352",
        "--context-shift-disabled",
        "--workspace-root",
        str(tmp_path / "workspace"),
        "--artifact-root",
        str(tmp_path / "artifacts"),
    ]


def _common_main_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(host, "_require_clean_repo", lambda _root: None)
    monkeypatch.setattr(host, "_git_identity", lambda _root: (HEAD, TREE))
    monkeypatch.setattr(host, "_frozen_core_fingerprint", lambda _root: CORE)


def test_current_llama_endpoint_is_exact_loopback_and_never_lm_studio_fallback() -> None:
    assert (
        host._require_local_llama_api_base("http://127.0.0.1:1234/v1")
        == "http://127.0.0.1:1234/v1"
    )
    for value in (
        "http://192.168.50.26:1234/v1",
        "http://localhost:1234/v1",
        "http://127.0.0.1:8080/v1",
        "http://127.0.0.1:1234",
    ):
        with pytest.raises(host.LlamaCppStageRQualificationError):
            host._require_local_llama_api_base(value)


def test_physical_preflight_failure_is_infra_invalid_without_semantic_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _common_main_monkeypatch(monkeypatch)
    monkeypatch.setattr(
        host,
        "_prepare_physical_condition",
        lambda **_kwargs: (_ for _ in ()).throw(
            host.LlamaCppStageRQualificationError("llama-server unavailable")
        ),
    )

    result = host.main(_argv(tmp_path))

    assert result == 2
    document = json.loads(
        (tmp_path / "artifacts" / "stage-r-llama-cpp-summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert document["classification"] == "INFRA_INVALID"
    assert document["phase"] == "physical_preflight"
    assert document["semantic_execution_started"] is False
    assert document["semantic_retry_count"] == 0
    assert document["fallback_count"] == 0


@pytest.mark.parametrize(
    ("classification", "exit_code"),
    [("PASS", 0), ("SEMANTIC_FAIL", 1)],
)
def test_valid_physical_condition_preserves_semantic_classification(
    classification: str,
    exit_code: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _common_main_monkeypatch(monkeypatch)
    preflight = {
        "target": object(),
        "verification": object(),
        "runtime": object(),
        "counter": object(),
        "evidence": {"endpoint": "http://127.0.0.1:1234/v1"},
    }
    monkeypatch.setattr(host, "_prepare_physical_condition", lambda **_kwargs: preflight)
    monkeypatch.setattr(host, "load_stage_r_semantic_authority", lambda _path: object())
    monkeypatch.setattr(
        host,
        "load_current_stage_r_scenario_set",
        lambda **_kwargs: object(),
    )

    async def fake_stage_r(**_kwargs):
        return {
            "classification": classification,
            "provider_request_count": 6,
            "executions": [],
        }

    monkeypatch.setattr(host, "_run_stage_r", fake_stage_r)

    result = host.main(_argv(tmp_path))

    assert result == exit_code
    document = json.loads(
        (tmp_path / "artifacts" / "stage-r-llama-cpp-summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert document["classification"] == classification
    assert document["provider_request_count"] == 8
    assert document["semantic_retry_count"] == 0
    assert document["fallback_count"] == 0


def test_thinking_off_completion_evidence_rejects_reasoning_output(tmp_path: Path) -> None:
    clean = tmp_path / "clean.json"
    clean.write_text(
        json.dumps(
            {
                "reasoning": {
                    "reasoning": "absent",
                    "reasoning_content": "absent",
                    "reasoning_tokens": 0,
                }
            }
        ),
        encoding="utf-8",
    )
    assert host._completion_evidence_is_thinking_off((clean,)) is True

    leaked = tmp_path / "leaked.json"
    leaked.write_text(
        json.dumps(
            {
                "reasoning": {
                    "reasoning": "absent",
                    "reasoning_content": "nonempty",
                    "reasoning_tokens": 0,
                }
            }
        ),
        encoding="utf-8",
    )
    assert host._completion_evidence_is_thinking_off((leaked,)) is False
