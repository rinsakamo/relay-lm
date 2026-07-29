from __future__ import annotations

import ast
import inspect
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

import relaylm.subjective_mem_retrieval_usage_ledger as ledger_owner
from relaylm.evidence_common import utf8_text_digest
from relaylm.evidence_store import EvidenceRecordStore, EvidenceStoreResult
from relaylm.relaymem_grounded_recall_response import build_grounded_recall_context
from relaylm.subjective_mem_retrieval import (
    RETRIEVAL_USAGE_EVENT_KIND,
    SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
    SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION,
    SubjectiveMemRetrievalBoundary,
    SubjectiveMemRetrievalProjectionManifest,
    SubjectiveMemRetrievalProjectionRow,
    SubjectiveMemRetrievalRequest,
    derive_subjective_mem_retrieval_usage_event,
)
from relaylm.subjective_mem_retrieval_projection_store import (
    PROJECTION_BUNDLE_FILENAME,
    delete_subjective_mem_retrieval_projection,
)
from relaylm.subjective_mem_retrieval_selection import (
    SubjectiveMemRetrievalContentBinding,
    SubjectiveMemRetrievalPreparedHandoff,
    select_subjective_mem_retrieval_handoff,
)
from relaylm.subjective_mem_retrieval_usage_ledger import (
    SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND,
    SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND,
    SubjectiveMemRetrievalAdmittedHandoff,
    finalize_subjective_mem_retrieval_usage,
)

D = "a" * 64
D2 = "b" * 64
PAGE = "sha256:" + "c" * 64
NOW = "2026-07-28T00:00:00+00:00"
LATER = "2026-07-28T00:00:01+00:00"
SPACE = "evidence-space-1"
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


def _manifest(*rows: SubjectiveMemRetrievalProjectionRow):
    return SubjectiveMemRetrievalProjectionManifest(
        projection_generation_id="projection-generation-1",
        source_snapshot_digest=D,
        source_schema_revision_digest=D2,
        row_digests=tuple(sorted(row.row_digest for row in rows)),
        built_at=NOW,
        complete=True,
        mixed_generation=False,
        policy_revision=SUBJECTIVE_MEM_RETRIEVAL_PROJECTION_POLICY_REVISION,
    )


def _request(manifest: SubjectiveMemRetrievalProjectionManifest):
    return SubjectiveMemRetrievalRequest(
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


def _binding(row: SubjectiveMemRetrievalProjectionRow):
    return SubjectiveMemRetrievalContentBinding(
        row_digest=row.row_digest,
        memory_id=row.memory_id,
        memory_revision=row.memory_revision,
        character_id="char1",
        workspace_authority_digest=D2,
        scope_binding_digest=D,
        grounded_content=CONTENT,
        grounded_content_digest=utf8_text_digest(CONTENT),
        token_estimate=16,
    )


def _prepared(*rows: SubjectiveMemRetrievalProjectionRow, shadow: bool = False):
    """Prepare one backend-bound handoff plus the ledger arguments it belongs to."""
    from relaylm.subjective_mem_retrieval import subjective_mem_retrieval_exclusion_reasons

    manifest = _manifest(*rows)
    request = _request(manifest)
    bindings = tuple(
        _binding(row) for row in rows if not subjective_mem_retrieval_exclusion_reasons(row)
    )
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=rows, content_bindings=bindings, shadow=shadow
    )
    assert projection.status != "refused"
    return handoff, {"request": request, "manifest": manifest, "rows": rows}


def _arguments(store: EvidenceRecordStore, handoff, bound, **changes):
    return {
        "store": store, "evidence_space_id": SPACE, "handoff": handoff,
        "occurred_at": NOW, "idempotency_key": "request-memory-use-1", **bound, **changes,
    }


def _record_ids(store: EvidenceRecordStore, record_kind: str) -> list[str]:
    directory = Path(store.root) / SPACE / "records" / record_kind
    return sorted(path.name for path in directory.glob("*.json")) if directory.is_dir() else []


