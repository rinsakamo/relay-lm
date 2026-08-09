from __future__ import annotations

import ast
import inspect
import json
from dataclasses import replace
from pathlib import Path

import pytest

import relaylm.subjective_mem_retrieval_projection as projection_module
import relaylm.subjective_mem_retrieval_projection_store as store_module
from relaylm.evidence.common import canonical_digest, utf8_text_digest
from relaylm.subjective_mem.models import (
    SUBJECTIVE_MEM_DECISION_SCHEMA,
    SUBJECTIVE_MEM_REVISION_SCHEMA,
    SubjectiveMemCurrentState,
    SubjectiveMemFormationSnapshot,
    SubjectiveMemRevision,
    SubjectiveMemScopeBinding,
    SubjectiveMemStrength,
)
from relaylm.subjective_mem_commit import ST1_RECEIPT_SCHEMA
from relaylm.subjective_mem_lifecycle import (
    LIFECYCLE_POLICY_REVISION,
    LIFECYCLE_RECEIPT_SCHEMA,
    LIFECYCLE_TRANSITION_SCHEMA,
)
from relaylm.subjective_mem_markdown import (
    LIFECYCLE_BLOCK_SCHEMA,
    PAGE_PARTITION_REVISION,
    PAGE_SCHEMA,
    RENDERER_REVISION,
    plan_subjective_mem_page,
    plan_subjective_mem_revision_successor,
    subjective_mem_block_identity,
    subjective_mem_page_identity,
)
from relaylm.subjective_mem_retrieval import (
    SubjectiveMemRetrievalProjectionRow,
    subjective_mem_retrieval_exclusion_reasons,
    validate_subjective_mem_retrieval_projection_manifest,
    validate_subjective_mem_retrieval_projection_row,
)
from relaylm.subjective_mem_retrieval_projection import (
    SubjectiveMemRetrievalProjectionSource,
    SubjectiveMemRetrievalProjectionSourceEntry,
    build_subjective_mem_retrieval_projection,
)
from relaylm.subjective_mem_retrieval_projection_store import (
    PROJECTION_BUNDLE_FILENAME,
    delete_subjective_mem_retrieval_projection,
    load_subjective_mem_retrieval_projection,
    read_subjective_mem_retrieval_projection,
    serialize_subjective_mem_retrieval_projection,
    write_subjective_mem_retrieval_projection,
)

SPACE = "evidence-space-1"
CHARACTER = "char1"
WORKSPACE = "a" * 64
PLATFORM = "relaylm.subjective_mem_commit.posix_dirfd.v1"
NOW = "2026-07-28T00:00:00+00:00"
GROUNDED = "grounded-observation-body"
MEANING = "subjective-meaning-body"
WORKSPACE_PATH = "/private/workspace/char1/memory/episodes/subjective-mem-v1.md"
SCOPE_DIGEST = canonical_digest(SubjectiveMemScopeBinding().to_dict())
TRANSITIONS = {"hidden": "forget", "pinned": "pin", "active": "correct"}


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


def _successor(predecessor: SubjectiveMemRevision, *, lifecycle_state: str):
    return replace(
        predecessor,
        memory_revision=predecessor.memory_revision + 1,
        predecessor_revision_or_null=predecessor.memory_revision,
        lifecycle_state=lifecycle_state,
        retrieval_visible=lifecycle_state in {"active", "pinned"},
        authorization_kind="lifecycle_transition",
        decision_id=f"smtransition-{predecessor.memory_id}-r{predecessor.memory_revision + 1}",
    )


def _publish(*chains: tuple[SubjectiveMemRevision, ...]):
    """Render one canonical page and record each commit's own page image.

    A published page digest is a point-in-time fact, so each revision keeps the
    digest of the page as it stood immediately after its own block was appended.
    """

    data: bytes | None = None
    committed: dict[tuple[str, int], str] = {}
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
            committed[(revision.memory_id, revision.memory_revision)] = (
                result.plan.post_image_digest
            )
    assert data is not None
    return data, committed


def _receipt_id(revision: SubjectiveMemRevision) -> str:
    return f"smreceipt-{revision.memory_id}-r{revision.memory_revision}"


def _selector(
    revision: SubjectiveMemRevision,
    committed_page_digest: str,
    *,
    mutation_state: str = "none",
    bound: bool = True,
    **changes,
) -> dict[str, object]:
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
            "canonical_page_digest": committed_page_digest,
            "authorization_kind": revision.authorization_kind,
            "authorization_id": revision.authorization_id,
            "current_receipt_id": _receipt_id(revision),
        }
    eligible = mutation_state == "none" and revision.lifecycle_state in {"active", "pinned"}
    current = SubjectiveMemCurrentState(
        memory_state_id=f"smstate-{revision.memory_id}",
        memory_id=revision.memory_id,
        character_id=revision.character_id,
        updated_at=NOW,
        mutation_state=mutation_state,
        retrieval_eligible=eligible,
        current_revision=revision.memory_revision,
        lifecycle_state=revision.lifecycle_state,
        **binding,
    )
    return {**current.to_dict(), **changes}


