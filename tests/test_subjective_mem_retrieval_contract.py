from __future__ import annotations

import ast
import inspect
from dataclasses import replace
from pathlib import Path

import pytest

import relaylm.subjective_mem_retrieval as retrieval
from relaylm.evidence.common import canonical_digest
from relaylm.subjective_mem_retrieval import (
    RETRIEVAL_EXCLUSION_REASONS,
    SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
    SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION,
    SubjectiveMemRetrievalBoundary,
    SubjectiveMemRetrievalExclusion,
    SubjectiveMemRetrievalProjectionManifest,
    SubjectiveMemRetrievalProjectionRow,
    SubjectiveMemRetrievalRequest,
    SubjectiveMemRetrievalSelection,
    derive_subjective_mem_retrieval_usage_event,
    subjective_mem_retrieval_exclusion_reasons,
    validate_subjective_mem_retrieval_exclusion,
    validate_subjective_mem_retrieval_projection_manifest,
    validate_subjective_mem_retrieval_projection_row,
    validate_subjective_mem_retrieval_request,
    validate_subjective_mem_retrieval_selection,
    validate_subjective_mem_retrieval_usage_event,
)

D = "a" * 64
D2 = "b" * 64
PAGE = "sha256:" + "c" * 64
NOW = "2026-07-28T00:00:00+00:00"


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


def _selection(request, manifest, *rows, **changes):
    """Build a selection whose reported counts match a population of exactly ``rows``.

    Cases that supply a wider or inconsistent candidate population override the
    reported counts explicitly, so the fixture never repairs a caller's numbers.
    """
    digests = tuple(sorted(row.row_digest for row in rows))
    base = SubjectiveMemRetrievalSelection(
        request_input_digest=request.input_digest,
        projection_generation_id=request.projection_generation_id,
        projection_manifest_digest=manifest.manifest_digest,
        selected_row_digests=digests,
        candidate_count=len(rows),
        eligible_count=len(rows),
        selected_count=len(rows),
        total_token_estimate=64 * len(rows),
        policy_revision=SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
    )
    return replace(base, **changes)


def test_request_is_content_free_deterministic_and_bounded() -> None:
    row = _row()
    manifest = _manifest(row)
    request = _request(manifest)
    assert validate_subjective_mem_retrieval_request(request) == ()
    assert request.input_digest == canonical_digest(request.to_digest_input())
    assert request.request_id == _request(manifest).request_id
    body = request.to_digest_input()
    assert not {"raw_query", "grounded_content", "subjective_meaning", "page_path"}.intersection(body)
    assert body["boundary"]["primary_mem_fallback_prohibited"] is True
    assert body["boundary"]["ordinary_runtime_not_wired"] is True


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"memory_kinds": ("semantic", "episodic")}, "subjective_mem_retrieval_request_memory_kinds_invalid"),
        ({"memory_kinds": ("episodic", "episodic")}, "subjective_mem_retrieval_request_memory_kinds_invalid"),
        ({"candidate_limit": 0}, "subjective_mem_retrieval_candidate_limit_invalid"),
        ({"token_budget": 8193}, "subjective_mem_retrieval_token_budget_invalid"),
        ({"policy_revision": "other"}, "subjective_mem_retrieval_policy_revision_invalid"),
        ({"query_plan_digest": "bad"}, "subjective_mem_retrieval_request_digest_invalid"),
        ({"boundary": replace(SubjectiveMemRetrievalBoundary(), primary_mem_fallback_prohibited=False)}, "subjective_mem_retrieval_boundary_invalid"),
    ],
)
def test_request_validation_fails_closed(changes, reason) -> None:
    manifest = _manifest(_row())
    assert reason in validate_subjective_mem_retrieval_request(_request(manifest, **changes))


@pytest.mark.parametrize("lifecycle", ["active", "pinned"])
def test_exact_active_and_pinned_rows_are_eligible(lifecycle: str) -> None:
    row = _row(lifecycle_state=lifecycle)
    assert validate_subjective_mem_retrieval_projection_row(row) == ()
    assert subjective_mem_retrieval_exclusion_reasons(row) == ()
    assert row.row_id == replace(row).row_id


