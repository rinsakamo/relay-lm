"""Focused LC-1D Restore final-record composition tests.

These prove the write-free deterministic final payload only. Reservation,
publication, replay, recovery, and Restore apply remain disabled.
"""
from __future__ import annotations

import ast
from dataclasses import replace
import inspect

from relaylm.evidence_common import canonical_digest
from relaylm.subjective_mem_lifecycle import (
    LIFECYCLE_INTENT_FINALIZATION_SCHEMA,
    LIFECYCLE_POLICY_REVISION,
    LIFECYCLE_RECEIPT_SCHEMA,
    LIFECYCLE_RESULT_SCHEMA,
    LIFECYCLE_TRANSITION_SCHEMA,
)
from relaylm.subjective_mem_lifecycle_engine import (
    LifecycleFinalRecordsWithBindings,
    final_lifecycle_state,
)
import relaylm.subjective_mem_restore_plan as restore_plan
from relaylm.subjective_mem_restore_plan import (
    build_subjective_mem_restore_final_records,
)
from relaylm.subjective_mem_tombstone_release import (
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND,
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_RECORD_KIND,
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_SCHEMA,
    SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_STATE_SCHEMA,
)
from test_subjective_mem_lifecycle_runtime import lifecycle_env
from test_subjective_mem_restore_runtime import _prepared_plan, _proposal, _store_files


def _final(env, *, key="lc1d-restore-final"):
    _forgotten, proposal = _proposal(env)
    prepared, reasons, _identity, _at = _prepared_plan(env, proposal, key=key)
    assert prepared is not None, reasons
    plan = prepared.plan
    final_state = final_lifecycle_state(plan)
    records, reasons = build_subjective_mem_restore_final_records(
        plan=plan, final_state=final_state
    )
    assert records is not None, reasons
    return plan, final_state, records


def _rebound(plan, bindings):
    return replace(plan, record_bindings=tuple(bindings))


def _bound(plan, kind: str):
    return next(
        (record_id, body)
        for record_kind, record_id, body in plan.record_bindings
        if record_kind == kind
    )


def test_restore_final_records_are_exact_and_deterministic(lifecycle_env) -> None:
    plan, final_state, records = _final(lifecycle_env)
    intent = dict(plan.prepared_intent)

    transition = records.transition
    assert transition["schema"] == LIFECYCLE_TRANSITION_SCHEMA
    assert transition["transition_id"] == plan.transition_id
    assert transition["character_id"] == plan.character_id
    assert transition["memory_id"] == plan.memory_id
    assert transition["from_revision"] == plan.from_revision
    assert transition["to_revision"] == plan.from_revision + 1
    assert transition["operation"] == "restore"
    assert transition["from_lifecycle_state"] == "hidden"
    assert transition["to_lifecycle_state"] == "active"
    assert transition["from_formation_stage"] == transition["to_formation_stage"]
    assert transition["authorized_by"] == intent["authorization_class"]
    assert transition["committed_at"] == plan.prepared_at

    receipt = records.receipt
    assert receipt["schema"] == LIFECYCLE_RECEIPT_SCHEMA
    assert receipt["operation_kind"] == "restore"
    assert receipt["operation_outcome"] == "committed"
    assert receipt["receipt_id"] == plan.receipt_id
    assert receipt["intent_digest"] == canonical_digest(intent)
    assert receipt["operation_id"] == plan.operation_id
    assert receipt["input_digest"] == plan.input_digest
    assert receipt["memory_ref"] == {
        "memory_id": plan.memory_id,
        "memory_revision": plan.to_revision,
    }
    assert receipt["predecessor_revision"] == plan.from_revision
    assert receipt["transition_id"] == plan.transition_id
    assert receipt["release_id"] == intent["release_id"]
    assert receipt["tombstone_id"] == intent["forget_tombstone_id"]
    assert receipt["tombstone_digest"] == intent["forget_tombstone_digest"]
    assert receipt["semantic_identity_digest"] == intent["semantic_identity_digest"]
    assert receipt["policy_revision"] == LIFECYCLE_POLICY_REVISION
    assert receipt["successor_revision_digest"] == plan.successor_revision_digest
    assert receipt["current_state_digest"] == canonical_digest(final_state.to_dict())
    assert receipt["projection_state"] == "rebuild_required"
    assert receipt["ordinary_retrieval_wired"] is False
    assert receipt["finalized_at"] == plan.prepared_at
    assert receipt["receipt_digest"] == canonical_digest(
        {key: value for key, value in receipt.items() if key != "receipt_digest"}
    )

    finalization = records.finalization
    assert finalization["schema"] == LIFECYCLE_INTENT_FINALIZATION_SCHEMA
    assert finalization["intent_id"] == plan.intent_id
    assert finalization["intent_digest"] == canonical_digest(intent)
    assert finalization["receipt_digest"] == receipt["receipt_digest"]
    assert finalization["status"] == "finalized"
    assert finalization["finalized_at"] == plan.prepared_at

    result = records.result
    assert result["schema"] == LIFECYCLE_RESULT_SCHEMA
    assert result["result_id"] == plan.result_id
    assert result["operation_kind"] == "restore"
    assert result["status"] == "committed"
    assert result["current_selector_id"] == plan.selector_id
    assert result["current_state_digest"] == canonical_digest(final_state.to_dict())
    assert result["result_digest"] == canonical_digest(
        {key: value for key, value in result.items() if key != "result_digest"}
    )

    projection = records.projection
    assert projection["memory_id"] == plan.memory_id
    assert projection["memory_revision"] == plan.to_revision
    assert projection["projection_state"] == "rebuild_required"
    assert projection["ordinary_retrieval_wired"] is False
    assert projection["updated_at"] == plan.prepared_at


