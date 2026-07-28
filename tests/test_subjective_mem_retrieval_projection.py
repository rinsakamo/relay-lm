from __future__ import annotations

import ast
import inspect
import json
from dataclasses import replace
from pathlib import Path

import pytest

import relaylm.subjective_mem_retrieval_projection as projection_module
from relaylm.evidence_common import canonical_digest, utf8_text_digest
from relaylm.subjective_mem import (
    SUBJECTIVE_MEM_DECISION_SCHEMA,
    SubjectiveMemCurrentState,
    SubjectiveMemFormationSnapshot,
    SubjectiveMemRevision,
    SubjectiveMemScopeBinding,
    SubjectiveMemStrength,
)
from relaylm.subjective_mem_commit import SubjectiveMemCommitReceipt
from relaylm.subjective_mem_lifecycle import LIFECYCLE_TRANSITION_SCHEMA
from relaylm.subjective_mem_markdown import (
    canonical_page_digest,
    plan_subjective_mem_page,
    plan_subjective_mem_revision_successor,
    subjective_mem_block_identity,
    subjective_mem_page_identity,
)
from relaylm.subjective_mem_retrieval import (
    subjective_mem_retrieval_exclusion_reasons,
    validate_subjective_mem_retrieval_projection_manifest,
    validate_subjective_mem_retrieval_projection_row,
)
from relaylm.subjective_mem_retrieval_projection import (
    PROJECTION_BUNDLE_FILENAME,
    SubjectiveMemRetrievalProjectionSource,
    SubjectiveMemRetrievalProjectionSourceEntry,
    build_subjective_mem_retrieval_projection,
    delete_subjective_mem_retrieval_projection,
    load_subjective_mem_retrieval_projection,
    read_subjective_mem_retrieval_projection,
    write_subjective_mem_retrieval_projection,
)

CHARACTER = "char1"
WORKSPACE = "a" * 64
NOW = "2026-07-28T00:00:00+00:00"
GROUNDED = "grounded-observation-body"
MEANING = "subjective-meaning-body"
WORKSPACE_PATH = "/private/workspace/char1/memory/episodes/subjective-mem-v1.md"


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


def _successor(predecessor: SubjectiveMemRevision, *, lifecycle_state: str, **changes):
    return replace(
        predecessor,
        memory_revision=predecessor.memory_revision + 1,
        predecessor_revision_or_null=predecessor.memory_revision,
        lifecycle_state=lifecycle_state,
        retrieval_visible=lifecycle_state in {"active", "pinned"},
        authorization_kind="lifecycle_transition",
        decision_id=f"smtransition-{predecessor.memory_id}-r2",
        **changes,
    )


def _page_bytes(*chains: tuple[SubjectiveMemRevision, ...]) -> bytes:
    """Render one canonical page through the canonical publication planners."""

    data: bytes | None = None
    for chain in chains:
        result = plan_subjective_mem_page(revision=chain[0], existing_bytes=data)
        assert result.plan is not None, result.reasons
        data = result.plan.rendered_bytes
        for predecessor, successor in zip(chain, chain[1:]):
            result = plan_subjective_mem_revision_successor(
                predecessor=predecessor, successor=successor, existing_bytes=data
            )
            assert result.plan is not None, result.reasons
            data = result.plan.rendered_bytes
    assert data is not None
    return data


