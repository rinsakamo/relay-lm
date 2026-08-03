"""Characterization: Primary MEM lifecycle mutation and retrieval exclusion.

Locks the currently implemented invariants around:

- Correct (I-3): targeted apply, inspectable revision history, idempotent
  replay by operation, token scope binding, prepared-fault recovery;
- Forget / hide (I-4): hidden successor excludes the memory from ordinary
  retrieval, a fresh index reload (restart analog) keeps it excluded, and no
  physical purge of prior page bytes is performed;
- Pin / Unpin (I-5B): only pin governance state changes, lifecycle and
  retrieval eligibility stay untouched, hidden targets are rejected;
- Held Apply / Discard (I-7C): held candidates stay distinct from formed
  memories, decisions are idempotent and scope-checked, and a decided
  candidate cannot be re-decided the other way;
- namespace/character isolation for identical identifiers and content.

These tests describe today's behavior, not the target architecture.
"""
from __future__ import annotations

import pytest
from _relaymem_characterization_support import (
    eligibility_of,
    form_primary_memory,
    held_candidate_template,
    prepare_store,
)

from relaylm.config import RelayLMConfig
from relaylm.relaymem_held_governance import (
    HeldGovernanceRuntimeError,
    apply_held_governance_decision,
    list_held_governance_history,
    persist_held_candidate_evidence,
    preflight_held_governance_decision,
)
from relaylm.relaymem_primary_correction import (
    PrimaryCorrectionError,
    apply_primary_memory_correction,
    list_primary_memory_corrections,
    preflight_primary_memory_correction,
    recover_primary_memory_corrections,
)
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    apply_primary_memory_forget,
    apply_primary_memory_forget_hidden_successor,
    preflight_primary_memory_forget,
    recover_primary_memory_forget,
)
from relaylm.relaymem_primary_forget_commit import PrimaryForgetCommitResult
from relaylm.relaymem_primary_pin import (
    PrimaryPinError,
    preflight_primary_memory_pin,
)
from relaylm.relaymem_primary_pin_apply import (
    apply_primary_memory_pin,
    apply_primary_memory_unpin,
    get_primary_memory_pin_state,
)
from relaylm.subjective_mem_retrieval_cutover import (
    SubjectiveMemRetrievalPrimaryWriterDecision,
    resolve_subjective_mem_retrieval_primary_writer_decision,
)

PRIMARY_WRITER_DECISION = resolve_subjective_mem_retrieval_primary_writer_decision(RelayLMConfig(backends={}, model_routes={}))

CHARACTER = "char-a"
NAMESPACE = "characterization-ns-a"
OTHER_NAMESPACE = "characterization-ns-b"


@pytest.mark.parametrize(
    "primary_writer_decision",
    (object(), object.__new__(SubjectiveMemRetrievalPrimaryWriterDecision)),
    ids=("foreign", "malformed_exact_type"),
)
@pytest.mark.parametrize(
    ("operation", "error_type"),
    (
        (apply_primary_memory_correction, PrimaryCorrectionError),
        (recover_primary_memory_corrections, PrimaryCorrectionError),
        (apply_primary_memory_forget, PrimaryForgetError),
        (recover_primary_memory_forget, PrimaryForgetError),
        (apply_primary_memory_pin, PrimaryPinError),
        (apply_primary_memory_unpin, PrimaryPinError),
    ),
)
def test_primary_mutations_reject_foreign_writer_decision_before_store_access(
    tmp_path, operation, error_type, primary_writer_decision
):
    arguments = {
        "store_root": str(tmp_path / "missing"),
        "namespace": NAMESPACE,
        "primary_writer_decision": primary_writer_decision,
    }
    if operation is apply_primary_memory_correction:
        arguments.update(
            character_id=CHARACTER,
            memory_id="not-a-memory-id",
            expected_revision=0,
            operation_id="invalid",
            apply_token="invalid",
        )
    elif operation in (apply_primary_memory_pin, apply_primary_memory_unpin):
        arguments.update(character_id=CHARACTER, memory_id="not-a-memory-id", expected_revision=0, reason="invalid", operation_id="invalid", apply_token="invalid")
    elif operation is apply_primary_memory_forget:
        arguments.update(
            character_id=CHARACTER,
            memory_id="not-a-memory-id",
            expected_revision=0,
            expected_lifecycle_state="invalid",
            reason="invalid",
            operation_id="invalid",
            apply_token="invalid",
        )
    elif operation is recover_primary_memory_forget:
        arguments.update(memory_id="not-a-memory-id", operation_id="invalid")
    with pytest.raises(error_type, match="reconciliation_required"):
        operation(**arguments)
    assert not (tmp_path / "missing").exists()


