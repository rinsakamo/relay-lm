"""Phase I-4D exclusion across representative Forget recovery states."""
from __future__ import annotations

from _relaylm_phase_i4b_test_support import NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm_phase_i4d_primary_retrieval_exclusion_smoke import (
    apply_forget,
    expect_fault,
    issue,
    prepared_and_recovery_states,
    recall,
)


def assert_fault_state_excluded(seam: str) -> None:
    with prepared_store() as (root, memory_id):
        active = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id
        )
        operation_id = f"i4d-recovery-{seam}"[:128]
        token = issue(root, memory_id, operation_id, 1)
        expect_fault(lambda: apply_forget(root, memory_id, operation_id, token, 1, seam))
        result = recall(root, [active.relative_path])
        require(result["primary_recall_runtime"]["selected_count"] == 0, (seam, result))


def main() -> None:
    prepared_and_recovery_states()
    for seam in (
        "after_m3g_index_before_log",
        "after_controls_reread_before_tombstone",
        "after_tombstone_publish_before_reread",
        "after_finalization_before_return",
    ):
        assert_fault_state_excluded(seam)
    print("Phase I-4D recovery state exclusion smoke passed")


if __name__ == "__main__":
    main()
