"""Characterization: RelaySLP durable queue enqueue (B2) and lifecycle (B3).

Locks the currently implemented invariants:

- re-running the same eligible B2 enqueue never duplicates the durable queue
  record (``duplicate_existing``);
- the dispatch idempotency key binds the namespace, so identical work in two
  namespaces produces two distinct durable records;
- B3 transitions are fenced by record revision, expected state, claim owner,
  claim generation, and lease token;
- terminal queue states are immutable ("already-finalized work is not
  applied again");
- a failure before the durable apply leaves the queue unchanged;
- non-exact inputs (plain dicts, tampered preflight results) fail closed and
  never gain enqueue/transition authority.
"""
from __future__ import annotations

import os

import pytest

from _relaymem_characterization_support import (
    build_dispatch_preflight_ready,
    enqueue_durable_job,
    queue_files,
)
from relaylm.relaymem_slp_durable_enqueue import enqueue_relaymem_slp_durable_job
from relaylm.relaymem_slp_queue_state import (
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)

NAMESPACE = "characterization-ns-a"
OTHER_NAMESPACE = "characterization-ns-b"


@pytest.fixture()
def queue_root(tmp_path):
    root = tmp_path / "queue"
    root.mkdir()
    return root


def _enqueued_record(queue_root, *, namespace=NAMESPACE, run_id="run-b2-1"):
    _, _, dispatch = build_dispatch_preflight_ready(namespace=namespace, run_id=run_id)
    result = enqueue_durable_job(dispatch, queue_root)
    assert result.status == "enqueued_new", result.blocked_reasons
    assert type(result.durable_record) is dict
    return dispatch, dict(result.durable_record)