def _create_receipt(revision, selector, page_digest, **changes) -> dict[str, object]:
    page_id, _path, _partition = subjective_mem_page_identity(
        character_id=revision.character_id, memory_kind=revision.memory_kind
    )
    block_id, anchor = subjective_mem_block_identity(revision.memory_id, 1)
    body = {
        "schema": ST1_RECEIPT_SCHEMA,
        "receipt_id": _receipt_id(revision),
        "operation_kind": "create",
        "operation_outcome": "committed",
        "evidence_space_id": SPACE,
        "character_id": revision.character_id,
        "memory_ref": {"memory_id": revision.memory_id, "memory_revision": 1},
        "decision_id": revision.authorization_id,
        "target_page_id": page_id,
        "memory_block_id": block_id,
        "memory_block_anchor": anchor,
        "post_image_digest": page_digest,
        "current_state_digest": canonical_digest(selector),
        "renderer_revision": RENDERER_REVISION,
        "partition_revision": PAGE_PARTITION_REVISION,
        "platform_revision": PLATFORM,
        "finalized_at": NOW,
    }
    return _seal(body, changes)


def _lifecycle_receipt(revision, selector, page_digest, **changes) -> dict[str, object]:
    page_id, _path, _partition = subjective_mem_page_identity(
        character_id=revision.character_id, memory_kind=revision.memory_kind
    )
    block_id, _anchor = subjective_mem_block_identity(
        revision.memory_id, revision.memory_revision
    )
    body = {
        "schema": LIFECYCLE_RECEIPT_SCHEMA,
        "receipt_id": _receipt_id(revision),
        "operation_kind": TRANSITIONS.get(revision.lifecycle_state, "forget"),
        "operation_outcome": "committed",
        "evidence_space_id": SPACE,
        "character_id": revision.character_id,
        "memory_ref": {
            "memory_id": revision.memory_id,
            "memory_revision": revision.memory_revision,
        },
        "predecessor_revision": revision.memory_revision - 1,
        "transition_id": revision.authorization_id,
        "authorization_class": "user_management",
        "reason_category": "user_requested",
        "policy_revision": LIFECYCLE_POLICY_REVISION,
        "revision_schema": SUBJECTIVE_MEM_REVISION_SCHEMA,
        "page_schema": PAGE_SCHEMA,
        "block_schema": LIFECYCLE_BLOCK_SCHEMA,
        "renderer_revision": RENDERER_REVISION,
        "partition_revision": PAGE_PARTITION_REVISION,
        "platform_revision": PLATFORM,
        "page_id": page_id,
        "successor_block_id": block_id,
        "post_image_digest": page_digest,
        "successor_revision_digest": canonical_digest(revision.to_dict()),
        "current_state_digest": canonical_digest(selector),
        "finalized_at": NOW,
    }
    return _seal(body, changes)


def _seal(body: dict, changes: dict) -> dict[str, object]:
    payload = {
        key: value for key, value in {**body, **changes}.items() if key != "receipt_digest"
    }
    return {**payload, "receipt_digest": canonical_digest(payload)}


def _authorization(revision: SubjectiveMemRevision, receipt, **changes):
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
            "operation": receipt.get("operation_kind"),
            "from_lifecycle_state": "active",
            "to_lifecycle_state": revision.lifecycle_state,
            "from_formation_stage": revision.formation_stage,
            "to_formation_stage": revision.formation_stage,
            "authorized_by": receipt.get("authorization_class"),
            "committed_at": receipt.get("finalized_at"),
        }
    return {**body, **changes}


def _entry(
    revision: SubjectiveMemRevision,
    page: bytes,
    committed: dict,
    *,
    receipt_changes: dict | None = None,
    authorization_changes: dict | None = None,
    **selector_changes,
) -> SubjectiveMemRetrievalProjectionSourceEntry:
    page_digest = committed[(revision.memory_id, revision.memory_revision)]
    selector = _selector(revision, page_digest, **selector_changes)
    build = _create_receipt if revision.memory_revision == 1 else _lifecycle_receipt
    receipt = build(revision, selector, page_digest, **(receipt_changes or {}))
    return SubjectiveMemRetrievalProjectionSourceEntry(
        canonical_page_bytes=page,
        current_selector_record=selector,
        current_receipt_record=receipt,
        authorization_record=_authorization(
            revision, receipt, **(authorization_changes or {})
        ),
    )


