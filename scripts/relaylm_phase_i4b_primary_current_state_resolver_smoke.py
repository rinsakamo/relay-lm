"""Canonical current-state resolver and Correct compatibility smoke."""
from __future__ import annotations

from relaylm.relaymem_primary_correction import (
    apply_primary_memory_correction,
    preflight_primary_memory_correction,
)
from relaylm.relaymem_primary_current_state import (
    PRIMARY_CURRENT_STATE_SCHEMA,
    load_primary_current_state_index,
    resolve_primary_current_identity,
    resolve_primary_current_state,
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
        state = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id, expected_revision=1
        )
        require(state.schema == PRIMARY_CURRENT_STATE_SCHEMA, state)
        require(state.lifecycle_state == "active", state)
        require(state.mutation_state == "none", state)
        require(state.retrieval_eligible is True, state)
        require(state.current_revision == 1, state)
        require(state.current_physical_id == memory_id, state)
        require(state.controls_valid and state.page_valid, state)
        require(snapshot_tree(root) == before, "resolver wrote to store")
        rendered = repr(state) + repr(state.to_log_dict())
        for forbidden in (
            memory_id,
            NAMESPACE,
            state.relative_path,
            state.page_digest,
            "好きな飲み物は紅茶です。",
        ):
            require(forbidden not in rendered, forbidden)

        index = load_primary_current_state_index(root, namespace=NAMESPACE)
        resolved = resolve_primary_current_identity(index, memory_id)
        require(resolved == (memory_id, 1, True), resolved)

        preflight = preflight_primary_memory_correction(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            corrected_title="好きな飲み物",
            corrected_summary="好きな飲み物はコーヒーです。",
            reason="ユーザーが明示的に訂正したため",
            operation_id="phase-i4b-correct-op",
        )
        applied = apply_primary_memory_correction(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            operation_id="phase-i4b-correct-op",
            apply_token=preflight["apply_token"],
        )
        require(applied["result_revision"] == 2, applied)

        state2 = resolve_primary_current_state(
            root, namespace=NAMESPACE, memory_id=memory_id, expected_revision=2
        )
        require(state2.memory_id == memory_id, state2)
        require(state2.current_revision == 2, state2)
        require(state2.current_physical_id != memory_id, state2)
        require(state2.lifecycle_state == "active", state2)
        require(state2.retrieval_eligible is True, state2)

        index2 = load_primary_current_state_index(root, namespace=NAMESPACE)
        prior = resolve_primary_current_identity(index2, memory_id)
        current = resolve_primary_current_identity(index2, state2.current_physical_id)
        require(prior == (memory_id, 2, False), prior)
        require(current == (memory_id, 2, True), current)

    print("Phase I-4B Primary current-state resolver smoke passed")


if __name__ == "__main__":
    main()