def _transition(queue_root, request):
    return transition_relaymem_slp_queue_state(
        request,
        queue_root=str(queue_root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )


def _claim(queue_root, record, *, owner="worker-a", lease_seconds=300):
    return _transition(
        queue_root,
        RelayMEMSLPQueueTransitionRequest(
            transition_kind="claim",
            job_id=str(record["job_id"]),
            dispatch_idempotency_key=str(record["dispatch_idempotency_key"]),
            expected_record_revision=int(record["record_revision"]),
            expected_state=str(record["state"]),
            claim_owner=owner,
            claim_generation=int(record["claim_generation"]),
            lease_duration_seconds=lease_seconds,
        ),
    )


class TestDurableEnqueueIdempotency:
    def test_reenqueue_of_same_eligible_work_does_not_duplicate(self, queue_root):
        dispatch, record = _enqueued_record(queue_root)
        assert len(queue_files(queue_root)) == 1

        replay = enqueue_durable_job(dispatch, queue_root)
        assert replay.status == "duplicate_existing"
        assert replay.duplicate_detected is True
        assert replay.enqueue_applied is False
        assert len(queue_files(queue_root)) == 1
        # The surviving record is byte-for-byte the original one.
        assert replay.durable_record == record

    def test_rebuilt_identical_chain_still_deduplicates(self, queue_root):
        _enqueued_record(queue_root, run_id="run-b2-2")
        # A fresh A1/A2/B1 composition of the same finalized turn derives the
        # same dispatch idempotency key, so the durable effect stays single.
        _, _, dispatch = build_dispatch_preflight_ready(
            namespace=NAMESPACE, run_id="run-b2-2"
        )
        replay = enqueue_durable_job(dispatch, queue_root)
        assert replay.status == "duplicate_existing"
        assert len(queue_files(queue_root)) == 1

    def test_namespace_is_bound_into_dispatch_identity(self, queue_root):
        _, record_a = _enqueued_record(queue_root, namespace=NAMESPACE, run_id="run-ns")
        _, record_b = _enqueued_record(
            queue_root, namespace=OTHER_NAMESPACE, run_id="run-ns"
        )
        assert record_a["dispatch_idempotency_key"] != record_b["dispatch_idempotency_key"]
        assert record_a["job_id"] != record_b["job_id"]
        assert record_a["namespace"] == NAMESPACE
        assert record_b["namespace"] == OTHER_NAMESPACE
        assert len(queue_files(queue_root)) == 2

    def test_enqueue_failure_before_durable_apply_leaves_queue_unchanged(
        self, queue_root, monkeypatch
    ):
        import relaylm.relaymem_slp_queue_storage as queue_storage

        _, _, dispatch = build_dispatch_preflight_ready(
            namespace=NAMESPACE, run_id="run-fault"
        )
        original_open = os.open

        def fail_record_create(path, flags, *args, **kwargs):
            if os.O_EXCL & flags and str(path).endswith(".json"):
                raise OSError("characterization injected create failure")
            return original_open(path, flags, *args, **kwargs)

        monkeypatch.setattr(queue_storage.os, "open", fail_record_create)
        result = enqueue_durable_job(dispatch, queue_root)
        monkeypatch.undo()

        assert result.status == "write_failed"
        assert result.enqueue_applied is False
        assert queue_files(queue_root) == []
        # The same work remains eligible afterwards.
        retry = enqueue_durable_job(dispatch, queue_root)
        assert retry.status == "enqueued_new"

    def test_review_required_policy_is_held_before_any_queue_io(self, queue_root):
        admission, handoff, dispatch = build_dispatch_preflight_ready(
            namespace=NAMESPACE,
            run_id="run-held",
            persistence_policy_status="review_required",
        )
        assert admission["admission_status"] == "held"
        assert "persistence_policy_requires_review" in admission["blocked_reasons"]
        assert handoff.status == "held"
        # A held admission never produces a durable job candidate, so nothing
        # downstream can enqueue it.
        assert dispatch.durable_job is None
        result = enqueue_durable_job(dispatch, queue_root)
        assert result.status == "invalid_input"
        assert queue_files(queue_root) == []

    def test_unknown_persistence_policy_fails_closed(self, queue_root):
        admission, _, dispatch = build_dispatch_preflight_ready(
            namespace=NAMESPACE,
            run_id="run-unknown-policy",
            persistence_policy_status="totally_new_policy",
        )
        assert admission["admission_status"] == "blocked"
        assert "persistence_policy_status_invalid" in admission["blocked_reasons"]
        assert dispatch.durable_job is None

    def test_plain_dict_preflight_never_gains_enqueue_authority(self, queue_root):
        _, _, dispatch = build_dispatch_preflight_ready(
            namespace=NAMESPACE, run_id="run-authority"
        )
        forged = dict(dispatch.to_runtime_dict())
        result = enqueue_relaymem_slp_durable_job(
            forged,
            queue_root=str(queue_root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        assert result.status == "invalid_input"
        assert "exact_b1_preflight_result_required" in result.blocked_reasons
        assert queue_files(queue_root) == []


class TestQueueLifecycleFencing:
    def test_claim_then_stale_claim_conflicts(self, queue_root):
        _, record = _enqueued_record(queue_root)
        first = _claim(queue_root, record)
        assert first.status == "applied"
        assert first.durable_record["state"] == "claimed"
        assert first.durable_record["claim_owner"] == "worker-a"

        # A second claimer holding the original queued snapshot loses on the
        # revision fence; the winning claim is untouched.
        second = _claim(queue_root, record, owner="worker-b")
        assert second.status == "conflict"
        assert "record_revision_mismatch" in second.blocked_reasons

    def test_commit_terminal_requires_exact_claim_fence(self, queue_root):
        _, record = _enqueued_record(queue_root)
        claimed = _claim(queue_root, record).durable_record

        forged = RelayMEMSLPQueueTransitionRequest(
            transition_kind="commit_terminal",
            job_id=str(claimed["job_id"]),
            dispatch_idempotency_key=str(claimed["dispatch_idempotency_key"]),
            expected_record_revision=int(claimed["record_revision"]),
            expected_state="claimed",
            claim_owner=str(claimed["claim_owner"]),
            claim_generation=int(claimed["claim_generation"]),
            lease_token="not-the-issued-lease-token",
            terminal_state="succeeded",
            terminal_reason_id="worker_reported_success",
        )
        result = _transition(queue_root, forged)
        assert result.status == "conflict"
        assert "lease_token_mismatch" in result.blocked_reasons

    def test_terminal_state_is_immutable(self, queue_root):
        _, record = _enqueued_record(queue_root)
        claimed = _claim(queue_root, record).durable_record
        done = _transition(
            queue_root,
            RelayMEMSLPQueueTransitionRequest(
                transition_kind="commit_terminal",
                job_id=str(claimed["job_id"]),
                dispatch_idempotency_key=str(claimed["dispatch_idempotency_key"]),
                expected_record_revision=int(claimed["record_revision"]),
                expected_state="claimed",
                claim_owner=str(claimed["claim_owner"]),
                claim_generation=int(claimed["claim_generation"]),
                lease_token=str(claimed["lease_token"]),
                terminal_state="succeeded",
                terminal_reason_id="worker_reported_success",
            ),
        )
        assert done.status == "applied"
        final = done.durable_record
        assert final["state"] == "succeeded"

        # A claim request can only legally name "queued"; the durable record's
        # terminal state is checked before every other fence and stays
        # immutable no matter what revision the caller presents.
        replay = _transition(
            queue_root,
            RelayMEMSLPQueueTransitionRequest(
                transition_kind="claim",
                job_id=str(final["job_id"]),
                dispatch_idempotency_key=str(final["dispatch_idempotency_key"]),
                expected_record_revision=int(final["record_revision"]),
                expected_state="queued",
                claim_owner="worker-late",
                claim_generation=int(final["claim_generation"]),
                lease_duration_seconds=300,
            ),
        )
        assert replay.status == "blocked"
        assert "terminal_state_immutable" in replay.blocked_reasons

    def test_stale_recovery_is_refused_while_lease_is_active(self, queue_root):
        _, record = _enqueued_record(queue_root)
        claimed = _claim(queue_root, record).durable_record
        result = _transition(
            queue_root,
            RelayMEMSLPQueueTransitionRequest(
                transition_kind="stale_recovery",
                job_id=str(claimed["job_id"]),
                dispatch_idempotency_key=str(claimed["dispatch_idempotency_key"]),
                expected_record_revision=int(claimed["record_revision"]),
                expected_state="claimed",
                claim_generation=int(claimed["claim_generation"]),
                lease_token=str(claimed["lease_token"]),
            ),
        )
        assert result.status == "not_ready"
        assert "stale_lease_not_expired" in result.blocked_reasons

    def test_plain_dict_request_never_gains_transition_authority(self, queue_root):
        _, record = _enqueued_record(queue_root)
        request = RelayMEMSLPQueueTransitionRequest(
            transition_kind="claim",
            job_id=str(record["job_id"]),
            dispatch_idempotency_key=str(record["dispatch_idempotency_key"]),
            expected_record_revision=int(record["record_revision"]),
            expected_state="queued",
            lease_duration_seconds=300,
        )
        result = _transition(queue_root, request.to_runtime_dict())
        assert result.status == "invalid_input"
        assert result.transition_applied is False
