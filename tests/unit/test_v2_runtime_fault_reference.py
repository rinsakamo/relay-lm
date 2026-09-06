from __future__ import annotations

from tools.v2_runtime_fault_reference import (
    CrashSafeRuntime,
    DurableStore,
    FakeActionSink,
)


def test_f0_crash_before_occurrence_admission_leaves_no_occurrence():
    runtime = CrashSafeRuntime.fresh()
    recovered = runtime.crash_and_recover()
    assert recovered.kernel.occurrences == {}
    assert recovered.kernel.current_head == "h0"


def test_f1_occurrence_admission_survives_crash_and_retry_identity():
    runtime = CrashSafeRuntime.fresh()
    first = runtime.ingest("進めて", logical_ingress_id="req-1")
    recovered = runtime.crash_and_recover()
    retry = recovered.ingest("進めて", logical_ingress_id="req-1")
    assert retry.occurrence_id == first.occurrence_id
    assert retry.new_occurrence is False
    assert len(recovered.kernel.occurrences) == 1


def test_f2_ephemeral_proposal_is_not_durable():
    runtime = CrashSafeRuntime.fresh()
    runtime.ingest("A")
    runtime.propose_value("x", "A")
    recovered = runtime.crash_and_recover()
    assert recovered.kernel.cells() == {}
    assert not hasattr(recovered, "pending_proposals")
    assert not hasattr(recovered.store, "pending_proposals")


def test_f3_partial_response_receipt_survives_without_commit():
    runtime = CrashSafeRuntime.fresh()
    before = runtime.kernel.current_head
    action = runtime.emit_response("hel")
    recovered = runtime.crash_and_recover()
    assert recovered.kernel.actions[action.id].content == "hel"
    assert recovered.kernel.current_head == before
    assert recovered.kernel.cells() == {}


def test_f4_transport_completion_survives_without_commit():
    runtime = CrashSafeRuntime.fresh()
    before = runtime.kernel.current_head
    action = runtime.emit_response("hello")
    runtime.complete_transport(action.id, marker="[DONE]")
    recovered = runtime.crash_and_recover()
    receipt = recovered.kernel.actions[action.id]
    assert receipt.transport_complete
    assert receipt.completion_marker == "[DONE]"
    assert recovered.kernel.current_head == before
    assert recovered.kernel.cells() == {}


def test_f5_unsettled_proposal_is_abandoned_on_restart():
    runtime = CrashSafeRuntime.fresh()
    proposal = runtime.propose_value("choice", "A")
    assert proposal.parent_head == runtime.kernel.current_head
    recovered = runtime.crash_and_recover()
    assert recovered.kernel.cells() == {}
    assert not hasattr(recovered.store, "proposals")


def test_f6_atomic_commit_is_old_or_new_head_never_split():
    runtime = CrashSafeRuntime.fresh()
    proposal = runtime.propose_value("x", "A")
    old_head = runtime.kernel.current_head

    preview = runtime.preview_settlement(proposal)
    assert preview.status == "COMMIT"
    assert runtime.kernel.current_head == old_head
    before_install_recovery = runtime.crash_and_recover()
    assert before_install_recovery.kernel.current_head == old_head
    assert before_install_recovery.kernel.cells() == {}

    durable = before_install_recovery.settle(proposal)
    assert durable.status == "COMMIT"
    new_head = before_install_recovery.kernel.current_head
    after_install_recovery = before_install_recovery.crash_and_recover()
    assert after_install_recovery.kernel.current_head == new_head
    assert after_install_recovery.kernel.cell("x").value == "A"
    assert not hasattr(after_install_recovery.store, "commit_receipts")


def test_f7_commit_survives_crash_before_client_acknowledgement():
    runtime = CrashSafeRuntime.fresh()
    result = runtime.settle(runtime.propose_value("name", "Mika"))
    assert result.status == "COMMIT"
    recovered = runtime.crash_and_recover()
    assert recovered.kernel.cell("name").value == "Mika"


def test_retry_and_distinct_same_content_compose_after_restart():
    runtime = CrashSafeRuntime.fresh()
    one = runtime.ingest("進めて", logical_ingress_id="req-1")
    recovered = runtime.crash_and_recover()
    replay = recovered.ingest("進めて", logical_ingress_id="req-1")
    independent = recovered.ingest("進めて", logical_ingress_id="req-2")
    assert replay.occurrence_id == one.occurrence_id
    assert independent.occurrence_id != one.occurrence_id
    assert len(recovered.kernel.occurrences) == 2


def test_stale_parent_proposal_rejects_after_recovery_and_new_commit():
    runtime = CrashSafeRuntime.fresh()
    old = runtime.propose_value("choice", "A")
    runtime.settle(runtime.propose_value("choice", "B"))
    recovered = runtime.crash_and_recover()
    stale = recovered.settle(old)
    assert stale.status == "REJECT"
    assert stale.reason == "stale_parent"
    assert recovered.kernel.cell("choice").value == "B"