def _source(*entries, **changes) -> SubjectiveMemRetrievalProjectionSource:
    base = SubjectiveMemRetrievalProjectionSource(
        evidence_space_id=SPACE,
        character_id=CHARACTER,
        workspace_authority_digest=WORKSPACE,
        admitted_scope_binding_digest=SCOPE_DIGEST,
        snapshot_taken_at=NOW,
        entries=tuple(entries),
    )
    return replace(base, **changes)


def _one_active(**entry_kwargs):
    """One memory whose current revision is an authority-bound active successor."""

    first = _revision()
    current = _successor(first, lifecycle_state="active")
    page, committed = _publish((first, current))
    return current, page, committed, _source(_entry(current, page, committed, **entry_kwargs))


def _built(source):
    built, reasons = build_subjective_mem_retrieval_projection(source)
    assert reasons == (), reasons
    assert built is not None
    return built


def _stored(tmp_path: Path, source) -> tuple[Path, dict]:
    root = tmp_path / "projection"
    root.mkdir()
    assert write_subjective_mem_retrieval_projection(
        projection_root=str(root), source=source, projection=_built(source)
    ) == ()
    target = root / PROJECTION_BUNDLE_FILENAME
    return target, json.loads(target.read_text(encoding="utf-8"))


def _reseal_bundle(target: Path, payload: dict) -> None:
    """Rewrite a bundle so every digest it carries is internally consistent.

    Row identity is taken from the production row object rather than recomputed
    here, so the forged bundle is exactly what an attacker with the serialized
    format could produce.
    """

    rows = [
        SubjectiveMemRetrievalProjectionRow(
            **{
                key: value
                for key, value in row.items()
                if key != "schema"
            }
        )
        for row in payload["rows"]
    ]
    ordered = sorted(rows, key=lambda item: item.row_digest)
    body = {
        "schema": payload["schema"],
        "manifest": {
            **payload["manifest"],
            "row_digests": [item.row_digest for item in ordered],
            "row_count": len(ordered),
        },
        "rows": [item.to_digest_input() for item in ordered],
        "canonical_authority": False,
        "rebuildable": True,
    }
    target.write_text(
        json.dumps({**body, "bundle_digest": canonical_digest(body)}), encoding="utf-8"
    )


def test_empty_supported_source_snapshot_builds_one_complete_empty_generation() -> None:
    built = _built(_source())
    assert built.rows == ()
    assert built.manifest.row_digests == ()
    assert validate_subjective_mem_retrieval_projection_manifest(built.manifest) == ()
    assert (built.manifest.complete, built.manifest.mixed_generation) == (True, False)
    assert built.manifest.built_at == NOW


def test_one_exact_valid_row_is_projected_and_ordinarily_eligible() -> None:
    revision, _page, _committed, source = _one_active()
    built = _built(source)
    assert len(built.rows) == 1
    row = built.rows[0]
    assert validate_subjective_mem_retrieval_projection_row(row) == ()
    assert subjective_mem_retrieval_exclusion_reasons(row) == ()
    assert row.projection_generation_id == source.projection_generation_id
    assert (row.memory_id, row.memory_revision) == (revision.memory_id, 2)
    assert row.finalized_receipt_verified and row.authorization_verified
    assert row.canonical_binding_verified and row.scope_admitted
    assert built.manifest.source_snapshot_digest == source.source_snapshot_digest


def test_projection_is_deterministic_and_independent_of_entry_order() -> None:
    first, second = _revision(), _revision("memory2")
    current, other = (
        _successor(first, lifecycle_state="active"),
        _successor(second, lifecycle_state="active"),
    )
    page, committed = _publish((first, current), (second, other))
    forward = _built(_source(_entry(current, page, committed), _entry(other, page, committed)))
    reverse = _built(_source(_entry(other, page, committed), _entry(current, page, committed)))
    assert forward.manifest == reverse.manifest
    assert forward.rows == reverse.rows
    assert forward.rows == tuple(sorted(forward.rows, key=lambda item: item.row_digest))
    assert len({row.memory_id for row in forward.rows}) == 2


def test_a_co_page_memory_does_not_invalidate_an_earlier_committed_selector() -> None:
    first, second = _revision(), _revision("memory2")
    current, other = (
        _successor(first, lifecycle_state="active"),
        _successor(second, lifecycle_state="active"),
    )
    page, committed = _publish((first, current), (second, other))
    built = _built(_source(_entry(current, page, committed), _entry(other, page, committed)))
    assert len(built.rows) == 2
    assert all(row.finalized_receipt_verified for row in built.rows)
    assert all(not subjective_mem_retrieval_exclusion_reasons(row) for row in built.rows)


