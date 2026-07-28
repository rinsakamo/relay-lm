from __future__ import annotations

import ast
import inspect
from dataclasses import replace
from pathlib import Path

import pytest

import relaylm.subjective_mem_retrieval_selection as selection_owner
from relaylm.evidence_common import utf8_text_digest
from relaylm.relaymem_grounded_recall_response import (
    MAX_EVIDENCE_ITEMS,
    MAX_FACT_TEXT_CHARS,
    build_grounded_recall_context,
)
from relaylm.subjective_mem_retrieval import (
    SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
    SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION,
    SubjectiveMemRetrievalBoundary,
    SubjectiveMemRetrievalProjectionManifest,
    SubjectiveMemRetrievalProjectionRow,
    SubjectiveMemRetrievalRequest,
)
from relaylm.subjective_mem_retrieval_selection import (
    SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SHAPE,
    SubjectiveMemRetrievalContentBinding,
    SubjectiveMemRetrievalPrimaryServedMetrics,
    characterize_subjective_mem_retrieval_shadow,
    select_subjective_mem_retrieval_handoff,
)

D = "a" * 64
D2 = "b" * 64
D3 = "d" * 64
PAGE = "sha256:" + "c" * 64
NOW = "2026-07-28T00:00:00+00:00"
CONTENT = "The recital finished before the rain started."


def _row(**changes) -> SubjectiveMemRetrievalProjectionRow:
    base = SubjectiveMemRetrievalProjectionRow(
        projection_generation_id="projection-generation-1",
        character_id="char1",
        memory_id="memory1",
        memory_revision=2,
        page_id="subjective-mem-page-char1-episodic",
        block_id="subjective-mem-block-memory1-r2",
        canonical_page_digest=PAGE,
        block_digest=D,
        revision_digest=D2,
        current_selector_id="subjective-mem-state-memory1",
        current_selector_digest=D,
        current_receipt_id="subjective-mem-receipt-memory1-r2",
        current_receipt_digest=D2,
        authorization_record_kind="subjective_mem_lifecycle_transition",
        authorization_id="subjective-mem-transition-memory1-r2",
        authorization_digest=D,
        workspace_authority_digest=D2,
        scope_binding_digest=D,
        lifecycle_state="active",
        mutation_state="none",
        retrieval_eligible=True,
        retrieval_visible=True,
        memory_kind="episodic",
        formation_stage="secondary",
        current_selector_unambiguous=True,
        latest_persisted_revision=True,
        finalized_receipt_verified=True,
        authorization_verified=True,
        canonical_binding_verified=True,
        scope_admitted=True,
        unresolved_intent_present=False,
        source_revision_schema="relaylm.subjective_mem_revision.v1",
        source_current_state_schema="relaylm.subjective_mem_current_state.v2",
        source_page_schema="relaylm.subjective_mem_page.v1",
        source_block_schema="relaylm.subjective_mem_lifecycle_block.v1",
        source_renderer_revision="relaylm.subjective_mem_renderer.v1",
        source_partition_revision="relaylm.subjective_mem_partition.v1",
        source_platform_revision="relaylm.subjective_mem_posix_commit.v1",
        projection_policy_revision=SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION,
    )
    return replace(base, **changes)


def _other_row(**changes) -> SubjectiveMemRetrievalProjectionRow:
    return _row(
        memory_id="memory2",
        block_id="subjective-mem-block-memory2-r2",
        current_selector_id="subjective-mem-state-memory2",
        current_receipt_id="subjective-mem-receipt-memory2-r2",
        authorization_id="subjective-mem-transition-memory2-r2",
        **changes,
    )


def _manifest(*rows: SubjectiveMemRetrievalProjectionRow, **changes):
    base = SubjectiveMemRetrievalProjectionManifest(
        projection_generation_id="projection-generation-1",
        source_snapshot_digest=D,
        source_schema_revision_digest=D2,
        row_digests=tuple(sorted(row.row_digest for row in rows)),
        built_at=NOW,
        complete=True,
        mixed_generation=False,
        policy_revision=SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION,
    )
    return replace(base, **changes)


