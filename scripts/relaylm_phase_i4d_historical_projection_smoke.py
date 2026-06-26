"""I-4D immutable used-memory receipt plus lifecycle overlay smoke."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_forget import (
    apply_primary_memory_forget,
    preflight_primary_memory_forget,
)
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

NOW = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
INJECTED = "好きな飲み物は紅茶です。"
REASON = "I4D_HISTORY_REASON_CANARY"


def main() -> None:
    with prepared_store() as (root, memory_id):
        run_id = "i4d-historical-run"
        require(write_run_receipt(root, {
            "schema": RUN_RECEIPT_SCHEMA,
            "runtime_private": True,
            "read_model_only": True,
            "request_id": "i4d-historical-request",
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
        }), "run receipt")
        require(write_used_receipt(root, {
            "schema": USED_RECEIPT_SCHEMA,
            "runtime_private": True,
            "read_model_only": True,
            "request_id": "i4d-historical-request",
            "run_id": run_id,
            "character_id": CHARACTER,
            "namespace": NAMESPACE,
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
        }), "used receipt")
        used_path = next((root / ".relaylm-lab-observation-v0/used").glob("*.json"))
        before = used_path.read_bytes()
        scope = LabObservationScope(
            known=True, available=True, character_id=CHARACTER,
            namespace=NAMESPACE, store_root=str(root), reason_ids=(),
        )
        active = build_lab_memory_used_projection(scope)
        item = active.items[0]
        require(item.injected_summary == INJECTED, item)
        require(item.current_summary == INJECTED, item)
        require(item.current_lifecycle_state == "active", item)
        require(item.representation_changed is False, item)
        require(item.lifecycle_changed is False, item)

        preflight = preflight_primary_memory_forget(
            store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE,
            memory_id=memory_id, expected_revision=1,
            expected_lifecycle_state="active", reason=REASON,
            operation_id="i4d-history-forget", now=NOW,
        )
        apply_primary_memory_forget(
            store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE,
            memory_id=memory_id, expected_revision=1,
            expected_lifecycle_state="active", reason=REASON,
            operation_id="i4d-history-forget",
            apply_token=str(preflight["apply_token"]), now=NOW,
        )
        hidden = build_lab_memory_used_projection(scope)
        item = hidden.items[0]
        require(item.injected_summary == INJECTED, item)
        require(item.current_summary is None, item)
        require(item.current_lifecycle_state == "hidden", item)
        require(item.representation_changed is False, item)
        require(item.lifecycle_changed is True, item)
        require(used_path.read_bytes() == before, "historical receipt changed")
        public = hidden.model_dump_json()
        require(REASON not in public, public)
        require(str(preflight["apply_token"]) not in public, public)

    print("Phase I-4D historical lifecycle projection smoke passed")


if __name__ == "__main__":
    main()