def _selector(
    revision: SubjectiveMemRevision,
    page: bytes,
    *,
    bound: bool = True,
    mutation_state: str = "none",
    lifecycle_state: str | None = None,
    **changes,
) -> dict[str, object]:
    state = lifecycle_state or revision.lifecycle_state
    page_id, _path, _partition = subjective_mem_page_identity(
        character_id=revision.character_id, memory_kind=revision.memory_kind
    )
    block_id, _anchor = subjective_mem_block_identity(
        revision.memory_id, revision.memory_revision
    )
    binding: dict[str, object] = {}
    if bound:
        binding = {
            "workspace_authority_digest": WORKSPACE,
            "scope_binding_digest": canonical_digest(revision.scope_binding.to_dict()),
            "page_id": page_id,
            "block_id": block_id,
            "canonical_page_digest": canonical_page_digest(page),
            "authorization_kind": revision.authorization_kind,
            "authorization_id": revision.authorization_id,
            "current_receipt_id": _receipt_id(revision),
        }
    current = SubjectiveMemCurrentState(
        memory_state_id=f"smstate-{revision.memory_id}",
        memory_id=revision.memory_id,
        character_id=revision.character_id,
        updated_at=NOW,
        mutation_state=mutation_state,
        retrieval_eligible=mutation_state == "none" and state in {"active", "pinned"},
        current_revision=revision.memory_revision,
        lifecycle_state=state,
        **binding,
    )
    return {**current.to_dict(), **changes}


def _receipt_id(revision: SubjectiveMemRevision) -> str:
    return f"smreceipt-{revision.memory_id}-r{revision.memory_revision}"


def _receipt(
    revision: SubjectiveMemRevision, selector: dict[str, object], **changes
) -> dict[str, object]:
    """Build the exact durable receipt family that publishes this revision."""

    page_id, path, _partition = subjective_mem_page_identity(
        character_id=revision.character_id, memory_kind=revision.memory_kind
    )
    block_id, anchor = subjective_mem_block_identity(
        revision.memory_id, revision.memory_revision
    )
    if revision.memory_revision == 1:
        body = SubjectiveMemCommitReceipt(
            receipt_id=_receipt_id(revision),
            finalization_id="smfinal-1",
            intent_id="smintent-1",
            intent_digest="b" * 64,
            sm1_operation_slot_id="smslot-1",
            sm1_operation_id="smop-1",
            sm1_operation_key_digest="c" * 64,
            evidence_space_id="space-1",
            character_id=revision.character_id,
            character_authority_digest="d" * 64,
            workspace_authority_digest=WORKSPACE,
            memory_id=revision.memory_id,
            decision_id=revision.authorization_id,
            prepared_revision_record_id="smprepared-1",
            prepared_revision_digest="e" * 64,
            prepared_manifest_id="smmanifest-1",
            prepared_manifest_digest="f" * 64,
            target_page_id=page_id,
            target_relative_path=path,
            memory_block_id=block_id,
            memory_block_anchor=anchor,
            pre_image_state="absent",
            pre_image_digest="sha256:" + "0" * 64,
            post_image_digest="sha256:" + "1" * 64,
            block_digest="sha256:" + "2" * 64,
            artifact_id="smartifact_" + "1" * 64,
            artifact_digest="3" * 64,
            page_schema="relaylm.subjective_mem_markdown_page.v1",
            renderer_revision="relaylm.subjective_mem_markdown_renderer.v1",
            partition_revision="relaylm.subjective_mem_page_partition.v1",
            platform_revision="relaylm.subjective_mem_commit.posix_dirfd.v1",
            current_state_digest=canonical_digest(selector),
            finalized_at=NOW,
        ).to_dict()
        return _resign(body, "receipt_digest", changes)
    body = {
        "schema": "relaylm.subjective_mem_lifecycle_receipt.v1",
        "receipt_id": _receipt_id(revision),
        "operation_kind": "forget",
        "operation_outcome": "committed",
        "character_id": revision.character_id,
        "memory_ref": {
            "memory_id": revision.memory_id,
            "memory_revision": revision.memory_revision,
        },
        "predecessor_revision": revision.memory_revision - 1,
        "transition_id": revision.authorization_id,
        "page_id": page_id,
        "successor_block_id": block_id,
        "platform_revision": "relaylm.subjective_mem_commit.posix_dirfd.v1",
        "current_state_digest": canonical_digest(selector),
        "finalized_at": NOW,
    }
    return _resign(body, "receipt_digest", changes)


