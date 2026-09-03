from __future__ import annotations

import pytest

from relaylm.v2_semantics import (
    ActionRequest,
    GovernancePolicy,
    InvalidTransactionError,
    ObservationInput,
    Proposal,
    Ref,
    SemanticTransactionStore,
    StaleGenerationError,
    TransactionRequest,
    apply,
    literal,
    ref,
    semantic_id,
    var,
)


T0 = "2026-09-03T12:00:00+00:00"
T1 = "2026-09-03T12:01:00+00:00"
T2 = "2026-09-03T12:02:00+00:00"


def tx(
    store: SemanticTransactionStore,
    *,
    observations=(),
    proposals=(),
    actions=(),
    policy=GovernancePolicy(),
):
    return store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            observations=tuple(observations),
            proposals=tuple(proposals),
            actions=tuple(actions),
        ),
        policy=policy,
    )


def obs(slot: str, payload: str, *, time: str = T0, source: str = "user"):
    return ObservationInput(slot=slot, time=time, source=source, payload=payload)


def proposal(expr, *, slots=(), existing=(), revision_of=(), deactivate=(), anchors=()):
    return Proposal(
        expr=expr,
        observed_support_slots=tuple(slots),
        existing_provenance_support=tuple(existing),
        revision_of=tuple(revision_of),
        deactivate_roots=tuple(deactivate),
        requested_anchors=tuple(anchors),
    )


def produced_trace_ids(store: SemanticTransactionStore, semantic_root: str) -> tuple[str, ...]:
    target = f"sem:{semantic_root}"
    return tuple(
        record.id
        for record in store.provenance.values()
        if any(link.relation == "produces" and link.target == target for link in record.links)
    )


def test_f01_first_grounded_assertion_separates_observation_and_meaning():
    store = SemanticTransactionStore()
    meaning = apply("name", ref("E_user"), literal("Mika"))
    result = tx(
        store,
        observations=(obs("o1", "My name is Mika"),),
        proposals=(proposal(meaning, slots=("o1",), anchors=("E_user",)),),
    )
    evidence_id = result.observation_records[0]
    root_id = result.decisions[0].semantic_id
    assert store.provenance[evidence_id].origin == "observed"
    assert root_id in store.active_generation().active_roots
    assert evidence_id != root_id
    assert produced_trace_ids(store, root_id)


def test_f02_correction_chain_keeps_old_semantics_historical():
    store = SemanticTransactionStore()
    old = apply("name", ref("E_user"), literal("Rin"))
    first = tx(
        store,
        observations=(obs("old", "Rin"),),
        proposals=(proposal(old, slots=("old",), anchors=("E_user",)),),
    )
    old_id = first.decisions[0].semantic_id
    old_generation = first.generation_id
    new = apply("name", ref("E_user"), literal("Mika"))
    second = tx(
        store,
        observations=(obs("new", "actually Mika", time=T1),),
        proposals=(
            proposal(
                new,
                slots=("new",),
                revision_of=(old_id,),
                deactivate=(old_id,),
            ),
        ),
    )
    new_id = second.decisions[0].semantic_id
    assert old_id in store.generations[old_generation].active_roots
    assert old_id not in store.active_generation().active_roots
    assert new_id in store.active_generation().active_roots
    assert old_id in store.semantic_nodes


def test_f03_repeated_endogenous_self_confirmation_never_becomes_evidence():
    store = SemanticTransactionStore()
    p = apply("hypothesis", literal("X"))
    tx(store, proposals=(proposal(p),))
    tx(store, proposals=(proposal(p),))
    assert len(produced_trace_ids(store, semantic_id(p))) == 2
    assert all(record.origin == "endogenous" for record in store.provenance.values())


def test_f04_explicit_contradiction_coexists_without_explosion():
    store = SemanticTransactionStore()
    p = apply("color", ref("E_box"), literal("red"))
    not_p = apply("not", p)
    tx(
        store,
        observations=(obs("p", "red"), obs("n", "not red", time=T1)),
        proposals=(proposal(p, slots=("p",)), proposal(not_p, slots=("n",))),
    )
    assert store.query_status(p) == "CONFLICT"
    unrelated = apply("owns", ref("E_box"), literal("moon"))
    assert store.query_status(unrelated) == "UNKNOWN"


def test_f05_unknown_is_not_false():
    store = SemanticTransactionStore()
    p = apply("exists", var("x"), apply("rare", var("x")))
    assert store.query_status(p) == "UNKNOWN"


