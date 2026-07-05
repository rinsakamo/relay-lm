"""UI-B1A read-only lifecycle visibility projection smoke."""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.config import RelayLMConfig
from relaylm.relaymem_slp_queue_record import (
    canonical_json_bytes,
    derive_dispatch_key,
    derive_job_id,
    format_timestamp,
    record_filename,
    validate_record_mapping,
)
from relaylm.soul_lab_lifecycle_visibility_projection import (
    _public_lifecycle,
    build_lab_lifecycle_visibility_projection,
)
from relaylm.soul_lab_observation_projection import LabObservationScope

NOW = datetime(2026, 6, 27, 6, 0, tzinfo=timezone.utc)
PRIVATE_CANARIES = (
    "好きな飲み物は紅茶です。",
    "slp-job-v0:",
    "slp-dispatch-v0:",
    "claim-secret-token",
    "Traceback",
    "/queue/",
    "/durable/",
)


def config(queue_root: Path, durable_root: Path) -> RelayLMConfig:
    return RelayLMConfig(
        backends={"local_backend": {"base_url": "http://127.0.0.1:9/v1"}},
        model_routes={
            "relaylm-default": {
                "backend": "local_backend",
                "character_id": CHARACTER,
                "memory_namespace": NAMESPACE,
                "mode": "memory_light",
            }
        },
        characters={CHARACTER: {"soul": "configured", "output_policy": "configured"}},
        relaymem_slp_queue_root=str(queue_root),
        relaymem_slp_durable_finalization_root=str(durable_root),
    )