def _resign(body: dict, field: str, changes: dict) -> dict[str, object]:
    payload = {key: value for key, value in {**body, **changes}.items() if key != field}
    return {**payload, field: canonical_digest(payload)}


def _authorization(revision: SubjectiveMemRevision, **changes) -> dict[str, object]:
    if revision.authorization_kind == "formation_decision":
        body = {
            "schema": SUBJECTIVE_MEM_DECISION_SCHEMA,
            "decision_id": revision.authorization_id,
            "character_id": revision.character_id,
            "outcome": "create",
            "result_memory_ref_or_null": {
                "memory_id": revision.memory_id,
                "memory_revision": 1,
            },
            "decided_at": NOW,
        }
    else:
        body = {
            "schema": LIFECYCLE_TRANSITION_SCHEMA,
            "transition_id": revision.authorization_id,
            "character_id": revision.character_id,
            "memory_id": revision.memory_id,
            "from_revision": revision.memory_revision - 1,
            "to_revision": revision.memory_revision,
            "to_lifecycle_state": revision.lifecycle_state,
            "committed_at": NOW,
        }
    return {**body, **changes}


def _entry(revision: SubjectiveMemRevision, page: bytes, **selector_changes):
    selector = _selector(revision, page, **selector_changes)
    return SubjectiveMemRetrievalProjectionSourceEntry(
        canonical_page_bytes=page,
        current_selector_record=selector,
        current_receipt_record=_receipt(revision, selector),
        authorization_record=_authorization(revision),
    )


def _source(*entries, **changes) -> SubjectiveMemRetrievalProjectionSource:
    base = SubjectiveMemRetrievalProjectionSource(
        character_id=CHARACTER,
        workspace_authority_digest=WORKSPACE,
        admitted_scope_binding_digest=canonical_digest(
            SubjectiveMemScopeBinding().to_dict()
        ),
        snapshot_taken_at=NOW,
        entries=tuple(entries),
    )
    return replace(base, **changes)


def _one_active_source(**selector_changes):
    revision = _revision()
    page = _page_bytes((revision,))
    return revision, page, _source(_entry(revision, page, **selector_changes))


def _built(source):
    built, reasons = build_subjective_mem_retrieval_projection(source)
    assert reasons == (), reasons
    assert built is not None
    return built


def test_empty_supported_source_snapshot_builds_one_complete_empty_generation() -> None:
    built = _built(_source())
    assert built.rows == ()
    assert built.manifest.row_digests == ()
    assert validate_subjective_mem_retrieval_projection_manifest(built.manifest) == ()
    assert built.manifest.complete is True
    assert built.manifest.mixed_generation is False
    assert built.manifest.built_at == NOW


def test_one_exact_valid_row_is_projected_and_ordinarily_eligible() -> None:
    revision, _page, source = _one_active_source()
    built = _built(source)
    assert len(built.rows) == 1
    row = built.rows[0]
    assert validate_subjective_mem_retrieval_projection_row(row) == ()
    assert subjective_mem_retrieval_exclusion_reasons(row) == ()
    assert row.projection_generation_id == source.projection_generation_id
    assert row.memory_id == revision.memory_id
    assert row.memory_revision == 1
    assert (row.lifecycle_state, row.mutation_state) == ("active", "none")
    assert built.manifest.row_digests == (row.row_digest,)
    assert built.manifest.source_snapshot_digest == source.source_snapshot_digest


def test_projection_is_deterministic_and_independent_of_entry_order() -> None:
    first, second = _revision(), _revision("memory2")
    page = _page_bytes((first,), (second,))
    forward = _built(_source(_entry(first, page), _entry(second, page)))
    reverse = _built(_source(_entry(second, page), _entry(first, page)))
    assert forward.manifest == reverse.manifest
    assert forward.rows == reverse.rows
    assert forward.manifest.manifest_digest == reverse.manifest.manifest_digest
    assert forward.rows == tuple(
        sorted(forward.rows, key=lambda item: item.row_digest)
    )
    assert len({row.memory_id for row in forward.rows}) == 2


