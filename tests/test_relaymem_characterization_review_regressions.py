"""Review regressions for the RelayMEM characterization suite.

These focused checks close gaps found while reviewing PR #579.  They keep the
same test-only boundary and assert observable current behavior rather than a
future storage architecture.
"""
from __future__ import annotations

from relaylm.config import RelayLMConfig
from relaylm.subjective_mem_retrieval_cutover import resolve_subjective_mem_retrieval_primary_writer_decision

import pytest

from _relaymem_characterization_support import form_primary_memory, prepare_store
from relaylm.relaymem_primary_correction import (
    apply_primary_memory_correction,
    preflight_primary_memory_correction,
)
from relaylm.relaymem_primary_current_state import resolve_primary_current_state
from relaylm.relaymem_primary_forget import (
    PrimaryForgetError,
    apply_primary_memory_forget_hidden_successor,
    preflight_primary_memory_forget,
)

CHARACTER = "char-a"
NAMESPACE = "characterization-review-ns"


def _prepared_store(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    prepare_store(root)
    return root


def test_correction_publishes_corrected_content_and_preserves_prior_page(tmp_path):
    store = _prepared_store(tmp_path)
    memory_id = form_primary_memory(
        store,
        namespace=NAMESPACE,
        candidate_id="cand-review-correction",
        title="favorite tea",
        summary="The user prefers black tea.",
    )
    prior_page = (
        store / "memory" / "mem" / "primary" / "projects" / f"{memory_id}.md"
    )

    preflight = preflight_primary_memory_correction(
        store_root=str(store),
        character_id=CHARACTER,
        namespace=NAMESPACE,
        memory_id=memory_id,
        expected_revision=1,
        corrected_title="favorite tea",
        corrected_summary="The user prefers green tea.",
        reason="user corrected the record",
        operation_id="op-review-correction",
    )
    result = apply_primary_memory_correction(
        store_root=str(store),
        character_id=CHARACTER,
        namespace=NAMESPACE,
        memory_id=memory_id,
        expected_revision=1,
        operation_id="op-review-correction",
        apply_token=preflight["apply_token"],
                 primary_writer_decision=resolve_subjective_mem_retrieval_primary_writer_decision(RelayLMConfig(backends={}, model_routes={})))

    assert result["status"] == "applied"
    state = resolve_primary_current_state(
        store, namespace=NAMESPACE, memory_id=memory_id
    )
    assert state.current_revision == 2
    assert state.current_physical_id != memory_id

    current_page = store / state.relative_path
    current_text = current_page.read_text(encoding="utf-8")
    assert "green tea" in current_text
    assert "black tea" not in current_text

    # Correct publishes an immutable successor; the prior revision remains
    # inspectable and retains its original bytes.
    assert prior_page.is_file()
    assert "black tea" in prior_page.read_text(encoding="utf-8")


def test_forget_fault_raises_primary_forget_error_not_an_arbitrary_exception(tmp_path):
    store = _prepared_store(tmp_path)
    memory_id = form_primary_memory(
        store,
        namespace=NAMESPACE,
        candidate_id="cand-review-forget",
        title="favorite tea",
        summary="The user prefers black tea.",
    )
    preflight = preflight_primary_memory_forget(
        store_root=str(store),
        character_id=CHARACTER,
        namespace=NAMESPACE,
        memory_id=memory_id,
        expected_revision=1,
        expected_lifecycle_state="active",
        reason="fault probe",
        operation_id="op-review-forget-fault",
    )

    with pytest.raises(PrimaryForgetError, match="reconciliation_required"):
        apply_primary_memory_forget_hidden_successor(
            store_root=str(store),
            character_id=CHARACTER,
            namespace=NAMESPACE,
            memory_id=memory_id,
            expected_revision=1,
            reason="fault probe",
            operation_id="op-review-forget-fault",
            apply_token=preflight["apply_token"],
            fault_at="before_hidden_successor_publication",
        )

    state = resolve_primary_current_state(
        store, namespace=NAMESPACE, memory_id=memory_id
    )
    assert state.lifecycle_state == "active"
    assert state.mutation_state == "prepared"
    assert state.current_revision == 1
