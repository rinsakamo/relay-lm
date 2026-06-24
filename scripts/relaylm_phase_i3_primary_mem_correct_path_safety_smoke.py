"""Filesystem substitution and correction-chain safety smoke for Phase I-3."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path, PurePosixPath

from relaylm.relaymem_primary_correction import PrimaryCorrectionError, preflight_primary_memory_correction
from relaylm.relaymem_primary_recall import _load_control_state
from relaylm_phase_i1_two_turn_primary_recall_smoke import CHARACTER, NAMESPACE
from _relaylm_phase_i3_test_support import form_primary_memory, require

REPO_ROOT = Path(__file__).resolve().parents[1]


def locate(root: Path, memory_id: str) -> tuple[Path, str]:
    control, reasons = _load_control_state(root)
    require(control is not None and not reasons, reasons)
    entries = [item for item in control["index"] if item.get("idempotency_key") == memory_id]
    require(len(entries) == 1, entries)
    relative = str(entries[0]["page_relative_path"])
    return root / PurePosixPath(relative), relative


def expect_rejected(root: Path, memory_id: str, operation_id: str) -> None:
    try:
        preflight_primary_memory_correction(
            store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE,
            memory_id=memory_id, expected_revision=1,
            corrected_title="corrected", corrected_summary="corrected summary",
            reason="path safety verification", operation_id=operation_id,
        )
    except PrimaryCorrectionError as error:
        require(error.code == "target_corrupt", (operation_id, error.code))
    else:
        raise AssertionError(operation_id)


def main() -> None:
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
        root = Path(directory)
        memory_id = form_primary_memory(
            root, namespace=NAMESPACE, candidate_id="phase-i3-link-substitution",
            title="original", summary="original summary",
        )
        page, _ = locate(root, memory_id)
        content = page.read_text(encoding="utf-8")
        alternate = root / "alternate-primary-page.md"
        alternate.write_text(content, encoding="utf-8")
        page.unlink()
        page.symlink_to(alternate)
        expect_rejected(root, memory_id, "link-substitution")

    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
        root = Path(directory)
        memory_id = form_primary_memory(
            root, namespace=NAMESPACE, candidate_id="phase-i3-path-substitution",
            title="original", summary="original summary",
        )
        _, relative = locate(root, memory_id)
        index = root / "memory" / "mem" / "index.md"
        text = index.read_text(encoding="utf-8")
        replacement = (PurePosixPath("..") / "alternate-primary-page.md").as_posix()
        index.write_text(text.replace(relative, replacement, 1), encoding="utf-8")
        expect_rejected(root, memory_id, "path-substitution")

    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
        root = Path(directory)
        memory_id = form_primary_memory(
            root, namespace=NAMESPACE, candidate_id="phase-i3-chain-conflict",
            title="original", summary="original summary",
        )
        correction_dir = root / "memory" / "mem" / "corrections" / "v0" / memory_id
        correction_dir.mkdir(parents=True)
        operation_key = "a" * 64
        (correction_dir / f"{operation_key}.applied.json").write_text(
            json.dumps({}, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        expect_rejected(root, memory_id, "correction-chain-conflict")

    print("Phase I-3 Primary MEM Correct path safety smoke passed")


if __name__ == "__main__":
    main()