def test_a_co_page_memory_does_not_invalidate_an_earlier_bound_selector() -> None:
    first, second = _revision(), _revision("memory2")
    page = _page_bytes((first,), (second,))
    built = _built(_source(_entry(first, page), _entry(second, page)))
    assert all(row.canonical_binding_verified for row in built.rows)
    assert all(not subjective_mem_retrieval_exclusion_reasons(row) for row in built.rows)


def test_duplicate_logical_selector_for_one_memory_fails_closed() -> None:
    revision = _revision()
    page = _page_bytes((revision,))
    duplicate = _entry(revision, page)
    other = _entry(revision, page, bound=False)
    built, reasons = build_subjective_mem_retrieval_projection(
        _source(duplicate, other)
    )
    assert built is None
    assert "subjective_mem_retrieval_projection_source_selector_duplicated" in reasons


def test_a_dangling_or_unsupported_source_entry_fails_closed() -> None:
    revision = _revision()
    page = _page_bytes((revision,))
    dangling = _entry(revision, page)
    dangling = replace(
        dangling,
        current_selector_record={**dangling.current_selector_record, "current_revision": 4},
    )
    built, reasons = build_subjective_mem_retrieval_projection(_source(dangling))
    assert built is None
    assert "subjective_mem_retrieval_projection_source_revision_missing" in reasons

    corrupt = replace(_entry(revision, page), canonical_page_bytes=b"not a page\n")
    built, reasons = build_subjective_mem_retrieval_projection(_source(corrupt))
    assert built is None
    assert "subjective_mem_retrieval_projection_source_page_unsupported" in reasons


def test_foreign_character_and_workspace_bindings_fail_closed() -> None:
    revision, page, _source_value = _one_active_source()
    foreign_character = _source(_entry(revision, page), character_id="char2")
    built, reasons = build_subjective_mem_retrieval_projection(foreign_character)
    assert built is None
    assert "subjective_mem_retrieval_projection_source_character_foreign" in reasons

    foreign_workspace = _source(_entry(revision, page), workspace_authority_digest="9" * 64)
    built, reasons = build_subjective_mem_retrieval_projection(foreign_workspace)
    assert built is None
    assert "subjective_mem_retrieval_projection_source_workspace_foreign" in reasons


def test_a_foreign_admitted_scope_binding_is_projected_but_never_selectable() -> None:
    revision, page, _unused = _one_active_source()
    source = _source(_entry(revision, page), admitted_scope_binding_digest="8" * 64)
    built = _built(source)
    row = built.rows[0]
    assert row.scope_admitted is False
    assert "scope_not_admitted" in subjective_mem_retrieval_exclusion_reasons(row)


def test_an_invalid_rt1a_row_is_refused_rather_than_projected() -> None:
    revision = _revision("memory/one")
    page = _page_bytes((revision,))
    built, reasons = build_subjective_mem_retrieval_projection(
        _source(_entry(revision, page))
    )
    assert built is None
    assert "subjective_mem_retrieval_projection_identifier_invalid" in reasons


@pytest.mark.parametrize("lifecycle_state", ["hidden", "held", "superseded", "purged"])
def test_non_visible_lifecycle_successors_remain_excluded(lifecycle_state: str) -> None:
    first = _revision()
    successor = _successor(first, lifecycle_state=lifecycle_state)
    page = _page_bytes((first, successor))
    built = _built(_source(_entry(successor, page)))
    row = built.rows[0]
    assert validate_subjective_mem_retrieval_projection_row(row) == ()
    assert row.retrieval_eligible is False and row.retrieval_visible is False
    reasons = subjective_mem_retrieval_exclusion_reasons(row)
    assert f"lifecycle_{lifecycle_state}" in reasons
    assert "retrieval_not_eligible" in reasons


