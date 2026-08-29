from __future__ import annotations

import subprocess

import pytest

import relaylm.actual_model_vllm_launch_preflight as launch_preflight
from relaylm.actual_model_vllm_launch_preflight import (
    HostProcess,
    VLLMHostPreflightError,
    find_stale_vllm_processes,
    parse_process_snapshot,
    snapshot_vllm_processes,
)


def test_process_guard_does_not_self_match_detector_search_text() -> None:
    processes = parse_process_snapshot(
        "410\tawk /vllm|EngineCore|uvicorn/ {print}\n"
        "411\tpython -m relaylm.actual_model_vllm_launch_preflight\n"
    )

    assert find_stale_vllm_processes(processes) == ()


def test_process_guard_detects_canonical_vllm_serve_process() -> None:
    processes = parse_process_snapshot(
        "510\t/usr/bin/vllm serve /models/gemma --port 8000\n"
    )

    stale = find_stale_vllm_processes(processes)

    assert len(stale) == 1
    assert stale[0].pid == 510


def test_process_guard_detects_python_module_vllm_api_server() -> None:
    processes = parse_process_snapshot(
        "511\t/usr/bin/python -m vllm.entrypoints.openai.api_server /models/gemma --port 8000\n"
    )

    stale = find_stale_vllm_processes(processes)

    assert len(stale) == 1
    assert stale[0].pid == 511


def test_process_guard_detects_exact_vllm_engine_core_title() -> None:
    processes = parse_process_snapshot("512\tVLLM::EngineCore\n")

    stale = find_stale_vllm_processes(processes)

    assert len(stale) == 1
    assert stale[0].pid == 512


def test_process_guard_ignores_engine_core_substring_in_detector() -> None:
    processes = parse_process_snapshot(
        "513\tawk /EngineCore/ {print}\n"
    )

    assert find_stale_vllm_processes(processes) == ()


def test_process_guard_ignores_unrelated_python_with_vllm_word_in_argument() -> None:
    processes = parse_process_snapshot(
        "610\t/usr/bin/python worker.py --note vllm --mode offline\n"
    )

    assert find_stale_vllm_processes(processes) == ()


def test_process_snapshot_rejects_malformed_rows() -> None:
    with pytest.raises(VLLMHostPreflightError, match="process snapshot row"):
        parse_process_snapshot("not-a-pid python worker.py\n")


def test_snapshot_uses_structured_ps_without_shell_search_expression() -> None:
    calls: list[object] = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="710\t/usr/bin/python worker.py\n",
            stderr="",
        )

    processes = snapshot_vllm_processes(run=fake_run)

    assert len(processes) == 1
    assert processes[0].pid == 710
    assert calls == [
        (
            (("ps", "-eo", "pid=,args="),),
            {
                "check": True,
                "capture_output": True,
                "text": True,
            },
        )
    ]


def test_cli_returns_success_for_clean_host(monkeypatch, capsys) -> None:
    monkeypatch.setattr(launch_preflight, "snapshot_vllm_processes", lambda: ())

    assert launch_preflight.main([]) == 0
    assert capsys.readouterr().out == "vLLM process preflight: clean\n"


def test_cli_fails_closed_for_stale_host(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        launch_preflight,
        "snapshot_vllm_processes",
        lambda: (HostProcess(pid=810, argv=("vllm", "serve")),),
    )

    assert launch_preflight.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "stale vLLM process: pid=810\n"