@pytest.mark.parametrize(
    ("changes", "reasons"),
    [
        ({"lifecycle_state": "held", "retrieval_eligible": False}, {"lifecycle_held", "retrieval_not_eligible"}),
        ({"lifecycle_state": "hidden", "retrieval_eligible": False}, {"lifecycle_hidden", "retrieval_not_eligible"}),
        ({"lifecycle_state": "superseded", "retrieval_eligible": False}, {"lifecycle_superseded", "retrieval_not_eligible"}),
        ({"lifecycle_state": "purged", "retrieval_eligible": False}, {"lifecycle_purged", "retrieval_not_eligible"}),
        ({"mutation_state": "prepared", "retrieval_eligible": False}, {"mutation_prepared", "retrieval_not_eligible"}),
        ({"mutation_state": "recovery_required", "retrieval_eligible": False}, {"mutation_recovery_required", "retrieval_not_eligible"}),
        ({"mutation_state": "corrupt", "retrieval_eligible": False}, {"mutation_corrupt", "retrieval_not_eligible"}),
        ({"retrieval_visible": False}, {"retrieval_not_visible"}),
        ({"current_selector_unambiguous": False}, {"current_selector_ambiguous"}),
        ({"latest_persisted_revision": False}, {"not_latest_persisted_revision"}),
        ({"canonical_binding_verified": False}, {"canonical_binding_unverified"}),
        ({"finalized_receipt_verified": False}, {"receipt_unverified"}),
        ({"authorization_verified": False}, {"authorization_unverified"}),
        ({"scope_admitted": False}, {"scope_not_admitted"}),
        ({"unresolved_intent_present": True}, {"unresolved_intent"}),
    ],
)
def test_exclusion_reasons_cover_fail_closed_currentness_and_state(changes, reasons) -> None:
    row = _row(**changes)
    assert validate_subjective_mem_retrieval_projection_row(row) == ()
    assert reasons.issubset(set(subjective_mem_retrieval_exclusion_reasons(row)))


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"memory_revision": 0}, "subjective_mem_retrieval_projection_revision_invalid"),
        ({"canonical_page_digest": D}, "subjective_mem_retrieval_projection_digest_invalid"),
        ({"authorization_record_kind": "primary_mem"}, "subjective_mem_retrieval_projection_authorization_kind_invalid"),
        ({"lifecycle_state": "unknown"}, "subjective_mem_retrieval_projection_lifecycle_invalid"),
        ({"mutation_state": "busy"}, "subjective_mem_retrieval_projection_mutation_invalid"),
        ({"memory_kind": "product_knowledge"}, "subjective_mem_retrieval_projection_memory_kind_invalid"),
        ({"formation_stage": "merged"}, "subjective_mem_retrieval_projection_formation_stage_invalid"),
        ({"retrieval_eligible": False}, "subjective_mem_retrieval_projection_eligibility_pair_invalid"),
        ({"scope_admitted": 1}, "subjective_mem_retrieval_projection_boolean_invalid"),
        ({"projection_policy_revision": "other"}, "subjective_mem_retrieval_projection_policy_revision_invalid"),
    ],
)
def test_projection_row_shape_and_pair_validation(changes, reason) -> None:
    row = _row(**changes)
    assert reason in validate_subjective_mem_retrieval_projection_row(row)
    assert subjective_mem_retrieval_exclusion_reasons(row) == ("projection_row_invalid",)


def test_projection_row_digest_binds_every_authority_family() -> None:
    row = _row()
    changes = {
        "current_selector_digest": D2,
        "current_receipt_digest": D,
        "authorization_digest": D2,
        "scope_binding_digest": D2,
        "canonical_page_digest": "sha256:" + "d" * 64,
        "source_renderer_revision": "relaylm.subjective_mem_renderer.v2",
    }
    for field, value in changes.items():
        assert replace(row, **{field: value}).row_digest != row.row_digest, field


