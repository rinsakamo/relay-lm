"""I-4C2 shared-lock and one-winner concurrency smoke."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_correction import (
    PrimaryCorrectionError,
    apply_primary_memory_correction,
    preflight_primary_memory_correction,
)
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    apply_primary_memory_forget,
    apply_primary_memory_forget_hidden_successor,
    preflight_primary_memory_forget,
    recover_primary_memory_forget,
)
from relaylm.relaymem_primary_mutation_coordinator import (
    inspect_primary_memory_operations,
    primary_memory_mutation_lock_path,
)

NOW = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
REASON = "I4C2_CONCURRENCY_REASON"


def issue(root, memory_id: str, operation_id: str) -> str:
    return str(
        preflight_primary_memory_forget(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason=REASON,
            operation_id=operation_id,
            now=NOW,
        )["apply_token"]
    )


def apply(root, memory_id: str, operation_id: str, token: str):
    return apply_primary_memory_forget(
        store_root=str(root),
        character_id=CHARACTER,
        namespace=NAMESPACE,
        memory_id=memory_id,
        expected_revision=1,
        expected_lifecycle_state="active",
        reason=REASON,
        operation_id=operation_id,
        apply_token=token,
        now=NOW,
    )


def capture(callable_):
    try:
        return ("ok", callable_())
    except (PrimaryForgetError, PrimaryCorrectionError) as exc:
        return ("error", exc.code)


def exact_same_retry() -> None:
    with prepared_store() as (root, memory_id):
        operation_id = "phase-i4c2-concurrent-exact"
        token = issue(root, memory_id, operation_id)
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(
                pool.map(
                    lambda _: capture(lambda: apply(root, memory_id, operation_id, token)),
                    range(2),
                )
            )
        require(all(kind == "ok" for kind, _ in outcomes), outcomes)
        results = [value for _, value in outcomes]
        require(all(result.status == "applied" for result in results), results)
        require(sum(result.tombstone_created for result in results) == 1, results)
        require(sum(result.idempotent_replay for result in results) == 1, results)
        state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(state.lifecycle_state == "hidden" and state.mutation_state == "none", state)


def different_forget_operations() -> None:
    with prepared_store() as (root, memory_id):
        operations = ("phase-i4c2-concurrent-a", "phase-i4c2-concurrent-b")
        tokens = {operation: issue(root, memory_id, operation) for operation in operations}
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(capture, lambda op=operation: apply(root, memory_id, op, tokens[op]))
                for operation in operations
            ]
            outcomes = [future.result() for future in futures]
        successes = [value for kind, value in outcomes if kind == "ok"]
        errors = [value for kind, value in outcomes if kind == "error"]
        require(len(successes) >= 1, outcomes)
        require(sum(result.status == "applied" for result in successes) == 1, outcomes)
        require(all(result.status in {"applied", "already_hidden"} for result in successes), outcomes)
        require(all(code in {"operation_conflict", "target_not_active"} for code in errors), outcomes)
        mutation_dir = root / "memory/mem/corrections/v0" / memory_id
        require(len(list(mutation_dir.glob("*.tombstone.json"))) == 1, mutation_dir)
        inspection = inspect_primary_memory_operations(root, memory_id=memory_id)
        require(inspection.corrupt is False and not inspection.pending, inspection)


def correct_vs_forget() -> None:
    with prepared_store() as (root, memory_id):
        forget_operation = "phase-i4c2-race-forget"
        forget_token = issue(root, memory_id, forget_operation)
        correction_operation = "phase-i4c2-race-correct"
        correction = preflight_primary_memory_correction(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            corrected_title="競合訂正",
            corrected_summary="競合する訂正候補です。",
            reason="競合試験",
            operation_id=correction_operation,
            now=NOW,
        )

        def correct():
            return apply_primary_memory_correction(
                store_root=str(root),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                operation_id=correction_operation,
                apply_token=correction["apply_token"],
                now=NOW,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            forget_future = pool.submit(capture, lambda: apply(root, memory_id, forget_operation, forget_token))
            correct_future = pool.submit(capture, correct)
            outcomes = [forget_future.result(), correct_future.result()]
        successes = [value for kind, value in outcomes if kind == "ok"]
        require(len(successes) == 1, outcomes)
        inspection = inspect_primary_memory_operations(root, memory_id=memory_id)
        require(inspection.corrupt is False and not inspection.pending, inspection)
        state = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(state.current_revision == 2, state)
        require(state.lifecycle_state in {"active", "hidden"}, state)


def recovery_vs_explicit_retry() -> None:
    with prepared_store() as (root, memory_id):
        operation_id = "phase-i4c2-recovery-explicit-race"
        token = issue(root, memory_id, operation_id)
        try:
            apply_primary_memory_forget_hidden_successor(
                store_root=str(root),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                expected_lifecycle_state="active",
                reason=REASON,
                operation_id=operation_id,
                apply_token=token,
                now=NOW,
                fault_at="after_prepared_publication",
            )
        except PrimaryForgetError as exc:
            require(exc.code == "reconciliation_required", exc.code)
        else:
            raise AssertionError("prepare fault did not fire")

        with ThreadPoolExecutor(max_workers=2) as pool:
            recovery_future = pool.submit(
                capture,
                lambda: recover_primary_memory_forget(
                    store_root=str(root),
                    namespace=NAMESPACE,
                    memory_id=memory_id,
                    operation_id=operation_id,
                    now=NOW,
                ),
            )
            explicit_future = pool.submit(
                capture, lambda: apply(root, memory_id, operation_id, token)
            )
            outcomes = [recovery_future.result(), explicit_future.result()]
        require(all(kind == "ok" for kind, _ in outcomes), outcomes)
        require(all(value.status == "applied" for _, value in outcomes), outcomes)
        mutation_dir = root / "memory/mem/corrections/v0" / memory_id
        require(len(list(mutation_dir.glob("*.tombstone.json"))) == 1, mutation_dir)
        require(primary_memory_mutation_lock_path(root, memory_id).name == ".lock", "lock changed")


def main() -> None:
    exact_same_retry()
    different_forget_operations()
    correct_vs_forget()
    recovery_vs_explicit_retry()
    print("Phase I-4C2 Primary Forget concurrency smoke passed")


if __name__ == "__main__":
    main()
