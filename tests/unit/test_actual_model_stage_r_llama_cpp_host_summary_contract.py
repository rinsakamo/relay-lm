from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import relaylm.actual_model_stage_r_llama_cpp_transaction as transaction


def _invoke(
    *,
    tmp_path: Path,
    monkeypatch,
    emitted_filename: str,
    selected_filename: str | None,
):
    def fake_run(*args, **kwargs):
        del args, kwargs
        (tmp_path / emitted_filename).write_text(
            json.dumps({"classification": "TEST_HOST_COMPLETED"}),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            args=["python"],
            returncode=0,
            stdout="host stdout",
            stderr="",
        )

    monkeypatch.setattr(transaction.subprocess, "run", fake_run)
    selected_path = (
        None
        if selected_filename is None
        else transaction._host_summary_path(
            artifact_root=tmp_path,
            filename=selected_filename,
        )
    )
    return transaction._invoke_host(
        repo_root=tmp_path,
        api_base="http://127.0.0.1:1234/v1",
        request_model="test-model",
        artifact_path=tmp_path / "model.gguf",
        revision="deadbeef",
        version="test-version",
        build=1,
        gpu_identity="test-gpu",
        launch_command=["llama-server"],
        log_path=tmp_path / "server.log",
        workspace_root=tmp_path / "workspace",
        artifact_root=tmp_path,
        replicate_id="0",
        host_module="test.host",
        host_summary_path=selected_path,
    )


def test_default_host_summary_filename_is_preserved(tmp_path, monkeypatch) -> None:
    result = _invoke(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        emitted_filename=transaction.DEFAULT_HOST_SUMMARY_FILENAME,
        selected_filename=None,
    )
    assert result["summary_path"] == str(
        tmp_path / transaction.DEFAULT_HOST_SUMMARY_FILENAME
    )
    assert result["summary"] == {"classification": "TEST_HOST_COMPLETED"}


def test_alternate_declared_host_summary_filename_is_used(tmp_path, monkeypatch) -> None:
    result = _invoke(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        emitted_filename="diagnostic-summary.json",
        selected_filename="diagnostic-summary.json",
    )
    assert result["summary_path"] == str(tmp_path / "diagnostic-summary.json")
    assert result["summary"] == {"classification": "TEST_HOST_COMPLETED"}


def test_missing_declared_summary_fails_closed(tmp_path, monkeypatch) -> None:
    with pytest.raises(
        transaction.LlamaCppTransactionError,
        match="declared summary artifact",
    ):
        _invoke(
            tmp_path=tmp_path,
            monkeypatch=monkeypatch,
            emitted_filename="other.json",
            selected_filename="declared.json",
        )


def test_undeclared_alternate_summary_is_not_silently_accepted(
    tmp_path,
    monkeypatch,
) -> None:
    with pytest.raises(
        transaction.LlamaCppTransactionError,
        match="declared summary artifact",
    ):
        _invoke(
            tmp_path=tmp_path,
            monkeypatch=monkeypatch,
            emitted_filename="epistemic-formation-t2-summary.json",
            selected_filename=None,
        )


def test_host_summary_filename_cannot_escape_artifact_root(tmp_path) -> None:
    for filename in ("../escape.json", "nested/summary.json", "/tmp/escape.json", ".."):
        with pytest.raises(
            transaction.LlamaCppTransactionError,
            match="inside artifact root",
        ):
            transaction._host_summary_path(
                artifact_root=tmp_path,
                filename=filename,
            )