@pytest.mark.parametrize("mutation_state", ["prepared", "recovery_required", "corrupt"])
def test_unresolved_mutation_states_remain_excluded_across_the_page(
    mutation_state: str,
) -> None:
    first, second = _revision(), _revision("memory2")
    page = _page_bytes((first,), (second,))
    built = _built(
        _source(
            _entry(first, page, mutation_state=mutation_state),
            _entry(second, page),
        )
    )
    by_memory = {row.memory_id: row for row in built.rows}
    blocked = by_memory["memory1"]
    assert f"mutation_{mutation_state}" in subjective_mem_retrieval_exclusion_reasons(blocked)
    assert all(row.unresolved_intent_present for row in built.rows)
    assert "unresolved_intent" in subjective_mem_retrieval_exclusion_reasons(
        by_memory["memory2"]
    )


def test_a_stale_selector_is_projected_as_not_latest_persisted_revision() -> None:
    first = _revision()
    successor = _successor(first, lifecycle_state="active")
    page = _page_bytes((first, successor))
    built = _built(_source(_entry(first, page)))
    row = built.rows[0]
    assert row.memory_revision == 1 and row.latest_persisted_revision is False
    assert "not_latest_persisted_revision" in subjective_mem_retrieval_exclusion_reasons(row)


def test_an_unbindable_receipt_or_authorization_is_projected_as_unverified() -> None:
    revision = _revision()
    page = _page_bytes((revision,))
    entry = _entry(revision, page)
    tampered = replace(
        entry,
        current_receipt_record={**entry.current_receipt_record, "finalized_at": "later"},
        authorization_record=_authorization(revision, decision_id="smdecision-other"),
    )
    row = _built(_source(tampered)).rows[0]
    assert row.finalized_receipt_verified is False
    assert row.authorization_verified is False
    reasons = subjective_mem_retrieval_exclusion_reasons(row)
    assert {"receipt_unverified", "authorization_unverified"}.issubset(set(reasons))


def test_deletion_and_full_rebuild_reproduce_the_same_generation(tmp_path: Path) -> None:
    first, second = _revision(), _revision("memory2")
    page = _page_bytes((first,), (second,))
    source = _source(_entry(first, page), _entry(second, page))
    root = tmp_path / "projection"
    root.mkdir()
    original = _built(source)
    assert write_subjective_mem_retrieval_projection(
        projection_root=str(root), projection=original
    ) == ()
    stored, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(root), source=source
    )
    assert reasons == () and stored == original

    assert delete_subjective_mem_retrieval_projection(projection_root=str(root)) == ()
    assert list(root.iterdir()) == []
    missing, reasons = read_subjective_mem_retrieval_projection(projection_root=str(root))
    assert missing is None
    assert reasons == ("subjective_mem_retrieval_projection_absent",)

    rebuilt = _built(source)
    assert write_subjective_mem_retrieval_projection(
        projection_root=str(root), projection=rebuilt
    ) == ()
    reloaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(root), source=source
    )
    assert reasons == () and reloaded == original
    assert rebuilt.manifest.manifest_digest == original.manifest.manifest_digest
    assert rebuilt.manifest.projection_generation_id == (
        original.manifest.projection_generation_id
    )
    assert tuple(row.row_digest for row in rebuilt.rows) == original.manifest.row_digests


def test_projection_deletion_leaves_every_canonical_and_durable_file_untouched(
    tmp_path: Path,
) -> None:
    revision, page, source = _one_active_source()
    canonical = tmp_path / "subjective-mem-v1.md"
    canonical.write_bytes(page)
    durable = tmp_path / "current-state.json"
    entry = source.entries[0]
    durable.write_text(json.dumps(entry.current_selector_record), encoding="utf-8")
    before = (canonical.read_bytes(), durable.read_bytes())

    root = tmp_path / "projection"
    root.mkdir()
    assert write_subjective_mem_retrieval_projection(
        projection_root=str(root), projection=_built(source)
    ) == ()
    assert [item.name for item in root.iterdir()] == [PROJECTION_BUNDLE_FILENAME]
    assert delete_subjective_mem_retrieval_projection(projection_root=str(root)) == ()
    assert delete_subjective_mem_retrieval_projection(projection_root=str(root)) == ()
    assert (canonical.read_bytes(), durable.read_bytes()) == before
    assert canonical.exists() and durable.exists()


