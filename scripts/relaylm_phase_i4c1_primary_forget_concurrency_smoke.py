"""I-4C1 Correct/Forget and Forget/Forget one-winner concurrency smoke."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

from _relaylm_phase_i4b_test_support import (
    CHARACTER,
    NAMESPACE,
    prepared_store,
    require,
)
from relaylm.relaymem_primary_correction import (
    PrimaryCorrectionError,
    apply_primary_memory_correction,
    preflight_primary_memory_correction,
)
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    apply_primary_memory_forget_hidden_successor,
    preflight_primary_memory_forget,
)
from relaylm.relaymem_primary_mutation_coordinator import inspect_primary_memory_operations

NOW = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
REASON = "通常検索から外すため"


def forget_preflight(root, memory_id, operation_id):
    return preflight_primary_memory_forget(
        store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE,
        memory_id=memory_id, expected_revision=1,
        expected_lifecycle_state="active", reason=REASON,
        operation_id=operation_id, now=NOW,
    )["apply_token"]


def forget_apply(root, memory_id, operation_id, token):
    return apply_primary_memory_forget_hidden_successor(
        store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE,
        memory_id=memory_id, expected_revision=1,
        expected_lifecycle_state="active", reason=REASON,
        operation_id=operation_id, apply_token=token, now=NOW,
    )


def concurrent_different_forgets() -> None:
    with prepared_store() as (root, memory_id):
        token_a = forget_preflight(root, memory_id, "phase-i4c1-race-a")
        token_b = forget_preflight(root, memory_id, "phase-i4c1-race-b")
        barrier = Barrier(2)

        def run(operation_id, token):
            barrier.wait()
            try:
                return ("ok", forget_apply(root, memory_id, operation_id, token))
            except PrimaryForgetError as exc:
                return ("error", exc.code)

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda args: run(*args), [
                ("phase-i4c1-race-a", token_a),
                ("phase-i4c1-race-b", token_b),
            ]))
        winners = [value for kind, value in outcomes if kind == "ok"]
        losers = [value for kind, value in outcomes if kind == "error"]
        require(len(winners) == 1, outcomes)
        require(len(losers) == 1, outcomes)
        require(losers[0] in {"stale_revision", "target_not_active", "operation_conflict"}, outcomes)
        inspection = inspect_primary_memory_operations(root, memory_id=memory_id)
        require(not inspection.corrupt, inspection)
        require(len(inspection.pending) == 1, inspection)
        current = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(current.lifecycle_state == "hidden", current)
        require(current.current_revision == 2, current)


def concurrent_same_forget() -> None:
    with prepared_store() as (root, memory_id):
        token = forget_preflight(root, memory_id, "phase-i4c1-race-same")
        barrier = Barrier(2)

        def run():
            barrier.wait()
            return forget_apply(root, memory_id, "phase-i4c1-race-same", token)

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = [future.result() for future in (pool.submit(run), pool.submit(run))]
        require(
            sorted(item.status for item in outcomes)
            == ["hidden_successor_existing", "hidden_successor_published"],
            outcomes,
        )
        require(all(item.result_revision == 2 for item in outcomes), outcomes)
        inspection = inspect_primary_memory_operations(root, memory_id=memory_id)
        require(len(inspection.pending) == 1, inspection)


def correct_forget_one_winner() -> None:
    with prepared_store() as (root, memory_id):
        forget_token = forget_preflight(root, memory_id, "phase-i4c1-race-forget")
        correction = preflight_primary_memory_correction(
            store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE,
            memory_id=memory_id, expected_revision=1,
            corrected_title="好きな飲み物（更新）",
            corrected_summary="好きな飲み物は緑茶です。",
            reason="内容を訂正するため",
            operation_id="phase-i4c1-race-correct", now=NOW,
        )
        barrier = Barrier(2)

        def run_forget():
            barrier.wait()
            try:
                return ("forget", "ok", forget_apply(
                    root, memory_id, "phase-i4c1-race-forget", forget_token
                ))
            except PrimaryForgetError as exc:
                return ("forget", "error", exc.code)

        def run_correct():
            barrier.wait()
            try:
                return ("correct", "ok", apply_primary_memory_correction(
                    store_root=str(root), character_id=CHARACTER,
                    namespace=NAMESPACE, memory_id=memory_id,
                    expected_revision=1,
                    operation_id="phase-i4c1-race-correct",
                    apply_token=correction["apply_token"], now=NOW,
                ))
            except PrimaryCorrectionError as exc:
                return ("correct", "error", exc.code)

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = [pool.submit(run_forget), pool.submit(run_correct)]
            outcomes = [future.result() for future in outcomes]
        require(sum(1 for _, state, _ in outcomes if state == "ok") == 1, outcomes)
        require(sum(1 for _, state, _ in outcomes if state == "error") == 1, outcomes)
        current = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(current.current_revision == 2, current)
        inspection = inspect_primary_memory_operations(root, memory_id=memory_id)
        require(not inspection.corrupt, inspection)
        if current.lifecycle_state == "hidden":
            require(len(inspection.pending) == 1, inspection)
            require(inspection.pending[0].operation_kind == "forget", inspection)
        else:
            require(current.lifecycle_state == "active", current)
            require(not inspection.pending, inspection)


def main() -> None:
    concurrent_different_forgets()
    concurrent_same_forget()
    correct_forget_one_winner()
    print("Phase I-4C1 Primary Forget concurrency smoke passed")


if __name__ == "__main__":
    main()
