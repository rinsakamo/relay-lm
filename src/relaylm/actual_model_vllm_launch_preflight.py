from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


class VLLMHostPreflightError(ValueError):
    """The bounded vLLM host-preflight process snapshot is not admissible."""


@dataclass(frozen=True, slots=True)
class HostProcess:
    pid: int
    argv: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.pid, bool) or not isinstance(self.pid, int) or self.pid <= 0:
            raise VLLMHostPreflightError("process pid must be a positive integer")
        if not self.argv or not all(isinstance(item, str) and item for item in self.argv):
            raise VLLMHostPreflightError("process argv must contain non-empty strings")


RunProcessSnapshot = Callable[..., subprocess.CompletedProcess[str]]


def parse_process_snapshot(snapshot_text: str) -> tuple[HostProcess, ...]:
    if not isinstance(snapshot_text, str):
        raise TypeError("snapshot_text must be a string")

    processes: list[HostProcess] = []
    seen_pids: set[int] = set()
    for line_number, raw_line in enumerate(snapshot_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split(maxsplit=1)
        if len(fields) != 2:
            raise VLLMHostPreflightError(
                f"process snapshot row {line_number} must contain pid and argv"
            )
        pid_text, command_text = fields
        try:
            pid = int(pid_text, 10)
        except ValueError as exc:
            raise VLLMHostPreflightError(
                f"process snapshot row {line_number} has invalid pid"
            ) from exc
        if pid <= 0 or pid in seen_pids:
            raise VLLMHostPreflightError(
                f"process snapshot row {line_number} has invalid or duplicate pid"
            )
        try:
            argv = tuple(shlex.split(command_text, posix=True))
        except ValueError as exc:
            raise VLLMHostPreflightError(
                f"process snapshot row {line_number} has malformed argv"
            ) from exc
        if not argv:
            raise VLLMHostPreflightError(
                f"process snapshot row {line_number} has empty argv"
            )
        processes.append(HostProcess(pid=pid, argv=argv))
        seen_pids.add(pid)
    return tuple(processes)


def _executable_name(value: str) -> str:
    return Path(value).name


def _is_canonical_vllm_server(process: HostProcess) -> bool:
    argv = process.argv
    executable = _executable_name(argv[0])
    if executable == "vllm" and len(argv) >= 2 and argv[1] == "serve":
        return True

    if executable.startswith("python"):
        for index, value in enumerate(argv[:-1]):
            if value == "-m" and argv[index + 1] == "vllm.entrypoints.openai.api_server":
                return True
    return False


def find_stale_vllm_processes(
    processes: Sequence[HostProcess],
) -> tuple[HostProcess, ...]:
    if not isinstance(processes, Sequence):
        raise TypeError("processes must be a sequence")
    stale: list[HostProcess] = []
    for process in processes:
        if not isinstance(process, HostProcess):
            raise TypeError("processes must contain HostProcess values")
        if _is_canonical_vllm_server(process):
            stale.append(process)
    return tuple(stale)


def snapshot_vllm_processes(
    *,
    run: RunProcessSnapshot = subprocess.run,
) -> tuple[HostProcess, ...]:
    try:
        completed = run(
            ("ps", "-eo", "pid=,args="),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise VLLMHostPreflightError("failed to acquire process snapshot") from exc
    if not isinstance(completed.stdout, str):
        raise VLLMHostPreflightError("process snapshot stdout must be text")
    return parse_process_snapshot(completed.stdout)


def _build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description=(
            "Fail closed when a canonical stale vLLM server process is present "
            "before a bounded actual-model launch transaction."
        )
    )


def main(argv: list[str] | None = None) -> int:
    _build_parser().parse_args(argv)
    try:
        stale = find_stale_vllm_processes(snapshot_vllm_processes())
    except VLLMHostPreflightError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if stale:
        for process in stale:
            print(f"stale vLLM server process: pid={process.pid}", file=sys.stderr)
        return 2

    print("vLLM process preflight: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