def test_persisted_and_public_projection_output_stays_content_free(
    tmp_path: Path,
) -> None:
    revision, page, source = _one_active_source()
    root = tmp_path / "projection"
    root.mkdir()
    built = _built(source)
    assert write_subjective_mem_retrieval_projection(
        projection_root=str(root), projection=built
    ) == ()
    serialized = (root / PROJECTION_BUNDLE_FILENAME).read_text(encoding="utf-8")
    for forbidden in (
        GROUNDED,
        MEANING,
        WORKSPACE_PATH,
        "memory/episodes",
        "grounded_content",
        "subjective_meaning",
        "raw_query",
        "prompt",
        "target_relative_path",
    ):
        assert forbidden not in serialized, forbidden
    assert json.loads(serialized)["canonical_authority"] is False
    assert json.loads(serialized)["rebuildable"] is True


def _stored_body(tmp_path: Path, source) -> tuple[Path, dict]:
    root = tmp_path / "projection"
    root.mkdir()
    assert write_subjective_mem_retrieval_projection(
        projection_root=str(root), projection=_built(source)
    ) == ()
    target = root / PROJECTION_BUNDLE_FILENAME
    return target, json.loads(target.read_text(encoding="utf-8"))


def _rewrite(target: Path, payload: dict, *, resign: bool) -> None:
    body = {key: value for key, value in payload.items() if key != "bundle_digest"}
    digest = canonical_digest(body) if resign else payload["bundle_digest"]
    target.write_text(json.dumps({**body, "bundle_digest": digest}), encoding="utf-8")


def test_an_unsigned_tampered_bundle_fails_closed(tmp_path: Path) -> None:
    _revision_value, _page, source = _one_active_source()
    target, payload = _stored_body(tmp_path, source)
    payload["rows"][0]["lifecycle_state"] = "pinned"
    _rewrite(target, payload, resign=False)
    loaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent)
    )
    assert loaded is None
    assert reasons == ("subjective_mem_retrieval_projection_bundle_tampered",)


def test_a_resigned_mixed_generation_bundle_fails_closed(tmp_path: Path) -> None:
    first, second = _revision(), _revision("memory2")
    page = _page_bytes((first,), (second,))
    source = _source(_entry(first, page), _entry(second, page))
    target, payload = _stored_body(tmp_path, source)
    payload["rows"][0]["projection_generation_id"] = "smretrievalgen_" + "b" * 64
    _rewrite(target, payload, resign=True)
    loaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent)
    )
    assert loaded is None
    assert "subjective_mem_retrieval_projection_mixed_generation" in reasons


def test_a_resigned_incomplete_manifest_fails_closed(tmp_path: Path) -> None:
    _revision_value, _page, source = _one_active_source()
    target, payload = _stored_body(tmp_path, source)
    payload["manifest"]["complete"] = False
    _rewrite(target, payload, resign=True)
    loaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent)
    )
    assert loaded is None
    assert "subjective_mem_retrieval_projection_manifest_state_invalid" in reasons


def test_a_resigned_population_mismatch_fails_closed(tmp_path: Path) -> None:
    first, second = _revision(), _revision("memory2")
    page = _page_bytes((first,), (second,))
    source = _source(_entry(first, page), _entry(second, page))
    target, payload = _stored_body(tmp_path, source)
    payload["rows"] = payload["rows"][:1]
    _rewrite(target, payload, resign=True)
    loaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent)
    )
    assert loaded is None
    assert "subjective_mem_retrieval_projection_population_mismatch" in reasons