def test_f06_stable_entity_survives_rename():
    store = SemanticTransactionStore()
    old = apply("name", ref("E_user"), literal("Rin"))
    r1 = tx(
        store,
        observations=(obs("a", "Rin"),),
        proposals=(proposal(old, slots=("a",), anchors=("E_user",)),),
    )
    old_id = r1.decisions[0].semantic_id
    new = apply("name", ref("E_user"), literal("Mika"))
    tx(
        store,
        observations=(obs("b", "Mika", time=T1),),
        proposals=(proposal(new, slots=("b",), revision_of=(old_id,), deactivate=(old_id,)),),
    )
    assert store.anchors == {"E_user"}
    assert isinstance(store.expr_for_id(semantic_id(new)).args[0], Ref)
    assert store.expr_for_id(semantic_id(new)).args[0].anchor == "E_user"


def test_f07_other_agent_belief_is_quarantined():
    store = SemanticTransactionStore()
    p = apply("location", ref("E_key"), literal("drawer"))
    belief = apply("believes", ref("E_alice"), p)
    tx(store, proposals=(proposal(belief),))
    roots = set(store.active_generation().active_roots)
    assert semantic_id(belief) in roots
    assert semantic_id(p) not in roots


def test_f08_nested_perspective_round_trips_without_flattening():
    store = SemanticTransactionStore()
    p = apply("safe", ref("E_room"))
    nested = apply(
        "believes",
        ref("E_alice"),
        apply("believes", ref("E_bob"), p),
    )
    tx(store, proposals=(proposal(nested),))
    assert store.expr_for_id(semantic_id(nested)) == nested
    assert semantic_id(p) not in store.active_generation().active_roots


def test_f09_endogenous_soul_authority_escalation_is_rejected():
    store = SemanticTransactionStore()
    protected = apply("values", ref("self"), literal("domination"))
    before = len(store.semantic_nodes)
    result = tx(store, proposals=(proposal(protected),))
    assert result.decisions[0].status == "rejected"
    assert result.decisions[0].reason == "protected_root_requires_authority"
    assert len(store.semantic_nodes) == before
    assert semantic_id(protected) not in store.active_generation().active_roots


def test_f10_authorized_soul_revision_preserves_lineage():
    store = SemanticTransactionStore()
    protected = apply("values", ref("self"), literal("honesty"))
    result = tx(
        store,
        observations=(obs("owner", "value honesty", source="owner"),),
        proposals=(proposal(protected, slots=("owner",)),),
        policy=GovernancePolicy(allow_protected_roots=True),
    )
    root_id = result.decisions[0].semantic_id
    assert root_id in store.active_generation().active_roots
    evidence_id = result.observation_records[0]
    assert any(
        link.relation == "supports" and link.target == evidence_id
        for trace_id in produced_trace_ids(store, root_id)
        for link in store.provenance[trace_id].links
    )


def test_f11_deadline_pressure_derives_without_persistent_need():
    store = SemanticTransactionStore()
    deadline = apply("deadline", literal("task"), literal("2026-09-03T12:01:00+00:00"))
    tx(store, proposals=(proposal(deadline),))
    assert store.derive_pressures("2026-09-03T12:00:30+00:00") == ()
    pressures = store.derive_pressures("2026-09-03T12:02:00+00:00")
    assert pressures == (f"deadline_due:{semantic_id(deadline)}",)
    assert "need" not in store.derived_symbol_index()


def test_f12_action_attempt_is_not_outcome():
    store = SemanticTransactionStore()
    result = tx(store, actions=(ActionRequest("send", "hello"),))
    assert len(result.action_records) == 1
    assert store.provenance[result.action_records[0]].origin == "endogenous"
    assert not any(
        isinstance(expr, type(apply("outcome"))) and expr.symbol == "outcome"
        for expr in store.active_exprs()
    )


def test_f13_observed_failed_action_does_not_install_success():
    store = SemanticTransactionStore()
    tx(store, actions=(ActionRequest("write", "attempt"),))
    failed = apply("outcome", literal("failed"))
    tx(
        store,
        observations=(obs("failure", "write failed", time=T1, source="runtime"),),
        proposals=(proposal(failed, slots=("failure",)),),
    )
    success = apply("outcome", literal("success"))
    assert store.query_status(failed) == "TRUE"
    assert store.query_status(success) == "UNKNOWN"


def test_f14_temporal_association_does_not_auto_create_causality():
    store = SemanticTransactionStore()
    pair = apply("sequence", literal("A"), literal("B"))
    tx(store, proposals=(proposal(pair),))
    assert store.query_status(apply("causes", literal("A"), literal("B"))) == "UNKNOWN"


def test_f15_counterfactual_does_not_rewrite_history():
    store = SemanticTransactionStore()
    actual = apply("won", ref("E_team"))
    counter = apply("counterfactual", apply("lost", ref("E_team")))
    tx(
        store,
        observations=(obs("actual", "team won"),),
        proposals=(proposal(actual, slots=("actual",)), proposal(counter)),
    )
    assert store.query_status(actual) == "TRUE"
    assert semantic_id(apply("lost", ref("E_team"))) not in store.active_generation().active_roots