def _request(manifest: SubjectiveMemRetrievalProjectionManifest, **changes):
    base = SubjectiveMemRetrievalRequest(
        character_id="char1",
        workspace_authority_digest=D2,
        admitted_scope_binding_digest=D,
        query_plan_digest=D2,
        request_correlation_digest=D,
        projection_generation_id=manifest.projection_generation_id,
        projection_manifest_digest=manifest.manifest_digest,
        memory_kinds=("episodic", "semantic"),
        candidate_limit=8,
        token_budget=1024,
        policy_revision=SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
        boundary=SubjectiveMemRetrievalBoundary(),
    )
    return replace(base, **changes)


def _binding(row: SubjectiveMemRetrievalProjectionRow, text: str = CONTENT, **changes):
    base = SubjectiveMemRetrievalContentBinding(
        row_digest=row.row_digest,
        memory_id=row.memory_id,
        memory_revision=row.memory_revision,
        character_id="char1",
        workspace_authority_digest=D2,
        scope_binding_digest=D,
        grounded_content=text,
        grounded_content_digest=utf8_text_digest(text),
        token_estimate=16,
    )
    return replace(base, **changes)


def _prepared(*rows: SubjectiveMemRetrievalProjectionRow, shadow: bool = True, **changes):
    """Prepare one handoff over exactly ``rows`` as the complete population."""
    manifest = _manifest(*rows)
    request = _request(manifest, **changes)
    bindings = tuple(_binding(row) for row in rows if not _excluded(row, request))
    return select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=rows, content_bindings=bindings, shadow=shadow
    )


def _excluded(row: SubjectiveMemRetrievalProjectionRow, request) -> bool:
    from relaylm.subjective_mem_retrieval import subjective_mem_retrieval_exclusion_reasons

    return bool(subjective_mem_retrieval_exclusion_reasons(row)) or (
        row.memory_kind not in request.memory_kinds
    )


@pytest.mark.parametrize("lifecycle", ["active", "pinned"])
def test_exact_active_and_pinned_current_rows_are_selected(lifecycle: str) -> None:
    row = _row(lifecycle_state=lifecycle)
    handoff, projection = _prepared(row)
    assert handoff is not None
    assert projection.status == "prepared"
    assert (projection.candidate_count, projection.eligible_count, projection.selected_count) == (1, 1, 1)
    assert handoff.selection.selected_row_digests == (row.row_digest,)
    assert handoff.handoff_shape == SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SHAPE
    assert handoff.evidence_items[0]["fact_text"] == CONTENT
    assert handoff.evidence_items[0]["pinned"] is (lifecycle == "pinned")