def test_restore_final_bindings_hold_release_record_and_singleton_state(
    lifecycle_env,
) -> None:
    plan, _final_state, records = _final(lifecycle_env)
    intent = dict(plan.prepared_intent)
    _receipt_id, forget_receipt = _bound(plan, "subjective_mem_lifecycle_receipt")
    _tombstone_id, tombstone = _bound(plan, "subjective_mem_forget_tombstone")

    assert isinstance(records, LifecycleFinalRecordsWithBindings)
    assert len(records.additional_records) == 1
    assert len(records.additional_logs) == 1

    kind, record_id, release = records.additional_records[0]
    assert kind == SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_RECORD_KIND
    assert record_id == intent["release_id"]
    assert release["schema"] == SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_SCHEMA
    assert release["release_id"] == records.receipt["release_id"]
    assert release["restore_transition_id"] == plan.transition_id
    assert release["restore_transition_digest"] == canonical_digest(records.transition)
    assert release["restore_receipt_id"] == plan.receipt_id
    assert release["restore_receipt_digest"] == records.receipt["receipt_digest"]
    assert release["forget_receipt_id"] == tombstone["receipt_id"]
    assert release["forget_receipt_digest"] == forget_receipt["receipt_digest"]
    assert release["forget_transition_id"] == tombstone["transition_id"]
    assert release["tombstone_id"] == intent["forget_tombstone_id"]
    assert release["tombstone_digest"] == intent["forget_tombstone_digest"]
    assert release["hidden_revision"] == plan.from_revision
    assert release["restored_revision"] == plan.to_revision
    assert release["released_at"] == plan.prepared_at
    assert release["content_free"] is True

    log_kind, log_key, events = records.additional_logs[0]
    assert log_kind == SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND
    assert log_key == intent["forget_tombstone_id"]
    assert len(events) == 1
    state = events[0]
    assert state["schema"] == SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_STATE_SCHEMA
    assert state["release_digest"] == release["release_digest"]
    assert state["effective"] is True
    assert state["content_free"] is True
    assert state["updated_at"] == plan.prepared_at

    # the plan bound an empty release log; finalization intentionally replaces it
    plan_release_logs = [
        events
        for kind, _key, events in plan.log_bindings
        if kind == SUBJECTIVE_MEM_FORGET_TOMBSTONE_RELEASE_LOG_KIND
    ]
    assert plan_release_logs == [()]


def test_restore_final_records_repeat_identically(lifecycle_env) -> None:
    plan, final_state, first = _final(lifecycle_env, key="repeat")
    second, reasons = build_subjective_mem_restore_final_records(
        plan=plan, final_state=final_state
    )
    assert second is not None, reasons
    assert first == second
    assert first.additional_records == second.additional_records
    assert first.additional_logs == second.additional_logs


