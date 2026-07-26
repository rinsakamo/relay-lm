"""Focused shared lifecycle finalization extension tests for LC-1D Restore."""
from __future__ import annotations

from types import SimpleNamespace

import relaylm.subjective_mem_lifecycle_engine as lifecycle_engine
from relaylm.subjective_mem_lifecycle_engine import (
    LifecycleFinalRecords,
    LifecycleFinalRecordsWithBindings,
)
from test_subjective_mem_lifecycle_runtime import lifecycle_env


def _plan(state, *, record_bindings=(), log_bindings=()):
    return SimpleNamespace(
        transition_id="transition-1",
        receipt_id="receipt-1",
        result_id="result-1",
        selector_id=state.memory_state_id,
        record_bindings=record_bindings,
        log_bindings=log_bindings,
    )


def _records(*, additional_records=(), additional_logs=()):
    record_type = (
        LifecycleFinalRecordsWithBindings
        if additional_records or additional_logs
        else LifecycleFinalRecords
    )
    kwargs = {}
    if record_type is LifecycleFinalRecordsWithBindings:
        kwargs = {
            "additional_records": additional_records,
            "additional_logs": additional_logs,
        }
    return record_type(
        {"transition_id": "transition-1"},
        {"receipt_id": "receipt-1"},
        {"finalization_id": "finalization-1"},
        {"result_id": "result-1"},
        {"projection_state": "rebuild_required"},
        **kwargs,
    )


def test_existing_finalizers_keep_empty_operation_owned_bindings(lifecycle_env) -> None:
    state = lifecycle_env["st1"].current_state
    assert state is not None
    records = _records()
    assert type(records) is LifecycleFinalRecords
    assert lifecycle_engine._final_records_errors(_plan(state), records, state) == ()


def test_final_payload_adds_operation_owned_record_and_evolved_log(lifecycle_env) -> None:
    state = lifecycle_env["st1"].current_state
    assert state is not None
    before = ({"effective": True},)
    after = (*before, {"effective": False, "release_id": "release-1"})
    plan = _plan(
        state,
        log_bindings=(("subjective_mem_forget_tombstone_state", "semantic-1", before),),
    )
    records = _records(
        additional_records=((
            "subjective_mem_forget_tombstone_release",
            "release-1",
            {"release_id": "release-1", "content_free": True},
        ),),
        additional_logs=((
            "subjective_mem_forget_tombstone_state",
            "semantic-1",
            after,
        ),),
    )
    assert lifecycle_engine._final_records_errors(plan, records, state) == ()
    commit_records, commit_logs = lifecycle_engine._final_commit_payload(
        plan, records, state
    )
    assert commit_records[-1] == records.additional_records[0]
    assert commit_logs[-1] == records.additional_logs[0]


def test_final_bindings_reject_core_or_predecessor_record_overwrite(
    lifecycle_env,
) -> None:
    state = lifecycle_env["st1"].current_state
    assert state is not None
    core = _records(additional_records=((
        lifecycle_engine.RECEIPT_RECORD_KIND,
        "other-receipt",
        {"unexpected": True},
    ),))
    assert lifecycle_engine._final_records_errors(_plan(state), core, state) == (
        "subjective_mem_lifecycle_final_binding_conflict",
    )
    bound = _records(additional_records=((
        "subjective_mem_forget_tombstone",
        "tombstone-1",
        {"unexpected": True},
    ),))
    plan = _plan(
        state,
        record_bindings=((
            "subjective_mem_forget_tombstone",
            "tombstone-1",
            {"effective": True},
        ),),
    )
    assert lifecycle_engine._final_records_errors(plan, bound, state) == (
        "subjective_mem_lifecycle_final_binding_conflict",
    )


def test_final_log_must_advance_bound_pre_image(lifecycle_env) -> None:
    state = lifecycle_env["st1"].current_state
    assert state is not None
    before = ({"effective": True},)
    plan = _plan(
        state,
        log_bindings=(("subjective_mem_forget_tombstone_state", "semantic-1", before),),
    )
    unchanged = _records(additional_logs=((
        "subjective_mem_forget_tombstone_state",
        "semantic-1",
        before,
    ),))
    assert lifecycle_engine._final_records_errors(plan, unchanged, state) == (
        "subjective_mem_lifecycle_final_binding_conflict",
    )


def test_partial_detection_accepts_exact_bound_log_pre_image_only(
    lifecycle_env,
) -> None:
    state = lifecycle_env["st1"].current_state
    assert state is not None
    before = ({"effective": True},)
    after = (*before, {"effective": False, "release_id": "release-1"})
    plan = _plan(
        state,
        log_bindings=(("subjective_mem_forget_tombstone_state", "semantic-1", before),),
    )
    records = _records(additional_logs=((
        "subjective_mem_forget_tombstone_state",
        "semantic-1",
        after,
    ),))

    class Tx:
        def __init__(self, tombstone_events):
            self.tombstone_events = tombstone_events

        def read_record(self, *, record_kind, record_id):
            return None

        def read_log(self, *, log_kind, key):
            if (log_kind, key) == (
                "subjective_mem_forget_tombstone_state",
                "semantic-1",
            ):
                return list(self.tombstone_events)
            return []

    assert lifecycle_engine._any_final_record_present_locked(
        tx=Tx(before), plan=plan, records=records, final_state=state
    ) is False
    assert lifecycle_engine._any_final_record_present_locked(
        tx=Tx(after), plan=plan, records=records, final_state=state
    ) is True
