"""Phase 6-B3 queue root path validation smoke."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from relaylm.relaymem_slp_queue_record import derive_job_id
from relaylm.relaymem_slp_queue_state import (
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)


def main() -> None:
    dispatch_key = "slp-dispatch-v0:" + "a" * 64
    request = RelayMEMSLPQueueTransitionRequest(
        transition_kind="claim",
        job_id=derive_job_id(dispatch_key),
        dispatch_idempotency_key=dispatch_key,
        expected_record_revision=0,
        expected_state="queued",
        claim_owner="worker-root-path",
        claim_generation=0,
        lease_token="",
        lease_duration_seconds=30,
        retry_class="unclassified",
        retry_not_before=None,
        failure_class="none",
        terminal_state="",
        terminal_reason_id="",
    )

    with TemporaryDirectory() as directory:
        parent = Path(directory).resolve()
        configured = parent / "configured"
        sibling = parent / "sibling"
        configured.mkdir()
        sibling.mkdir()
        parent_reference_root = str(configured / ".." / "sibling")

        result = transition_relaymem_slp_queue_state(
            request,
            queue_root=parent_reference_root,
            enabled=True,
            dry_run_only=True,
            apply_enabled=False,
        )
        assert result.status == "write_failed"
        assert "queue_root_parent_traversal_blocked" in result.blocked_reasons
        assert result.queue_io_performed is False
        assert list(sibling.iterdir()) == []

    print("Phase 6-B3 queue root path smoke: ok")


if __name__ == "__main__":
    main()