def test_complete_single_generation_manifest_is_noncanonical_and_rebuildable() -> None:
    rows = (_row(), _row(memory_id="memory2", block_id="block2", current_selector_id="state2", current_receipt_id="receipt2", authorization_id="auth2"))
    manifest = _manifest(*rows)
    assert validate_subjective_mem_retrieval_projection_manifest(manifest) == ()
    body = manifest.to_digest_input()
    assert body["canonical_authority"] is False
    assert body["rebuildable"] is True
    assert body["row_count"] == 2


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"row_digests": (D2, D)}, "subjective_mem_retrieval_projection_manifest_rows_invalid"),
        ({"row_digests": (D, D)}, "subjective_mem_retrieval_projection_manifest_rows_invalid"),
        ({"complete": False}, "subjective_mem_retrieval_projection_manifest_state_invalid"),
        ({"mixed_generation": True}, "subjective_mem_retrieval_projection_manifest_state_invalid"),
        ({"built_at": "naive"}, "subjective_mem_retrieval_projection_manifest_time_invalid"),
        ({"policy_revision": "other"}, "subjective_mem_retrieval_projection_policy_revision_invalid"),
    ],
)
def test_manifest_fail_closed_states(changes, reason) -> None:
    assert reason in validate_subjective_mem_retrieval_projection_manifest(_manifest(_row(), **changes))


def test_exclusion_identity_is_closed_and_content_free() -> None:
    row = _row(lifecycle_state="hidden", retrieval_eligible=False)
    manifest = _manifest(row)
    request = _request(manifest)
    exclusion = SubjectiveMemRetrievalExclusion(
        projection_generation_id=row.projection_generation_id,
        request_input_digest=request.input_digest,
        memory_id=row.memory_id,
        memory_revision=row.memory_revision,
        row_digest_or_null=row.row_digest,
        reason="lifecycle_hidden",
    )
    assert validate_subjective_mem_retrieval_exclusion(exclusion) == ()
    assert exclusion.reason in RETRIEVAL_EXCLUSION_REASONS
    assert exclusion.exclusion_id == replace(exclusion).exclusion_id
    assert "grounded_content" not in repr(exclusion.to_digest_input())
    assert validate_subjective_mem_retrieval_exclusion(replace(exclusion, reason="bad")) == (
        "subjective_mem_retrieval_exclusion_reason_invalid",
    )


def test_selection_requires_exact_request_manifest_generation_and_eligible_rows() -> None:
    row = _row()
    manifest = _manifest(row)
    request = _request(manifest)
    selection = _selection(request, manifest, row)
    assert validate_subjective_mem_retrieval_selection(
        request=request, manifest=manifest, rows=(row,), selection=selection
    ) == ()
    assert selection.selection_id == _selection(request, manifest, row).selection_id

    cases = (
        replace(selection, request_input_digest=D2),
        replace(selection, projection_generation_id="other-generation"),
        replace(selection, projection_manifest_digest=D2),
        replace(selection, selected_count=2),
        replace(selection, total_token_estimate=request.token_budget + 1),
        replace(selection, selected_row_digests=(D2,)),
    )
    for candidate in cases:
        assert validate_subjective_mem_retrieval_selection(
            request=request, manifest=manifest, rows=(row,), selection=candidate
        ), candidate


def test_selection_rejects_ineligible_or_foreign_generation_row() -> None:
    hidden = _row(lifecycle_state="hidden", retrieval_eligible=False)
    manifest = _manifest(hidden)
    request = _request(manifest)
    selection = _selection(request, manifest, hidden)
    reasons = validate_subjective_mem_retrieval_selection(
        request=request, manifest=manifest, rows=(hidden,), selection=selection
    )
    assert "subjective_mem_retrieval_selection_row_ineligible" in reasons

    foreign = _row(projection_generation_id="projection-generation-2")
    manifest = _manifest(foreign, projection_generation_id="projection-generation-1")
    request = _request(manifest)
    selection = _selection(request, manifest, foreign)
    assert "subjective_mem_retrieval_selection_row_ineligible" in validate_subjective_mem_retrieval_selection(
        request=request, manifest=manifest, rows=(foreign,), selection=selection
    )


def _mixed_population():
    """One eligible and one hidden candidate, both bound to the same manifest."""
    eligible = _row()
    hidden = _other_row(lifecycle_state="hidden", retrieval_eligible=False)
    manifest = _manifest(eligible, hidden)
    request = _request(manifest)
    return eligible, hidden, manifest, request


