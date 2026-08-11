from __future__ import annotations

import ast
import inspect
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

import relaylm.subjective_mem.retrieval_usage_ledger as ledger_owner
from relaylm.evidence.common import utf8_text_digest
from relaylm.evidence.store import EvidenceRecordStore, EvidenceStoreResult
from relaylm.relaymem_grounded_recall_response import build_grounded_recall_context
from relaylm.subjective_mem.retrieval import (
    RETRIEVAL_USAGE_EVENT_KIND,
    derive_subjective_mem_retrieval_usage_event,
)
from relaylm.subjective_mem.retrieval_projection_store import (
    PROJECTION_BUNDLE_FILENAME,
    delete_subjective_mem_retrieval_projection,
)
from relaylm.subjective_mem.retrieval_selection import (
    SubjectiveMemRetrievalCanonicalPageBinding,
    SubjectiveMemRetrievalPreparedHandoff,
    select_subjective_mem_retrieval_handoff,
)
from relaylm.subjective_mem.retrieval_usage_ledger import (
    SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND,
    SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND,
    SubjectiveMemRetrievalAdmittedHandoff,
    finalize_subjective_mem_retrieval_usage,
)

from test_subjective_mem_retrieval_selection import (  # noqa: E402  (shared fixture builders)
    D2,
    D3,
    GROUNDED as CONTENT,
    MEANING,
    _block,
    _manifest,
    _page,
    _request,
    _revision,
    _row,
    _successor,
)

NOW = "2026-07-28T00:00:00+00:00"
LATER = "2026-07-28T00:00:01+00:00"
SPACE = "evidence-space-1"


def _prepared(*memory_ids: str, shadow: bool = False, row_changes: dict | None = None):
    """Prepare one backend-bound handoff plus the ledger arguments it belongs to."""

    chains = []
    for memory_id in memory_ids:
        base = _revision(memory_id)
        chains.append((base, _successor(base)))
    data, page = _page(*chains)
    rows = tuple(
        _row(page, _block(page, memory_id, 2), **((row_changes or {}) if index == 0 else {}))
        for index, memory_id in enumerate(memory_ids)
    )
    manifest = _manifest(*rows)
    request = _request(manifest)
    pages = (
        () if row_changes
        else (SubjectiveMemRetrievalCanonicalPageBinding(canonical_page_bytes=data),)
    )
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=rows, canonical_pages=pages, shadow=shadow
    )
    assert projection.status != "refused", projection.blocked_reason_classes
    return handoff, {"request": request, "manifest": manifest, "rows": rows}, data


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
    handoff, bound, _data = _prepared("memory1", "memory2")
    assert type(handoff) is SubjectiveMemRetrievalPreparedHandoff

    admitted, outcome = finalize_subjective_mem_retrieval_usage(**_arguments(store, handoff, bound))
    assert outcome.status == "finalized" and outcome.event_count == 2 and outcome.admitted is True
    assert type(admitted) is SubjectiveMemRetrievalAdmittedHandoff
    assert admitted.finalization_status == "finalized"
    released = admitted.release_grounding_evidence()
    assert len(released) == 2 and all(type(item) is dict for item in released)
    assert {item["fact_text"] for item in released} == {CONTENT}
    assert len(_record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND)) == 2
    assert len(_record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND)) == 2


def test_only_an_admitted_handoff_releases_fresh_dictionaries_for_the_grounding_owner(store) -> None:
    handoff, bound, _data = _prepared("memory1", "memory2")
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


FORGED = "forged prose the canonical page never contained"