class _FailingTransaction:
    """A bounded double whose durable commit never succeeds."""

    def __init__(self, transaction) -> None:
        self._transaction = transaction

    def read_record(self, **kwargs):
        return self._transaction.read_record(**kwargs)

    def commit(self, **_kwargs) -> EvidenceStoreResult:
        return EvidenceStoreResult("failed", ("injected_commit_failure",))


class _FailingCommitStore(EvidenceRecordStore):
    @contextmanager
    def transaction(self, evidence_space_id: str):
        with super().transaction(evidence_space_id) as transaction:
            yield _FailingTransaction(transaction)


class _UnavailableStore(EvidenceRecordStore):
    @contextmanager
    def transaction(self, evidence_space_id: str):
        raise RuntimeError("evidence_store_unavailable")
        yield  # pragma: no cover - unreachable, keeps the generator contract explicit


@pytest.fixture()
def store(tmp_path: Path) -> EvidenceRecordStore:
    return EvidenceRecordStore(str(tmp_path / "evidence"))


def test_usage_events_are_finalized_atomically_before_the_handoff_is_admitted(store) -> None:
    first, second = _row(), _other_row()
    handoff, bound = _prepared(first, second)
    assert type(handoff) is SubjectiveMemRetrievalPreparedHandoff

    admitted, outcome = finalize_subjective_mem_retrieval_usage(**_arguments(store, handoff, bound))
    assert outcome.status == "finalized" and outcome.event_count == 2 and outcome.admitted is True
    assert type(admitted) is SubjectiveMemRetrievalAdmittedHandoff
    assert admitted.finalization_status == "finalized"
    assert admitted.release_grounding_evidence() == tuple(
        item.to_grounding_dict() for item in handoff.private_items
    )
    assert len(_record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND)) == 2
    assert len(_record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND)) == 2


def test_only_an_admitted_handoff_releases_fresh_dictionaries_for_the_grounding_owner(store) -> None:
    first, second = _row(), _other_row(lifecycle_state="pinned")
    handoff, bound = _prepared(first, second)
    admitted, outcome = finalize_subjective_mem_retrieval_usage(**_arguments(store, handoff, bound))
    assert outcome.status == "finalized" and admitted is not None

    released = admitted.release_grounding_evidence()
    assert all(type(item) is dict for item in released)
    result = build_grounded_recall_context(
        retrieved_memories=list(released), query_text="", character_id="char1"
    )
    assert result.status == "grounding_applied"
    log = result.to_log_dict()
    assert log["grounded_item_count"] == 2 and log["excluded_evidence_count"] == 0

    released[0]["fact_text"] = "tampered"
    again = admitted.release_grounding_evidence()
    assert again[0]["fact_text"] == CONTENT and again[0] is not released[0]


@pytest.mark.parametrize(
    ("tamper", "reason"),
    [
        ("prose", "subjective_mem_retrieval_private_item_content_digest_mismatch"),
        ("digest", "subjective_mem_retrieval_private_item_content_digest_mismatch"),
        ("identity", "subjective_mem_retrieval_private_item_row_mismatch"),
        ("lifecycle", "subjective_mem_retrieval_private_item_row_mismatch"),
        ("provenance", "subjective_mem_retrieval_private_item_row_mismatch"),
        ("row_digest", "subjective_mem_retrieval_usage_private_item_order_mismatch"),
        ("reorder", "subjective_mem_retrieval_usage_private_item_order_mismatch"),
        ("dropped", "subjective_mem_retrieval_usage_private_item_count_mismatch"),
        ("duplicated", "subjective_mem_retrieval_usage_private_item_count_mismatch"),
    ],
)
def test_tampered_private_evidence_is_refused_before_any_durable_write(store, tamper, reason) -> None:
    first, second = _row(), _other_row()
    handoff, bound = _prepared(first, second)
    items = handoff.private_items
    tampered = {
        "prose": (replace(items[0], grounded_content="forged prose"), items[1]),
        "digest": (replace(items[0], grounded_content_digest=D2), items[1]),
        "identity": (replace(items[0], memory_id="memory9"), items[1]),
        "lifecycle": (replace(items[0], lifecycle_state="pinned", pinned=True), items[1]),
        "provenance": (replace(items[0], provenance_source="user_assertion"), items[1]),
        "row_digest": (replace(items[0], row_digest=items[1].row_digest), items[1]),
        "reorder": (items[1], items[0]),
        "dropped": (items[0],),
        "duplicated": (items[0], items[0], items[1]),
    }[tamper]
    admitted, outcome = finalize_subjective_mem_retrieval_usage(
        **_arguments(store, replace(handoff, private_items=tampered), bound)
    )
    assert admitted is None and outcome.status == "refused"
    assert reason in outcome.blocked_reason_classes
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND) == []
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND) == []