def test_a_resigned_duplicate_row_bundle_fails_closed(tmp_path: Path) -> None:
    _revision_value, _page, source = _one_active_source()
    target, payload = _stored_body(tmp_path, source)
    payload["rows"] = payload["rows"] * 2
    _rewrite(target, payload, resign=True)
    loaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent)
    )
    assert loaded is None
    assert "subjective_mem_retrieval_projection_row_duplicated" in reasons


def test_a_resigned_unsupported_source_schema_revision_fails_closed(
    tmp_path: Path,
) -> None:
    _revision_value, _page, source = _one_active_source()
    target, payload = _stored_body(tmp_path, source)
    payload["manifest"]["source_schema_revision_digest"] = "7" * 64
    _rewrite(target, payload, resign=True)
    loaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent)
    )
    assert loaded is None
    assert "subjective_mem_retrieval_projection_source_revision_unsupported" in reasons


def test_a_stale_generation_is_never_served_for_a_changed_snapshot(
    tmp_path: Path,
) -> None:
    revision, page, source = _one_active_source()
    target, _payload = _stored_body(tmp_path, source)
    changed = _source(_entry(revision, page), snapshot_taken_at="2026-07-29T00:00:00+00:00")
    assert changed.source_snapshot_digest != source.source_snapshot_digest
    loaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent), source=changed
    )
    assert loaded is None
    assert reasons == ("subjective_mem_retrieval_projection_stale_generation",)

    served, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent), source=source
    )
    assert reasons == () and served is not None


def test_load_refuses_a_non_bundle_payload_without_partial_acceptance() -> None:
    for payload in (None, {}, {"schema": "other"}, [1, 2, 3]):
        loaded, reasons = load_subjective_mem_retrieval_projection(payload)
        assert loaded is None
        assert reasons == ("subjective_mem_retrieval_projection_bundle_tampered",)


def test_persistence_refuses_an_unsafe_or_relative_projection_root(
    tmp_path: Path,
) -> None:
    built = _built(_source())
    for root in ("", "relative/path", str(tmp_path / "absent")):
        reasons = write_subjective_mem_retrieval_projection(
            projection_root=root, projection=built
        )
        assert reasons and reasons[0].startswith(
            "subjective_mem_retrieval_projection_root_"
        )


def test_projection_owner_has_no_primary_shadow_or_request_path_dependency() -> None:
    source = inspect.getsource(projection_module)
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
        "__future__",
        "json",
        "os",
        "stat",
        "dataclasses",
        "pathlib",
        "relaylm.evidence_common",
        "relaylm.subjective_mem",
        "relaylm.subjective_mem_lifecycle",
        "relaylm.subjective_mem_markdown",
        "relaylm.subjective_mem_retrieval",
    }
    executable = _executable_source(tree)
    for forbidden in (
        "relaymem_primary",
        "relaymem_retrieval",
        "relayctx",
        "RelayCTX",
        "usage_event",
        "shadow",
        "sqlite",
        "threading",
        "subprocess",
        "scheduler",
        "grounded_content",
        "subjective_meaning",
        "relative_path",
    ):
        assert forbidden not in executable, forbidden


def _executable_source(tree: ast.Module) -> str:
    """Return the module source with every docstring removed."""

    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        assert isinstance(body, list)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            if isinstance(body[0].value.value, str):
                body.pop(0)
    return ast.unparse(tree)


def test_review_triggers_remain_bounded() -> None:
    source = inspect.getsource(projection_module)
    assert len(source.splitlines()) < 700
    tree = ast.parse(source)
    lengths = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = max(getattr(item, "end_lineno", node.lineno) for item in ast.walk(node))
            lengths.append((node.name, end - node.lineno + 1))
    assert max(length for _, length in lengths) <= 80, lengths
    assert Path(projection_module.__file__).name == (
        "subjective_mem_retrieval_projection.py"
    )
