from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from _relaylm_o1f_support import assert_public_result_safe, initial_record, require, stale_claimed_record, write_record
import relaylm.relaymem_slp_queue_state as queue_state
from relaylm.relaymem_slp_scheduler_operational_validation import (
    validate_durable_finalization_locator,
    validate_queue_root_inventory,
    validate_source_queue_correlation,
)


def _queue_path(root: Path, record: dict[str, object]) -> Path:
    return root / queue_state._record_filename(str(record["dispatch_idempotency_key"]))


def _expect_unsafe(root: Path, label: str) -> None:
    result = validate_queue_root_inventory(queue_root=str(root), max_scan_entries=32)
    require(result.status == "unsafe", (label, result.projection()))
    assert_public_result_safe(result)


def main() -> int:
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = initial_record()
        _queue_path(root, record).write_bytes(b"{")
        _expect_unsafe(root, "malformed_json")

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = initial_record()
        _queue_path(root, record).write_bytes(b'{"a":1,"a":2}')
        _expect_unsafe(root, "duplicate_key_json")

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = initial_record()
        _queue_path(root, record).write_text(json.dumps(record, indent=2), encoding="utf-8")
        _expect_unsafe(root, "noncanonical_json")

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = initial_record()
        record["state"] = "paused"
        _queue_path(root, record).write_bytes(queue_state._canonical_json_bytes(record))
        _expect_unsafe(root, "unsupported_state")

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = stale_claimed_record()
        del record["lease_token"]
        _queue_path(root, record).write_bytes(queue_state._canonical_json_bytes(record))
        _expect_unsafe(root, "missing_required_claim_field")

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = initial_record()
        target = root / "target.json"
        target.write_text("{}", encoding="utf-8")
        os.symlink(target, _queue_path(root, record))
        _expect_unsafe(root, "symlink_blocked")

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = initial_record()
        path = write_record(root, record)
        os.link(path, root / "extra-hardlink")
        _expect_unsafe(root, "hardlink_blocked")

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = initial_record()
        _queue_path(root, record).write_bytes(b"{" + b"a" * (40 * 1024) + b"}")
        _expect_unsafe(root, "oversized_record")

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        locator = "c" * 64
        (root / f"durable-finalization-v0-{locator}.base.json").write_bytes(b"{")
        durable = validate_durable_finalization_locator(sealed_root=str(root), locator_digest=locator)
        require(durable.status == "unsafe", durable.projection())
        assert_public_result_safe(durable)

    mismatch = validate_source_queue_correlation(
        source_dispatch_idempotency_key="source-key",
        queue_dispatch_idempotency_key="queue-key",
    )
    require(mismatch.status == "unsafe", mismatch.projection())
    assert_public_result_safe(mismatch)

    print("ok O1F corruption validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
