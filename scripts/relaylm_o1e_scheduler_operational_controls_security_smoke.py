from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
for candidate in (REPO_ROOT, SCRIPTS_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from relaylm.relaymem_slp_scheduler_operations import run_relaymem_slp_scheduler_operational_controls_once
from relaylm_o1e_scheduler_operational_controls_smoke import (
    _base_config,
    _contains,
    _stale_claimed_record,
    _write,
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    private_memory = "PRIVATE_MEMORY_CONTENT_CANARY"
    protected_source = "PROTECTED_SOURCE_CONTENT_CANARY"
    raw_exception = "Traceback: /tmp/private/root token secret"
    raw_path = "/tmp/relaylm/private/o1e"

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = _stale_claimed_record()
        path = _write(root, record)
        result = run_relaymem_slp_scheduler_operational_controls_once(
            config=_base_config(
                relaymem_slp_queue_root=str(root),
                relaymem_local_scheduler_operational_controls_enabled=True,
                relaymem_local_scheduler_operational_controls_dry_run_only=True,
                relaymem_local_scheduler_operational_controls_apply_enabled=False,
                relaymem_local_scheduler_stale_recovery_enabled=True,
                relaymem_local_scheduler_stale_recovery_dry_run_only=True,
                relaymem_local_scheduler_stale_recovery_apply_enabled=False,
            ),
            now=datetime(2026, 6, 22, 0, 0, 3, tzinfo=timezone.utc),
            fault_injector=lambda seam: None,
        )
        projection = result.projection()
        public_text = repr(projection) + repr(result)
        forbidden = (
            private_memory,
            protected_source,
            raw_exception,
            raw_path,
            str(root),
            str(path),
            str(record["job_id"]),
            str(record["dispatch_idempotency_key"]),
            str(record["lease_token"]),
            str(record["lease_acquired_at"]),
            str(record["lease_expires_at"]),
            str(record["updated_at"]),
            str(record["run_id"]),
            str(record["session_id"]),
        )
        for value in forbidden:
            require(value not in public_text, projection)
            require(not _contains(projection, value), projection)
        require("stale_recovery_result" not in projection, projection)
        require("scheduler_policy_result" not in projection, projection)
        require(projection["stale_recovery_status"] == "stale_recovery_dry_run_ready", projection)
    print("ok O1E public projections omit private operational material")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