@pytest.mark.parametrize(
    "tamper",
    [
        "prose", "prose_with_matching_digest", "digest", "identity", "lifecycle",
        "provenance", "token_estimate", "row_digest", "reorder", "dropped", "duplicated",
        "dropped_page", "substituted_page",
    ],
)
def test_tampered_canonical_evidence_is_refused_before_any_durable_write(store, tamper) -> None:
    handoff, bound, _data = _prepared("memory1", "memory2")
    items = handoff._private_items
    tampered = {
        "prose": replace(handoff, _private_items=(replace(items[0], grounded_content=FORGED), items[1])),
        "prose_with_matching_digest": replace(
            handoff,
            _private_items=(
                replace(
                    items[0], grounded_content=FORGED,
                    grounded_content_digest=utf8_text_digest(FORGED),
                ),
                items[1],
            ),
        ),
        "digest": replace(handoff, _private_items=(replace(items[0], grounded_content_digest=D3), items[1])),
        "identity": replace(handoff, _private_items=(replace(items[0], memory_id="memory9"), items[1])),
        "lifecycle": replace(
            handoff, _private_items=(replace(items[0], lifecycle_state="pinned", pinned=True), items[1])
        ),
        "provenance": replace(
            handoff, _private_items=(replace(items[0], provenance_source="other_allowed_source"), items[1])
        ),
        "token_estimate": replace(handoff, _private_items=(replace(items[0], token_estimate=1), items[1])),
        "row_digest": replace(
            handoff, _private_items=(replace(items[0], row_digest=items[1].row_digest), items[1])
        ),
        "reorder": replace(handoff, _private_items=(items[1], items[0])),
        "dropped": replace(handoff, _private_items=(items[0],)),
        "duplicated": replace(handoff, _private_items=(items[0], items[0])),
        "dropped_page": replace(handoff, _canonical_pages=()),
        "substituted_page": replace(
            handoff,
            _canonical_pages=(
                SubjectiveMemRetrievalCanonicalPageBinding(
                    canonical_page_bytes=b"not canonical markdown\n"
                ),
            ),
        ),
    }[tamper]
    admitted, outcome = finalize_subjective_mem_retrieval_usage(
        **_arguments(store, tampered, bound)
    )
    assert admitted is None and outcome.status == "refused"
    assert outcome.blocked_reason_classes != ()
    assert FORGED not in repr(outcome.to_dict())
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND) == []
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND) == []


def test_persisted_usage_event_has_the_exact_contract_identity_and_is_content_free(store) -> None:
    handoff, bound, _data = _prepared("memory1")
    row = bound["rows"][0]
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
    handoff, bound, _data = _prepared("memory1", "memory2")
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


def test_a_different_second_replay_admits_the_same_evidence_without_a_second_pair(
    store,
) -> None:
    """A response-lost replay is idempotent across wall-clock seconds.

    `LATER` is exactly one second after `NOW`, so this is deterministic and
    needs no sleep. The stable result slot is authoritative and the first
    finalization owns the occurrence time: the newly supplied occurrence is the
    only value not compared, so the replay resolves to the original event and
    admits the same evidence without writing a second durable pair.
    """

    handoff, bound, _data = _prepared("memory1")
    admitted, outcome = finalize_subjective_mem_retrieval_usage(
        **_arguments(store, handoff, bound)
    )
    assert outcome.status == "finalized"
    before = _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND)

    replayed, second = finalize_subjective_mem_retrieval_usage(
        **_arguments(store, handoff, bound, occurred_at=LATER)
    )
    assert second.status == "duplicate_finalized"
    assert replayed is not None
    assert replayed.release_grounding_evidence() == admitted.release_grounding_evidence()
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND) == before


def _records(store: EvidenceRecordStore, record_kind: str) -> list[Path]:
    return sorted((Path(store.root) / SPACE / "records" / record_kind).glob("*.json"))


