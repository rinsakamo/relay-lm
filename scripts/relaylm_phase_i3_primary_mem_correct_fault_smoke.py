"""Crash/recovery and fail-closed visibility smoke for Phase I-3."""
from __future__ import annotations

import tempfile
from pathlib import Path

from relaylm.relaymem_primary_correction import (
    PrimaryCorrectionError,
    apply_primary_memory_correction,
    list_primary_memory_corrections,
    preflight_primary_memory_correction,
    recover_primary_memory_corrections,
)
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.soul_lab_app import create_app
from relaylm.soul_lab_observation_projection import (
    build_lab_recent_memory_projection,
    resolve_lab_observation_scope,
)
from relaylm_phase_i1_two_turn_primary_recall_smoke import CHARACTER, NAMESPACE
from _relaylm_phase_i3_test_support import form_primary_memory, require, write_config

REPO_ROOT = Path(__file__).resolve().parents[1]
FAULTS = (
    "after_audit_prepared",
    "after_successor_page_publication",
    "after_index_apply",
    "after_reconciliation",
    "after_audit_finalization",
)


def main() -> None:
    for fault in FAULTS:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            root = Path(directory)
            queue = root / "queue"
            protected = root / "protected"
            store = root / "store"
            queue.mkdir()
            protected.mkdir()
            store.mkdir()
            scoped_value = resolve_relaymem_character_store_root(str(store), CHARACTER)
            require(scoped_value is not None, fault)
            scoped = Path(scoped_value)
            memory_id = form_primary_memory(
                scoped,
                namespace=NAMESPACE,
                candidate_id=f"phase-i3-fault-{fault}",
                title="before correction",
                summary="before correction summary",
            )
            config_path = root / "config.yaml"
            write_config(
                config_path,
                port=9,
                queue=queue,
                protected=protected,
                store=store,
                enqueue_enabled=False,
            )
            app = create_app(str(config_path))
            scope = resolve_lab_observation_scope(
                app.state.relaylm_config,
                character_id=CHARACTER,
                namespace=NAMESPACE,
            )
            token = preflight_primary_memory_correction(
                store_root=str(scoped),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                corrected_title="after correction",
                corrected_summary="after correction summary",
                reason=f"fault verification {fault}",
                operation_id=f"operation-{fault}",
            )["apply_token"]
            try:
                apply_primary_memory_correction(
                    store_root=str(scoped),
                    character_id=CHARACTER,
                    namespace=NAMESPACE,
                    memory_id=memory_id,
                    expected_revision=1,
                    operation_id=f"operation-{fault}",
                    apply_token=token,
                    fault_at=fault,
                )
            except PrimaryCorrectionError as error:
                expected = "response_lost" if fault == "after_audit_finalization" else "reconciliation_required"
                require(error.code == expected, (fault, error.code))
            else:
                raise AssertionError(f"fault did not fire: {fault}")

            before_recovery = build_lab_recent_memory_projection(scope, limit=20)
            require(len(before_recovery.items) == 1, before_recovery.model_dump())
            if fault == "after_audit_finalization":
                require(before_recovery.items[0].revision == 2, before_recovery.model_dump())
                recovered = recover_primary_memory_corrections(
                    store_root=str(scoped), namespace=NAMESPACE
                )
                require(recovered == {"recovered": 0, "failed": 0}, recovered)
            else:
                # A prepared successor is never visible until the immutable applied
                # receipt finalizes the revision transition.
                require(before_recovery.items[0].revision == 1, before_recovery.model_dump())
                require(
                    "before correction" in before_recovery.items[0].bounded_summary,
                    before_recovery.model_dump(),
                )
                recovered = recover_primary_memory_corrections(
                    store_root=str(scoped), namespace=NAMESPACE
                )
                require(recovered == {"recovered": 1, "failed": 0}, recovered)

            after_recovery = build_lab_recent_memory_projection(scope, limit=20)
            require(len(after_recovery.items) == 1, after_recovery.model_dump())
            require(after_recovery.items[0].revision == 2, after_recovery.model_dump())
            require(
                "after correction" in after_recovery.items[0].bounded_summary,
                after_recovery.model_dump(),
            )
            require(len(list(scoped.glob("memory/mem/primary/*/*.md"))) == 2, fault)
            history = list_primary_memory_corrections(
                store_root=str(scoped), namespace=NAMESPACE, memory_id=memory_id
            )
            require(history["correction_count"] == 1, history)

            # Response loss and recovery both converge exact replay to the same
            # immutable success result rather than creating revision 3.
            replay = apply_primary_memory_correction(
                store_root=str(scoped),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                operation_id=f"operation-{fault}",
                apply_token=token,
            )
            require(replay["idempotent_replay"] is True, replay)
            require(replay["result_revision"] == 2, replay)
            require(len(list(scoped.glob("memory/mem/primary/*/*.md"))) == 2, fault)

    print("Phase I-3 Primary MEM Correct fault/recovery smoke passed")


if __name__ == "__main__":
    main()
