#!/usr/bin/env python3
"""I1-GE I1-GC/C1-5/B2/completion process-exit validation."""
from __future__ import annotations

import _relaylm_i1ge_crash_validation as validation


_PUBLIC_RECONSTRUCT_CHILD = "._relaylm_i1ge_crash_child_public_reconstruct.py"


def _run_replay_matrix_with_public_reconstruct_seam() -> None:
    """Run the replay crash matrix with the reconstruction seam patched at facade level."""

    original_child = validation.CHILD
    original_text = original_child.read_text("utf-8")
    patched_text = original_text.replace(
        "            original = replay_impl._reconstruct_source\n",
        "            original = replay_public._reconstruct_source\n",
        1,
    ).replace(
        '            stack.enter_context(patch.object(replay_impl, "_reconstruct_source", new=reconstructed))\n',
        '            stack.enter_context(patch.object(replay_public, "_reconstruct_source", new=reconstructed))\n',
        1,
    )
    if patched_text == original_text:
        raise AssertionError("replay_reconstruct_child_patch_missing")

    patched_child = original_child.with_name(_PUBLIC_RECONSTRUCT_CHILD)
    patched_child.write_text(patched_text, encoding="utf-8")
    validation.CHILD = patched_child
    try:
        validation.run_replay_matrix()
    finally:
        validation.CHILD = original_child
        patched_child.unlink(missing_ok=True)


if __name__ == "__main__":
    _run_replay_matrix_with_public_reconstruct_seam()
    print("RelayLM I1-GE replay crash smoke passed")
