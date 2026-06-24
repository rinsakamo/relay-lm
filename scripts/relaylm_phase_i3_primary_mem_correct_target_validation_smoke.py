"""Fail-closed target validation smoke for Phase I-3."""
from __future__ import annotations

import tempfile
from pathlib import Path, PurePosixPath

from relaylm.relaymem_primary_correction import PrimaryCorrectionError, preflight_primary_memory_correction
from relaylm.relaymem_primary_recall import _load_control_state
from relaylm_phase_i1_two_turn_primary_recall_smoke import CHARACTER, NAMESPACE
from _relaylm_phase_i3_test_support import form_primary_memory, require

REPO_ROOT = Path(__file__).resolve().parents[1]


def page_for(root: Path, memory_id: str) -> Path:
    control, reasons = _load_control_state(root)
    require(control is not None and not reasons, reasons)
    entries = [item for item in control["index"] if item.get("idempotency_key") == memory_id]
    require(len(entries) == 1, entries)
    return root / PurePosixPath(str(entries[0]["page_relative_path"]))


def rejected(root: Path, memory_id: str, operation_id: str) -> None:
    try:
        preflight_primary_memory_correction(
            store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE,
            memory_id=memory_id, expected_revision=1,
            corrected_title="corrected", corrected_summary="corrected summary",
            reason="target validation", operation_id=operation_id,
        )
    except PrimaryCorrectionError as error:
        require(error.code == "target_corrupt", (operation_id, error.code))
    else:
        raise AssertionError(operation_id)


def main() -> None:
    for kind in ("malformed", "wrong_schema", "invalid_lineage", "directory"):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            root = Path(directory)
            memory_id = form_primary_memory(
                root, namespace=NAMESPACE, candidate_id=f"phase-i3-{kind}",
                title="original", summary="original summary",
            )
            page = page_for(root, memory_id)
            text = page.read_text(encoding="utf-8")
            if kind == "malformed":
                page.write_text("not canonical\n", encoding="utf-8")
            elif kind == "wrong_schema":
                page.write_text(text.replace("relaymem.primary_page.v0", "relaymem.primary_page.v9", 1), encoding="utf-8")
            elif kind == "invalid_lineage":
                marker = "lineage_fingerprint: "
                before, after = text.split(marker, 1)
                _, remainder = after.split("\n", 1)
                page.write_text(before + marker + ("0" * 64) + "\n" + remainder, encoding="utf-8")
            else:
                page.unlink()
                page.mkdir()
            rejected(root, memory_id, kind)

    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
        root = Path(directory)
        memory_id = form_primary_memory(
            root, namespace=NAMESPACE, candidate_id="phase-i3-control-mismatch",
            title="original", summary="original summary",
        )
        (root / "memory" / "mem" / "log.md").write_text("# Log\n", encoding="utf-8")
        rejected(root, memory_id, "index-log-mismatch")

    print("Phase I-3 Primary MEM Correct target validation smoke passed")


if __name__ == "__main__":
    main()
