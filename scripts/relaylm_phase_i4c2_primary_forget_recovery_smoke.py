"""I-4C2 normal, corrected-revision, replay, resolver, and leakage smoke."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

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
    PrimaryForgetError,
    apply_primary_memory_forget,
    preflight_primary_memory_forget,
    recover_primary_memory_forget,
)
from relaylm.relaymem_primary_mutation_coordinator import (
    inspect_primary_memory_operations,
    primary_memory_mutation_lock_path,
)
from relaylm.relaymem_primary_recall import _load_control_state

NOW = datetime(2026, 6, 26, 0, 0, tzinfo=timezone.utc)
REASON = "I4C2_REASON_CANARY_通常検索から外すため"


def issue(root, memory_id: str, operation_id: str, revision: int, reason: str = REASON) -> str:
    return str(
        preflight_primary_memory_forget(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=revision,
            expected_lifecycle_state="active",
            reason=reason,
            operation_id=operation_id,
            now=NOW,
        )["apply_token"]
    )


def apply(root, memory_id: str, operation_id: str, token: str, revision: int, reason: str = REASON, now=NOW):
    return apply_primary_memory_forget(
        store_root=str(root),
        character_id=CHARACTER,
        namespace=NAMESPACE,
        memory_id=memory_id,
        expected_revision=revision,
        expected_lifecycle_state="active",
        reason=reason,
        operation_id=operation_id,
        apply_token=token,
        now=now,
    )


def assert_finalized(root, memory_id: str, result_revision: int) -> tuple[str, dict]:
    state = resolve_primary_current_state(
        root, namespace=NAMESPACE, memory_id=memory_id
    )
    require(state.lifecycle_state == "hidden", state)
    require(state.mutation_state == "none", state)
    require(state.retrieval_eligible is False, state)
    require(state.current_revision == result_revision, state)
    require(state.page_valid is True and state.controls_valid is True, state)

    control, reasons = _load_control_state(root)
    require(control is not None and not reasons, reasons)
    index = [
        item for item in control["index"]
        if item.get("idempotency_key") == state.current_physical_id
    ]
    log = [
        item for item in control["log"]
        if item.get("idempotency_key") == state.current_physical_id
    ]
    require(len(index) == 1 and len(log) == 1, (index, log))
    require(index[0]["page_relative_path"] == state.relative_path, index)
    require(log[0]["page_relative_path"] == state.relative_path, log)
    require(index[0]["page_digest"] == state.page_digest, index)
    require(log[0]["page_digest"] == state.page_digest, log)

    mutation_dir = root / "memory/mem/corrections/v0" / memory_id
    tombstones = list(mutation_dir.glob("*.tombstone.json"))
    require(len(tombstones) == 1, tombstones)
    tombstone = json.loads(tombstones[0].read_text(encoding="utf-8"))
    require(tombstone["schema_version"] == "relaylm.mem.forget_tombstone.v0", tombstone)
    require(tombstone["runtime_private"] is True, tombstone)
    require(tombstone["status"] == "reconciled", tombstone)
    require(tombstone["page_converged"] is True, tombstone)
    require(tombstone["index_converged"] is True, tombstone)
    require(tombstone["log_converged"] is True, tombstone)
    require(tombstone["retrieval_exclusion_claimed"] is False, tombstone)
    require(tombstone["recovery_required"] is False, tombstone)
    return state.current_physical_id, tombstone


def normal_and_replay() -> None:
    with prepared_store() as (root, memory_id):
        prior = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        prior_path = root / prior.relative_path
        prior_bytes = prior_path.read_bytes()
        token = issue(root, memory_id, "phase-i4c2-normal", 1)
        alternate_token = issue(root, memory_id, "phase-i4c2-already-hidden", 1)

        result = apply(root, memory_id, "phase-i4c2-normal", token, 1)
        require(result.status == "applied", result)
        require(result.prepared_present is True, result)
        require(result.hidden_successor_present is True, result)
        require(result.page_converged is True, result)
        require(result.index_converged is True and result.log_converged is True, result)
        require(result.tombstone_present is True and result.tombstone_created is True, result)
        require(result.applied_receipt_present is False, result)
        require(result.idempotent_replay is False, result)
        require(result.lifecycle_state == "hidden" and result.mutation_state == "none", result)
        require(result.retrieval_eligible is False and result.recovery_required is False, result)
        require(result.prior_revision == 1 and result.result_revision == 2, result)
        require(prior_path.read_bytes() == prior_bytes, "prior active page changed")

        hidden_id, tombstone = assert_finalized(root, memory_id, 2)
        hidden_page = next(root.rglob(f"{hidden_id}.md")).read_text(encoding="utf-8")
        require(REASON not in hidden_page, "reason leaked to hidden page")
        require(token not in hidden_page, "token leaked to hidden page")

        replay = apply(
            root,
            memory_id,
            "phase-i4c2-normal",
            token,
            1,
            now=NOW + timedelta(hours=1),
        )
        require(replay.status == "applied", replay)
        require(replay.idempotent_replay is True, replay)
        require(replay.tombstone_created is False, replay)
        _, tombstone_after = assert_finalized(root, memory_id, 2)
        require(tombstone_after["tombstone_id"] == tombstone["tombstone_id"], tombstone_after)
        require(tombstone_after == tombstone, "exact replay changed tombstone")

        recovered = recover_primary_memory_forget(
            store_root=str(root),
            namespace=NAMESPACE,
            memory_id=memory_id,
            operation_id="phase-i4c2-normal",
            now=NOW + timedelta(days=1),
        )
        require(recovered.idempotent_replay is True, recovered)
        require(recovered.status == "applied", recovered)

        already_hidden = apply(
            root,
            memory_id,
            "phase-i4c2-already-hidden",
            alternate_token,
            1,
        )
        require(already_hidden.status == "already_hidden", already_hidden)
        require(already_hidden.result_revision == 2, already_hidden)

        for bad_token, bad_reason in (
            (token + "x", REASON),
            (token, REASON + "-different"),
        ):
            try:
                apply(
                    root,
                    memory_id,
                    "phase-i4c2-normal",
                    bad_token,
                    1,
                    reason=bad_reason,
                    now=NOW + timedelta(hours=1),
                )
            except PrimaryForgetError as exc:
                require(exc.code == "operation_conflict", exc.code)
            else:
                raise AssertionError("different exact replay binding was accepted")

        inspection = inspect_primary_memory_operations(root, memory_id=memory_id)
        require(inspection.corrupt is False, inspection)
        require(not inspection.pending, inspection)
        require(len(inspection.operations) == 2, inspection)
        require(primary_memory_mutation_lock_path(root, memory_id).name == ".lock", "lock path changed")

        public = repr(result) + repr(result.to_log_dict()) + repr(replay) + repr(recovered)
        for forbidden in (
            str(root), CHARACTER, NAMESPACE, memory_id, token, REASON,
            hidden_id, tombstone["tombstone_id"], tombstone["tombstone_digest"],
            "lineage_fingerprint", "operation_key", "binding_digest",
            "target_relative_path", "Traceback",
        ):
            require(forbidden not in public, forbidden)


def corrected_revision() -> None:
    with prepared_store() as (root, memory_id):
        correction = preflight_primary_memory_correction(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            corrected_title="好きな飲み物（訂正済み）",
            corrected_summary="好きな飲み物は緑茶です。",
            reason="訂正理由",
            operation_id="phase-i4c2-correct-before-forget",
            now=NOW,
        )
        applied = apply_primary_memory_correction(
            store_root=str(root),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            operation_id="phase-i4c2-correct-before-forget",
            apply_token=correction["apply_token"],
            now=NOW,
        )
        require(applied["status"] == "applied", applied)
        current = resolve_primary_current_state(root, namespace=NAMESPACE, memory_id=memory_id)
        require(current.current_revision == 2 and current.lifecycle_state == "active", current)
        prior_path = root / current.relative_path
        prior_bytes = prior_path.read_bytes()

        token = issue(root, memory_id, "phase-i4c2-forget-corrected", 2)
        result = apply(root, memory_id, "phase-i4c2-forget-corrected", token, 2)
        require(result.prior_revision == 2 and result.result_revision == 3, result)
        require(prior_path.read_bytes() == prior_bytes, "corrected active page changed")
        assert_finalized(root, memory_id, 3)


def no_durable_recovery() -> None:
    with prepared_store() as (root, memory_id):
        result = recover_primary_memory_forget(
            store_root=str(root),
            namespace=NAMESPACE,
            memory_id=memory_id,
            operation_id="phase-i4c2-no-operation",
            now=NOW,
        )
        require(result.status == "not_recoverable", result)
        require(result.prepared_present is False, result)
        require(result.tombstone_present is False, result)


def main() -> None:
    normal_and_replay()
    corrected_revision()
    no_durable_recovery()
    print("Phase I-4C2 Primary Forget recovery/finalization smoke passed")


if __name__ == "__main__":
    main()