def test_selection_orders_pinned_first_then_deterministically_and_replays() -> None:
    first, second = _row(), _other_row(lifecycle_state="pinned")
    handoff, projection = _prepared(first, second)
    assert handoff is not None
    assert handoff.ranked_row_digests == (second.row_digest, first.row_digest)
    replay_handoff, replay_projection = _prepared(first, second)
    assert replay_handoff == handoff and replay_projection == projection
    reordered_handoff, reordered_projection = _prepared(second, first)
    assert reordered_handoff == handoff and reordered_projection == projection


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"lifecycle_state": "held", "retrieval_eligible": False}, "lifecycle_held"),
        ({"lifecycle_state": "hidden", "retrieval_eligible": False}, "lifecycle_hidden"),
        ({"lifecycle_state": "superseded", "retrieval_eligible": False}, "lifecycle_superseded"),
        ({"lifecycle_state": "purged", "retrieval_eligible": False}, "lifecycle_purged"),
        ({"mutation_state": "prepared", "retrieval_eligible": False}, "mutation_prepared"),
        ({"mutation_state": "recovery_required", "retrieval_eligible": False}, "mutation_recovery_required"),
        ({"mutation_state": "corrupt", "retrieval_eligible": False}, "mutation_corrupt"),
        ({"latest_persisted_revision": False}, "not_latest_persisted_revision"),
        ({"current_selector_unambiguous": False}, "current_selector_ambiguous"),
        ({"canonical_binding_verified": False}, "canonical_binding_unverified"),
        ({"finalized_receipt_verified": False}, "receipt_unverified"),
        ({"authorization_verified": False}, "authorization_unverified"),
        ({"scope_admitted": False}, "scope_not_admitted"),
        ({"unresolved_intent_present": True}, "unresolved_intent"),
        ({"retrieval_visible": False}, "retrieval_not_visible"),
    ],
)
def test_prohibited_rows_are_excluded_and_counted_by_reason_class(changes, reason) -> None:
    row = _row(**changes)
    handoff, projection = _prepared(row)
    assert handoff is not None
    assert projection.status == "prepared_empty"
    assert (projection.eligible_count, projection.selected_count) == (0, 0)
    assert handoff.evidence_items == () and handoff.ranked_row_digests == ()
    assert (reason, 1) in projection.excluded_count_by_reason_class


def test_selection_never_fills_an_empty_result_from_another_authority() -> None:
    handoff, projection = _prepared(_row(lifecycle_state="hidden", retrieval_eligible=False))
    assert handoff is not None
    assert projection.selected_count == 0
    assert projection.handoff_shape_class == "empty"
    assert projection.ordinary_route_admitted is False
    assert projection.to_dict()["served_authority"] == "primary_mem"


def test_selection_refuses_an_incomplete_or_duplicated_population() -> None:
    first, second = _row(), _other_row()
    manifest = _manifest(first, second)
    request = _request(manifest)
    _handoff, projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=(first,), content_bindings=()
    )
    assert projection.status == "refused"
    assert "subjective_mem_retrieval_selection_population_incomplete" in projection.blocked_reason_classes

    _handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(_manifest(first)), manifest=_manifest(first), rows=(first, first),
        content_bindings=(),
    )
    assert projection.status == "refused"
    assert "subjective_mem_retrieval_selection_rows_duplicated" in projection.blocked_reason_classes


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"projection_generation_id": "projection-generation-2"}, "subjective_mem_retrieval_selection_row_generation_mismatch"),
        ({"character_id": "char2"}, "subjective_mem_retrieval_selection_row_character_foreign"),
        ({"workspace_authority_digest": D3}, "subjective_mem_retrieval_selection_row_workspace_foreign"),
        ({"scope_binding_digest": D3}, "subjective_mem_retrieval_selection_row_scope_authority_mismatch"),
        ({"projection_policy_revision": "other"}, "subjective_mem_retrieval_projection_policy_revision_invalid"),
        ({"source_platform_revision": "not a token"}, "subjective_mem_retrieval_projection_identifier_invalid"),
    ],
)
def test_selection_fails_closed_on_row_authority_disagreement(changes, reason) -> None:
    row = _row(**changes)
    _handoff, projection = _prepared(row)
    assert projection.status == "refused"
    assert reason in projection.blocked_reason_classes


def test_selection_fails_closed_on_request_manifest_and_generation_mismatch() -> None:
    row = _row()
    manifest = _manifest(row)
    other = _manifest(row, projection_generation_id="projection-generation-2")
    _handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(other), manifest=manifest, rows=(row,), content_bindings=()
    )
    assert projection.status == "refused"
    assert "subjective_mem_retrieval_selection_generation_mismatch" in projection.blocked_reason_classes

    _handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(manifest, projection_manifest_digest=D3), manifest=manifest,
        rows=(row,), content_bindings=(),
    )
    assert "subjective_mem_retrieval_selection_manifest_mismatch" in projection.blocked_reason_classes


