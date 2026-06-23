"""Temporary content-free probe for the final-fence convergence case."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import relaylm.relaymem_primary_pipeline as pipeline
from relaylm.relaymem_slp_primary_worker import execute_relaymem_slp_primary_worker

from relaylm_phase6c1_primary_worker_fault_smoke import renew_current
from relaylm_phase6c1_primary_worker_test_support import (
    build_request,
    claimed_record,
    fixed_queue_time,
    prepare_store,
    read_record,
    require,
    write_record,
)


def main() -> int:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-final-fence-probe")
        path = write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(queue_root, store_root, record=record)
        real_m3h = pipeline.audit_relaymem_primary_index_log_reconciliation_recovery

        def renew_after_m3h(**kwargs):
            result = real_m3h(**kwargs)
            renew_current(queue_root, path)
            return result

        with (
            fixed_queue_time(),
            patch.object(
                pipeline,
                "audit_relaymem_primary_index_log_reconciliation_recovery",
                side_effect=renew_after_m3h,
            ),
        ):
            stale = execute_relaymem_slp_primary_worker(request)
        require(stale.status == "lease_lost_before_transition", "stale fence")
        renewed = read_record(path)
        later_request, _ = build_request(queue_root, store_root, record=renewed)
        with fixed_queue_time():
            later = execute_relaymem_slp_primary_worker(later_request)
        if later.status != "terminal_succeeded":
            error_type = type(
                f"LaterWorkerStatus_{later.status}",
                (AssertionError,),
                {},
            )
            raise error_type()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
