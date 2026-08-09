from __future__ import annotations

import ast
import dataclasses
import inspect
from dataclasses import replace
from pathlib import Path

import pytest

import relaylm.subjective_mem_retrieval_selection as selection_owner
from relaylm.evidence.common import canonical_digest, utf8_text_digest
from relaylm.relaymem_grounded_recall_response import MAX_EVIDENCE_ITEMS
from relaylm.subjective_mem.models import (
    SubjectiveMemFormationSnapshot,
    SubjectiveMemRevision,
    SubjectiveMemScopeBinding,
    SubjectiveMemStrength,
)
from relaylm.subjective_mem.markdown import (
    MAX_CANONICAL_PAGE_BYTES,
    SubjectiveMemMarkdownBlock,
    SubjectiveMemMarkdownPage,
    parse_subjective_mem_page_bytes,
    plan_subjective_mem_page,
    plan_subjective_mem_revision_successor,
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
    SubjectiveMemRetrievalCanonicalPageBinding,
    SubjectiveMemRetrievalPreparedHandoff,
    select_subjective_mem_retrieval_handoff,
    validate_subjective_mem_retrieval_prepared_handoff,
)
from relaylm.token_budget import estimate_text_tokens

CHARACTER = "char1"
D = "a" * 64
D2 = "b" * 64
D3 = "d" * 64
NOW = "2026-07-28T00:00:00+00:00"
GROUNDED = "The recital finished before the rain started."
MEANING = "subjective-meaning-body"
SCOPE_DIGEST = canonical_digest(SubjectiveMemScopeBinding().to_dict())


def _revision(memory_id: str = "memory1", **changes) -> SubjectiveMemRevision:
    base = SubjectiveMemRevision(
        memory_id=memory_id,
        character_id=CHARACTER,
        assessment_id="assessment1",
        assessment_revision=1,
        grounded_content=GROUNDED,
        grounded_content_digest=utf8_text_digest(GROUNDED),
        subjective_meaning=MEANING,
        memory_kind="episodic",
        scope_binding=SubjectiveMemScopeBinding(),
        formation_snapshot=SubjectiveMemFormationSnapshot(
            soul_revision="soul.v1",
            memory_policy_revision="memory.v1",
            boundary_revision="boundary.v1",
            scene_policy_revision_or_null=None,
            relationship_revision_or_null=None,
            formation_schema_version="subjective-mem-v1",
            model_revision="model.v1",
        ),
        strength=SubjectiveMemStrength(
            grounded_confidence=1.0,
            subjective_conviction=0.5,
            salience="medium",
            reinforcement_count=0,
            strength_basis="assessment_support",
        ),
        decision_id=f"smdecision-{memory_id}",
        created_at=NOW,
    )
    return replace(base, **changes)


def _successor(predecessor: SubjectiveMemRevision, *, lifecycle_state: str = "active"):
    return replace(
        predecessor,
        memory_revision=predecessor.memory_revision + 1,
        predecessor_revision_or_null=predecessor.memory_revision,
        lifecycle_state=lifecycle_state,
        retrieval_visible=lifecycle_state in {"active", "pinned"},
        authorization_kind="lifecycle_transition",
        decision_id=f"smtransition-{predecessor.memory_id}-r{predecessor.memory_revision + 1}",
    )


def _page(*chains: tuple[SubjectiveMemRevision, ...]) -> tuple[bytes, SubjectiveMemMarkdownPage]:
    """Render one canonical page from complete revision chains and parse it back."""
    data: bytes | None = None
    for chain in chains:
        for index, revision in enumerate(chain):
            if index == 0:
                result = plan_subjective_mem_page(revision=revision, existing_bytes=data)
            else:
                result = plan_subjective_mem_revision_successor(
                    predecessor=chain[index - 1], successor=revision, existing_bytes=data
                )
            assert result.plan is not None, result.reasons
            data = result.plan.rendered_bytes
    assert data is not None
    parsed, reasons = parse_subjective_mem_page_bytes(data)
    assert parsed is not None, reasons
    return data, parsed


def _block(page: SubjectiveMemMarkdownPage, memory_id: str, revision: int):
    matches = [
        item
        for item in page.blocks
        if item.revision.memory_id == memory_id and item.revision.memory_revision == revision
    ]
    assert len(matches) == 1
    return matches[0]