def write_durable_markers(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    locators = {"pending": "1" * 64, "complete": "2" * 64, "isolated": "3" * 64}
    for name, locator in locators.items():
        (root / f"durable-finalization-v0-{locator}.base.json").write_text("{}\n", encoding="utf-8")
        (root / f"durable-finalization-v0-{locator}.seal.json").write_text("{}\n", encoding="utf-8")
        if name == "complete":
            (root / f"durable-finalization-completion-v0-{locator}.json").write_text("{}\n", encoding="utf-8")
        if name == "isolated":
            (root / f"durable-finalization-v0-{locator}.segment-isolation.json").write_text("{}\n", encoding="utf-8")


def record(state: str, index: int, *, failure_class: str = "none", terminal_reason_id: str = "none") -> dict[str, object]:
    base = {
        "schema_version": "relaymem.slp_durable_job.v0",
        "job_id": "",
        "dispatch_idempotency_key": "",
        "dispatch_key_version": "relaymem.slp_dispatch_key.v0",
        "candidate_schema_version": "relaymem.slp_enqueue_candidate.v0",
        "candidate_kind": "relayslp_deferred_job",
        "trigger_mode": "turn_end",
        "processing_stage": "primary_formation",
        "source_event_kind": "turn",
        "run_id": f"ui-b1a-run-{index}",
        "turn_index": index,
        "session_id": None,
        "namespace": NAMESPACE,
        "source_count": 1,
        "source_lineage_fingerprint": f"{index + 10:064x}"[-64:],
        "source_admission_status": "eligible_for_enqueue",
        "runtime_terminal_status": "completed",
        "persistence_policy_status": "allowed",
        "state": state,
        "record_revision": 1,
        "created_at": format_timestamp(NOW),
        "updated_at": format_timestamp(NOW),
        "attempt_count": 0,
        "claim_generation": 0,
        "claim_owner": "",
        "lease_token": "",
        "lease_acquired_at": None,
        "lease_expires_at": None,
        "retry_class": "unclassified",
        "retry_not_before": None,
        "failure_class": failure_class,
        "terminal_reason_id": "" if state in {"queued", "claimed"} else terminal_reason_id,
    }
    if state == "claimed":
        base.update({
            "record_revision": 2,
            "attempt_count": 1,
            "claim_generation": 1,
            "claim_owner": "ui-b1a-worker",
            "lease_token": "claim-secret-token",
            "lease_acquired_at": format_timestamp(NOW),
            "lease_expires_at": format_timestamp(NOW + timedelta(minutes=5)),
        })
    dispatch = derive_dispatch_key(base)
    base["dispatch_idempotency_key"] = dispatch
    base["job_id"] = derive_job_id(dispatch)
    errors = validate_record_mapping(base)
    require(errors == (), errors)
    return base


def write_queue_records(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    records = [
        record("queued", 0),
        record("claimed", 1),
        record("succeeded", 2),
        record("failed", 3, failure_class="policy_held", terminal_reason_id="held_by_policy"),
        record("failed", 4, failure_class="policy_blocked", terminal_reason_id="blocked_by_policy"),
        record("dead_letter", 5, failure_class="worker_failed", terminal_reason_id="terminal_failed"),
    ]
    for item in records:
        path = root / record_filename(str(item["dispatch_idempotency_key"]))
        path.write_bytes(canonical_json_bytes(item))


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        queue_root = tmp / "queue"
        durable_root = tmp / "durable"
        write_queue_records(queue_root)
        write_durable_markers(durable_root)

        with prepared_store() as (store_root, memory_id):
            scope = LabObservationScope(
                known=True,
                available=True,
                character_id=CHARACTER,
                namespace=NAMESPACE,
                store_root=str(store_root),
                reason_ids=(),
            )
            projection = build_lab_lifecycle_visibility_projection(scope, config=config(queue_root, durable_root))
            require(projection.schema_ == "relaylm.lab.lifecycle_visibility.v0", projection)
            require(projection.read_only is True, projection)
            require(projection.mutation_controls_exposed is False, projection)
            require(projection.scheduler_controls_exposed is False, projection)
            require(projection.repair_controls_exposed is False, projection)
            require(projection.raw_content_included is False, projection)
            require(projection.raw_paths_included is False, projection)
            require(projection.raw_private_identifiers_included is False, projection)
            item = next(entry for entry in projection.memory_items if entry.memory_id == memory_id)
            require(item.current_lifecycle_state == "active", item)
            require(item.current_revision == 1, item)
            require(item.current_physical_status == "current", item)
            require(item.retrieval_eligible is True, item)
            require(item.historical_used_memory_remains_unchanged is True, item)

            require(projection.durable_finalization.status == "mixed", projection.durable_finalization)
            require(projection.durable_finalization.pending_count == 1, projection.durable_finalization)
            require(projection.durable_finalization.complete_count == 1, projection.durable_finalization)
            require(projection.durable_finalization.isolated_count == 1, projection.durable_finalization)
            require(projection.durable_finalization.content_free is True, projection.durable_finalization)
            require(projection.durable_finalization.locator_values_included is False, projection.durable_finalization)
            require(projection.durable_finalization.path_values_included is False, projection.durable_finalization)

            queue = projection.queue_worker
            require(queue.status == "mixed", queue)
            require(queue.queued_count == 1, queue)
            require(queue.processing_count == 1, queue)
            require(queue.formed_count == 1, queue)
            require(queue.held_count == 1, queue)
            require(queue.blocked_count == 1, queue)
            require(queue.failed_count == 1, queue)
            require(queue.scheduler_controls_exposed is False, queue)
            require(queue.worker_controls_exposed is False, queue)
            require(queue.queue_identifiers_included is False, queue)
            require(queue.claim_values_included is False, queue)

            fresh = projection.fresh_conversation
            require(fresh.browser_local_session_reset_visible is True, fresh)
            require(fresh.durable_memory_store_reset is False, fresh)
            require(fresh.durable_memory_store_retained is True, fresh)
            require(fresh.active_current_memories_remain_retrieval_eligible is True, fresh)
            require(fresh.hidden_or_current_ineligible_memories_remain_excluded is True, fresh)
            require(fresh.home_transcript_is_durable_source is False, fresh)

            require(_public_lifecycle("active", "none") == "active", "active vocabulary")
            require(_public_lifecycle("hidden", "none") == "hidden", "hidden vocabulary")
            require(_public_lifecycle("active", "prepared") == "prepared", "prepared vocabulary")
            require(_public_lifecycle("active", "recovery_required") == "recovery_required", "recovery vocabulary")
            require(_public_lifecycle("active", "corrupt") == "corrupt", "corrupt vocabulary")

            public = json.dumps(
                projection.model_dump(mode="json", by_alias=True),
                ensure_ascii=False,
                sort_keys=True,
            )
            for canary in PRIVATE_CANARIES:
                require(canary not in public, (canary, public))

    print("UI-B1A lifecycle visibility API smoke passed")


if __name__ == "__main__":
    main()