def test_persisted_usage_event_has_the_exact_contract_identity_and_is_content_free(store) -> None:
    row = _row()
    handoff, bound = _prepared(row)
    _admitted, outcome = finalize_subjective_mem_retrieval_usage(**_arguments(store, handoff, bound))
    assert outcome.status == "finalized"

    expected, reasons = derive_subjective_mem_retrieval_usage_event(
        selection=handoff.selection, row=row, event_kind=RETRIEVAL_USAGE_EVENT_KIND,
        occurred_at=NOW, idempotency_key="request-memory-use-1", **bound,
    )
    assert reasons == () and expected is not None
    stored = store.read_record(
        evidence_space_id=SPACE, record_kind=SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND,
        record_id=expected.usage_event_id,
    )
    assert stored == expected.to_dict()
    public = outcome.to_dict()
    assert public["raw_query_persisted"] is False and public["memory_content_persisted"] is False
    assert public["runtime_private_evidence_omitted"] is True
    body = repr(stored) + repr(public["blocked_reason_classes"])
    for forbidden in (
        CONTENT, "request-memory-use-1", "raw_query", "grounded_content",
        "subjective_meaning", "prompt", "/",
    ):
        assert forbidden not in body, forbidden


def test_the_same_exact_usage_slot_is_idempotent_without_an_extra_event(store) -> None:
    handoff, bound = _prepared(_row(), _other_row())
    arguments = _arguments(store, handoff, bound)
    _admitted, first = finalize_subjective_mem_retrieval_usage(**arguments)
    assert first.status == "finalized"
    before = _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND)

    admitted, second = finalize_subjective_mem_retrieval_usage(**arguments)
    assert second.status == "duplicate_finalized"
    assert (second.event_count, second.duplicate_count) == (0, 2)
    assert type(admitted) is SubjectiveMemRetrievalAdmittedHandoff
    assert admitted.finalization_status == "duplicate_finalized"
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND) == before


def test_a_divergent_event_in_the_same_slot_is_an_integrity_conflict(store) -> None:
    handoff, bound = _prepared(_row())
    _admitted, outcome = finalize_subjective_mem_retrieval_usage(**_arguments(store, handoff, bound))
    assert outcome.status == "finalized"
    before = _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND)

    admitted, conflict = finalize_subjective_mem_retrieval_usage(
        **_arguments(store, handoff, bound, occurred_at=LATER)
    )
    assert admitted is None and conflict.status == "conflict"
    assert "subjective_mem_retrieval_usage_slot_integrity_conflict" in conflict.blocked_reason_classes
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND) == before


def _records(store: EvidenceRecordStore, record_kind: str) -> list[Path]:
    return sorted((Path(store.root) / SPACE / "records" / record_kind).glob("*.json"))