def test_an_unbound_legacy_selector_can_never_become_ordinarily_eligible() -> None:
    revision, page, committed, _unused = _one_active()
    built, reasons = build_subjective_mem_retrieval_projection(
        _source(_entry(revision, page, committed, bound=False))
    )
    assert built is None
    assert "subjective_mem_retrieval_projection_source_selector_unbound" in reasons


def test_duplicate_logical_selector_for_one_memory_fails_closed() -> None:
    revision, page, committed, _unused = _one_active()
    built, reasons = build_subjective_mem_retrieval_projection(
        _source(
            _entry(revision, page, committed),
            _entry(revision, page, committed, receipt_changes={"finalized_at": "2026-07-29T00:00:00+00:00"}),
        )
    )
    assert built is None
    assert "subjective_mem_retrieval_projection_source_selector_duplicated" in reasons


def test_a_dangling_or_unsupported_source_entry_fails_closed() -> None:
    revision, page, committed, _unused = _one_active()
    entry = _entry(revision, page, committed)
    dangling = replace(
        entry,
        current_selector_record={**entry.current_selector_record, "current_revision": 7},
    )
    built, reasons = build_subjective_mem_retrieval_projection(_source(dangling))
    assert built is None
    assert "subjective_mem_retrieval_projection_source_revision_missing" in reasons

    corrupt = replace(entry, canonical_page_bytes=b"not a canonical page\n")
    built, reasons = build_subjective_mem_retrieval_projection(_source(corrupt))
    assert built is None
    assert "subjective_mem_retrieval_projection_source_page_unsupported" in reasons


def test_foreign_character_workspace_and_evidence_space_fail_closed() -> None:
    revision, page, committed, _unused = _one_active()
    entry = _entry(revision, page, committed)
    built, reasons = build_subjective_mem_retrieval_projection(
        _source(entry, character_id="char2")
    )
    assert built is None
    assert "subjective_mem_retrieval_projection_source_character_foreign" in reasons

    built, reasons = build_subjective_mem_retrieval_projection(
        _source(entry, workspace_authority_digest="9" * 64)
    )
    assert built is None
    assert "subjective_mem_retrieval_projection_source_workspace_foreign" in reasons

    built = _built(_source(entry, evidence_space_id="evidence-space-2"))
    assert built.rows[0].finalized_receipt_verified is False
    assert "receipt_unverified" in subjective_mem_retrieval_exclusion_reasons(built.rows[0])


def test_a_foreign_admitted_scope_binding_is_projected_but_never_selectable() -> None:
    revision, page, committed, _unused = _one_active()
    built = _built(
        _source(_entry(revision, page, committed), admitted_scope_binding_digest="8" * 64)
    )
    row = built.rows[0]
    assert row.scope_admitted is False
    assert "scope_not_admitted" in subjective_mem_retrieval_exclusion_reasons(row)


def test_an_invalid_rt1a_row_is_refused_rather_than_projected() -> None:
    first = _revision("memory/one")
    current = _successor(first, lifecycle_state="active")
    page, committed = _publish((first, current))
    built, reasons = build_subjective_mem_retrieval_projection(
        _source(_entry(current, page, committed))
    )
    assert built is None
    assert "subjective_mem_retrieval_projection_identifier_invalid" in reasons


@pytest.mark.parametrize("lifecycle_state", ["hidden", "held", "superseded", "purged"])
def test_non_visible_lifecycle_successors_remain_excluded(lifecycle_state: str) -> None:
    first = _revision()
    current = _successor(first, lifecycle_state=lifecycle_state)
    page, committed = _publish((first, current))
    built = _built(_source(_entry(current, page, committed)))
    row = built.rows[0]
    assert validate_subjective_mem_retrieval_projection_row(row) == ()
    assert (row.retrieval_eligible, row.retrieval_visible) == (False, False)
    reasons = subjective_mem_retrieval_exclusion_reasons(row)
    assert f"lifecycle_{lifecycle_state}" in reasons
    assert "retrieval_not_eligible" in reasons
    if lifecycle_state != "hidden":
        assert row.finalized_receipt_verified is False
        assert "receipt_unverified" in reasons


@pytest.mark.parametrize("mutation_state", ["prepared", "recovery_required", "corrupt"])
def test_unresolved_mutation_states_remain_excluded_across_the_page(
    mutation_state: str,
) -> None:
    first, second = _revision(), _revision("memory2")
    current, other = (
        _successor(first, lifecycle_state="active"),
        _successor(second, lifecycle_state="active"),
    )
    page, committed = _publish((first, current), (second, other))
    built = _built(
        _source(
            _entry(current, page, committed, mutation_state=mutation_state),
            _entry(other, page, committed),
        )
    )
    by_memory = {row.memory_id: row for row in built.rows}
    blocked = subjective_mem_retrieval_exclusion_reasons(by_memory["memory1"])
    assert f"mutation_{mutation_state}" in blocked
    assert all(row.unresolved_intent_present for row in built.rows)
    assert "unresolved_intent" in subjective_mem_retrieval_exclusion_reasons(
        by_memory["memory2"]
    )