def _row(
    page: SubjectiveMemMarkdownPage, block: SubjectiveMemMarkdownBlock, **changes
) -> SubjectiveMemRetrievalProjectionRow:
    """Build the projection row RT-1B derives for one exact parsed canonical block."""
    revision = block.revision
    legacy = revision.memory_revision == 1 and revision.authorization_kind == "formation_decision"
    base = SubjectiveMemRetrievalProjectionRow(
        projection_generation_id="projection-generation-1",
        character_id=page.character_id,
        memory_id=revision.memory_id,
        memory_revision=revision.memory_revision,
        page_id=page.page_id,
        block_id=block.block_id,
        canonical_page_digest=page.page_digest,
        block_digest=block.block_digest.removeprefix("sha256:"),
        revision_digest=block.revision_digest,
        current_selector_id=f"smstate-{revision.memory_id}",
        current_selector_digest=D,
        current_receipt_id=f"smreceipt-{revision.memory_id}-r{revision.memory_revision}",
        current_receipt_digest=D2,
        authorization_record_kind=(
            "subjective_mem_decision" if legacy else "subjective_mem_lifecycle_transition"
        ),
        authorization_id=revision.authorization_id,
        authorization_digest=D,
        workspace_authority_digest=D2,
        scope_binding_digest=canonical_digest(revision.scope_binding.to_dict()),
        lifecycle_state=revision.lifecycle_state,
        mutation_state="none",
        retrieval_eligible=revision.lifecycle_state in {"active", "pinned"},
        retrieval_visible=revision.retrieval_visible,
        memory_kind=revision.memory_kind,
        formation_stage=revision.formation_stage,
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
        character_id=CHARACTER,
        workspace_authority_digest=D2,
        admitted_scope_binding_digest=SCOPE_DIGEST,
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


def _binding(data) -> SubjectiveMemRetrievalCanonicalPageBinding:
    return SubjectiveMemRetrievalCanonicalPageBinding(canonical_page_bytes=data)


@pytest.fixture()
def single():
    """One canonical page holding one exact current active revision-2 memory."""
    first = _revision()
    data, page = _page((first, _successor(first)))
    row = _row(page, _block(page, "memory1", 2))
    manifest = _manifest(row)
    return {
        "bytes": data, "page": page, "row": row, "manifest": manifest,
        "request": _request(manifest), "rows": (row,), "pages": (_binding(data),),
    }


def _select(env, **changes):
    arguments = {
        "request": env["request"], "manifest": env["manifest"], "rows": env["rows"],
        "canonical_pages": env["pages"], **changes,
    }
    return select_subjective_mem_retrieval_handoff(**arguments)


def test_the_caller_attested_prose_binding_api_no_longer_exists() -> None:
    assert not hasattr(selection_owner, "SubjectiveMemRetrievalContentBinding")
    parameters = inspect.signature(select_subjective_mem_retrieval_handoff).parameters
    assert "content_bindings" not in parameters and "canonical_pages" in parameters
    binding_fields = {
        item.name for item in dataclasses.fields(SubjectiveMemRetrievalCanonicalPageBinding)
    }
    assert binding_fields == {"canonical_page_bytes"}


@pytest.mark.parametrize("lifecycle", ["active", "pinned"])
def test_exact_active_and_pinned_rows_bind_to_their_canonical_block(lifecycle: str) -> None:
    first = _revision()
    data, page = _page((first, _successor(first, lifecycle_state=lifecycle)))
    row = _row(page, _block(page, "memory1", 2))
    manifest = _manifest(row)
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(manifest), manifest=manifest, rows=(row,),
        canonical_pages=(_binding(data),),
    )
    assert handoff is not None and projection.status == "prepared"
    item = handoff._private_items[0]
    assert item.grounded_content == GROUNDED
    assert item.grounded_content_digest == utf8_text_digest(GROUNDED)
    assert item.pinned is (lifecycle == "pinned")
    assert handoff.handoff_shape == SUBJECTIVE_MEM_RETRIEVAL_HANDOFF_SHAPE