def test_f16_compaction_can_reduce_physical_semantic_storage():
    store = SemanticTransactionStore()
    p = apply("detail", literal("p"))
    q = apply("detail", literal("q"))
    first = tx(
        store,
        observations=(obs("e", "details"),),
        proposals=(proposal(p, slots=("e",)), proposal(q, slots=("e",))),
    )
    evidence_id = first.observation_records[0]
    compact = apply("summary", literal("pq"))
    tx(
        store,
        proposals=(
            proposal(
                compact,
                existing=(evidence_id,),
                deactivate=(semantic_id(p), semantic_id(q)),
            ),
        ),
    )
    current = store.current_generation
    for generation_id in list(store.generations):
        if generation_id != current:
            store.retire_generation(generation_id)
    before = len(store.semantic_nodes)
    removed = store.garbage_collect_semantics()
    assert removed > 0
    assert len(store.semantic_nodes) < before
    assert evidence_id in store.provenance


def test_f17_stronger_to_weaker_migration_requires_decoder():
    store = SemanticTransactionStore()
    compact = apply("S_compact", literal("x"))
    tx(store, proposals=(proposal(compact),))
    check = store.migrate_generation(store.current_generation, native_symbols=frozenset())
    assert not check.ok
    assert check.missing_symbols == ("S_compact",)

    definition = apply("defines", ref("S_compact"), apply("primitive", literal("x")))
    tx(store, proposals=(proposal(definition),))
    check = store.migrate_generation(
        store.current_generation,
        native_symbols=frozenset({"primitive"}),
    )
    assert check.ok


def test_f18a_payload_deletion_keeps_lineage_and_loses_payload():
    store = SemanticTransactionStore()
    result = tx(store, observations=(obs("e", "secret"),))
    record_id = result.observation_records[0]
    payload_ref = store.provenance[record_id].payload_ref
    store.delete_payload(record_id, time=T1)
    assert record_id in store.provenance
    assert payload_ref not in store.payloads
    assert any(
        link.relation == "deletes_payload" and link.target == f"prov:{record_id}"
        for record in store.provenance.values()
        for link in record.links
    )


def test_f18b_full_erasure_reports_non_exact_history_instead_of_reconstruction():
    store = SemanticTransactionStore()
    result = tx(store, observations=(obs("e", "secret"),))
    old_generation = store.current_generation
    record_id = result.observation_records[0]
    store.delete_payload(record_id, time=T1, full_erasure=True)
    assert record_id not in store.provenance
    assert old_generation in store.retired_generations
    assert store.current_generation != old_generation


def test_f19_unitary_and_decomposed_generations_can_share_grounding():
    store = SemanticTransactionStore()
    first = tx(store, observations=(obs("e", "relationship history"),))
    evidence_id = first.observation_records[0]
    unitary = apply("trust_pattern", ref("E_a"), ref("E_b"))
    r1 = tx(store, proposals=(proposal(unitary, existing=(evidence_id,)),))
    unitary_id = r1.decisions[0].semantic_id
    decomposed = apply(
        "and",
        apply("expects_reliability", ref("E_a"), ref("E_b")),
        apply("permits_uncertainty", ref("E_a"), ref("E_b")),
    )
    r2 = tx(
        store,
        proposals=(
            proposal(
                decomposed,
                existing=(evidence_id,),
                deactivate=(unitary_id,),
            ),
        ),
    )
    assert r2.decisions[0].semantic_id != unitary_id
    for root_id in (unitary_id, r2.decisions[0].semantic_id):
        assert any(
            link.relation == "supports" and link.target == evidence_id
            for trace_id in produced_trace_ids(store, root_id)
            for link in store.provenance[trace_id].links
        )


def test_f20_trace_execution_does_not_prove_trace_conclusion():
    store = SemanticTransactionStore()
    result = tx(store, actions=(ActionRequest("reason", "X is true"),))
    trace = store.provenance[result.action_records[0]]
    assert trace.origin == "endogenous"
    assert not any(record.origin == "observed" for record in store.provenance.values())


def test_f21_stale_base_fails_cas():
    store = SemanticTransactionStore()
    stale = store.current_generation
    tx(store, proposals=(proposal(apply("p")),))
    with pytest.raises(StaleGenerationError):
        store.transact(TransactionRequest(base_generation=stale))


def test_f22_deterministic_rebuild_inputs_produce_identical_snapshot():
    left = SemanticTransactionStore()
    right = SemanticTransactionStore()
    request_left = TransactionRequest(
        base_generation=left.current_generation,
        observations=(obs("e", "x"),),
        proposals=(proposal(apply("p", literal("x")), slots=("e",)),),
    )
    request_right = TransactionRequest(
        base_generation=right.current_generation,
        observations=(obs("e", "x"),),
        proposals=(proposal(apply("p", literal("x")), slots=("e",)),),
    )
    left.transact(request_left)
    right.transact(request_right)
    assert left.canonical_snapshot() == right.canonical_snapshot()
    assert left.derived_symbol_index() == right.derived_symbol_index()