def test_a_stale_selector_is_projected_as_not_latest_persisted_revision() -> None:
    first = _revision()
    second = _successor(first, lifecycle_state="active")
    third = replace(
        _successor(second, lifecycle_state="active"),
        decision_id="smtransition-memory1-r3",
    )
    page, committed = _publish((first, second, third))
    built = _built(_source(_entry(second, page, committed)))
    row = built.rows[0]
    assert (row.memory_revision, row.latest_persisted_revision) == (2, False)
    assert "not_latest_persisted_revision" in subjective_mem_retrieval_exclusion_reasons(row)


@pytest.mark.parametrize(
    "receipt_changes",
    [
        {"operation_kind": "pin"},
        {"policy_revision": "relaylm.subjective_mem_other_policy.v1"},
        {"predecessor_revision": 99},
        {"successor_revision_digest": "5" * 64},
    ],
)
def test_shared_authority_rejects_impossible_lifecycle_receipts(receipt_changes) -> None:
    """The shared owner's exact lineage rules now govern the projected flag."""

    first = _revision()
    current = _successor(first, lifecycle_state="hidden")
    page, committed = _publish((first, current))
    built = _built(_source(_entry(current, page, committed, receipt_changes=receipt_changes)))
    row = built.rows[0]
    assert row.finalized_receipt_verified is False
    assert "receipt_unverified" in subjective_mem_retrieval_exclusion_reasons(row)


@pytest.mark.parametrize(
    "authorization_changes",
    [
        {"to_revision": 99},
        {"to_lifecycle_state": "active"},
        {"authorized_by": "someone_else"},
        {"committed_at": "2026-07-29T00:00:00+00:00"},
    ],
)
def test_shared_authority_rejects_unbound_transition_records(authorization_changes) -> None:
    first = _revision()
    current = _successor(first, lifecycle_state="hidden")
    page, committed = _publish((first, current))
    built = _built(
        _source(_entry(current, page, committed, authorization_changes=authorization_changes))
    )
    row = built.rows[0]
    assert row.authorization_verified is False
    assert "authorization_unverified" in subjective_mem_retrieval_exclusion_reasons(row)


def test_a_selector_naming_another_receipt_is_never_receipt_verified() -> None:
    revision, page, committed, _unused = _one_active()
    built = _built(
        _source(_entry(revision, page, committed, receipt_changes={"receipt_id": "smreceipt-other"}))
    )
    row = built.rows[0]
    assert row.finalized_receipt_verified is False
    assert "receipt_unverified" in subjective_mem_retrieval_exclusion_reasons(row)


@pytest.mark.parametrize(
    "record",
    [
        {"schema": "x", "value": float("nan")},
        {"schema": "x", 1: "non-string-key"},
        {"schema": "x", "value": object()},
        {"schema": "x", "value": {"nested": [1, {float("inf"): 2}]}},
        {"schema": "x", "value": "\ud800"},
        {"schema": "x", "value": {"nested": ["ok", "lone-\udfff-surrogate"]}},
        {"schema": "x", "\ud800": "surrogate-key"},
    ],
)
def test_a_non_canonical_source_record_fails_closed_without_raising(record) -> None:
    revision, page, committed, _unused = _one_active()
    entry = replace(_entry(revision, page, committed), authorization_record=record)
    built, reasons = build_subjective_mem_retrieval_projection(_source(entry))
    assert built is None
    assert reasons == ("subjective_mem_retrieval_projection_source_not_canonical",)


@pytest.mark.parametrize(
    "field",
    ["evidence_space_id", "character_id", "snapshot_taken_at"],
)
def test_unencodable_text_in_an_identity_bearing_source_string_fails_closed(
    field: str,
) -> None:
    """A lone surrogate cannot be UTF-8 encoded, so canonicalization must refuse it.

    The builder contract is ``(value_or_none, reasons)``; an unencodable
    identity value must never surface as ``UnicodeEncodeError``.
    """

    revision, page, committed, _unused = _one_active()
    entry = _entry(revision, page, committed)
    source = _source(entry, **{field: f"bound-\ud800-{field}"})
    built, reasons = build_subjective_mem_retrieval_projection(source)
    assert built is None
    assert reasons == ("subjective_mem_retrieval_projection_source_not_canonical",)