def test_token_estimate_comes_from_the_existing_deterministic_estimator(single) -> None:
    handoff, _projection = _select(single)
    assert handoff is not None
    expected = estimate_text_tokens(GROUNDED).estimated_tokens
    assert handoff._private_items[0].token_estimate == expected
    assert handoff.total_token_estimate == expected
    assert handoff.selection.total_token_estimate == expected


def test_token_budget_overflow_fails_closed_rather_than_truncating(single) -> None:
    handoff, projection = _select(single, request=_request(single["manifest"], token_budget=1))
    assert handoff is None and projection.status == "refused"
    assert projection.token_budget_class == "exceeded"
    assert projection.blocked_reason_classes == (
        "subjective_mem_retrieval_selection_token_budget_exceeded",
    )


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"canonical_page_digest": "sha256:" + "e" * 64}, "subjective_mem_retrieval_selection_canonical_page_mismatch"),
        ({"block_digest": D3}, "subjective_mem_retrieval_selection_canonical_block_mismatch"),
        ({"revision_digest": D3}, "subjective_mem_retrieval_selection_canonical_block_mismatch"),
        ({"memory_id": "memory9"}, "subjective_mem_retrieval_selection_canonical_block_mismatch"),
        ({"memory_revision": 3}, "subjective_mem_retrieval_selection_canonical_block_mismatch"),
        ({"memory_kind": "semantic"}, "subjective_mem_retrieval_selection_canonical_revision_mismatch"),
        ({"formation_stage": "secondary"}, "subjective_mem_retrieval_selection_canonical_revision_mismatch"),
        ({"lifecycle_state": "pinned"}, "subjective_mem_retrieval_selection_canonical_revision_mismatch"),
        ({"authorization_id": "smtransition-other"}, "subjective_mem_retrieval_selection_canonical_authorization_mismatch"),
        ({"authorization_record_kind": "subjective_mem_decision"}, "subjective_mem_retrieval_selection_canonical_authorization_mismatch"),
        ({"block_id": "subjective-mem-block-memory1-r9"}, "subjective_mem_retrieval_selection_canonical_block_ambiguous"),
        ({"page_id": "subjective-mem-page-char1-other"}, "subjective_mem_retrieval_selection_canonical_page_missing"),
    ],
)
def test_a_row_that_disagrees_with_its_canonical_block_fails_closed(changes, reason) -> None:
    first = _revision()
    data, page = _page((first, _successor(first)))
    row = _row(page, _block(page, "memory1", 2), **changes)
    manifest = _manifest(row)
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(manifest), manifest=manifest, rows=(row,),
        canonical_pages=(_binding(data),),
    )
    assert handoff is None and projection.status == "refused"
    assert reason in projection.blocked_reason_classes


def test_a_retrieval_visibility_disagreement_fails_closed() -> None:
    """A visible row whose canonical revision is not retrieval-visible is refused."""
    first = _revision()
    data, page = _page((first, _successor(first, lifecycle_state="hidden")))
    block = _block(page, "memory1", 2)
    row = _row(page, block, lifecycle_state="active", retrieval_eligible=True, retrieval_visible=True)
    manifest = _manifest(row)
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(manifest), manifest=manifest, rows=(row,),
        canonical_pages=(_binding(data),),
    )
    assert handoff is None
    assert "subjective_mem_retrieval_selection_canonical_revision_mismatch" in (
        projection.blocked_reason_classes
    )


def test_a_scope_binding_that_disagrees_with_canonical_authority_fails_closed() -> None:
    first = _revision()
    data, page = _page((first, _successor(first)))
    row = _row(page, _block(page, "memory1", 2), scope_binding_digest=D3)
    manifest = _manifest(row)
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(manifest, admitted_scope_binding_digest=D3), manifest=manifest,
        rows=(row,), canonical_pages=(_binding(data),),
    )
    assert handoff is None
    assert "subjective_mem_retrieval_selection_canonical_scope_mismatch" in (
        projection.blocked_reason_classes
    )