def test_selection_fails_closed_on_mixed_generation_and_unsupported_policy() -> None:
    first, second = _row(), _other_row(projection_generation_id="projection-generation-2")
    _handoff, projection = _prepared(first, second)
    assert projection.status == "refused"

    row = _row()
    manifest = _manifest(row)
    _handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(manifest, policy_revision="other"), manifest=manifest,
        rows=(row,), content_bindings=(),
    )
    assert "subjective_mem_retrieval_policy_revision_invalid" in projection.blocked_reason_classes
    assert projection.projection_generation_ready is False


def test_selection_refuses_a_candidate_limit_overflow() -> None:
    first, second = _row(), _other_row()
    _handoff, projection = _prepared(first, second, candidate_limit=1)
    assert projection.status == "refused"
    assert "subjective_mem_retrieval_selection_candidate_limit_exceeded" in projection.blocked_reason_classes


def test_selection_refuses_a_token_budget_overflow_instead_of_truncating() -> None:
    first, second = _row(), _other_row()
    manifest = _manifest(first, second)
    request = _request(manifest, token_budget=24)
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=(first, second),
        content_bindings=(_binding(first), _binding(second)),
    )
    assert handoff is None
    assert projection.status == "refused"
    assert projection.token_budget_class == "exceeded"
    assert "subjective_mem_retrieval_selection_token_budget_exceeded" in projection.blocked_reason_classes


def test_selection_refuses_a_handoff_wider_than_the_grounding_owner_accepts() -> None:
    rows = tuple(
        _row(memory_id=f"memory{index}", block_id=f"subjective-mem-block-memory{index}-r2")
        for index in range(MAX_EVIDENCE_ITEMS + 1)
    )
    manifest = _manifest(*rows)
    request = _request(manifest, candidate_limit=len(rows), token_budget=8192)
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=rows,
        content_bindings=tuple(_binding(row) for row in rows),
    )
    assert handoff is None
    assert "subjective_mem_retrieval_selection_handoff_shape_oversize" in projection.blocked_reason_classes


def test_only_requested_memory_kinds_are_selected_after_exact_eligibility() -> None:
    episodic, semantic = _row(), _other_row(memory_kind="semantic")
    manifest = _manifest(episodic, semantic)
    request = _request(manifest, memory_kinds=("episodic",))
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=(episodic, semantic),
        content_bindings=(_binding(episodic),),
    )
    assert handoff is not None
    assert (projection.eligible_count, projection.selected_count) == (2, 1)
    assert projection.not_requested_kind_count == 1
    assert handoff.ranked_row_digests == (episodic.row_digest,)


@pytest.mark.parametrize(
    ("bindings_for", "reason"),
    [
        ("missing", "subjective_mem_retrieval_selection_content_binding_missing"),
        ("duplicate", "subjective_mem_retrieval_selection_content_binding_duplicated"),
        ("unselected", "subjective_mem_retrieval_selection_content_binding_unselected"),
    ],
)
def test_content_bindings_must_match_the_selected_rows_exactly(bindings_for, reason) -> None:
    first, second = _row(), _other_row()
    manifest = _manifest(first, second)
    request = _request(manifest)
    excluded = _other_row(lifecycle_state="hidden", retrieval_eligible=False)
    bindings = {
        "missing": (_binding(first),),
        "duplicate": (_binding(first), _binding(first), _binding(second)),
        "unselected": (_binding(first), _binding(second), _binding(excluded)),
    }[bindings_for]
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=(first, second), content_bindings=bindings
    )
    assert handoff is None
    assert projection.blocked_reason_classes == (reason,)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"memory_id": "memory9"}, "subjective_mem_retrieval_selection_content_binding_mismatch"),
        ({"memory_revision": 1}, "subjective_mem_retrieval_selection_content_binding_mismatch"),
        ({"character_id": "char2"}, "subjective_mem_retrieval_selection_content_binding_mismatch"),
        ({"workspace_authority_digest": D3}, "subjective_mem_retrieval_selection_content_binding_mismatch"),
        ({"scope_binding_digest": D3}, "subjective_mem_retrieval_selection_content_binding_mismatch"),
        ({"grounded_content": ""}, "subjective_mem_retrieval_selection_content_binding_malformed"),
        ({"grounded_content": "x" * (MAX_FACT_TEXT_CHARS + 1)}, "subjective_mem_retrieval_selection_content_binding_malformed"),
        ({"grounded_content_digest": D3}, "subjective_mem_retrieval_selection_content_binding_digest_mismatch"),
        ({"token_estimate": 0}, "subjective_mem_retrieval_selection_content_binding_token_estimate_invalid"),
    ],
)
def test_stale_foreign_or_malformed_content_bindings_fail_closed(changes, reason) -> None:
    row = _row()
    manifest = _manifest(row)
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(manifest), manifest=manifest, rows=(row,),
        content_bindings=(_binding(row, **changes),),
    )
    assert handoff is None
    assert projection.blocked_reason_classes == (reason,)