def test_selection_accepts_exact_mixed_eligible_and_ineligible_population() -> None:
    eligible, hidden, manifest, request = _mixed_population()
    selection = _selection(request, manifest, eligible, candidate_count=2, eligible_count=1)
    assert validate_subjective_mem_retrieval_selection(
        request=request, manifest=manifest, rows=(eligible, hidden), selection=selection
    ) == ()
    assert selection.candidate_count == 2
    assert (selection.eligible_count, selection.selected_count) == (1, 1)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"candidate_count": 1}, "subjective_mem_retrieval_selection_candidate_count_mismatch"),
        ({"candidate_count": 3}, "subjective_mem_retrieval_selection_candidate_count_mismatch"),
        ({"eligible_count": 0}, "subjective_mem_retrieval_selection_eligible_count_mismatch"),
        ({"eligible_count": 2}, "subjective_mem_retrieval_selection_eligible_count_mismatch"),
    ],
)
def test_selection_rejects_misreported_population_counts(changes, reason) -> None:
    eligible, hidden, manifest, request = _mixed_population()
    counts = {"candidate_count": 2, "eligible_count": 1, **changes}
    selection = _selection(request, manifest, eligible, **counts)
    assert reason in validate_subjective_mem_retrieval_selection(
        request=request, manifest=manifest, rows=(eligible, hidden), selection=selection
    )


def test_selection_rejects_a_duplicate_supplied_candidate_row() -> None:
    row = _row()
    manifest = _manifest(row)
    request = _request(manifest)
    selection = _selection(request, manifest, row, candidate_count=2, eligible_count=2)
    reasons = validate_subjective_mem_retrieval_selection(
        request=request, manifest=manifest, rows=(row, row), selection=selection
    )
    assert "subjective_mem_retrieval_selection_rows_duplicated" in reasons
    assert "subjective_mem_retrieval_selection_row_missing" in reasons


def test_selection_rejects_a_duplicate_selected_row_digest() -> None:
    row = _row()
    manifest = _manifest(row)
    request = _request(manifest)
    selection = _selection(
        request, manifest, row,
        selected_row_digests=(row.row_digest, row.row_digest), selected_count=2,
    )
    reasons = validate_subjective_mem_retrieval_selection(
        request=request, manifest=manifest, rows=(row,), selection=selection
    )
    assert "subjective_mem_retrieval_selection_row_digests_invalid" in reasons
    assert "subjective_mem_retrieval_selection_selected_count_mismatch" in reasons


def test_selection_requires_selected_count_to_equal_unique_selected_digests() -> None:
    row = _row()
    manifest = _manifest(row)
    request = _request(manifest)
    selection = _selection(request, manifest, row, selected_count=0)
    assert "subjective_mem_retrieval_selection_selected_count_mismatch" in (
        validate_subjective_mem_retrieval_selection(
            request=request, manifest=manifest, rows=(row,), selection=selection
        )
    )


def test_selection_rejects_an_unselected_foreign_generation_candidate() -> None:
    eligible = _row()
    foreign = _other_row(projection_generation_id="projection-generation-2")
    manifest = _manifest(eligible, foreign)
    request = _request(manifest)
    selection = _selection(request, manifest, eligible, candidate_count=2, eligible_count=2)
    assert "subjective_mem_retrieval_selection_row_generation_mismatch" in (
        validate_subjective_mem_retrieval_selection(
            request=request, manifest=manifest, rows=(eligible, foreign), selection=selection
        )
    )


def test_selection_rejects_an_unselected_manifest_unbound_candidate() -> None:
    eligible = _row()
    unbound = _other_row()
    manifest = _manifest(eligible)
    request = _request(manifest)
    selection = _selection(request, manifest, eligible, candidate_count=2, eligible_count=2)
    assert "subjective_mem_retrieval_selection_row_unmanifested" in (
        validate_subjective_mem_retrieval_selection(
            request=request, manifest=manifest, rows=(eligible, unbound), selection=selection
        )
    )


def test_selection_rejects_a_candidate_population_above_the_request_limit() -> None:
    first, second = _row(), _other_row()
    manifest = _manifest(first, second)
    request = _request(manifest, candidate_limit=1)
    selection = _selection(request, manifest, first, candidate_count=2, eligible_count=2)
    assert "subjective_mem_retrieval_selection_candidate_limit_exceeded" in (
        validate_subjective_mem_retrieval_selection(
            request=request, manifest=manifest, rows=(first, second), selection=selection
        )
    )