def test_a_page_for_a_foreign_character_is_refused() -> None:
    foreign = _revision(character_id="char2")
    foreign_data, foreign_page = _page((foreign, _successor(foreign)))
    own = _revision()
    _own_data, own_page = _page((own, _successor(own)))
    row = _row(own_page, _block(own_page, "memory1", 2))
    manifest = _manifest(row)
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(manifest), manifest=manifest, rows=(row,),
        canonical_pages=(_binding(foreign_data),),
    )
    assert handoff is None
    assert foreign_page.character_id == "char2"
    assert "subjective_mem_retrieval_selection_canonical_page_unsupported" in (
        projection.blocked_reason_classes
    )


@pytest.mark.parametrize(
    ("pages_for", "reason"),
    [
        ("missing", "subjective_mem_retrieval_selection_canonical_page_missing"),
        ("duplicate", "subjective_mem_retrieval_selection_canonical_page_duplicated"),
        ("extra", "subjective_mem_retrieval_selection_canonical_page_extra"),
    ],
)
def test_page_bindings_must_match_the_selected_rows_exactly(single, pages_for, reason) -> None:
    semantic = _revision("memory2", memory_kind="semantic")
    other_data, _other_page = _page((semantic, _successor(semantic)))
    pages = {
        "missing": (),
        "duplicate": (_binding(single["bytes"]), _binding(single["bytes"])),
        "extra": (_binding(single["bytes"]), _binding(other_data)),
    }[pages_for]
    handoff, projection = _select(single, canonical_pages=pages)
    assert handoff is None and projection.status == "refused"
    assert projection.blocked_reason_classes == (reason,)


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        (b"not canonical markdown\n", "subjective_mem_retrieval_selection_canonical_page_unsupported"),
        (b"", "subjective_mem_retrieval_selection_canonical_page_out_of_bounds"),
        (b"x" * (MAX_CANONICAL_PAGE_BYTES + 1), "subjective_mem_retrieval_selection_canonical_page_out_of_bounds"),
        ("not bytes", "subjective_mem_retrieval_selection_canonical_page_out_of_bounds"),
    ],
)
def test_malformed_or_oversized_page_bytes_fail_closed(single, data, reason) -> None:
    handoff, projection = _select(single, canonical_pages=(_binding(data),))
    assert handoff is None and projection.blocked_reason_classes == (reason,)


def test_a_noncanonical_or_unsupported_schema_page_is_refused(single) -> None:
    for damaged in (
        single["bytes"].rstrip(b"\n"),
        single["bytes"].replace(b"relaylm.subjective_mem_markdown_page.v1", b"relaylm.forged.v9"),
    ):
        handoff, projection = _select(single, canonical_pages=(_binding(damaged),))
        assert handoff is None
        assert projection.blocked_reason_classes == (
            "subjective_mem_retrieval_selection_canonical_page_unsupported",
        )


def test_one_page_with_several_memories_resolves_only_the_exact_selected_blocks() -> None:
    first, second = _revision("memory1"), _revision("memory2")
    data, page = _page((first, _successor(first)), (second, _successor(second)))
    assert len(page.blocks) == 4
    rows = (_row(page, _block(page, "memory1", 2)), _row(page, _block(page, "memory2", 2)))
    manifest = _manifest(*rows)
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(manifest), manifest=manifest, rows=rows,
        canonical_pages=(_binding(data),),
    )
    assert handoff is not None and projection.selected_count == 2
    assert {item.memory_id for item in handoff._private_items} == {"memory1", "memory2"}
    assert {item.memory_revision for item in handoff._private_items} == {2}


def test_extraction_is_deterministic_under_binding_and_row_reordering() -> None:
    first, second = _revision("memory1"), _revision("memory2")
    data, page = _page((first, _successor(first)), (second, _successor(second)))
    row_a, row_b = _row(page, _block(page, "memory1", 2)), _row(page, _block(page, "memory2", 2))
    manifest = _manifest(row_a, row_b)
    request = _request(manifest)
    first_handoff, first_projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=(row_a, row_b), canonical_pages=(_binding(data),)
    )
    second_handoff, second_projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=(row_b, row_a), canonical_pages=(_binding(data),)
    )
    assert first_handoff == second_handoff and first_projection == second_projection


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
def test_prohibited_rows_are_excluded_and_need_no_canonical_page(changes, reason) -> None:
    first = _revision()
    _data, page = _page((first, _successor(first)))
    row = _row(page, _block(page, "memory1", 2), **changes)
    manifest = _manifest(row)
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(manifest), manifest=manifest, rows=(row,), canonical_pages=()
    )
    assert handoff is not None and projection.status == "prepared_empty"
    assert (projection.eligible_count, projection.selected_count) == (0, 0)
    assert handoff._private_items == () and handoff._canonical_pages == ()
    assert (reason, 1) in projection.excluded_count_by_reason_class