def test_unencodable_text_in_a_selector_or_receipt_record_fails_closed() -> None:
    revision, page, committed, _unused = _one_active()
    entry = _entry(revision, page, committed)
    for changed in (
        replace(
            entry,
            current_selector_record={
                **entry.current_selector_record,
                "updated_at": "2026-07-28T00:00:00+00:00\ud800",
            },
        ),
        replace(
            entry,
            current_receipt_record={
                **entry.current_receipt_record,
                "reason_category": "user-\udfff-requested",
            },
        ),
    ):
        built, reasons = build_subjective_mem_retrieval_projection(_source(changed))
        assert built is None
        assert reasons == ("subjective_mem_retrieval_projection_source_not_canonical",)


def test_canonicalization_names_the_exact_expected_failure_classes() -> None:
    """The guard catches the three exact stages and never a broad exception."""

    handlers = [
        node
        for node in ast.walk(ast.parse(inspect.getsource(projection_module)))
        if isinstance(node, ast.ExceptHandler)
    ]
    caught = {
        tuple(sorted(item.id for item in node.type.elts))
        for node in handlers
        if isinstance(node.type, ast.Tuple)
    }
    assert ("TypeError", "UnicodeEncodeError", "ValueError") in caught
    for node in handlers:
        names = (
            {item.id for item in node.type.elts}
            if isinstance(node.type, ast.Tuple)
            else {getattr(node.type, "id", "")}
        )
        assert not names & {"Exception", "BaseException"}, names


@pytest.mark.parametrize(
    "source",
    [
        None,
        "not-a-source",
        _source(evidence_space_id=""),
        _source(workspace_authority_digest="short"),
        _source(snapshot_taken_at=""),
        _source(entries=("not-an-entry",)),
    ],
)
def test_a_malformed_source_returns_reasons_instead_of_raising(source) -> None:
    built, reasons = build_subjective_mem_retrieval_projection(source)
    assert built is None
    assert reasons and all(
        reason.startswith("subjective_mem_retrieval_projection_source_") for reason in reasons
    )


def test_deletion_and_full_rebuild_reproduce_the_same_generation(tmp_path: Path) -> None:
    first, second = _revision(), _revision("memory2")
    current, other = (
        _successor(first, lifecycle_state="active"),
        _successor(second, lifecycle_state="active"),
    )
    page, committed = _publish((first, current), (second, other))
    source = _source(_entry(current, page, committed), _entry(other, page, committed))
    original = _built(source)
    target, _payload = _stored(tmp_path, source)
    root = target.parent

    stored, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(root), source=source
    )
    assert reasons == () and stored == original

    assert delete_subjective_mem_retrieval_projection(projection_root=str(root)) == ()
    assert list(root.iterdir()) == []
    missing, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(root), source=source
    )
    assert missing is None
    assert reasons == ("subjective_mem_retrieval_projection_absent",)

    rebuilt = _built(source)
    assert write_subjective_mem_retrieval_projection(
        projection_root=str(root), source=source, projection=rebuilt
    ) == ()
    reloaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(root), source=source
    )
    assert reasons == () and reloaded == original
    assert rebuilt.manifest.manifest_digest == original.manifest.manifest_digest
    assert tuple(row.row_digest for row in rebuilt.rows) == original.manifest.row_digests


def test_projection_deletion_leaves_every_canonical_and_durable_file_untouched(
    tmp_path: Path,
) -> None:
    revision, page, committed, source = _one_active()
    canonical = tmp_path / "subjective-mem-v1.md"
    canonical.write_bytes(page)
    durable = tmp_path / "current-state.json"
    durable.write_text(
        json.dumps(source.entries[0].current_selector_record), encoding="utf-8"
    )
    before = (canonical.read_bytes(), durable.read_bytes())

    target, _payload = _stored(tmp_path, source)
    root = target.parent
    assert [item.name for item in root.iterdir()] == [PROJECTION_BUNDLE_FILENAME]
    assert delete_subjective_mem_retrieval_projection(projection_root=str(root)) == ()
    assert delete_subjective_mem_retrieval_projection(projection_root=str(root)) == ()
    assert (canonical.read_bytes(), durable.read_bytes()) == before
    assert canonical.exists() and durable.exists()


def test_persisted_and_public_projection_output_stays_content_free(tmp_path: Path) -> None:
    _revision_value, _page, _committed, source = _one_active()
    target, _payload = _stored(tmp_path, source)
    serialized = target.read_text(encoding="utf-8")
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
    decoded = json.loads(serialized)
    assert decoded["canonical_authority"] is False and decoded["rebuildable"] is True


