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
    select_subjective_mem_retrieval_handoff,
)
from relaylm.subjective_mem_retrieval_usage_ledger import (
    SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND,
    SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND,
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
    assert handoff.admitted_grounding_evidence()[0] is None

    admitted, outcome = finalize_subjective_mem_retrieval_usage(**_arguments(store, handoff, bound))
    assert outcome.status == "finalized" and outcome.event_count == 2 and outcome.admitted is True
    assert admitted is not None and admitted.admitted is True
    assert admitted.admitted_grounding_evidence() == (handoff.evidence_items, ())
    assert len(_record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND)) == 2
    assert len(_record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND)) == 2


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
    assert admitted is not None and admitted.admitted is True
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


def test_a_partial_existing_durable_result_fails_closed(store) -> None:
    first, second = _row(), _other_row()
    handoff, bound = _prepared(first, second)
    arguments = _arguments(store, handoff, bound)
    _admitted, outcome = finalize_subjective_mem_retrieval_usage(**arguments)
    assert outcome.status == "finalized"

    results = Path(store.root) / SPACE / "records" / SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND
    sorted(results.glob("*.json"))[0].unlink()

    admitted, partial = finalize_subjective_mem_retrieval_usage(**arguments)
    assert admitted is None and partial.status == "conflict"
    assert "subjective_mem_retrieval_usage_partial_existing_result" in partial.blocked_reason_classes


@pytest.mark.parametrize(
    ("handoff_change", "reason"),
    [
        ("shadow", "subjective_mem_retrieval_usage_shadow_not_admissible"),
        ("admitted", "subjective_mem_retrieval_usage_handoff_already_admitted"),
    ],
)
def test_no_usage_event_is_written_for_a_shadow_or_already_admitted_handoff(
    store, handoff_change, reason
) -> None:
    if handoff_change == "shadow":
        handoff, bound = _prepared(_row(), shadow=True)
    else:
        prepared, bound = _prepared(_row())
        handoff = replace(prepared, admitted=True)
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
    assert admitted is not None


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
