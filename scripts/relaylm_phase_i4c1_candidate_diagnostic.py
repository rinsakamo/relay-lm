"""Emit bounded reason IDs for an I-4C1 candidate construction failure."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    apply_primary_memory_forget_hidden_successor,
    preflight_primary_memory_forget,
)
from relaylm.relaymem_primary_page_candidate import (
    build_relaymem_primary_hidden_page_candidate,
)
from relaylm.relaymem_primary_write_preflight import (
    build_relaymem_primary_write_preflight_dry_run,
)

NOW = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
REASON = "通常検索から外すため"
OPERATION = "phase-i4c1-candidate-diagnostic"


def main() -> None:
    with prepared_store() as (root, memory_id):
        token = preflight_primary_memory_forget(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason=REASON,
            operation_id=OPERATION,
            now=NOW,
        )["apply_token"]
        try:
            apply_primary_memory_forget_hidden_successor(
                store_root=str(root),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                expected_lifecycle_state="active",
                reason=REASON,
                operation_id=OPERATION,
                apply_token=token,
                now=NOW,
            )
        except PrimaryForgetError as exc:
            print("apply_error=", exc.code)
        mutation_dir = root / "memory/mem/corrections/v0" / memory_id
        files = list(mutation_dir.glob("*.prepared.json"))
        print("prepared_count=", len(files))
        if len(files) != 1:
            return
        prepared = json.loads(files[0].read_text(encoding="utf-8"))
        lineage = {
            "schema_version": "relaymem.primary_source_lineage.v0",
            "content_free": True,
            "content_included": False,
            "raw_text_included": False,
            "source_event_kind": prepared["source_event_kind"],
            "namespace": prepared["namespace"],
            "valid": True,
            "lineage_fingerprint": prepared["lineage_fingerprint"],
            "lineage_shape": {
                "source_event_id_present": True,
                "run_id_present": False,
                "session_id_present": False,
                "turn_index_present": False,
            },
            "blocked_reasons": [],
        }
        candidate = {
            "candidate_id": prepared["successor_candidate_id"],
            "source_event_kind": prepared["source_event_kind"],
            "memory_layer": "primary",
            "memory_kind": prepared["memory_kind"],
            "promotion_policy": "free_to_update",
            "safety_scope": "ordinary_memory",
        }
        preflight = build_relaymem_primary_write_preflight_dry_run(
            candidates=[candidate],
            source_lineage_artifact=lineage,
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        page = build_relaymem_primary_hidden_page_candidate(
            preflight_artifact=preflight,
            source_lineage_artifact=lineage,
            prepared_artifact=prepared,
        )
        print("preflight_operation_count=", preflight.get("operation_count"))
        print("preflight_reasons=", preflight.get("blocked_reasons"))
        print("page_count=", page.get("page_candidate_count"))
        print("page_reasons=", page.get("blocked_reasons"))


if __name__ == "__main__":
    main()
