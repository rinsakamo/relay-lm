from __future__ import annotations

import os

import pytest

from tools.v1_external_qualification_hindsight_runtime import (
    _configure_consolidation_reasoning_effort,
    _configure_retain_reasoning_effort,
)


def test_configure_retain_reasoning_effort_binds_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HINDSIGHT_API_RETAIN_LLM_REASONING_EFFORT", raising=False)

    observed = _configure_retain_reasoning_effort("none")

    assert observed == "none"
    assert os.environ["HINDSIGHT_API_RETAIN_LLM_REASONING_EFFORT"] == "none"


def test_configure_retain_reasoning_effort_rejects_other_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HINDSIGHT_API_RETAIN_LLM_REASONING_EFFORT", raising=False)

    with pytest.raises(RuntimeError, match="retain reasoning effort must be none"):
        _configure_retain_reasoning_effort("low")

    assert "HINDSIGHT_API_RETAIN_LLM_REASONING_EFFORT" not in os.environ


def test_configure_consolidation_reasoning_effort_binds_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "HINDSIGHT_API_CONSOLIDATION_LLM_REASONING_EFFORT", raising=False
    )

    observed = _configure_consolidation_reasoning_effort("none")

    assert observed == "none"
    assert (
        os.environ["HINDSIGHT_API_CONSOLIDATION_LLM_REASONING_EFFORT"] == "none"
    )


def test_configure_consolidation_reasoning_effort_rejects_other_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "HINDSIGHT_API_CONSOLIDATION_LLM_REASONING_EFFORT", raising=False
    )

    with pytest.raises(
        RuntimeError, match="consolidation reasoning effort must be none"
    ):
        _configure_consolidation_reasoning_effort("low")

    assert "HINDSIGHT_API_CONSOLIDATION_LLM_REASONING_EFFORT" not in os.environ