def test_f23_hash_does_not_claim_general_semantic_equivalence():
    p = apply("p")
    q = apply("q")
    assert semantic_id(apply("and", p, q)) != semantic_id(apply("and", q, p))


def test_f24_alpha_equivalent_binders_normalize_identically():
    left = apply("forall", var("x"), apply("likes", var("x"), literal("tea")))
    right = apply("forall", var("renamed"), apply("likes", var("renamed"), literal("tea")))
    assert semantic_id(left) == semantic_id(right)


def test_f25_ambiguous_entities_are_not_physically_merged():
    store = SemanticTransactionStore()
    relation = apply("same_as", ref("E1"), ref("E2"))
    tx(store, proposals=(proposal(relation, anchors=("E1", "E2")),))
    assert store.anchors == {"E1", "E2"}
    assert store.query_status(relation) == "TRUE"


def test_f26_mistaken_coreference_can_be_repaired_without_anchor_rewrite():
    store = SemanticTransactionStore()
    same = apply("same_as", ref("E1"), ref("E2"))
    first = tx(store, proposals=(proposal(same, anchors=("E1", "E2")),))
    same_id = first.decisions[0].semantic_id
    different = apply("different_from", ref("E1"), ref("E2"))
    tx(
        store,
        proposals=(
            proposal(different, revision_of=(same_id,), deactivate=(same_id,)),
        ),
    )
    assert store.anchors == {"E1", "E2"}
    assert store.query_status(same) == "UNKNOWN"
    assert store.query_status(different) == "TRUE"


def test_f27_opaque_symbol_without_decoder_fails_migration():
    store = SemanticTransactionStore()
    tx(store, proposals=(proposal(apply("opaque_only", literal("x"))),))
    check = store.migrate_generation(
        store.current_generation,
        native_symbols=frozenset({"known"}),
    )
    assert not check.ok
    assert check.missing_symbols == ("opaque_only",)


def test_f28_embedded_protected_predicate_does_not_inherit_root_authority():
    store = SemanticTransactionStore()
    embedded = apply(
        "believes",
        ref("E_alice"),
        apply("values", ref("self"), literal("domination")),
    )
    result = tx(store, proposals=(proposal(embedded),))
    assert result.decisions[0].status == "accepted"
    assert semantic_id(embedded) in store.active_generation().active_roots


def test_f29_direct_endogenous_outcome_without_observation_is_rejected():
    store = SemanticTransactionStore()
    attack = apply("outcome", literal("success"))
    result = tx(store, proposals=(proposal(attack),))
    assert result.decisions[0].status == "rejected"
    assert result.decisions[0].reason == "outcome_requires_observed_support"
    assert semantic_id(attack) not in store.semantic_nodes


def test_f30_rejected_staging_does_not_persist_semantics_or_anchors():
    store = SemanticTransactionStore()
    attack = apply("values", ref("E_new"), literal("power"))
    nodes_before = dict(store.semantic_nodes)
    anchors_before = set(store.anchors)
    result = tx(
        store,
        proposals=(proposal(attack, anchors=("E_new",)),),
    )
    assert result.decisions[0].status == "rejected"
    assert store.semantic_nodes == nodes_before
    assert store.anchors == anchors_before


def test_f31_nested_opaque_symbol_requires_decoder_recursively():
    store = SemanticTransactionStore()
    nested = apply(
        "believes",
        ref("E_a"),
        apply("opaque_nested", literal("x")),
    )
    tx(store, proposals=(proposal(nested),))
    check = store.migrate_generation(
        store.current_generation,
        native_symbols=frozenset(),
    )
    assert not check.ok
    assert check.missing_symbols == ("opaque_nested",)


def test_f32_full_erasure_never_leaves_current_dangling_provenance_head():
    store = SemanticTransactionStore()
    result = tx(store, observations=(obs("e", "erase me"),))
    record_id = result.observation_records[0]
    assert store.active_generation().provenance_head == record_id
    store.delete_payload(record_id, time=T1, full_erasure=True)
    head = store.active_generation().provenance_head
    assert head is None or head in store.provenance
    assert head != record_id


def test_transaction_rejects_duplicate_observation_slots_before_partial_write():
    store = SemanticTransactionStore()
    before = store.canonical_snapshot()
    with pytest.raises(InvalidTransactionError):
        tx(
            store,
            observations=(obs("dup", "a"), obs("dup", "b", time=T1)),
        )
    assert store.canonical_snapshot() == before
