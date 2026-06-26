"""Verify I-4C1 commits N+1 hidden after a real I-3 correction."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import (
    CHARACTER,
    NAMESPACE,
    prepared_store,
    require,
)
from relaylm.relaymem_primary_correction import (
    apply_primary_memory_correction,
    preflight_primary_memory_correction,
)
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import (
    apply_primary_memory_forget_hidden_successor,
    preflight_primary_memory_forget,
)
from relaylm.relaymem_primary_recall import _load_control_state

NOW = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)


def main() -> None:
    with prepared_store() as (root, memory_id):
        correction = preflight_primary_memory_correction(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            corrected_title="好きな飲み物（訂正済み）",
            corrected_summary="好きな飲み物は緑茶です。",
            reason="元の内容を訂正するため",
            operation_id="phase-i4c1-correct-before-forget",
            now=NOW,
        )
        corrected = apply_primary_memory_correction(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            operation_id="phase-i4c1-correct-before-forget",
            apply_token=correction["apply_token"],
            now=NOW,
        )
        require(corrected["status"] == "applied", corrected)
        active = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id
        )
        require(active.lifecycle_state == "active", active)
        require(active.mutation_state == "none", active)
        require(active.current_revision == 2, active)
        prior_physical = active.current_physical_id
        prior_page = root / active.relative_path
        prior_bytes = prior_page.read_bytes()

        forget = preflight_primary_memory_forget(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=2,
            expected_lifecycle_state="active",
            reason="訂正済みの記憶を通常検索から外すため",
            operation_id="phase-i4c1-forget-corrected",
            now=NOW,
        )
        result = apply_primary_memory_forget_hidden_successor(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=2,
            expected_lifecycle_state="active",
            reason="訂正済みの記憶を通常検索から外すため",
            operation_id="phase-i4c1-forget-corrected",
            apply_token=forget["apply_token"],
            now=NOW,
        )
        require(result.status == "hidden_successor_published", result)
        require(result.prior_revision == 2, result)
        require(result.result_revision == 3, result)
        require(prior_page.read_bytes() == prior_bytes, "corrected page changed")

        hidden = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id
        )
        require(hidden.lifecycle_state == "hidden", hidden)
        require(hidden.mutation_state == "recovery_required", hidden)
        require(hidden.retrieval_eligible is False, hidden)
        require(hidden.current_revision == 3, hidden)
        require(hidden.current_physical_id != prior_physical, hidden)
        require(hidden.metadata["prior_physical_id"] == prior_physical, hidden)
        require(hidden.metadata["memory_id"] == memory_id, hidden)

        control, reasons = _load_control_state(root)
        require(control is not None and not reasons, reasons)
        require(
            all(
                item.get("idempotency_key") != hidden.current_physical_id
                for item in (*control["index"], *control["log"])
            ),
            "M3f/M3g unexpectedly advanced controls",
        )
        print("Phase I-4C1 corrected-revision Forget smoke passed")


if __name__ == "__main__":
    main()
