"""Atomic exploration budget: never refund, repeat or infer physical permission."""

import json
import multiprocessing
from pathlib import Path

import pytest

from tools import wsl_cuda_exploration_ledger as ledger


GRANT = "1" * 64
COMMENT = 5965167491
RECEIPT_SHA = "2" * 64
EVIDENCE_SHA = "3" * 64


def initialized(tmp_path: Path) -> Path:
    path = tmp_path / "ledger.json"
    ledger.initialize_ledger(
        path,
        execution_grant_sha256=GRANT,
        execution_comment_id=COMMENT,
    )
    return path


def reserve(path: Path, index: int):
    return ledger.reserve_trial(
        path,
        execution_comment_id=COMMENT,
        execution_grant_sha256=GRANT,
        trial_descriptor_sha256=f"{index:064x}",
        frozen_checkout=f"/immutable/v1/checkout-{index}",
        receipt_path=path.parent / f"receipt-{index}.json",
        output_root=path.parent / f"output-{index}",
    )


def block(path: Path, reservation: dict, *, cleanup: bool = True):
    return ledger.finalize_trial(
        path,
        reservation_id=reservation["reservation_id"],
        status="BLOCKED",
        queue_receipt_sha256=RECEIPT_SHA,
        evidence_manifest_sha256=EVIDENCE_SHA,
        cleanup_verified=cleanup,
        zero_requests_verified=True,
        strict_closure_verified=False,
    )


def test_owner_budget_is_an_exact_non_executable_storage_binding(tmp_path: Path) -> None:
    path = initialized(tmp_path)
    state = ledger.inspect_ledger(path)
    assert state["budget_comment_id"] == 5965167490
    assert state["campaign_id"] == "wsl-cuda-exploration-20261003-a"
    assert state["maximum_exploration_trials"] == 8
    assert state["trials"] == []
    assert path.stat().st_mode & 0o077 == 0
    with pytest.raises(ledger.CampaignLedgerError, match="existing ledger"):
        ledger.initialize_ledger(path, execution_grant_sha256=GRANT, execution_comment_id=COMMENT)
    with pytest.raises(ledger.CampaignLedgerError, match="separate later"):
        ledger.initialize_ledger(tmp_path / "bad.json", execution_grant_sha256=GRANT, execution_comment_id=5965167490)
    assert not (tmp_path / "bad.json").exists()


def test_nonrefundable_reservation_blocks_restart_without_terminal(tmp_path: Path) -> None:
    path = initialized(tmp_path)
    one = reserve(path, 1)
    assert one["trial_id"] == "exp-01"
    assert ledger.inspect_ledger(path)["trials"][0]["status"] == "RESERVED"
    with pytest.raises(ledger.CampaignLedgerError, match="previous trial"):
        reserve(path, 2)
    # Restart means a fresh read of the same persistent ledger, not another budget.
    assert ledger.inspect_ledger(path)["trials"][0]["reservation_id"] == one["reservation_id"]
    block(path, one)
    two = reserve(path, 2)
    assert two["trial_id"] == "exp-02"
    assert two["reservation_id"] != one["reservation_id"]


def test_wrong_grant_and_reused_paths_fail_without_spending(tmp_path: Path) -> None:
    path = initialized(tmp_path)
    with pytest.raises(ledger.CampaignLedgerError, match="grant"):
        ledger.reserve_trial(
            path,
            execution_comment_id=COMMENT,
            execution_grant_sha256="4" * 64,
            trial_descriptor_sha256="5" * 64,
            frozen_checkout="/v1/immutable",
            receipt_path=tmp_path / "receipt-1.json",
            output_root=tmp_path / "output-1",
        )
    assert ledger.inspect_ledger(path)["trials"] == []
    one = reserve(path, 1)
    block(path, one)
    with pytest.raises(ledger.CampaignLedgerError, match="reuse"):
        ledger.reserve_trial(
            path,
            execution_comment_id=COMMENT,
            execution_grant_sha256=GRANT,
            trial_descriptor_sha256="5" * 64,
            frozen_checkout="/v1/immutable",
            receipt_path=tmp_path / "receipt-1.json",
            output_root=tmp_path / "output-new",
        )
    assert len(ledger.inspect_ledger(path)["trials"]) == 1