def test_a_different_second_replay_never_repairs_a_partial_pair(store) -> None:
    """A missing pair member stays fail-closed even across wall-clock seconds.

    The orphaned event was written under the original second, so a later replay
    cannot find it by the occurrence-dependent event identity. The transaction
    identity binds the stable result slots instead, so the attempted later write
    presents the same transaction as the original finalization and collides
    rather than creating a parallel pair beside the orphan.
    """

    handoff, bound, _data = _prepared("memory1")
    _admitted, outcome = finalize_subjective_mem_retrieval_usage(
        **_arguments(store, handoff, bound)
    )
    assert outcome.status == "finalized"

    # Remove only the result, leaving the original event and the committed
    # transaction journal exactly as the first finalization wrote them.
    _records(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND)[0].unlink()
    before = (
        _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND),
        _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND),
    )
    assert len(before[0]) == 1 and before[1] == []

    admitted, conflict = finalize_subjective_mem_retrieval_usage(
        **_arguments(store, handoff, bound, occurred_at=LATER)
    )
    assert admitted is None and conflict.status == "conflict"
    assert (
        _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND),
        _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND),
    ) == before


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
    handoff, bound, _data = _prepared("memory1")
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
    handoff, bound, _data = _prepared("memory1", "memory2")
    arguments = _arguments(store, handoff, bound)
    _admitted, outcome = finalize_subjective_mem_retrieval_usage(**arguments)
    assert outcome.status == "finalized"

    event, reasons = derive_subjective_mem_retrieval_usage_event(
        selection=handoff.selection, row=bound["rows"][0], event_kind=RETRIEVAL_USAGE_EVENT_KIND,
        occurred_at=NOW, idempotency_key="request-memory-use-1", **bound,
    )
    assert reasons == () and event is not None
    space = Path(store.root) / SPACE / "records"
    (space / SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND / f"{event.usage_event_id}.json").unlink()
    (space / SUBJECTIVE_MEM_RETRIEVAL_USAGE_RESULT_RECORD_KIND / f"{event.result_id}.json").unlink()

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
    handoff, bound, _data = _prepared("memory1", shadow=handoff_change == "shadow")
    if handoff_change != "shadow":
        handoff = replace(handoff, ranked_row_digests=())
    admitted, outcome = finalize_subjective_mem_retrieval_usage(**_arguments(store, handoff, bound))
    assert admitted is None and outcome.status == "refused"
    assert outcome.blocked_reason_classes == (reason,)
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND) == []


def test_no_usage_event_is_written_for_an_empty_or_considered_only_result(store) -> None:
    handoff, bound, _data = _prepared(
        "memory1", row_changes={"lifecycle_state": "hidden", "retrieval_eligible": False}
    )
    admitted, outcome = finalize_subjective_mem_retrieval_usage(**_arguments(store, handoff, bound))
    assert admitted is None and outcome.status == "refused"
    assert outcome.blocked_reason_classes == ("subjective_mem_retrieval_usage_selection_empty",)
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND) == []

    selected_base, considered_base = _revision("memory1"), _revision("memory2")
    data, page = _page(
        (selected_base, _successor(selected_base)),
        (considered_base, _successor(considered_base)),
    )
    rows = (
        _row(page, _block(page, "memory1", 2)),
        _row(page, _block(page, "memory2", 2), mutation_state="corrupt", retrieval_eligible=False),
    )
    manifest = _manifest(*rows)
    request = _request(manifest)
    considered_handoff, projection = select_subjective_mem_retrieval_handoff(
        request=request, manifest=manifest, rows=rows,
        canonical_pages=(SubjectiveMemRetrievalCanonicalPageBinding(canonical_page_bytes=data),),
        shadow=False,
    )
    assert projection.selected_count == 1 and projection.candidate_count == 2
    _admitted, outcome = finalize_subjective_mem_retrieval_usage(
        **_arguments(
            store, considered_handoff,
            {"request": request, "manifest": manifest, "rows": rows},
        )
    )
    assert outcome.status == "finalized" and outcome.event_count == 1
    assert len(_record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND)) == 1


def test_a_handoff_that_disagrees_with_its_selection_is_refused(store) -> None:
    handoff, bound, _data = _prepared("memory1", "memory2")
    tampered = replace(handoff, ranked_row_digests=handoff.ranked_row_digests[:1])
    admitted, outcome = finalize_subjective_mem_retrieval_usage(
        **_arguments(store, tampered, bound)
    )
    assert admitted is None and outcome.status == "refused"
    assert outcome.blocked_reason_classes == (
        "subjective_mem_retrieval_usage_handoff_selection_mismatch",
    )
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND) == []


def test_an_injected_durable_failure_returns_no_admitted_handoff(tmp_path: Path) -> None:
    handoff, bound, _data = _prepared("memory1", "memory2")
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
    handoff, bound, _data = _prepared("memory1")
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

    rebuilt_handoff, rebuilt_bound, _data = _prepared("memory1")
    assert rebuilt_handoff.selection == handoff.selection
    admitted, replayed = finalize_subjective_mem_retrieval_usage(
        **_arguments(store, rebuilt_handoff, rebuilt_bound)
    )
    assert replayed.status == "duplicate_finalized" and replayed.event_count == 0
    assert type(admitted) is SubjectiveMemRetrievalAdmittedHandoff