def test_selection_rejects_a_token_budget_overflow() -> None:
    row = _row()
    manifest = _manifest(row)
    request = _request(manifest)
    selection = _selection(
        request, manifest, row, total_token_estimate=request.token_budget + 1
    )
    assert "subjective_mem_retrieval_selection_budget_invalid" in (
        validate_subjective_mem_retrieval_selection(
            request=request, manifest=manifest, rows=(row,), selection=selection
        )
    )


def test_usage_event_derivation_rejects_a_population_binding_failure() -> None:
    row = _row()
    unbound = _other_row()
    manifest = _manifest(row)
    request = _request(manifest)
    selection = _selection(request, manifest, row, candidate_count=2, eligible_count=2)
    event, reasons = derive_subjective_mem_retrieval_usage_event(
        request=request, manifest=manifest, rows=(row, unbound), selection=selection, row=row,
        event_kind="grounded_context_admitted", occurred_at=NOW, idempotency_key="use-key",
    )
    assert event is None
    assert "subjective_mem_retrieval_selection_row_unmanifested" in reasons


def test_usage_event_is_deterministic_content_free_and_raw_key_never_serialized() -> None:
    row = _row()
    manifest = _manifest(row)
    request = _request(manifest)
    selection = _selection(request, manifest, row)
    kwargs = dict(
        request=request, manifest=manifest, rows=(row,), selection=selection, row=row,
        event_kind="grounded_context_admitted", occurred_at=NOW,
        idempotency_key="request-memory-use-1",
    )
    event, reasons = derive_subjective_mem_retrieval_usage_event(**kwargs)
    assert reasons == () and event is not None
    assert validate_subjective_mem_retrieval_usage_event(event) == ()
    replay, reasons = derive_subjective_mem_retrieval_usage_event(**kwargs)
    assert reasons == () and replay == event
    body = event.to_dict()
    assert "request-memory-use-1" not in repr(body)
    assert body["content_free"] is True
    for forbidden in ("raw_query", "grounded_content", "subjective_meaning", "prompt"):
        assert forbidden not in repr(body)

    later, reasons = derive_subjective_mem_retrieval_usage_event(
        **{**kwargs, "occurred_at": "2026-07-28T00:00:01+00:00"}
    )
    assert reasons == () and later is not None
    assert later.usage_slot_id == event.usage_slot_id
    assert later.result_id == event.result_id
    assert later.usage_event_id != event.usage_event_id


def test_usage_event_requires_an_exact_selected_eligible_row() -> None:
    row = _row()
    manifest = _manifest(row)
    request = _request(manifest)
    unselected = _selection(request, manifest, candidate_count=1, eligible_count=1)
    event, reasons = derive_subjective_mem_retrieval_usage_event(
        request=request, manifest=manifest, rows=(row,), selection=unselected, row=row,
        event_kind="grounded_context_admitted", occurred_at=NOW,
        idempotency_key="use-key",
    )
    assert event is None
    assert "subjective_mem_retrieval_usage_binding_invalid" in reasons

    selection = _selection(request, manifest, row)
    event, reasons = derive_subjective_mem_retrieval_usage_event(
        request=request, manifest=manifest, rows=(row,), selection=selection, row=row,
        event_kind="candidate_considered", occurred_at=NOW, idempotency_key="use-key",
    )
    assert event is None
    assert "subjective_mem_retrieval_usage_event_kind_invalid" in reasons


def test_contract_owner_has_no_runtime_primary_cache_or_io_dependency() -> None:
    source = inspect.getsource(retrieval)
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert imports == {
        "__future__", "re", "dataclasses", "datetime", "typing",
        "relaylm.evidence.common",
    }
    for forbidden in (
        "relaymem_primary", "relaymem_retrieval", "subjective_mem_lifecycle_runtime",
        "subjective_mem.lifecycle_engine", "EvidenceRecordStore", "Path(", "sqlite",
        "open(", "write_text", "read_text",
    ):
        assert forbidden not in source, forbidden


def test_review_triggers_remain_bounded() -> None:
    source = inspect.getsource(retrieval)
    assert len(source.splitlines()) < 700
    tree = ast.parse(source)
    lengths = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = max(getattr(item, "end_lineno", node.lineno) for item in ast.walk(node))
            lengths.append((node.name, end - node.lineno + 1))
    assert max(length for _, length in lengths) <= 80, lengths
    assert Path(retrieval.__file__).name == "subjective_mem_retrieval.py"