def test_selection_never_fills_an_empty_result_from_another_authority() -> None:
    first = _revision()
    _data, page = _page((first, _successor(first, lifecycle_state="hidden")))
    row = _row(page, _block(page, "memory1", 2))
    manifest = _manifest(row)
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(manifest), manifest=manifest, rows=(row,), canonical_pages=()
    )
    assert handoff is not None and projection.selected_count == 0
    assert projection.handoff_shape_class == "empty"
    assert projection.ordinary_route_admitted is False
    assert projection.to_dict()["served_authority"] == "primary_mem"


def test_selection_refuses_an_incomplete_or_duplicated_population(single) -> None:
    prior = _row(single["page"], _block(single["page"], "memory1", 1))
    manifest = _manifest(single["row"], prior)
    handoff, projection = _select(single, manifest=manifest, request=_request(manifest))
    assert handoff is None
    assert "subjective_mem_retrieval_selection_population_incomplete" in (
        projection.blocked_reason_classes
    )

    handoff, projection = _select(single, rows=(single["row"], single["row"]))
    assert handoff is None
    assert "subjective_mem_retrieval_selection_rows_duplicated" in projection.blocked_reason_classes


def test_selection_refuses_a_candidate_limit_overflow() -> None:
    first, second = _revision("memory1"), _revision("memory2")
    data, page = _page((first, _successor(first)), (second, _successor(second)))
    rows = (_row(page, _block(page, "memory1", 2)), _row(page, _block(page, "memory2", 2)))
    manifest = _manifest(*rows)
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(manifest, candidate_limit=1), manifest=manifest, rows=rows,
        canonical_pages=(_binding(data),),
    )
    assert handoff is None
    assert "subjective_mem_retrieval_selection_candidate_limit_exceeded" in (
        projection.blocked_reason_classes
    )


def test_selection_refuses_a_handoff_wider_than_the_grounding_owner_accepts() -> None:
    chains = []
    for index in range(MAX_EVIDENCE_ITEMS + 1):
        base = _revision(f"memory{index}")
        chains.append((base, _successor(base)))
    data, page = _page(*chains)
    rows = tuple(_row(page, _block(page, f"memory{index}", 2)) for index in range(len(chains)))
    manifest = _manifest(*rows)
    request = _request(manifest, candidate_limit=len(rows), token_budget=8192)
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=rows, canonical_pages=(_binding(data),)
    )
    assert handoff is None
    assert "subjective_mem_retrieval_selection_handoff_shape_oversize" in (
        projection.blocked_reason_classes
    )


def test_only_requested_memory_kinds_are_selected_after_exact_eligibility() -> None:
    episodic, semantic = _revision("memory1"), _revision("memory2", memory_kind="semantic")
    episodic_bytes, episodic_page = _page((episodic, _successor(episodic)))
    _semantic_bytes, semantic_page = _page((semantic, _successor(semantic)))
    rows = (
        _row(episodic_page, _block(episodic_page, "memory1", 2)),
        _row(semantic_page, _block(semantic_page, "memory2", 2)),
    )
    manifest = _manifest(*rows)
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=_request(manifest, memory_kinds=("episodic",)), manifest=manifest, rows=rows,
        canonical_pages=(_binding(episodic_bytes),),
    )
    assert handoff is not None
    assert (projection.eligible_count, projection.selected_count) == (2, 1)
    assert projection.not_requested_kind_count == 1


