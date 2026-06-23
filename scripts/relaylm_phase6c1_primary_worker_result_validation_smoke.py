"""Strict result-ledger validation smoke for the Phase 6-C1-2 worker."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from relaylm.relaymem_slp_primary_worker import (
    build_relaymem_slp_primary_worker_node_result,
    execute_relaymem_slp_primary_worker,
    project_relaymem_slp_primary_worker,
)

from relaylm_phase6c1_primary_worker_test_support import (
    build_request,
    claimed_record,
    fixed_queue_time,
    prepare_store,
    require,
    write_record,
)


def expect_rejected(value: object) -> None:
    for projector in (
        project_relaymem_slp_primary_worker,
        build_relaymem_slp_primary_worker_node_result,
    ):
        try:
            projector(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        raise AssertionError(("invalid worker result accepted", projector.__name__))


def main() -> int:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-worker-result-validation")
        write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(queue_root, store_root, record=record)
        with fixed_queue_time():
            result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "terminal_succeeded", result.to_log_dict())

        # The exact production result remains projectable and deterministic.
        first = project_relaymem_slp_primary_worker(result).to_log_dict()
        second = project_relaymem_slp_primary_worker(result).to_log_dict()
        require(first == second, "worker projection is not deterministic")
        build_relaymem_slp_primary_worker_node_result(result)

        invalid_results = (
            {},
            replace(result, status="unknown_status"),
            replace(result, enabled=False),
            replace(result, dry_run_only=True, apply_enabled=False),
            replace(
                result,
                m3e_checkpoint_passed=False,
                m3g_checkpoint_passed=True,
            ),
            replace(result, source_checkpoint_passed=False),
            replace(result, lease_renewal_count=True),
            replace(result, lease_renewal_count=0),
            replace(result, pipeline_result={}),
            replace(result, outcome_result={}),
            replace(result, queue_transition_result={}),
            replace(result, final_checkpoint_passed=False),
            replace(result, queue_transition_performed=False),
            replace(result, queue_transition_result=None),
            replace(result, outcome_result=None),
            replace(result, side_effect_started=False),
            replace(result, reason_ids=["invalid_reason_container"]),
            replace(result, reason_ids=("INVALID REASON",)),
        )
        for invalid in invalid_results:
            expect_rejected(invalid)

    print("Phase 6-C1 worker result validation smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