@pytest.mark.parametrize(
    ("damage", "reason"),
    [
        ("result_present_event_missing", "subjective_mem_retrieval_usage_pair_incomplete"),
        ("event_present_result_missing", "subjective_mem_retrieval_usage_pair_incomplete"),
        ("exact_result_divergent_event", "subjective_mem_retrieval_usage_slot_integrity_conflict"),
        ("exact_event_divergent_result", "subjective_mem_retrieval_usage_slot_integrity_conflict"),
    ],
)
def test_an_incomplete_or_divergent_event_result_pair_fails_closed(store, damage, reason) -> None:
    handoff, bound = _prepared(_row())
    arguments = _arguments(store, handoff, bound)
    _admitted, outcome = finalize_subjective_mem_retrieval_usage(**arguments)
    assert outcome.status == "finalized"

    events = _records(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND)
    results = _records(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND)
    if damage == "result_present_event_missing":
        events[0].unlink()
    elif damage == "event_present_result_missing":
        results[0].unlink()
    elif damage == "exact_result_divergent_event":
        events[0].write_text('{"schema": "relaylm.forged.v1"}', encoding="utf-8")
    else:
        results[0].write_text('{"schema": "relaylm.forged.v1"}', encoding="utf-8")
    before = (
        [path.name for path in _records(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND)],
        [path.name for path in _records(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND)],
    )

    admitted, conflict = finalize_subjective_mem_retrieval_usage(**arguments)
    assert admitted is None and conflict.status == "conflict"
    assert conflict.blocked_reason_classes == (reason,)
    assert before == (
        [path.name for path in _records(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND)],
        [path.name for path in _records(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND)],
    )


def test_one_exact_pair_beside_one_absent_pair_fails_closed(store) -> None:
    first, second = _row(), _other_row()
    handoff, bound = _prepared(first, second)
    arguments = _arguments(store, handoff, bound)
    _admitted, outcome = finalize_subjective_mem_retrieval_usage(**arguments)
    assert outcome.status == "finalized"

    _records(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND)[0].unlink()
    _records(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND)[0].unlink()

    admitted, partial = finalize_subjective_mem_retrieval_usage(**arguments)
    assert admitted is None and partial.status == "conflict"
    assert partial.blocked_reason_classes == (
        "subjective_mem_retrieval_usage_partial_existing_result",
    )
    assert len(_records(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND)) == 1


@pytest.mark.parametrize(
    ("handoff_change", "reason"),
    [
        ("shadow", "subjective_mem_retrieval_usage_shadow_not_admissible"),
        ("emptied", "subjective_mem_retrieval_usage_selection_empty"),
    ],
)
def test_no_usage_event_is_written_for_a_shadow_or_emptied_handoff(
    store, handoff_change, reason
) -> None:
    handoff, bound = _prepared(_row(), shadow=handoff_change == "shadow")
    if handoff_change != "shadow":
        handoff = replace(handoff, ranked_row_digests=())
    admitted, outcome = finalize_subjective_mem_retrieval_usage(**_arguments(store, handoff, bound))
    assert admitted is None and outcome.status == "refused"
    assert outcome.blocked_reason_classes == (reason,)
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND) == []


def test_no_usage_event_is_written_for_an_empty_or_considered_only_result(store) -> None:
    handoff, bound = _prepared(_row(lifecycle_state="hidden", retrieval_eligible=False))
    admitted, outcome = finalize_subjective_mem_retrieval_usage(**_arguments(store, handoff, bound))
    assert admitted is None and outcome.status == "refused"
    assert outcome.blocked_reason_classes == ("subjective_mem_retrieval_usage_selection_empty",)
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND) == []

    selected = _row()
    considered = _other_row(mutation_state="corrupt", retrieval_eligible=False)
    handoff, bound = _prepared(selected, considered)
    _admitted, outcome = finalize_subjective_mem_retrieval_usage(**_arguments(store, handoff, bound))
    assert outcome.status == "finalized" and outcome.event_count == 1
    assert len(_record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND)) == 1


