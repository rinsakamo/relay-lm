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
    semantic_id,
    var,
)


T0 = "2026-09-03T12:00:00+00:00"


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
