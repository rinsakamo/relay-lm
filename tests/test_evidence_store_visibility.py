"""Concurrency regression tests for EV-1 transaction visibility."""
from __future__ import annotations

import threading

import pytest

from relaylm.evidence.store import EvidenceRecordStore


def test_public_reader_waits_for_transaction_commit(tmp_path) -> None:
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    evidence_space_id = "evsp_visibility"
    writer_entered = threading.Event()
    release_writer = threading.Event()
    reader_started = threading.Event()
    observed: list[dict | None] = []
    errors: list[BaseException] = []

    def writer() -> None:
        try:
            with store.transaction(evidence_space_id) as tx:
                writer_entered.set()
                assert release_writer.wait(timeout=5)
                result = tx.commit(
                    transaction_id="tx_visibility",
                    records=(("source_event", "sourceevent_visibility", {"value": 1}),),
                    logs=(),
                )
                assert result.status in {"created", "duplicate_existing"}
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    def reader() -> None:
        try:
            reader_started.set()
            observed.append(
                store.read_record(
                    evidence_space_id=evidence_space_id,
                    record_kind="source_event",
                    record_id="sourceevent_visibility",
                )
            )
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    writer_thread = threading.Thread(target=writer)
    reader_thread = threading.Thread(target=reader)
    writer_thread.start()
    assert writer_entered.wait(timeout=5)
    reader_thread.start()
    assert reader_started.wait(timeout=5)

    # The reader must remain behind the evidence-space lock while the writer's
    # prepared transaction is incomplete; it cannot observe a partial authority
    # set or return an early "not found" result.
    reader_thread.join(timeout=0.05)
    assert reader_thread.is_alive()

    release_writer.set()
    writer_thread.join(timeout=5)
    reader_thread.join(timeout=5)
    assert not writer_thread.is_alive()
    assert not reader_thread.is_alive()
    assert errors == []
    assert observed == [{"value": 1}]


def test_corrupt_persisted_log_fails_closed_without_replacement(tmp_path) -> None:
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    evidence_space_id = "evsp_corrupt_log"
    path = (
        store.root
        / evidence_space_id
        / "logs"
        / "capture_sequence"
        / "managed_user_input.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(RuntimeError, match="evidence_store_log_corrupt"):
        store.read_log(
            evidence_space_id=evidence_space_id,
            log_kind="capture_sequence",
            key="managed_user_input",
        )

    assert path.read_text(encoding="utf-8") == "{not-json"