def test_crash_before_external_attempt_registration_can_still_dispatch():
    runtime = CrashSafeRuntime.fresh()
    sink = FakeActionSink()
    action = runtime.emit_response("send")

    recovered = runtime.crash_and_recover()
    assert action.id not in recovered.store.external_receipts
    receipt = recovered.begin_external_dispatch(action.id, mode="NON_IDEMPOTENT")
    assert receipt.status == "ATTEMPT_REGISTERED"
    result = sink.invoke(action.id, idempotent=False)
    receipt = recovered.record_external_success(result)
    assert receipt.status == "SUCCEEDED"
    assert sink.effect_count(action.id) == 1


def test_non_idempotent_unknown_dispatch_is_not_blindly_retried():
    runtime = CrashSafeRuntime.fresh()
    sink = FakeActionSink()
    action = runtime.emit_response("send")
    runtime.begin_external_dispatch(action.id, mode="NON_IDEMPOTENT")
    sink.invoke(action.id, idempotent=False)

    recovered = runtime.crash_and_recover()
    receipt = recovered.recover_external(action.id, sink)
    assert receipt.status == "OUTCOME_UNKNOWN"
    assert sink.effect_count(action.id) == 1
    assert sink.call_count(action.id) == 1


def test_idempotent_unknown_dispatch_can_retry_without_duplicate_effect():
    runtime = CrashSafeRuntime.fresh()
    sink = FakeActionSink()
    action = runtime.emit_response("send")
    runtime.begin_external_dispatch(action.id, mode="IDEMPOTENT")
    sink.invoke(action.id, idempotent=True)

    recovered = runtime.crash_and_recover()
    receipt = recovered.recover_external(action.id, sink)
    assert receipt.status == "SUCCEEDED"
    assert sink.effect_count(action.id) == 1
    assert sink.call_count(action.id) == 2


def test_recorded_external_success_survives_before_cognitive_commit():
    runtime = CrashSafeRuntime.fresh()
    sink = FakeActionSink()
    action = runtime.emit_response("send")
    runtime.begin_external_dispatch(action.id, mode="NON_IDEMPOTENT")
    result = sink.invoke(action.id, idempotent=False)
    runtime.record_external_success(result)

    recovered = runtime.crash_and_recover()
    receipt = recovered.external_receipt(action.id)
    assert receipt.status == "SUCCEEDED"
    assert recovered.kernel.cells() == {}


def test_external_success_is_not_fabricated_before_result_receipt():
    runtime = CrashSafeRuntime.fresh()
    action = runtime.emit_response("send")
    receipt = runtime.begin_external_dispatch(action.id, mode="NON_IDEMPOTENT")
    assert receipt.status == "ATTEMPT_REGISTERED"
    recovered = runtime.crash_and_recover()
    assert recovered.external_receipt(action.id).status == "ATTEMPT_REGISTERED"


def test_runtime_receipts_store_identity_not_semantic_payload():
    runtime = CrashSafeRuntime.fresh()
    action = runtime.emit_response("private semantic payload")
    receipt = runtime.begin_external_dispatch(action.id, mode="NON_IDEMPOTENT")
    assert receipt.action_id == action.id
    assert not hasattr(receipt, "content")
    assert "private semantic payload" not in repr(runtime.store.external_receipts)


def test_privacy_delete_survives_recovery_without_secret_in_durable_image():
    runtime = CrashSafeRuntime.fresh()
    occurrence = runtime.ingest("secret alpha")
    runtime.settle(
        runtime.propose_value(
            "summary",
            "secret alpha",
            supports=(occurrence.occurrence_id,),
            derived_from=(occurrence.occurrence_id,),
        )
    )
    runtime.privacy_delete_occurrence(occurrence.occurrence_id)
    recovered = runtime.crash_and_recover()
    assert recovered.kernel.occurrences[occurrence.occurrence_id].content is None
    assert "secret alpha" not in repr(recovered.store.kernel_image)
    assert "secret alpha" not in repr(recovered.store.external_receipts)


def test_delivery_attempts_compact_but_logical_retry_identity_survives():
    runtime = CrashSafeRuntime.fresh()
    first = runtime.ingest("A", logical_ingress_id="req-1")
    assert runtime.kernel.deliveries
    recovered = runtime.crash_and_recover()
    assert recovered.kernel.deliveries == {}
    retry = recovered.ingest("A", logical_ingress_id="req-1")
    assert retry.occurrence_id == first.occurrence_id
    assert retry.new_occurrence is False


def test_minimal_store_has_no_general_transaction_fsm_or_proposals():
    store = DurableStore.fresh()
    assert not hasattr(store, "transactions")
    assert not hasattr(store, "phase")
    assert not hasattr(store, "pending_proposals")
    assert not hasattr(store, "model_intermediates")