@pytest.fixture()
def store(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    prepare_store(root)
    return root


@pytest.fixture()
def formed(store):
    memory_id = form_primary_memory(
        store,
        namespace=NAMESPACE,
        candidate_id="cand-lifecycle",
        title="favorite tea",
        summary="The user prefers black tea.",
    )
    return store, memory_id


def _correction_preflight(store, memory_id, *, revision=1, operation_id="op-corr-1",
                          summary="The user prefers green tea.", namespace=NAMESPACE,
                          character_id=CHARACTER):
    return preflight_primary_memory_correction(
        store_root=str(store),
        character_id=character_id,
        namespace=namespace,
        memory_id=memory_id,
        expected_revision=revision,
        corrected_title="favorite tea",
        corrected_summary=summary,
        reason="user corrected the record",
        operation_id=operation_id,
    )


class TestCorrection:
    def test_correction_targets_intended_memory_and_keeps_history(self, formed):
        store, memory_id = formed
        preflight = _correction_preflight(store, memory_id)
        assert preflight["status"] == "ready"
        assert preflight["diff"]["summary_changed"] is True

        result = apply_primary_memory_correction(
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            operation_id="op-corr-1",
            apply_token=preflight["apply_token"],
                     primary_writer_decision=resolve_subjective_mem_retrieval_primary_writer_decision(RelayLMConfig(backends={}, model_routes={})))
        assert result["status"] == "applied"
        assert result["prior_revision"] == 1
        assert result["result_revision"] == 2
        assert result["idempotent_replay"] is False

        history = list_primary_memory_corrections(
            store_root=str(store), namespace=NAMESPACE, memory_id=memory_id
        )
        assert len(history["items"]) == 1
        assert history["items"][0]["status"] == "reconciled"

    def test_correction_replay_by_operation_id_is_idempotent(self, formed):
        store, memory_id = formed
        preflight = _correction_preflight(store, memory_id)
        kwargs = dict(
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            operation_id="op-corr-1",
            apply_token=preflight["apply_token"],
        )
        first = apply_primary_memory_correction(**kwargs,
                    primary_writer_decision=resolve_subjective_mem_retrieval_primary_writer_decision(RelayLMConfig(backends={}, model_routes={})))
        replay = apply_primary_memory_correction(**kwargs,
                     primary_writer_decision=resolve_subjective_mem_retrieval_primary_writer_decision(RelayLMConfig(backends={}, model_routes={})))
        assert replay["idempotent_replay"] is True
        assert replay["result_revision"] == first["result_revision"] == 2
        state = resolve_primary_current_state(
            store, namespace=NAMESPACE, memory_id=memory_id
        )
        assert state.current_revision == 2

    def test_cross_character_apply_is_rejected(self, formed):
        store, memory_id = formed
        preflight = _correction_preflight(store, memory_id)
        with pytest.raises(PrimaryCorrectionError, match="token_invalid"):
            apply_primary_memory_correction(
                store_root=str(store),
                character_id="char-b",
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                operation_id="op-corr-1",
                apply_token=preflight["apply_token"],
                primary_writer_decision=resolve_subjective_mem_retrieval_primary_writer_decision(RelayLMConfig(backends={}, model_routes={})))
        state = resolve_primary_current_state(
            store, namespace=NAMESPACE, memory_id=memory_id
        )
        assert state.current_revision == 1

    def test_cross_namespace_preflight_is_rejected(self, formed):
        store, memory_id = formed
        with pytest.raises(PrimaryCorrectionError, match="not_found_or_wrong_scope"):
            _correction_preflight(store, memory_id, namespace=OTHER_NAMESPACE)

    def test_fault_after_prepared_is_excluded_then_recoverable(self, formed):
        store, memory_id = formed
        preflight = _correction_preflight(store, memory_id)
        with pytest.raises(PrimaryCorrectionError, match="reconciliation_required"):
            apply_primary_memory_correction(
                store_root=str(store),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                operation_id="op-corr-1",
                apply_token=preflight["apply_token"],
                fault_at="after_audit_prepared",
                primary_writer_decision=resolve_subjective_mem_retrieval_primary_writer_decision(RelayLMConfig(backends={}, model_routes={})))
        # The failed SLP-side apply does not report a committed result and the
        # prepared claim makes the memory ineligible until convergence.
        state = resolve_primary_current_state(
            store, namespace=NAMESPACE, memory_id=memory_id
        )
        assert state.mutation_state == "recovery_required"
        decision = eligibility_of(
            store, namespace=NAMESPACE, physical_id=state.current_physical_id
        )
        assert decision.eligible is False
        assert decision.reason_id == "excluded_prepared"

        recovered = recover_primary_memory_corrections(
            store_root=str(store), namespace=NAMESPACE,
                        primary_writer_decision=resolve_subjective_mem_retrieval_primary_writer_decision(RelayLMConfig(backends={}, model_routes={})))
        assert recovered == {"recovered": 1, "failed": 0}
        state = resolve_primary_current_state(
            store, namespace=NAMESPACE, memory_id=memory_id
        )
        assert state.mutation_state == "none"
        assert state.lifecycle_state == "active"


class TestForgetHideAndRetrieval:
    def _forget(self, store, memory_id, *, operation_id="op-forget-1"):
        preflight = preflight_primary_memory_forget(
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason="user asked to forget",
            operation_id=operation_id,
        )
        assert preflight["status"] == "ready"
        return apply_primary_memory_forget(
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason="user asked to forget",
            operation_id=operation_id,
            apply_token=preflight["apply_token"],
                   primary_writer_decision=resolve_subjective_mem_retrieval_primary_writer_decision(RelayLMConfig(backends={}, model_routes={})))

    def test_forgotten_memory_is_excluded_from_ordinary_retrieval(self, formed):
        store, memory_id = formed
        result = self._forget(store, memory_id).to_log_dict()
        assert result["status"] == "applied"
        assert result["lifecycle_state"] == "hidden"
        assert result["retrieval_eligible"] is False

        # Both the prior physical revision and the hidden successor are
        # excluded; the eligibility index is rebuilt from disk each time, so
        # this is also the fresh-process (restart) read.
        prior = eligibility_of(store, namespace=NAMESPACE, physical_id=memory_id)
        assert (prior.eligible, prior.reason_id) == (False, "excluded_prior_revision")
        state = resolve_primary_current_state(
            store, namespace=NAMESPACE, memory_id=memory_id
        )
        successor = eligibility_of(
            store, namespace=NAMESPACE, physical_id=state.current_physical_id
        )
        assert (successor.eligible, successor.reason_id) == (False, "excluded_hidden")

    def test_forget_is_lifecycle_hide_not_physical_purge(self, formed):
        store, memory_id = formed
        self._forget(store, memory_id)
        # Current behavior keeps the prior page bytes on disk; Forget is a
        # lifecycle exclusion, not secure deletion. Tests must not pretend
        # a physical-purge guarantee exists.
        prior_page = (
            store / "memory" / "mem" / "primary" / "projects" / f"{memory_id}.md"
        )
        assert prior_page.is_file()
        assert "black tea" in prior_page.read_text(encoding="utf-8")

    def test_commit_fault_before_hidden_publication_fails_closed(self, formed):
        store, memory_id = formed
        preflight = preflight_primary_memory_forget(
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason="fault probe",
            operation_id="op-forget-fault",
        )
        with pytest.raises(Exception, match="reconciliation_required"):
            apply_primary_memory_forget_hidden_successor(
                store_root=str(store),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=1,
                reason="fault probe",
                operation_id="op-forget-fault",
                apply_token=preflight["apply_token"],
                fault_at="before_hidden_successor_publication",
            )
        # Failure before the durable hidden publication does not falsely
        # report success; the prepared claim already excludes the memory.
        state = resolve_primary_current_state(
            store, namespace=NAMESPACE, memory_id=memory_id
        )
        assert state.lifecycle_state == "active"
        assert state.mutation_state == "prepared"
        assert state.current_revision == 1
        decision = eligibility_of(store, namespace=NAMESPACE, physical_id=memory_id)
        assert (decision.eligible, decision.reason_id) == (False, "excluded_prepared")

        # Re-running the same operation converges the interrupted Forget.
        retry = apply_primary_memory_forget(
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason="fault probe",
            operation_id="op-forget-fault",
            apply_token=preflight["apply_token"],
                    primary_writer_decision=resolve_subjective_mem_retrieval_primary_writer_decision(RelayLMConfig(backends={}, model_routes={}))).to_log_dict()
        assert retry["status"] == "applied"
        assert retry["lifecycle_state"] == "hidden"
        assert retry["result_revision"] == 2

    def test_forget_commit_result_shape_is_content_free(self, formed):
        store, memory_id = formed
        result = self._forget(store, memory_id)
        log = result.to_log_dict()
        assert log["content_included"] is False
        assert log["path_included"] is False
        assert log["identifier_included"] is False


class TestPinUnpin:
    def _pin(self, store, memory_id, *, operation_id="op-pin-1"):
        preflight = preflight_primary_memory_pin(
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            reason="keep this",
            operation_id=operation_id,
        )
        assert preflight["status"] == "ready"
        return apply_primary_memory_pin(primary_writer_decision=PRIMARY_WRITER_DECISION,
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            reason="keep this",
            operation_id=operation_id,
            apply_token=preflight["apply_token"],
        )

    def test_pin_changes_only_pin_state(self, formed):
        store, memory_id = formed
        result = self._pin(store, memory_id)
        assert result.status == "applied"
        assert result.effect_applied is True
        assert get_primary_memory_pin_state(
            store, namespace=NAMESPACE, memory_id=memory_id
        ) == "pinned"
        # Lifecycle and retrieval eligibility are untouched by Pin.
        state = resolve_primary_current_state(
            store, namespace=NAMESPACE, memory_id=memory_id
        )
        assert state.lifecycle_state == "active"
        assert state.mutation_state == "none"
        assert state.current_revision == 1
        decision = eligibility_of(store, namespace=NAMESPACE, physical_id=memory_id)
        assert (decision.eligible, decision.reason_id) == (
            True,
            "eligible_current_active",
        )

    def test_pin_replay_is_idempotent(self, formed):
        store, memory_id = formed
        preflight = preflight_primary_memory_pin(
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            reason="keep this",
            operation_id="op-pin-1",
        )
        kwargs = dict(
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            reason="keep this",
            operation_id="op-pin-1",
            apply_token=preflight["apply_token"],
        )
        first = apply_primary_memory_pin(primary_writer_decision=PRIMARY_WRITER_DECISION, **kwargs)
        replay = apply_primary_memory_pin(primary_writer_decision=PRIMARY_WRITER_DECISION, **kwargs)
        assert first.idempotent_replay is False
        assert replay.idempotent_replay is True
        assert replay.status == "applied"

    def test_unpin_of_unpinned_memory_reports_already_unpinned(self, formed):
        store, memory_id = formed
        from relaylm.relaymem_primary_pin import preflight_primary_memory_unpin

        preflight = preflight_primary_memory_unpin(
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            reason="not pinned yet",
            operation_id="op-unpin-1",
        )
        result = apply_primary_memory_unpin(primary_writer_decision=PRIMARY_WRITER_DECISION,
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            reason="not pinned yet",
            operation_id="op-unpin-1",
            apply_token=preflight["apply_token"],
        )
        assert result.status == "already_unpinned"
        assert result.effect_applied is False

    def test_pin_rejects_hidden_memory(self, formed):
        store, memory_id = formed
        forget_preflight = preflight_primary_memory_forget(
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason="hide first",
            operation_id="op-forget-pin",
        )
        apply_primary_memory_forget(
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            expected_lifecycle_state="active",
            reason="hide first",
            operation_id="op-forget-pin",
            apply_token=forget_preflight["apply_token"],
            primary_writer_decision=resolve_subjective_mem_retrieval_primary_writer_decision(RelayLMConfig(backends={}, model_routes={})))
        with pytest.raises(PrimaryPinError, match="target_not_active"):
            preflight_primary_memory_pin(
                store_root=str(store),
                character_id=CHARACTER,
                namespace=NAMESPACE,
                memory_id=memory_id,
                expected_revision=2,
                reason="pin hidden",
                operation_id="op-pin-hidden",
            )


class TestHeldApplyDiscard:
    def _decide(self, store, candidate, action, *, operation_id, reason="operator_reviewed"):
        preflight = preflight_held_governance_decision(
            store,
            candidate_id=candidate["candidate_id"],
            action=action,
            expected_character_id=candidate["character_id"],
            expected_namespace=candidate["namespace"],
            operation_id=operation_id,
            reason=reason,
        )
        assert preflight["status"] == "ready", preflight
        return apply_held_governance_decision(
            store,
            candidate_id=candidate["candidate_id"],
            action=action,
            expected_character_id=candidate["character_id"],
            expected_namespace=candidate["namespace"],
            operation_id=operation_id,
            reason=reason,
            apply_token=preflight["apply_token"],
        )

    def test_held_apply_records_decision_without_forming_memory(self, store):
        candidate = held_candidate_template()
        persist_held_candidate_evidence(store, candidate)
        receipt = self._decide(store, candidate, "apply", operation_id="op-held-1")
        assert receipt["status"] == "applied"
        # The current I-7C apply adopts the held item as governance evidence
        # only; it does not mutate Primary MEM or the queue and starts nothing.
        assert receipt["primary_mem_mutated"] is False
        assert receipt["queue_state_mutated"] is False
        assert receipt["worker_started"] is False
        assert receipt["scheduler_started"] is False
        # No Primary MEM page appears anywhere in the store.
        assert list((store / "memory" / "mem" / "primary").rglob("*.md")) == []

    def test_held_decision_replay_is_idempotent(self, store):
        candidate = held_candidate_template()
        persist_held_candidate_evidence(store, candidate)
        preflight = preflight_held_governance_decision(
            store,
            candidate_id=candidate["candidate_id"],
            action="apply",
            expected_character_id=candidate["character_id"],
            expected_namespace=candidate["namespace"],
            operation_id="op-held-1",
            reason="operator_reviewed",
        )
        kwargs = dict(
            candidate_id=candidate["candidate_id"],
            action="apply",
            expected_character_id=candidate["character_id"],
            expected_namespace=candidate["namespace"],
            operation_id="op-held-1",
            reason="operator_reviewed",
            apply_token=preflight["apply_token"],
        )
        first = apply_held_governance_decision(store, **kwargs)
        replay = apply_held_governance_decision(store, **kwargs)
        assert first["status"] == "applied"
        assert replay["status"] == "already_applied"
        assert replay["idempotent_replay"] is True

    def test_decided_candidate_cannot_be_reversed(self, store):
        candidate = held_candidate_template()
        persist_held_candidate_evidence(store, candidate)
        self._decide(store, candidate, "apply", operation_id="op-held-1")
        conflict = apply_held_governance_decision(
            store,
            candidate_id=candidate["candidate_id"],
            action="discard",
            expected_character_id=candidate["character_id"],
            expected_namespace=candidate["namespace"],
            operation_id="op-held-2",
            reason="changed_mind",
            apply_token="token-never-validated-after-decision",
        )
        assert conflict["status"] == "operation_conflict"
        history = list_held_governance_history(
            store, candidate_id=candidate["candidate_id"]
        )
        assert [(item["status"], item["action"]) for item in history["items"]] == [
            ("applied", "apply")
        ]

    def test_held_decision_is_namespace_scope_checked(self, store):
        candidate = held_candidate_template()
        persist_held_candidate_evidence(store, candidate)
        preflight = preflight_held_governance_decision(
            store,
            candidate_id=candidate["candidate_id"],
            action="apply",
            expected_character_id=candidate["character_id"],
            expected_namespace=OTHER_NAMESPACE,
            operation_id="op-held-1",
            reason="operator_reviewed",
        )
        assert preflight["status"] == "blocked"
        assert preflight["reason_code"] == "wrong_namespace"
        assert preflight["apply_token"] is None

    def test_already_final_candidate_cannot_be_persisted_as_held(self, store):
        with pytest.raises(HeldGovernanceRuntimeError, match="not_held"):
            persist_held_candidate_evidence(
                store, held_candidate_template(status="applied")
            )


class TestNamespaceIsolation:
    def test_same_candidate_in_two_namespaces_forms_distinct_memories(self, store):
        memory_a = form_primary_memory(
            store,
            namespace=NAMESPACE,
            candidate_id="cand-shared",
            title="shared title",
            summary="Shared summary text.",
        )
        memory_b = form_primary_memory(
            store,
            namespace=OTHER_NAMESPACE,
            candidate_id="cand-shared",
            title="shared title",
            summary="Shared summary text.",
        )
        # Identical identifiers and content still derive namespace-distinct
        # idempotency keys and pages.
        assert memory_a != memory_b
        pages = store / "memory" / "mem" / "primary" / "projects"
        assert (pages / f"{memory_a}.md").is_file()
        assert (pages / f"{memory_b}.md").is_file()

    def test_eligibility_index_never_leaks_across_namespaces(self, store):
        memory_a = form_primary_memory(
            store,
            namespace=NAMESPACE,
            candidate_id="cand-shared",
            title="shared title",
            summary="Shared summary text.",
        )
        memory_b = form_primary_memory(
            store,
            namespace=OTHER_NAMESPACE,
            candidate_id="cand-shared",
            title="shared title",
            summary="Shared summary text.",
        )
        own = eligibility_of(store, namespace=NAMESPACE, physical_id=memory_a)
        assert own.eligible is True

        # A candidate declared for another namespace is rejected outright.
        declared = eligibility_of(
            store,
            namespace=NAMESPACE,
            physical_id=memory_b,
            candidate_namespace=OTHER_NAMESPACE,
        )
        assert (declared.eligible, declared.reason_id) == (
            False,
            "excluded_scope_mismatch",
        )
        # And a foreign physical id does not resolve to an eligible memory in
        # this namespace's index.
        foreign = eligibility_of(store, namespace=NAMESPACE, physical_id=memory_b)
        assert foreign.eligible is False

    def test_correction_cannot_cross_namespaces(self, store):
        memory_a = form_primary_memory(
            store,
            namespace=NAMESPACE,
            candidate_id="cand-shared",
            title="shared title",
            summary="Shared summary text.",
        )
        with pytest.raises(PrimaryCorrectionError, match="not_found_or_wrong_scope"):
            preflight_primary_memory_correction(
                store_root=str(store),
                character_id=CHARACTER,
                namespace=OTHER_NAMESPACE,
                memory_id=memory_a,
                expected_revision=1,
                corrected_title="shared title",
                corrected_summary="Attempted cross-namespace edit.",
                reason="attempted cross-scope",
                operation_id="op-cross-1",
            )