def test_no_persisted_projection_is_trusted_without_its_exact_source() -> None:
    for entry_point in (
        load_subjective_mem_retrieval_projection,
        read_subjective_mem_retrieval_projection,
        write_subjective_mem_retrieval_projection,
    ):
        parameter = inspect.signature(entry_point).parameters["source"]
        assert parameter.default is inspect.Parameter.empty, entry_point.__name__
    public = {name for name in store_module.__all__ if not name.startswith(("MAX", "PROJ", "SUB"))}
    assert public == {
        "delete_subjective_mem_retrieval_projection",
        "load_subjective_mem_retrieval_projection",
        "read_subjective_mem_retrieval_projection",
        "serialize_subjective_mem_retrieval_projection",
        "write_subjective_mem_retrieval_projection",
    }


def test_an_unchanged_bundle_is_accepted_only_against_its_exact_source(
    tmp_path: Path,
) -> None:
    revision, page, committed, source = _one_active()
    target, payload = _stored(tmp_path, source)
    loaded, reasons = load_subjective_mem_retrieval_projection(payload, source=source)
    assert reasons == () and loaded == _built(source)

    changed = _source(
        _entry(revision, page, committed), snapshot_taken_at="2026-07-29T00:00:00+00:00"
    )
    assert changed.source_snapshot_digest != source.source_snapshot_digest
    loaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent), source=changed
    )
    assert loaded is None
    assert reasons == ("subjective_mem_retrieval_projection_stale_generation",)


@pytest.mark.parametrize(
    "field,value",
    [
        ("lifecycle_state", "pinned"),
        ("scope_binding_digest", "7" * 64),
        ("memory_id", "memory9"),
        ("workspace_authority_digest", "6" * 64),
        ("current_selector_digest", "5" * 64),
    ],
)
def test_a_fully_redigested_altered_bundle_fails_against_the_original_source(
    tmp_path: Path, field: str, value: str
) -> None:
    """An internally consistent forgery must not survive the source rebuild."""

    _revision_value, _page, _committed, source = _one_active()
    target, payload = _stored(tmp_path, source)
    payload["rows"][0][field] = value
    _reseal_bundle(target, payload)

    forged = json.loads(target.read_text(encoding="utf-8"))
    assert forged["rows"][0][field] == value
    rows = [
        SubjectiveMemRetrievalProjectionRow(
            **{key: item for key, item in row.items() if key != "schema"}
        )
        for row in forged["rows"]
    ]
    assert forged["manifest"]["row_digests"] == [row.row_digest for row in rows]
    assert validate_subjective_mem_retrieval_projection_row(rows[0]) == ()

    loaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent), source=source
    )
    assert loaded is None
    assert reasons == ("subjective_mem_retrieval_projection_not_source_exact",)


def test_write_refuses_a_projection_that_is_not_the_exact_source_rebuild(
    tmp_path: Path,
) -> None:
    revision, page, committed, source = _one_active()
    other = _source(
        _entry(revision, page, committed), snapshot_taken_at="2026-07-30T00:00:00+00:00"
    )
    root = tmp_path / "projection"
    root.mkdir()
    reasons = write_subjective_mem_retrieval_projection(
        projection_root=str(root), source=source, projection=_built(other)
    )
    assert reasons == ("subjective_mem_retrieval_projection_not_source_exact",)
    assert list(root.iterdir()) == []

    handcrafted = replace(_built(source), rows=())
    reasons = write_subjective_mem_retrieval_projection(
        projection_root=str(root), source=source, projection=handcrafted
    )
    assert reasons == ("subjective_mem_retrieval_projection_not_source_exact",)
    assert list(root.iterdir()) == []


def test_an_unsigned_tampered_bundle_fails_closed(tmp_path: Path) -> None:
    _revision_value, _page, _committed, source = _one_active()
    target, payload = _stored(tmp_path, source)
    payload["rows"][0]["lifecycle_state"] = "pinned"
    target.write_text(json.dumps(payload), encoding="utf-8")
    loaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent), source=source
    )
    assert loaded is None
    assert reasons == ("subjective_mem_retrieval_projection_bundle_tampered",)


def test_a_resigned_mixed_generation_bundle_fails_closed(tmp_path: Path) -> None:
    _revision_value, _page, _committed, source = _one_active()
    target, payload = _stored(tmp_path, source)
    payload["rows"][0]["projection_generation_id"] = "smretrievalgen_" + "b" * 64
    _reseal_bundle(target, payload)
    loaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent), source=source
    )
    assert loaded is None
    assert "subjective_mem_retrieval_projection_mixed_generation" in reasons


def test_a_resigned_incomplete_manifest_fails_closed(tmp_path: Path) -> None:
    _revision_value, _page, _committed, source = _one_active()
    target, payload = _stored(tmp_path, source)
    payload["manifest"]["complete"] = False
    _reseal_bundle(target, payload)
    loaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent), source=source
    )
    assert loaded is None
    assert "subjective_mem_retrieval_projection_manifest_state_invalid" in reasons


