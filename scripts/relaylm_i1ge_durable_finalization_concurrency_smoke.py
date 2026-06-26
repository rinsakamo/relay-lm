#!/usr/bin/env python3
"""I1-GE fresh-process replay/finalizer/discovery concurrency validation."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from _relaylm_i1ge_crash_validation import (
    CHILD,
    ROOT,
    _env,
    assert_complete,
    production_snapshot,
    require,
    result_status,
    run_child,
)

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import relaylm_i1gc_durable_finalization_replay_smoke as gc  # noqa: E402
import relaylm_o1b_sealed_replay_lane_smoke as o1b  # noqa: E402
import relaylm_wave2_cross_slice_convergence_smoke as w2  # noqa: E402


def _command(root: Path, name: str) -> list[str]:
    return [
        sys.executable,
        str(CHILD),
        "replay-normal",
        "--root",
        str(root.resolve()),
        "--result-name",
        name,
    ]


def test_two_fresh_replay_processes() -> None:
    with TemporaryDirectory(prefix="relaylm-i1ge-concurrency-") as directory:
        root = Path(directory)
        run_child("prepare-sealed", root, result_name="prepare")
        first = subprocess.Popen(
            _command(root, "first"),
            cwd=ROOT,
            env=_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        second = subprocess.Popen(
            _command(root, "second"),
            cwd=ROOT,
            env=_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        outputs: list[tuple[int, str, str]] = []
        for process in (first, second):
            try:
                stdout, stderr = process.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate(timeout=5)
                raise AssertionError(("concurrent_replay_timeout", stdout, stderr))
            outputs.append((int(process.returncode), stdout, stderr))
        require(all(code == 0 for code, _, _ in outputs), outputs)
        statuses = {result_status(root, "first"), result_status(root, "second")}
        require(
            statuses <= {"completed", "already_complete", "exact_duplicate", "replay_lock_busy"},
            statuses,
        )
        require(statuses & {"completed", "exact_duplicate", "already_complete"}, statuses)
        assert_complete(root)
        before = production_snapshot(root)
        run_child("replay-normal", root, result_name="third")
        require(result_status(root, "third") == "already_complete", statuses)
        require(production_snapshot(root) == before, (before, production_snapshot(root)))


def main() -> None:
    test_two_fresh_replay_processes()
    # Existing permanent authorities exercise normal finalizer vs restart replay,
    # replay-fence busy mapping, O1B completion/candidate replacement, and the
    # authoritative I1-GD isolation appearance race.
    gc.test_process_races_and_normal_finalizer()
    o1b.test_inventory_bounds_and_reread_changes()
    o1b.test_cross_process_busy_mapping()
    w2.test_authority_and_isolation_race()
    print("RelayLM I1-GE concurrency crash smoke passed")


if __name__ == "__main__":
    main()