def test_a_prepared_handoff_carries_no_admission_state_and_cannot_self_admit(single) -> None:
    handoff, projection = _select(single)
    assert handoff is not None and handoff.shadow is True
    assert projection.shadow is True and projection.usage_event_recorded is False

    fields = {item.name for item in dataclasses.fields(SubjectiveMemRetrievalPreparedHandoff)}
    assert "admitted" not in fields
    assert not [
        name
        for name in dir(handoff)
        if not name.startswith("_") and callable(getattr(handoff, name, None))
    ]
    with pytest.raises(TypeError):
        replace(handoff, admitted=True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        handoff.shadow = False


def test_prepared_private_items_are_immutable_and_expose_no_release_api(single) -> None:
    handoff, _projection = _select(single)
    item = handoff._private_items[0]
    assert type(handoff._private_items) is tuple
    with pytest.raises(dataclasses.FrozenInstanceError):
        item.grounded_content = "tampered"
    assert not [
        value
        for value in vars(handoff).values()
        if isinstance(value, (dict, list)) or (
            isinstance(value, tuple) and any(isinstance(entry, (dict, list)) for entry in value)
        )
    ]
    assert not [
        name
        for name in dir(item)
        if not name.startswith("_") and callable(getattr(item, name, None))
    ]
    assert not hasattr(item, "to_grounding_dict")


def test_prepared_state_exposes_no_supported_evidence_materialization(single) -> None:
    """No public selection API turns prepared state into an E1-R4 dictionary."""
    handoff, _projection = _select(single)
    assert not hasattr(selection_owner, "SubjectiveMemRetrievalPrivateItem")
    assert "SubjectiveMemRetrievalPrivateItem" not in selection_owner.__all__
    assert not [name for name in selection_owner.__all__ if name.startswith("_")]
    assert "to_grounding_dict" not in _executable_source(selection_owner)

    public_names = [name for name in dir(handoff) if not name.startswith("_")]
    assert public_names == [
        "handoff_shape", "ranked_row_digests", "schema", "selected_count", "selection",
        "shadow", "total_token_estimate",
    ]
    for name in public_names:
        value = getattr(handoff, name)
        assert not callable(value)
        assert not isinstance(value, (dict, list))
    assert tuple(item.row_digest for item in handoff._private_items) == handoff.ranked_row_digests
    for item in handoff._private_items:
        assert item.provenance_source == "user_assertion"
        assert item.memory_layer == "subjective"


def test_canonical_page_binding_order_is_normalized_by_parsed_page_identity() -> None:
    """Two distinct required pages produce one handoff regardless of input order."""
    episodic, semantic = _revision("memory1"), _revision("memory2", memory_kind="semantic")
    episodic_bytes, episodic_page = _page((episodic, _successor(episodic)))
    semantic_bytes, semantic_page = _page((semantic, _successor(semantic)))
    assert episodic_page.page_id != semantic_page.page_id
    rows = (
        _row(episodic_page, _block(episodic_page, "memory1", 2)),
        _row(semantic_page, _block(semantic_page, "memory2", 2)),
    )
    manifest = _manifest(*rows)
    request = _request(manifest)
    forward, forward_projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=rows,
        canonical_pages=(_binding(episodic_bytes), _binding(semantic_bytes)),
    )
    reversed_handoff, reversed_projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=rows,
        canonical_pages=(_binding(semantic_bytes), _binding(episodic_bytes)),
    )
    assert forward is not None and forward.selected_count == 2
    assert forward == reversed_handoff
    assert forward_projection == reversed_projection
    assert forward._private_items == reversed_handoff._private_items
    assert forward._canonical_pages == reversed_handoff._canonical_pages
    assert forward.total_token_estimate == reversed_handoff.total_token_estimate

    reordered = replace(forward, _canonical_pages=tuple(reversed(forward._canonical_pages)))
    assert validate_subjective_mem_retrieval_prepared_handoff(
        request=request, manifest=manifest, rows=rows, handoff=reordered
    ) == ("subjective_mem_retrieval_prepared_handoff_not_canonical",)


def test_an_exact_prepared_handoff_revalidates_against_its_canonical_bytes(single) -> None:
    handoff, _projection = _select(single)
    assert validate_subjective_mem_retrieval_prepared_handoff(
        request=single["request"], manifest=single["manifest"], rows=single["rows"], handoff=handoff
    ) == ()
    assert validate_subjective_mem_retrieval_prepared_handoff(
        request=single["request"], manifest=single["manifest"], rows=single["rows"], handoff=object()
    ) == ("subjective_mem_retrieval_prepared_handoff_invalid",)


