from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_parser(tmp_path: Path, log_text: str) -> subprocess.CompletedProcess[str]:
    log_path = tmp_path / "profiler.log"
    log_path.write_text(log_text, encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "relaylm.actual_model_vllm_profiler",
            "--log",
            str(log_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_profiler_cli_parses_observed_backtick_recommendation(tmp_path: Path) -> None:
    result = _run_parser(
        tmp_path,
        "INFO To fully utilize available GPU memory, use `--kv-cache-memory=1493352960`.\n",
    )

    assert result.returncode == 0
    assert result.stdout == "1493352960\n"
    assert result.stderr == ""


def test_profiler_cli_parses_documented_bytes_form(tmp_path: Path) -> None:
    result = _run_parser(
        tmp_path,
        "INFO recommendation: --kv-cache-memory-bytes=1618644685\n",
    )

    assert result.returncode == 0
    assert result.stdout == "1618644685\n"


def test_profiler_cli_allows_repeated_identical_recommendation(tmp_path: Path) -> None:
    result = _run_parser(
        tmp_path,
        "\n".join(
            [
                "INFO `--kv-cache-memory=1493352960`",
                "INFO repeated `--kv-cache-memory-bytes=1493352960`",
            ]
        ),
    )

    assert result.returncode == 0
    assert result.stdout == "1493352960\n"


def test_profiler_cli_rejects_conflicting_recommendations(tmp_path: Path) -> None:
    result = _run_parser(
        tmp_path,
        "INFO `--kv-cache-memory=1493352960`\nINFO --kv-cache-memory-bytes=1493352961\n",
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "conflicting" in result.stderr


def test_profiler_cli_rejects_missing_recommendation(tmp_path: Path) -> None:
    result = _run_parser(tmp_path, "INFO CUDA graph capture complete\n")

    assert result.returncode == 2
    assert result.stdout == ""
    assert "not found" in result.stderr