def test_a_resigned_duplicate_row_bundle_fails_closed(tmp_path: Path) -> None:
    _revision_value, _page, _committed, source = _one_active()
    target, payload = _stored(tmp_path, source)
    payload["rows"] = payload["rows"] * 2
    _reseal_bundle(target, payload)
    loaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent), source=source
    )
    assert loaded is None
    assert "subjective_mem_retrieval_projection_row_duplicated" in reasons


def test_a_resigned_unsupported_source_schema_revision_fails_closed(tmp_path: Path) -> None:
    _revision_value, _page, _committed, source = _one_active()
    target, payload = _stored(tmp_path, source)
    payload["manifest"]["source_schema_revision_digest"] = "7" * 64
    _reseal_bundle(target, payload)
    loaded, reasons = read_subjective_mem_retrieval_projection(
        projection_root=str(target.parent), source=source
    )
    assert loaded is None
    assert "subjective_mem_retrieval_projection_source_revision_unsupported" in reasons


def test_load_refuses_a_non_bundle_payload_without_partial_acceptance() -> None:
    _revision_value, _page, _committed, source = _one_active()
    for payload in (None, {}, {"schema": "other"}, [1, 2, 3]):
        loaded, reasons = load_subjective_mem_retrieval_projection(payload, source=source)
        assert loaded is None
        assert reasons == ("subjective_mem_retrieval_projection_bundle_tampered",)


def test_persistence_refuses_an_unsafe_or_relative_projection_root(tmp_path: Path) -> None:
    _revision_value, _page, _committed, source = _one_active()
    for root in ("", "relative/path", str(tmp_path / "absent")):
        reasons = write_subjective_mem_retrieval_projection(
            projection_root=root, source=source, projection=_built(source)
        )
        assert reasons and reasons[0].startswith("subjective_mem_retrieval_projection_root_")
        loaded, reasons = read_subjective_mem_retrieval_projection(
            projection_root=root, source=source
        )
        assert loaded is None
        assert reasons[0].startswith("subjective_mem_retrieval_projection_root_")


def test_projection_owns_no_duplicate_receipt_or_lifecycle_evaluator() -> None:
    source = inspect.getsource(projection_module)
    assert "validate_subjective_mem_committed_receipt(" in source
    assert "validate_subjective_mem_committed_authorization(" in source
    assert "subjective_mem_committed_authorization_ref(" in source
    for forbidden in (
        "COMMITTED_LIFECYCLE_OPERATIONS",
        "LIFECYCLE_RECEIPT_SCHEMA",
        "LIFECYCLE_TRANSITION_SCHEMA",
        "ST1_RECEIPT_SCHEMA",
        "operation_kind",
        "transition_id",
        "successor_revision_digest",
        "from_lifecycle_state",
    ):
        assert forbidden not in source, forbidden


def test_projection_modules_have_no_primary_shadow_or_request_path_dependency() -> None:
    expected = {
        projection_module: {
            "__future__",
            "dataclasses",
            "relaylm.evidence.common",
            "relaylm.subjective_mem.models",
            "relaylm.subjective_mem_lifecycle_authority",
            "relaylm.subjective_mem_markdown",
            "relaylm.subjective_mem_retrieval",
        },
        store_module: {
            "__future__",
            "json",
            "os",
            "stat",
            "dataclasses",
            "pathlib",
            "relaylm.evidence.common",
            "relaylm.subjective_mem_retrieval",
            "relaylm.subjective_mem_retrieval_projection",
        },
    }
    for module, imports in expected.items():
        tree = ast.parse(inspect.getsource(module))
        observed = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        observed.update(
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        assert observed == imports, module.__name__
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
            "EvidenceRecordStore",
            "EvidenceStoreTransaction",
            "grounded_content",
            "subjective_meaning",
            "relative_path",
        ):
            assert forbidden not in executable, (module.__name__, forbidden)


def _executable_source(tree: ast.Module) -> str:
    """Return the module source with every docstring removed."""

    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            if isinstance(body[0].value.value, str):
                body.pop(0)
    return ast.unparse(tree)


def test_review_triggers_remain_bounded() -> None:
    for module in (projection_module, store_module):
        source = inspect.getsource(module)
        assert len(source.splitlines()) < 700, module.__name__
        lengths = []
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = max(getattr(item, "end_lineno", node.lineno) for item in ast.walk(node))
                lengths.append((node.name, end - node.lineno + 1))
        assert max(length for _, length in lengths) <= 80, (module.__name__, lengths)
    assert Path(projection_module.__file__).name == "subjective_mem_retrieval_projection.py"
    assert Path(store_module.__file__).name == "subjective_mem_retrieval_projection_store.py"
