"""I-4C2 ownership smoke: governance finalizes without implementing I-4D M2 exclusion."""
from __future__ import annotations

from datetime import datetime, timezone

from _relaylm_phase_i4b_test_support import CHARACTER, NAMESPACE, prepared_store, require
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import (
    apply_primary_memory_forget,
    preflight_primary_memory_forget,
)
from relaylm.relaymem_primary_current_state import (
    load_primary_current_state_index,
    resolve_primary_current_identity,
)

NOW = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)


def main() -> None:
    with prepared_store() as (root, memory_id):
        before = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id
        )
        prior_physical = before.current_physical_id
        token = preflight_primary_memory_forget(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason="I-4C2 ownership boundary smoke",
            operation_id="phase-i4c2-ownership-boundary",
            now=NOW,
        )["apply_token"]
        result = apply_primary_memory_forget(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason="I-4C2 ownership boundary smoke",
            operation_id="phase-i4c2-ownership-boundary",
            apply_token=token,
            now=NOW,
        )
        require(result.status == "applied", result)

        governance = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id
        )
        require(governance.lifecycle_state == "hidden", governance)
        require(governance.mutation_state == "none", governance)
        require(governance.retrieval_eligible is False, governance)

        correction_projection = load_primary_current_state_index(
            root, namespace=NAMESPACE
        )
        prior_identity = resolve_primary_current_identity(
            correction_projection, prior_physical
        )
        require(prior_identity == (memory_id, 1, True), prior_identity)
        hidden_identity = resolve_primary_current_identity(
            correction_projection, governance.current_physical_id
        )
        require(hidden_identity == (memory_id, 1, False), hidden_identity)

        print("Phase I-4C2 ownership boundary smoke passed")


if __name__ == "__main__":
    main()