def test_a_handoff_that_disagrees_with_its_selection_is_refused(store) -> None:
    first, second = _row(), _other_row()
    handoff, bound = _prepared(first, second)
    tampered = replace(handoff, ranked_row_digests=(first.row_digest,))
    admitted, outcome = finalize_subjective_mem_retrieval_usage(
        **_arguments(store, tampered, bound)
    )
    assert admitted is None and outcome.status == "refused"
    assert outcome.blocked_reason_classes == (
        "subjective_mem_retrieval_usage_handoff_selection_mismatch",
    )
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND) == []


def test_an_injected_durable_failure_returns_no_admitted_handoff(tmp_path: Path) -> None:
    handoff, bound = _prepared(_row(), _other_row())
    failing = _FailingCommitStore(str(tmp_path / "evidence"))
    admitted, outcome = finalize_subjective_mem_retrieval_usage(**_arguments(failing, handoff, bound))
    assert admitted is None and outcome.status == "failed" and outcome.admitted is False
    assert "injected_commit_failure" in outcome.blocked_reason_classes
    assert _record_ids(failing, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND) == []

    unavailable = _UnavailableStore(str(tmp_path / "evidence"))
    admitted, outcome = finalize_subjective_mem_retrieval_usage(
        **_arguments(unavailable, handoff, bound)
    )
    assert admitted is None and outcome.status == "failed"
    assert outcome.blocked_reason_classes == ("subjective_mem_retrieval_usage_store_unavailable",)


def test_durable_events_survive_projection_deletion_and_deterministic_rebuild(
    store, tmp_path: Path
) -> None:
    row = _row()
    handoff, bound = _prepared(row)
    _admitted, outcome = finalize_subjective_mem_retrieval_usage(**_arguments(store, handoff, bound))
    assert outcome.status == "finalized"
    persisted = _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND)

    projection_root = tmp_path / "projection"
    projection_root.mkdir()
    bundle = projection_root / PROJECTION_BUNDLE_FILENAME
    bundle.write_bytes(b"{}")
    assert delete_subjective_mem_retrieval_projection(projection_root=str(projection_root)) == ()
    assert not bundle.exists()
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND) == persisted

    rebuilt_handoff, rebuilt_bound = _prepared(_row())
    assert rebuilt_handoff.selection == handoff.selection
    admitted, replayed = finalize_subjective_mem_retrieval_usage(
        **_arguments(store, rebuilt_handoff, rebuilt_bound)
    )
    assert replayed.status == "duplicate_finalized" and replayed.event_count == 0
    assert type(admitted) is SubjectiveMemRetrievalAdmittedHandoff


def test_ledger_depends_one_way_on_selection_and_reuses_the_evidence_store() -> None:
    tree = ast.parse(inspect.getsource(ledger_owner))
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
        "__future__", "dataclasses", "typing", "relaylm.evidence_common",
        "relaylm.evidence_store", "relaylm.subjective_mem_retrieval",
        "relaylm.subjective_mem_retrieval_selection",
    }
    assert "SubjectiveMemRetrievalAdmittedHandoff" not in inspect.getsource(
        inspect.getmodule(select_subjective_mem_retrieval_handoff)
    )
    selection_source = inspect.getsource(
        inspect.getmodule(select_subjective_mem_retrieval_handoff)
    )
    assert "subjective_mem_retrieval_usage_ledger" not in selection_source
    for forbidden in (
        "portable_lock", "os.replace", "fsync", "mkdir", "relaymem_primary",
        "relaymem_retrieval", "open(", "write_bytes", "read_bytes", "unlink",
    ):
        assert forbidden not in _executable_source(ledger_owner), forbidden


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
    source = inspect.getsource(ledger_owner)
    assert len(source.splitlines()) < 700
    tree = ast.parse(source)
    lengths = [
        (node.name, max(getattr(item, "end_lineno", node.lineno) for item in ast.walk(node)) - node.lineno + 1)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert max(length for _, length in lengths) <= 80, lengths
    assert Path(ledger_owner.__file__).name == "subjective_mem_retrieval_usage_ledger.py"
