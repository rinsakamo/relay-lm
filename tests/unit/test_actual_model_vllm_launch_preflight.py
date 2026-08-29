from __future__ import annotations

import subprocess

import pytest

from relaylm.actual_model_vllm_launch_preflight import (
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