def test_a_shadow_result_can_never_become_admitted_or_served_evidence() -> None:
    handoff, projection = _prepared(_row())
    assert handoff is not None and handoff.shadow is True and handoff.admitted is False
    assert projection.shadow is True and projection.usage_event_recorded is False
    assert handoff.admitted_grounding_evidence() == (
        None, ("subjective_mem_retrieval_handoff_shadow_not_admitted",)
    )
    forced = replace(handoff, admitted=True)
    assert forced.admitted_grounding_evidence()[0] is None

    backend_bound, _projection = _prepared(_row(), shadow=False)
    assert backend_bound is not None
    assert backend_bound.admitted_grounding_evidence() == (
        None, ("subjective_mem_retrieval_handoff_not_finalized",)
    )
    assert replace(backend_bound, admitted=True).admitted_grounding_evidence()[0] is not None


def test_public_projection_leaks_no_content_path_query_or_private_identifier() -> None:
    row = _row()
    handoff, projection = _prepared(row)
    assert handoff is not None
    body = repr(projection.to_dict()) + repr(projection) + repr(handoff)
    for forbidden in (
        CONTENT, row.row_digest, row.memory_id, row.current_selector_digest,
        row.current_receipt_digest, row.authorization_digest, row.canonical_page_digest,
        row.projection_generation_id, D, D2, PAGE, "grounded_content", "raw_query",
        "subjective_meaning", "prompt", "page_path", "/",
    ):
        assert forbidden not in body, forbidden
    assert projection.runtime_private_evidence_omitted is True


def test_prepared_private_items_are_the_shape_the_existing_grounding_owner_consumes() -> None:
    first, second = _row(), _other_row(lifecycle_state="pinned")
    handoff, _projection = _prepared(first, second)
    assert handoff is not None
    result = build_grounded_recall_context(
        retrieved_memories=list(handoff.evidence_items), query_text="", character_id="char1"
    )
    assert result.status == "grounding_applied"
    log = result.to_log_dict()
    assert log["grounded_item_count"] == 2 and log["excluded_evidence_count"] == 0
    assert log["runtime_private_evidence_omitted"] is True


def test_characterization_is_deterministic_bounded_and_content_free() -> None:
    excluded = _other_row(lifecycle_state="held", retrieval_eligible=False)
    _handoff, shadow = _prepared(_row(), excluded)
    primary = SubjectiveMemRetrievalPrimaryServedMetrics(
        attempted=True, candidate_count=3, selected_count=1, latency_class="within_bound"
    )
    characterization, reasons = characterize_subjective_mem_retrieval_shadow(
        primary=primary, shadow=shadow, replay=shadow,
        subjective_latency_class="within_bound", projection_rebuild_equivalent=True,
    )
    assert reasons == () and characterization is not None
    body = characterization.to_dict()
    assert body["deterministic_replay_class"] == "deterministic"
    assert body["projection_rebuild_equivalence_class"] == "equivalent"
    assert body["outcome_agreement_class"] == "both_non_empty"
    assert body["leakage_outcome"] == "no_leakage_detected"
    assert body["runtime_private_content_combined"] is False
    assert body["served_authority"] == "primary_mem"
    assert ["lifecycle_held", 1] in body["exclusion_reason_class_counts"]
    repeat, _reasons = characterize_subjective_mem_retrieval_shadow(
        primary=primary, shadow=shadow, replay=shadow,
        subjective_latency_class="within_bound", projection_rebuild_equivalent=True,
    )
    assert repeat == characterization
    assert CONTENT not in repr(body) and D not in repr(body)


