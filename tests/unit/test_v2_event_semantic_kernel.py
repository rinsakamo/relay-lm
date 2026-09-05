from __future__ import annotations

import pytest

from tools.v2_event_semantic_kernel import (
    EventSemanticKernel,
    InvalidSemanticInput,
    WorkOption,
)


def test_d0_same_content_independent_ingress_are_distinct_occurrences():
    k = EventSemanticKernel()
    a = k.ingest("進めて")
    b = k.ingest("進めて")
    assert a.new_occurrence and b.new_occurrence
    assert a.occurrence_id != b.occurrence_id
    assert k.occurrences[a.occurrence_id].content == k.occurrences[b.occurrence_id].content


def test_d1_proven_retry_is_one_logical_occurrence_two_deliveries():
    k = EventSemanticKernel()
    first = k.ingest("進めて", logical_ingress_id="req-1")
    retry = k.ingest("進めて", logical_ingress_id="req-1")
    assert first.occurrence_id == retry.occurrence_id
    assert first.delivery_id != retry.delivery_id
    assert retry.new_occurrence is False
    assert k.deliveries[retry.delivery_id].replay is True


def test_d1_retry_identity_cannot_hide_changed_content():
    k = EventSemanticKernel()
    k.ingest("A", logical_ingress_id="req-1")
    with pytest.raises(InvalidSemanticInput):
        k.ingest("B", logical_ingress_id="req-1")


def test_d2_repeated_go_ahead_can_have_second_cognitive_effect():
    k = EventSemanticKernel()
    one = k.ingest("進めて")
    s1 = k.settle(k.propose_value("progress", 1, supports=(one.occurrence_id,)))
    two = k.ingest("進めて")
    s2 = k.settle(k.propose_value("progress", 2, supports=(two.occurrence_id,)))
    assert s1.status == s2.status == "COMMIT"
    assert k.cell("progress").value == 2


def test_d3_concurrent_stale_proposal_cannot_last_write_win():
    k = EventSemanticKernel()
    h0 = k.current_head
    a = k.propose_value("x", "A", parent_head=h0)
    b = k.propose_value("x", "B", parent_head=h0)
    assert k.settle(a).status == "COMMIT"
    stale = k.settle(b)
    assert stale.status == "REJECT"
    assert stale.reason == "stale_parent"
    assert k.cell("x").value == "A"


def test_d4_receipt_order_does_not_manufacture_world_order():
    k = EventSemanticKernel()
    b = k.ingest("B arrived", world_rank=2)
    a = k.ingest("A arrived later", world_rank=1)
    assert k.receipt_relation(b.occurrence_id, a.occurrence_id) == "BEFORE"
    assert k.world_relation(a.occurrence_id, b.occurrence_id) == "BEFORE"


def test_d5_unknown_world_order_remains_unknown():
    k = EventSemanticKernel()
    a = k.ingest("A")
    b = k.ingest("B")
    assert k.receipt_relation(a.occurrence_id, b.occurrence_id) == "BEFORE"
    assert k.world_relation(a.occurrence_id, b.occurrence_id) == "UNKNOWN"


def test_d6_late_evidence_revises_past_claim_without_rewriting_lineage_order():
    k = EventSemanticKernel()
    first = k.ingest("outage began 12:30", world_rank=30)
    first_result = k.settle(
        k.propose_value(
            "outage_start",
            "12:30",
            supports=(first.occurrence_id,),
        )
    )
    assert first_result.status == "COMMIT"
    old_head = k.current_head
    late = k.ingest("correction: outage began 12:00", world_rank=0)
    late_result = k.settle(
        k.propose_value(
            "outage_start",
            "12:00",
            supports=(late.occurrence_id,),
        )
    )
    assert late_result.status == "COMMIT"
    assert k.cell("outage_start").value == "12:00"
    assert k.heads[k.current_head].parent == old_head
    assert k.receipt_relation(first.occurrence_id, late.occurrence_id) == "BEFORE"
    assert k.world_relation(late.occurrence_id, first.occurrence_id) == "BEFORE"