def test_ambiguous_cleanup_blocks_subsequent_reservation(tmp_path: Path) -> None:
    path = initialized(tmp_path)
    one = reserve(path, 1)
    block(path, one, cleanup=False)
    with pytest.raises(ledger.CampaignLedgerError, match="cleanup"):
        reserve(path, 2)


def test_exactly_eight_slots_and_no_extra_trial(tmp_path: Path) -> None:
    path = initialized(tmp_path)
    for n in range(1, 9):
        block(path, reserve(path, n))
    assert [t["trial_id"] for t in ledger.inspect_ledger(path)["trials"]] == [
        f"exp-{n:02d}" for n in range(1, 9)
    ]
    with pytest.raises(ledger.CampaignLedgerError, match="eight"):
        reserve(path, 9)


def test_strict_success_stops_exploration_and_requires_evidence(tmp_path: Path) -> None:
    path = initialized(tmp_path)
    one = reserve(path, 1)
    with pytest.raises(ledger.CampaignLedgerError, match="needs strict closure"):
        ledger.finalize_trial(
            path,
            reservation_id=one["reservation_id"],
            status="PASSED",
            queue_receipt_sha256=RECEIPT_SHA,
            evidence_manifest_sha256=EVIDENCE_SHA,
            cleanup_verified=True,
            zero_requests_verified=True,
            strict_closure_verified=False,
        )
    assert ledger.inspect_ledger(path)["trials"][0]["status"] == "RESERVED"
    ledger.finalize_trial(
        path,
        reservation_id=one["reservation_id"],
        status="PASSED",
        queue_receipt_sha256=RECEIPT_SHA,
        evidence_manifest_sha256=EVIDENCE_SHA,
        cleanup_verified=True,
        zero_requests_verified=True,
        strict_closure_verified=True,
    )
    with pytest.raises(ledger.CampaignLedgerError, match="first strict PASS"):
        reserve(path, 2)
    with pytest.raises(ledger.CampaignLedgerError, match="already written"):
        block(path, one)


def test_corrupted_ledger_fails_closed(tmp_path: Path) -> None:
    path = initialized(tmp_path)
    path.write_text('{"format_version": 99}')
    with pytest.raises(ledger.CampaignLedgerError, match="identity or schema"):
        reserve(path, 1)
    path.write_text("not-json")
    with pytest.raises(ledger.CampaignLedgerError, match="cannot be verified"):
        ledger.inspect_ledger(path)


def _concurrent_reserve(path: str, index: int, gate: multiprocessing.Event, results: multiprocessing.Queue) -> None:
    gate.wait(5)
    try:
        result = reserve(Path(path), index)
        results.put(("ok", result["trial_id"]))
    except ledger.CampaignLedgerError as exc:
        results.put(("blocked", str(exc)))


def test_concurrent_reservations_do_not_allocate_two_trials(tmp_path: Path) -> None:
    path = initialized(tmp_path)
    gate = multiprocessing.Event()
    results = multiprocessing.Queue()
    workers = [
        multiprocessing.Process(target=_concurrent_reserve, args=(str(path), n, gate, results))
        for n in (1, 2)
    ]
    for worker in workers:
        worker.start()
    gate.set()
    for worker in workers:
        worker.join(timeout=10)
        assert worker.exitcode == 0
    outcomes = [results.get(timeout=5) for _ in workers]
    assert sum(outcome[0] == "ok" for outcome in outcomes) == 1
    assert sum(outcome[0] == "blocked" for outcome in outcomes) == 1
    state = ledger.inspect_ledger(path)
    assert len(state["trials"]) == 1
    assert state["trials"][0]["trial_id"] == "exp-01"


def test_symlink_ledger_is_never_reset_or_followed(tmp_path: Path) -> None:
    path = initialized(tmp_path)
    alias = tmp_path / "alias.json"
    alias.symlink_to(path)
    with pytest.raises(ledger.CampaignLedgerError, match="not a regular"):
        ledger.inspect_ledger(alias)
    assert len(ledger.inspect_ledger(path)["trials"]) == 0
