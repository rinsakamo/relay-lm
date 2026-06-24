"""Crash/recovery and fail-closed visibility smoke for Phase I-3."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from relaylm import _relaymem_primary_index_log_apply_io as apply_io
from relaylm.relaymem_primary_correction import (
    PrimaryCorrectionError,
    apply_primary_memory_correction,
    list_primary_memory_corrections,
    preflight_primary_memory_correction,
    recover_primary_memory_corrections,
)
from relaylm.relaymem_primary_index_log_reconciliation import (
    build_relaymem_primary_index_log_reconciliation_preflight,
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
SYNTHETIC_FAULTS = (
    "after_audit_prepared",
    "after_successor_page_publication",
    "after_reconciliation",
    "after_audit_finalization",
)


class InjectedIndexAppliedCrash(BaseException):
    """Simulate process loss after durable index replace and before log apply."""


def build_fixture(fault: str) -> tuple[tempfile.TemporaryDirectory[str], Path, str, Any]:
    directory = tempfile.TemporaryDirectory(dir=REPO_ROOT)
    root = Path(directory.name)
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
    return directory, scoped, memory_id, scope


def issue_token(scoped: Path, memory_id: str, fault: str) -> str:
    return str(
        preflight_primary_memory_correction(
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
    )


def assert_converged(
    *, scoped: Path, memory_id: str, scope: Any, token: str, fault: str
) -> None:
    current = build_lab_recent_memory_projection(scope, limit=20)
    require(len(current.items) == 1, current.model_dump())
    require(current.items[0].revision == 2, current.model_dump())
    require("after correction" in current.items[0].bounded_summary, current.model_dump())
    require(len(list(scoped.glob("memory/mem/primary/*/*.md"))) == 2, fault)
    history = list_primary_memory_corrections(
        store_root=str(scoped), namespace=NAMESPACE, memory_id=memory_id
    )
    require(history["correction_count"] == 1, history)

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


def run_synthetic_fault(fault: str) -> None:
    directory, scoped, memory_id, scope = build_fixture(fault)
    try:
        token = issue_token(scoped, memory_id, fault)
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
            expected = (
                "response_lost"
                if fault == "after_audit_finalization"
                else "reconciliation_required"
            )
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
            require(before_recovery.items[0].revision == 1, before_recovery.model_dump())
            require(
                "before correction" in before_recovery.items[0].bounded_summary,
                before_recovery.model_dump(),
            )
            recovered = recover_primary_memory_corrections(
                store_root=str(scoped), namespace=NAMESPACE
            )
            require(recovered == {"recovered": 1, "failed": 0}, recovered)
        assert_converged(
            scoped=scoped,
            memory_id=memory_id,
            scope=scope,
            token=token,
            fault=fault,
        )
    finally:
        directory.cleanup()


def run_index_applied_log_pending_fault() -> None:
    fault = "after_index_apply_before_log_apply"
    directory, scoped, memory_id, scope = build_fixture(fault)
    captured_receipts: list[dict[str, Any]] = []
    original_writer = __import__(
        "relaylm.relaymem_primary_correction", fromlist=["apply_relaymem_primary_page_write"]
    ).apply_relaymem_primary_page_write
    correction_module = __import__("relaylm.relaymem_primary_correction", fromlist=["*"])
    original_replace = apply_io._atomic_replace_control

    def capture_writer(*args: object, **kwargs: object) -> dict[str, Any]:
        result = original_writer(*args, **kwargs)
        receipt = result.get("receipt")
        if isinstance(receipt, dict):
            captured_receipts.append(receipt)
        return result

    def crash_after_index(*args: object, **kwargs: object) -> dict[str, Any]:
        result = original_replace(*args, **kwargs)
        if kwargs.get("role") == "index" and result.get("reconciled") is True:
            raise InjectedIndexAppliedCrash()
        return result

    try:
        token = issue_token(scoped, memory_id, fault)
        correction_module.apply_relaymem_primary_page_write = capture_writer
        apply_io._atomic_replace_control = crash_after_index
        try:
            apply_primary_memory_correction(
                store_root=str(scoped),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                operation_id=f"operation-{fault}",
                apply_token=token,
            )
        except InjectedIndexAppliedCrash:
            pass
        else:
            raise AssertionError("index-applied crash did not fire")
        finally:
            apply_io._atomic_replace_control = original_replace
            correction_module.apply_relaymem_primary_page_write = original_writer

        require(captured_receipts, "M3e receipt not captured")
        partial = build_relaymem_primary_index_log_reconciliation_preflight(
            receipt=captured_receipts[-1],
            root_path=str(scoped),
            enabled=True,
            dry_run_only=True,
        )
        require(partial["status"] == "log_update_required", partial)
        require(partial["index_update_required"] is False, partial)
        require(partial["log_update_required"] is True, partial)

        # Canonical index/log disagreement must not expose the prepared successor.
        before_recovery = build_lab_recent_memory_projection(scope, limit=20)
        require(
            not any(item.revision == 2 for item in before_recovery.items),
            before_recovery.model_dump(),
        )
        require(
            not any("after correction" in item.bounded_summary for item in before_recovery.items),
            before_recovery.model_dump(),
        )

        recovered = recover_primary_memory_corrections(
            store_root=str(scoped), namespace=NAMESPACE
        )
        require(recovered == {"recovered": 1, "failed": 0}, recovered)
        assert_converged(
            scoped=scoped,
            memory_id=memory_id,
            scope=scope,
            token=token,
            fault=fault,
        )
    finally:
        apply_io._atomic_replace_control = original_replace
        correction_module.apply_relaymem_primary_page_write = original_writer
        directory.cleanup()


def main() -> None:
    for fault in SYNTHETIC_FAULTS:
        run_synthetic_fault(fault)
    run_index_applied_log_pending_fault()
    print("Phase I-3 Primary MEM Correct fault/recovery smoke passed")


if __name__ == "__main__":
    main()
