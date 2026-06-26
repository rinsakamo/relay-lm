#!/usr/bin/env python3
"""I1-GE crash-output leakage and inherited filesystem-security validation."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from _relaylm_i1ge_crash_child import EXIT_CODES
from _relaylm_i1ge_crash_validation import (
    assert_content_free_process,
    require,
    run_child,
    run_existing_scripts,
)


def test_crash_output_is_content_free() -> None:
    cases = (
        ("nonstream", "after_protected_body_release_before_normal_finalizer"),
        ("stream", "after_terminal_visible_completion_before_normal_finalizer"),
        ("replay-crash", "after_exact_b2_reread_before_downstream_verification"),
        ("retention-crash", "after_isolation_marker_reread_before_first_component_deletion"),
    )
    for action, seam in cases:
        with TemporaryDirectory(prefix="relaylm-i1ge-security-") as directory:
            root = Path(directory)
            if action == "replay-crash":
                run_child("prepare-sealed", root, result_name="prepare")
            elif action == "retention-crash":
                run_child("prepare-complete-expired", root, result_name="prepare")
            completed = run_child(
                action,
                root,
                seam=seam,
                expected=EXIT_CODES[seam],
            )
            assert_content_free_process(completed)
            require(len(completed.stdout) <= 4096 and len(completed.stderr) <= 4096, seam)


def main() -> None:
    test_crash_output_is_content_free()
    # These permanent lower authorities cover symlink, hardlink, unsafe type,
    # path escape, duplicate keys, malformed/noncanonical UTF-8/JSON, unknown
    # fields, non-finite values, oversize objects, and inode/type replacement.
    run_existing_scripts(
        (
            "scripts/relaylm_i1gb_durable_finalization_publication_smoke.py",
            "scripts/relaylm_i1gc_durable_finalization_replay_smoke.py",
            "scripts/relaylm_i1gd_durable_finalization_retention_smoke.py",
            "scripts/relaylm_o1b_sealed_replay_lane_security_smoke.py",
            "scripts/relaylm_wave2_cross_slice_security_smoke.py",
        )
    )
    print("RelayLM I1-GE security crash smoke passed")


if __name__ == "__main__":
    main()