def test_d7_correction_changes_current_value_without_erasing_prior_head():
    k = EventSemanticKernel()
    old_occ = k.ingest("Mike")
    first = k.settle(
        k.propose_value("name", "Mike", supports=(old_occ.occurrence_id,))
    )
    assert first.status == "COMMIT"
    old_head = k.current_head
    new_occ = k.ingest("I meant Mika")
    second = k.settle(
        k.propose_value("name", "Mika", supports=(new_occ.occurrence_id,))
    )
    assert second.status == "COMMIT"
    assert k.cell("name").value == "Mika"
    assert k.cell("name", old_head).value == "Mike"


def test_d8_ordinary_update_does_not_mark_prior_value_as_error():
    k = EventSemanticKernel()
    a = k.ingest("address A")
    k.settle(k.propose_value("address", "A", supports=(a.occurrence_id,)))
    old_head = k.current_head
    b = k.ingest("moved to B")
    k.settle(k.propose_value("address", "B", supports=(b.occurrence_id,)))
    assert k.cell("address", old_head).value == "A"
    assert k.cell("address").value == "B"
    assert "error" not in k.cells()


def test_d9_invalidate_sole_support_yields_unknown_not_negation():
    k = EventSemanticKernel()
    o = k.ingest("P")
    k.settle(k.propose_value("P", True, supports=(o.occurrence_id,)))
    result = k.settle(k.proposal_after_support_invalidation(o.occurrence_id))
    assert result.status == "COMMIT"
    p = k.cell("P")
    assert p.value is None
    assert p.supported is False
    assert "not:P" not in k.cells()


def test_d10_invalidate_one_independent_support_preserves_claim():
    k = EventSemanticKernel()
    a = k.ingest("P from A")
    b = k.ingest("P from B")
    k.settle(
        k.propose_value(
            "P",
            True,
            supports=(a.occurrence_id, b.occurrence_id),
        )
    )
    result = k.settle(k.proposal_after_support_invalidation(a.occurrence_id))
    assert result.status == "COMMIT"
    p = k.cell("P")
    assert p.value is True and p.supported
    assert p.supports == frozenset({b.occurrence_id})


def test_d11_demotion_changes_projection_not_content_or_support():
    k = EventSemanticKernel()
    o = k.ingest("rare detail")
    k.settle(k.propose_value("detail", "rare", supports=(o.occurrence_id,)))
    before = k.cell("detail")
    result = k.settle(k.proposal_demote("detail"))
    assert result.status == "COMMIT"
    after = k.cell("detail")
    assert after.value == before.value
    assert after.supports == before.supports
    assert after.hot is False
    assert "detail" not in k.hot_projection()


def test_d12_privacy_delete_removes_source_content_and_ordinary_derivative():
    k = EventSemanticKernel()
    o = k.ingest("secret alpha")
    k.settle(
        k.propose_value(
            "summary",
            "secret alpha",
            supports=(o.occurrence_id,),
            derived_from=(o.occurrence_id,),
        )
    )
    result = k.privacy_delete_occurrence(o.occurrence_id)
    assert result.status == "COMMIT"
    assert k.occurrences[o.occurrence_id].content is None
    assert k.occurrences[o.occurrence_id].redacted
    assert "summary" not in k.hot_projection()
    assert all(
        cell.value != "secret alpha"
        for head in k.heads.values()
        for _key, cell in head.cells
    )
    assert all(not hasattr(delivery, "content") for delivery in k.deliveries.values())


def test_d13_restore_is_new_transition_not_time_travel():
    k = EventSemanticKernel()
    k.settle(k.propose_value("mode", "A"))
    old_head = k.current_head
    k.settle(k.propose_value("mode", "B"))
    before_restore = k.current_head
    result = k.settle(k.proposal_restore(old_head))
    assert result.status == "COMMIT"
    assert k.cell("mode").value == "A"
    assert k.current_head != old_head
    assert k.heads[k.current_head].parent == before_restore


