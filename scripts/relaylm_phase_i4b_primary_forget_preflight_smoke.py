"""Read-only Forget preflight, token, history, and no-write smoke."""
from __future__ import annotations

from datetime import datetime, timezone

from relaylm.relaymem_primary_forget import (
    HISTORY_SCHEMA,
    PREFLIGHT_RESPONSE_SCHEMA,
    list_primary_memory_forget_history,
    preflight_primary_memory_forget,
    validate_primary_memory_forget_token,
)
from relaylm.relaymem_primary_mutation_coordinator import (
    inspect_primary_memory_operations,
)
from _relaylm_phase_i4b_test_support import (
    CHARACTER,
    NAMESPACE,
    prepared_store,
    require,
    snapshot_tree,
)


def main() -> None:
    with prepared_store() as (root, memory_id):
        before = snapshot_tree(root)
        issued = datetime(2026, 6, 25, 0, 0, tzinfo=timezone.utc)
        preflight = preflight_primary_memory_forget(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason="今後の通常会話では検索対象から外すため",
            operation_id="phase-i4b-forget-op",
            now=issued,
        )
        require(preflight["schema"] == PREFLIGHT_RESPONSE_SCHEMA, preflight)
        require(preflight["status"] == "ready", preflight)
        require(preflight["read_only"] is True, preflight)
        require(preflight["memory_id"] == memory_id, preflight)
        require(len(preflight["memory_title"]) <= 160, preflight)
        require(len(preflight["bounded_summary"]) <= 512, preflight)
        require(preflight["current_revision"] == 1, preflight)
        require(preflight["current_lifecycle_state"] == "active", preflight)
        require(preflight["target_revision"] == 2, preflight)
        require(preflight["target_lifecycle_state"] == "hidden", preflight)
        require(
            preflight["effects"]
            == {
                "ordinary_retrieval_excluded": True,
                "relayctx_injection_excluded": True,
                "physical_deletion": False,
                "audit_evidence_retained": True,
                "historical_used_memory_unchanged": True,
            },
            preflight,
        )
        validated = validate_primary_memory_forget_token(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason="今後の通常会話では検索対象から外すため",
            operation_id="phase-i4b-forget-op",
            apply_token=preflight["apply_token"],
            now=issued,
        )
        require(validated["valid"] is True, validated)
        history = list_primary_memory_forget_history(
            store_root=str(root),
            namespace=NAMESPACE,
            memory_id=memory_id,
        )
        require(history["schema"] == HISTORY_SCHEMA, history)
        require(history["source"] == "relaylm_runtime", history)
        require(history["read_only"] is True, history)
        require(history["forget_count"] == 0, history)
        require(history["items"] == [], history)
        inspection = inspect_primary_memory_operations(root, memory_id=memory_id)
        require(not inspection.operations, inspection)
        require(snapshot_tree(root) == before, "read-only Forget path mutated store")

        public_text = repr(preflight) + repr(history)
        for forbidden in (
            str(root),
            "page_digest",
            "current_physical_id",
            "lineage_fingerprint",
            "queue",
            "lease",
            "prompt",
            "transcript",
            "Traceback",
        ):
            require(forbidden not in public_text, forbidden)

    print("Phase I-4B Primary Forget preflight smoke passed")


if __name__ == "__main__":
    main()