def test_characterization_reports_empty_agreement_without_cross_authority_fallback() -> None:
    _handoff, shadow = _prepared(_row(lifecycle_state="hidden", retrieval_eligible=False))
    characterization, reasons = characterize_subjective_mem_retrieval_shadow(
        primary=SubjectiveMemRetrievalPrimaryServedMetrics(
            attempted=True, candidate_count=0, selected_count=0
        ),
        shadow=shadow,
    )
    assert reasons == () and characterization is not None
    assert characterization.outcome_agreement_class == "both_empty"
    assert characterization.deterministic_replay_class == "not_evaluated"
    assert characterization.projection_rebuild_equivalence_class == "not_evaluated"


def test_characterization_refuses_private_content_and_non_shadow_projections() -> None:
    handoff, shadow = _prepared(_row())
    served, _projection = _prepared(_row(), shadow=False)
    primary = SubjectiveMemRetrievalPrimaryServedMetrics(
        attempted=True, candidate_count=1, selected_count=1
    )
    result, reasons = characterize_subjective_mem_retrieval_shadow(primary=primary, shadow=handoff)
    assert result is None
    assert "subjective_mem_retrieval_characterization_projection_invalid" in reasons

    result, reasons = characterize_subjective_mem_retrieval_shadow(primary=primary, shadow=_projection)
    assert result is None
    assert "subjective_mem_retrieval_characterization_shadow_mode_required" in reasons

    result, reasons = characterize_subjective_mem_retrieval_shadow(
        primary=primary, shadow=shadow, subjective_latency_class="fast"
    )
    assert result is None
    assert "subjective_mem_retrieval_characterization_latency_class_invalid" in reasons

    result, reasons = characterize_subjective_mem_retrieval_shadow(primary=served, shadow=shadow)
    assert result is None
    assert "subjective_mem_retrieval_characterization_primary_metrics_invalid" in reasons


def test_selection_owner_never_wires_the_ordinary_route_or_imports_the_ledger() -> None:
    source = inspect.getsource(selection_owner)
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    )
    assert imports == {
        "__future__", "collections.abc", "dataclasses", "typing",
        "relaylm.evidence_common", "relaylm.relaymem_grounded_recall_response",
        "relaylm.subjective_mem_retrieval",
    }
    executable = _executable_source(selection_owner)
    for forbidden in (
        "subjective_mem_retrieval_usage_ledger", "relaymem_primary", "relaymem_retrieval",
        "relayctx", "RelayCTX", "EvidenceRecordStore", "build_grounded_recall_context",
        "Path(", "open(", "read_text", "write_text", "requests", "httpx",
    ):
        assert forbidden not in executable, forbidden


def _executable_source(module) -> str:
    """Module source without docstrings, so prose never satisfies a symbol scan."""

    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ) and ast.get_docstring(node):
            node.body = node.body[1:]
    return ast.unparse(tree)


def test_review_triggers_remain_bounded() -> None:
    source = inspect.getsource(selection_owner)
    assert len(source.splitlines()) < 700
    tree = ast.parse(source)
    lengths = [
        (node.name, max(getattr(item, "end_lineno", node.lineno) for item in ast.walk(node)) - node.lineno + 1)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert max(length for _, length in lengths) <= 80, lengths
    assert Path(selection_owner.__file__).name == "subjective_mem_retrieval_selection.py"