ADMITTED_FIELDS = {
    "schema": "forged", "handoff_shape": "forged", "finalization_status": "finalized",
    "selected_count": 1, "total_token_estimate": 1, "selection": None,
    "ranked_row_digests": (), "_private_items": (), "_admission_seal": object(),
}


def test_an_admitted_handoff_cannot_be_directly_constructed_or_replaced(store) -> None:
    handoff, bound, _data = _prepared("memory1", "memory2")
    with pytest.raises(TypeError):
        SubjectiveMemRetrievalAdmittedHandoff()
    with pytest.raises(TypeError):
        SubjectiveMemRetrievalAdmittedHandoff(**ADMITTED_FIELDS)
    with pytest.raises(TypeError):
        SubjectiveMemRetrievalAdmittedHandoff(
            **{**ADMITTED_FIELDS, "_private_items": handoff._private_items}
        )

    admitted, outcome = finalize_subjective_mem_retrieval_usage(**_arguments(store, handoff, bound))
    assert outcome.status == "finalized" and admitted is not None
    for changes in (
        {"_private_items": ()},
        {"selected_count": 99},
        {"finalization_status": "finalized"},
        {"selection": handoff.selection},
    ):
        with pytest.raises(TypeError):
            replace(admitted, **changes)
    assert len(admitted.release_grounding_evidence()) == 2


def test_an_unsealed_admitted_object_cannot_release_evidence(store) -> None:
    handoff, bound, _data = _prepared("memory1")
    unsealed = object.__new__(SubjectiveMemRetrievalAdmittedHandoff)
    with pytest.raises(RuntimeError):
        unsealed.release_grounding_evidence()

    for name, value in ADMITTED_FIELDS.items():
        object.__setattr__(
            unsealed, name, handoff._private_items if name == "_private_items" else value
        )
    with pytest.raises(RuntimeError):
        unsealed.release_grounding_evidence()
    assert _record_ids(store, SUBJECTIVE_MEM_RETRIEVAL_USAGE_EVENT_RECORD_KIND) == []


def test_only_the_finalizer_seals_an_admitted_handoff_including_duplicates(store) -> None:
    handoff, bound, _data = _prepared("memory1", "memory2")
    arguments = _arguments(store, handoff, bound)
    admitted, first = finalize_subjective_mem_retrieval_usage(**arguments)
    assert first.status == "finalized"
    assert len(admitted.release_grounding_evidence()) == 2

    duplicate, second = finalize_subjective_mem_retrieval_usage(**arguments)
    assert second.status == "duplicate_finalized"
    assert duplicate is not None and duplicate.finalization_status == "duplicate_finalized"
    assert duplicate.release_grounding_evidence() == admitted.release_grounding_evidence()

    # A later-second replay is the same slot, so it seals the same evidence
    # rather than conflicting; only the finalizer may seal it.
    later, third = finalize_subjective_mem_retrieval_usage(
        **_arguments(store, handoff, bound, occurred_at=LATER)
    )
    assert third.status == "duplicate_finalized"
    assert later is not None and later.finalization_status == "duplicate_finalized"
    assert later.release_grounding_evidence() == admitted.release_grounding_evidence()

    source = inspect.getsource(ledger_owner)
    assert source.count("_seal_admitted_handoff(") == 3
    assert source.count("_ADMISSION_SEAL") == 3


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
        "__future__", "dataclasses", "typing", "relaylm.evidence.common",
        "relaylm.evidence.store", "relaylm.subjective_mem.retrieval",
        "relaylm.subjective_mem.retrieval_selection",
    }
    assert "SubjectiveMemRetrievalAdmittedHandoff" not in inspect.getsource(
        inspect.getmodule(select_subjective_mem_retrieval_handoff)
    )
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
    assert Path(ledger_owner.__file__).name == "retrieval_usage_ledger.py"