def test_d14_response_emitted_then_commit():
    k = EventSemanticKernel()
    action = k.emit_action("name is Mika")
    proposal = k.propose_value("name", "Mika")
    result = k.settle(proposal)
    assert result.status == "COMMIT"
    assert k.actions[action.id].content == "name is Mika"


def test_d15_response_emitted_then_noop():
    k = EventSemanticKernel()
    k.settle(k.propose_value("name", "Mika"))
    action = k.emit_action("still Mika")
    result = k.settle(k.propose_value("name", "Mika"))
    assert result.status == "NOOP"
    assert k.actions[action.id].content == "still Mika"


def test_d16_response_emitted_then_rejected_persistence():
    k = EventSemanticKernel()
    action = k.emit_action("visible but not durable")
    result = k.settle(k.propose_value("claim", "X", admissible=False))
    assert result.status == "REJECT"
    assert "claim" not in k.cells()
    assert k.actions[action.id].content == "visible but not durable"


def test_d17_pending_old_proposal_cannot_time_travel_after_new_head():
    k = EventSemanticKernel()
    h0 = k.current_head
    k.emit_action("A", parent_head=h0)
    old_proposal = k.propose_value("choice", "A", parent_head=h0)
    b = k.ingest("actually B")
    new_result = k.settle(
        k.propose_value(
            "choice",
            "B",
            supports=(b.occurrence_id,),
            parent_head=h0,
        )
    )
    assert new_result.status == "COMMIT"
    stale = k.settle(old_proposal)
    assert stale.status == "REJECT"
    assert stale.reason == "stale_parent"
    assert k.cell("choice").value == "B"


def test_d18_transport_completion_marker_does_not_commit_cognition():
    k = EventSemanticKernel()
    before = k.current_head
    action = k.emit_action("hello")
    completed = k.complete_transport(action.id, marker="[DONE]")
    assert completed.transport_complete
    assert completed.completion_marker == "[DONE]"
    assert k.current_head == before
    assert k.cells() == {}


def test_d19_endogenous_recurrence_cannot_satisfy_observed_support_requirement():
    k = EventSemanticKernel()
    endogenous = k.ingest("self-thought", source="endogenous")
    proposal = k.propose_value(
        "world_claim",
        True,
        supports=(endogenous.occurrence_id,),
        require_observed_support=True,
    )
    assert k.settle(proposal).reason == "observed_support_required"
    proposal2 = k.propose_value(
        "world_claim",
        True,
        supports=(endogenous.occurrence_id,),
        require_observed_support=True,
    )
    assert k.settle(proposal2).reason == "observed_support_required"


def test_d20_zero_work_requires_no_sleep_state():
    k = EventSemanticKernel()
    choice = k.choose_work(
        (
            WorkOption("forward", expected_gain=1.0, cost=2.0),
            WorkOption("reorganize", expected_gain=0.5, cost=1.0),
        )
    )
    assert choice is None
    assert all("sleep" not in key.lower() for key in vars(k))


def test_d21_positive_roi_can_choose_reorganization():
    choice = EventSemanticKernel.choose_work(
        (
            WorkOption("forward", expected_gain=2.0, cost=1.8),
            WorkOption("reorganize", expected_gain=5.0, cost=1.0),
        )
    )
    assert choice is not None
    assert choice.name == "reorganize"


def test_d22_negative_roi_skips_reorganization():
    choice = EventSemanticKernel.choose_work(
        (
            WorkOption("forward", expected_gain=2.0, cost=1.0),
            WorkOption("reorganize", expected_gain=1.0, cost=3.0),
        )
    )
    assert choice is not None
    assert choice.name == "forward"