def test_restore_final_records_reject_non_exact_final_state(lifecycle_env) -> None:
    plan, final_state, _records = _final(lifecycle_env, key="wrong-final-state")
    for broken in (
        replace(final_state, lifecycle_state="hidden", retrieval_eligible=False),
        replace(final_state, updated_at="2020-01-01T00:00:00+00:00"),
        replace(final_state, block_id="smblock_foreign"),
        replace(final_state, canonical_page_digest="sha256:" + "0" * 64),
        replace(final_state, current_receipt_id="smreceipt_foreign"),
    ):
        records, reasons = build_subjective_mem_restore_final_records(
            plan=plan, final_state=broken
        )
        assert records is None
        assert reasons == ("subjective_mem_restore_final_state_not_exact",)


def test_restore_final_records_reject_non_restore_or_invalid_plan(
    lifecycle_env,
) -> None:
    plan, final_state, _records = _final(lifecycle_env, key="wrong-plan")
    for broken in (
        replace(plan, operation_kind="correct"),
        replace(plan, pre_image_state="absent"),
    ):
        records, reasons = build_subjective_mem_restore_final_records(
            plan=broken, final_state=final_state
        )
        assert records is None
        assert reasons == ("subjective_mem_restore_final_plan_not_exact",)


def test_restore_final_records_reject_unbound_or_changed_forget_authority(
    lifecycle_env,
) -> None:
    plan, final_state, _records = _final(lifecycle_env, key="bad-authority")
    bindings = list(plan.record_bindings)
    receipt_index = next(
        index
        for index, binding in enumerate(bindings)
        if binding[0] == "subjective_mem_lifecycle_receipt"
    )
    tombstone_index = next(
        index
        for index, binding in enumerate(bindings)
        if binding[0] == "subjective_mem_forget_tombstone"
    )
    receipt_kind, receipt_id, receipt = bindings[receipt_index]
    tombstone_kind, tombstone_id, tombstone = bindings[tombstone_index]

    missing = [item for index, item in enumerate(bindings) if index != tombstone_index]
    duplicate = bindings + [(receipt_kind, receipt_id, receipt)]
    for broken in (missing, duplicate):
        records, reasons = build_subjective_mem_restore_final_records(
            plan=_rebound(plan, broken), final_state=final_state
        )
        assert records is None
        assert reasons == ("subjective_mem_restore_final_forget_authority_not_bound",)

    foreign = list(bindings)
    foreign[tombstone_index] = (
        tombstone_kind,
        tombstone_id,
        {**tombstone, "memory_id": "smmemory_foreign"},
    )
    non_forget = list(bindings)
    non_forget[receipt_index] = (
        receipt_kind,
        receipt_id,
        {**receipt, "operation_kind": "correct"},
    )
    tampered = list(bindings)
    tampered[tombstone_index] = (
        tombstone_kind,
        tombstone_id,
        {**tombstone, "tombstone_digest": "f" * 64},
    )
    for broken in (foreign, non_forget, tampered):
        records, reasons = build_subjective_mem_restore_final_records(
            plan=_rebound(plan, broken), final_state=final_state
        )
        assert records is None
        assert reasons == ("subjective_mem_restore_final_forget_authority_not_exact",)


def test_restore_final_records_make_no_mutation(lifecycle_env) -> None:
    # the Forget setup inside _final is the only writer; the builder must add none
    plan, final_state, records = _final(lifecycle_env, key="no-mutation-final")
    assert records is not None
    before_page = lifecycle_env["page_path"].read_bytes()
    before_files = _store_files(lifecycle_env)
    build_subjective_mem_restore_final_records(plan=plan, final_state=final_state)

    assert lifecycle_env["page_path"].read_bytes() == before_page
    assert _store_files(lifecycle_env) == before_files
    assert not any(
        "release" in item or "restore" in item for item in _store_files(lifecycle_env)
    )


def test_restore_plan_module_final_builder_is_storage_neutral() -> None:
    source = inspect.getsource(restore_plan)
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any(
        "restore_runtime" in module or "evidence_store" in module
        for module in imported
    )
    assert "build_subjective_mem_forget_tombstone_release_authority(" in source
    for forbidden in (
        "reserve_lifecycle_publication",
        "publish_lifecycle_post_image",
        "resolve_finalized_replay",
        "tx.commit(",
        "write_record(",
        "write_log(",
        "read_record(",
        "read_log(",
        "open(",
        "Path(",
    ):
        assert forbidden not in source
    assert callable(restore_plan.build_subjective_mem_restore_final_records)
