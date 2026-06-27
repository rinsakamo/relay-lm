"""Phase I-4F crash/fault and fail-closed retrieval validation smoke."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import apply_primary_memory_forget, preflight_primary_memory_forget
from relaylm.relaymem_primary_retrieval_eligibility import load_primary_retrieval_eligibility_index
from relaylm_phase_i4c2_primary_forget_fault_smoke import main as i4c2_fault_main
from relaylm_phase_i4d_primary_retrieval_exclusion_smoke import main as i4d_exclusion_main

NOW = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
REASON = "I4F_FAULT_REASON_CANARY"


def issue(root, memory_id: str, operation_id: str) -> str:
    return str(preflight_primary_memory_forget(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=REASON, operation_id=operation_id, now=NOW)["apply_token"])


def after_preflight_only_is_read_only() -> None:
    with prepared_store() as (root, memory_id):
        before = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        token = issue(root, memory_id, "i4f-after-preflight-only")
        after = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(after == before, (before, after))
        mutation_dir = root / "memory/mem/corrections/v0" / memory_id
        require(not list(mutation_dir.glob("*.prepared.json")), mutation_dir)
        require(not list(mutation_dir.glob("*.tombstone.json")), mutation_dir)
        index = load_primary_retrieval_eligibility_index(root, namespace=NAMESPACE)
        require(index.evaluate(after.current_physical_id).reason_id == "eligible_current_active", index)

        result = apply_primary_memory_forget(store_root=str(root), character_id=CHARACTER, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1, expected_lifecycle_state="active", reason=REASON, operation_id="i4f-after-preflight-only", apply_token=token, now=NOW)
        require(result.status == "applied", result)
        hidden = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(hidden.lifecycle_state == "hidden", hidden)
        require(hidden.retrieval_eligible is False, hidden)


def main() -> None:
    after_preflight_only_is_read_only()
    i4c2_fault_main()
    i4d_exclusion_main()
    print("Phase I-4F Forget fault validation smoke passed")


if __name__ == "__main__":
    main()
