from __future__ import annotations

import json

import pytest

from relaylm.v2_semantics import (
    InvalidTransactionError,
    ObservationInput,
    Proposal,
    SemanticTransactionStore,
    TransactionRequest,
    apply,
    literal,
    ref,
    semantic_id,
    var,
)


T0 = "2026-09-03T12:00:00+00:00"
T1 = "2026-09-03T12:01:00+00:00"


def test_durable_snapshot_restores_canonical_state_and_rebuilds_views():
    store = SemanticTransactionStore()
    meaning = apply("p", literal("x"))
    result = store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            observations=(
                ObservationInput(
                    slot="e",
                    time=T0,
                    source="user",
                    payload="x",
                ),
            ),
            proposals=(Proposal(meaning, observed_support_slots=("e",)),),
        )
    )
    evidence_id = result.observation_records[0]
    payload_ref = store.provenance[evidence_id].payload_ref
    snapshot = store.canonical_snapshot()

    rebuilt = SemanticTransactionStore.from_snapshot(snapshot)

    assert rebuilt.canonical_snapshot() == snapshot
    assert rebuilt.current_generation == store.current_generation
    assert rebuilt.query_status(meaning) == "TRUE"
    assert rebuilt.derived_symbol_index() == store.derived_symbol_index()
    assert payload_ref is not None
    assert rebuilt.payloads[payload_ref] == "x"


def test_bound_expression_is_one_context_safe_content_addressed_root():
    store = SemanticTransactionStore()
    quantified = apply(
        "forall",
        var("x"),
        apply("exists", var("y"), apply("pair", var("x"), var("y"))),
    )
    result = store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            proposals=(Proposal(quantified),),
        )
    )
    root_id = result.decisions[0].semantic_id

    assert root_id == semantic_id(quantified)
    assert set(store.semantic_nodes) == {root_id}
    assert semantic_id(store.expr_for_id(root_id)) == root_id

    for generation_id in list(store.generations):
        if generation_id != store.current_generation:
            store.retire_generation(generation_id)
    assert store.garbage_collect_semantics() == 0
    assert set(store.semantic_nodes) == {root_id}


def test_durable_snapshot_rejects_tampered_semantic_hash():
    store = SemanticTransactionStore()
    store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            proposals=(Proposal(apply("p", literal("x"))),),
        )
    )
    raw = json.loads(store.canonical_snapshot().decode("utf-8"))
    node_id = next(iter(raw["semantic_nodes"]))
    raw["semantic_nodes"][node_id] = '["lit","tampered"]'
    tampered = json.dumps(
        raw,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    with pytest.raises(InvalidTransactionError, match="semantic snapshot hash mismatch"):
        SemanticTransactionStore.from_snapshot(tampered)


def test_accepted_refs_close_into_anchor_registry_without_side_metadata():
    store = SemanticTransactionStore()
    meaning = apply(
        "believes",
        ref("E_alice"),
        apply("location", ref("E_key"), literal("drawer")),
    )

    result = store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            proposals=(Proposal(meaning),),
        )
    )

    assert result.decisions[0].status == "accepted"
    assert store.anchors == {"E_alice", "E_key"}
    snapshot = store.canonical_snapshot()
    rebuilt = SemanticTransactionStore.from_snapshot(snapshot)
    assert rebuilt.anchors == store.anchors
    assert rebuilt.canonical_snapshot() == snapshot


def test_full_erasure_reports_unreconstructable_migration_and_survives_rebuild():
    store = SemanticTransactionStore()
    meaning = apply("fact", ref("E_subject"), literal("grounded"))
    result = store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            observations=(
                ObservationInput(
                    slot="e",
                    time=T0,
                    source="user",
                    payload="grounded fact",
                ),
            ),
            proposals=(Proposal(meaning, observed_support_slots=("e",)),),
        )
    )
    evidence_id = result.observation_records[0]
    root_id = result.decisions[0].semantic_id

    before = store.migrate_generation(
        store.current_generation,
        native_symbols=frozenset({"fact"}),
    )
    assert before.ok
    assert before.missing_symbols == ()
    assert before.missing_provenance == ()

    store.delete_payload(evidence_id, time=T1, full_erasure=True)

    assert root_id in store.active_generation().active_roots
    assert evidence_id not in store.provenance
    after = store.migrate_generation(
        store.current_generation,
        native_symbols=frozenset({"fact"}),
    )
    assert not after.ok
    assert after.missing_symbols == ()
    assert after.missing_provenance == (evidence_id,)

    rebuilt = SemanticTransactionStore.from_snapshot(store.canonical_snapshot())
    assert rebuilt.migrate_generation(
        rebuilt.current_generation,
        native_symbols=frozenset({"fact"}),
    ) == after


def test_f33_generation_provenance_head_tracks_append_order_not_event_time():
    store = SemanticTransactionStore()
    first = store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            observations=(
                ObservationInput(
                    slot="later-time-first",
                    time=T1,
                    source="user",
                    payload="first append",
                ),
            ),
        )
    )
    first_generation = first.generation_id
    first_head = store.generations[first_generation].provenance_head
    assert first_head == first.observation_records[0]

    second = store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            observations=(
                ObservationInput(
                    slot="backdated-later",
                    time=T0,
                    source="replay",
                    payload="second append with earlier event time",
                ),
            ),
        )
    )
    second_head = store.active_generation().provenance_head

    assert second_head == second.observation_records[0]
    assert second_head != first_head
    assert store.generations[first_generation].provenance_head == first_head
    assert any(
        link.relation == "previous" and link.target == first_head
        for link in store.provenance[second_head].links
    )
