"""PR3 SOUL Lab shared read-context behavior-preservation smoke."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.soul_lab_observation_projection import (
    LabObservationScope,
    build_lab_memory_used_projection,
)
from relaylm.soul_lab_observation_store import (
    RUN_RECEIPT_SCHEMA,
    USED_RECEIPT_SCHEMA,
    write_run_receipt,
    write_used_receipt,
)
from relaylm.soul_lab_used_memory_lifecycle_projection import (
    build_lab_memory_used_lifecycle_projection,
)

NOW = datetime(2026, 7, 5, 0, 0, tzinfo=timezone.utc)
INJECTED = "好きな飲み物は紅茶です。"


def _scope(root: object) -> LabObservationScope:
    return LabObservationScope(
        known=True,
        available=True,
        character_id=CHARACTER,
        namespace=NAMESPACE,
        store_root=str(root),
        reason_ids=(),
    )


def _run_payload(run_id: str) -> dict[str, object]:
    return {
        "schema": RUN_RECEIPT_SCHEMA,
        "runtime_private": True,
        "read_model_only": True,
        "request_id": f"{run_id}-request",
        "run_id": run_id,
        "character_id": CHARACTER,
        "namespace": NAMESPACE,
        "started_at": NOW.isoformat(),
        "completed_at": NOW.isoformat(),
        "duration_ms": 0,
        "response_mode": "non_stream",
        "http_status": 200,
        "relayrun_status": "completed",
        "relayctx_repack_status": "applied",
        "relayctx_unpack_status": "completed",
        "slp_status": "disabled",
        "recovery_required": False,
        "reason_ids": [],
    }


def _used_payload(
    *,
    run_id: str,
    memory_id: str,
    character_id: str = CHARACTER,
    namespace: str = NAMESPACE,
) -> dict[str, object]:
    return {
        "schema": USED_RECEIPT_SCHEMA,
        "runtime_private": True,
        "read_model_only": True,
        "request_id": f"{run_id}-request",
        "run_id": run_id,
        "character_id": character_id,
        "namespace": namespace,
        "retrieval_attempted": True,
        "candidate_discovered": True,
        "selected": True,
        "relayctx_injection_performed": True,
        "backend_bound_included": True,
        "items": [{
            "memory_id": memory_id,
            "injected_summary": INJECTED,
            "source_kind": "preference",
        }],
        "captured_at": NOW.isoformat(),
        "reason_ids": [],
    }


def _assert_empty_pair(scope: LabObservationScope, reason: str | None = None) -> None:
    used = build_lab_memory_used_projection(scope)
    lifecycle = build_lab_memory_used_lifecycle_projection(scope)
    require(used.availability == "empty", used)
    require(lifecycle.availability == "empty", lifecycle)
    require(used.items == [], used)
    require(lifecycle.items == [], lifecycle)
    if reason is not None:
        require(reason in used.bounded_reason_ids, used.bounded_reason_ids)
        require(reason in lifecycle.bounded_reason_ids, lifecycle.bounded_reason_ids)


def main() -> None:
    unavailable = LabObservationScope(
        known=True,
        available=False,
        character_id=CHARACTER,
        namespace=NAMESPACE,
        store_root=None,
        reason_ids=("character_store_unavailable",),
    )
    used = build_lab_memory_used_projection(unavailable)
    lifecycle = build_lab_memory_used_lifecycle_projection(unavailable)
    require(used.availability == "unavailable", used)
    require(lifecycle.availability == "unavailable", lifecycle)
    require(used.bounded_reason_ids == ["character_store_unavailable"], used)
    require(lifecycle.bounded_reason_ids == ["character_store_unavailable"], lifecycle)

    with prepared_store() as (root, _memory_id):
        scope = _scope(root)
        _assert_empty_pair(scope)

    with prepared_store() as (root, _memory_id):
        run_id = "pr3-no-used-receipt"
        require(write_run_receipt(str(root), _run_payload(run_id)), "run receipt")
        scope = _scope(root)
        _assert_empty_pair(scope)
        used = build_lab_memory_used_projection(scope)
        lifecycle = build_lab_memory_used_lifecycle_projection(scope)
        require(used.run_id == run_id, used)
        require(lifecycle.run_id == run_id, lifecycle)
        require(used.response_generation_completed is True, used)
        require(lifecycle.response_generation_completed is True, lifecycle)

    with prepared_store() as (root, memory_id):
        run_id = "pr3-used-match"
        require(write_run_receipt(str(root), _run_payload(run_id)), "run receipt")
        require(
            write_used_receipt(str(root), _used_payload(run_id=run_id, memory_id=memory_id)),
            "used receipt",
        )
        scope = _scope(root)
        used = build_lab_memory_used_projection(scope)
        lifecycle = build_lab_memory_used_lifecycle_projection(scope)
        require(used.availability == "available", used)
        require(lifecycle.availability == "available", lifecycle)
        require(used.items[0].current_summary == INJECTED, used.items[0])
        require(lifecycle.items[0].current_summary == INJECTED, lifecycle.items[0])
        require(lifecycle.items[0].current_lifecycle_state == "active", lifecycle.items[0])

    with prepared_store() as (root, memory_id):
        run_id = "pr3-used-mismatch"
        require(write_run_receipt(str(root), _run_payload(run_id)), "run receipt")
        require(
            write_used_receipt(
                str(root),
                _used_payload(
                    run_id=run_id,
                    memory_id=memory_id,
                    character_id=CHARACTER,
                    namespace="other-namespace",
                ),
            ),
            "mismatched used receipt",
        )
        _assert_empty_pair(_scope(root), "observation_receipt_scope_mismatch")

    print("PR3 SOUL Lab read-context projection smoke passed")


if __name__ == "__main__":
    main()