@pytest.mark.parametrize(
    "tamper",
    [
        "forged_prose", "forged_digest", "forged_identity", "forged_token_estimate",
        "reordered_items", "dropped_item", "duplicated_item", "forged_total",
        "dropped_page", "substituted_page",
    ],
)
def test_a_caller_authored_handoff_fails_canonical_revalidation(tamper) -> None:
    first, second = _revision("memory1"), _revision("memory2")
    data, page = _page((first, _successor(first)), (second, _successor(second)))
    rows = (_row(page, _block(page, "memory1", 2)), _row(page, _block(page, "memory2", 2)))
    manifest = _manifest(*rows)
    request = _request(manifest)
    handoff, _projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=rows, canonical_pages=(_binding(data),)
    )
    assert handoff is not None
    items = handoff._private_items
    forged = "forged prose the canonical page never contained"
    tampered = {
        "forged_prose": replace(
            handoff,
            _private_items=(
                replace(
                    items[0], grounded_content=forged,
                    grounded_content_digest=utf8_text_digest(forged),
                ),
                items[1],
            ),
        ),
        "forged_digest": replace(
            handoff, _private_items=(replace(items[0], grounded_content_digest=D3), items[1])
        ),
        "forged_identity": replace(
            handoff, _private_items=(replace(items[0], memory_id="memory9"), items[1])
        ),
        "forged_token_estimate": replace(
            handoff, _private_items=(replace(items[0], token_estimate=1), items[1])
        ),
        "reordered_items": replace(handoff, _private_items=(items[1], items[0])),
        "dropped_item": replace(handoff, _private_items=(items[0],)),
        "duplicated_item": replace(handoff, _private_items=(items[0], items[0])),
        "forged_total": replace(handoff, total_token_estimate=1),
        "dropped_page": replace(handoff, _canonical_pages=()),
        "substituted_page": replace(
            handoff, _canonical_pages=(_binding(b"not canonical markdown\n"),)
        ),
    }[tamper]
    reasons = validate_subjective_mem_retrieval_prepared_handoff(
        request=request, manifest=manifest, rows=rows, handoff=tampered
    )
    assert reasons != ()
    assert forged not in repr(reasons)


def test_public_projection_leaks_no_canonical_bytes_prose_path_or_private_identifier(single) -> None:
    handoff, projection = _select(single)
    row = single["row"]
    body = repr(projection.to_dict()) + repr(projection) + repr(handoff)
    for forbidden in (
        GROUNDED, MEANING, row.row_digest, row.memory_id, row.current_selector_digest,
        row.current_receipt_digest, row.authorization_digest, row.canonical_page_digest,
        row.projection_generation_id, D, D2, "sha256:", "grounded_content", "raw_query",
        "subjective_meaning", "prompt", "page_path", "/", "relaylm_page_id",
    ):
        assert forbidden not in body, forbidden
    assert projection.runtime_private_evidence_omitted is True


def _executable_source(module) -> str:
    """Module source without docstrings, so prose never satisfies a symbol scan."""

    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ) and ast.get_docstring(node):
            node.body = node.body[1:]
    return ast.unparse(tree)


def test_selection_owner_imports_no_characterization_ledger_or_io() -> None:
    tree = ast.parse(inspect.getsource(selection_owner))
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
        "__future__", "dataclasses", "typing", "relaylm.evidence.common",
        "relaylm.relaymem_grounded_recall_response", "relaylm.subjective_mem.markdown",
        "relaylm.subjective_mem_retrieval", "relaylm.token_budget",
    }
    executable = _executable_source(selection_owner)
    for forbidden in (
        "subjective_mem_retrieval_characterization", "subjective_mem_retrieval_usage_ledger",
        "characterize_", "relaymem_primary", "relaymem_retrieval", "relayctx", "RelayCTX",
        "EvidenceRecordStore", "build_grounded_recall_context", "Path(", "open(",
        "read_text", "write_text", "read_bytes", "write_bytes", "requests", "httpx",
    ):
        assert forbidden not in executable, forbidden


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
