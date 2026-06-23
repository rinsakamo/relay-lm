#!/usr/bin/env python3
"""Validate current Phase 6-C1 worker and restart boundaries."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/architecture/phase6c1_primary_mem_worker_contract.md"


def require(text: str, *anchors: str) -> None:
    missing = [anchor for anchor in anchors if anchor not in text]
    if missing:
        raise AssertionError(f"missing Phase 6-C1 contract anchors: {missing!r}")


def forbid(text: str, *anchors: str) -> None:
    present = [anchor for anchor in anchors if anchor in text]
    if present:
        raise AssertionError(f"forbidden Phase 6-C1 contract claims: {present!r}")


def main() -> int:
    text = CONTRACT.read_text(encoding="utf-8")

    require(
        text,
        "relaylm_doc_type: contract",
        "Phase 6-C1 is implemented through C1-5",
        "relaymem.slp_primary_worker_source.v0",
        "The canonical B2/B3 durable queue record is intentionally content-free.",
        "If neither the hot cache nor the exact durable artifact can supply the protected capture",
        "before M3e page publication",
        "before M3g index/log apply",
        "dispatch_idempotency_key",
        "memory-write idempotency key",
        "retry_class = transient_lock_contention",
        "retry_class = primary_reconciliation_retry",
        "manual_confirmation_required",
        "journaled_recovery_candidate",
        "dead_letter",
        "execute_relaymem_primary_pipeline",
        "C1-5",
        "durably enqueued jobs",
        "no automatic retry for corruption",
        "one-job queued-record claim/rehydrate/execute adapter",
    )

    require(
        text,
        "after M3e and before M3f",
        "after index publication and before log publication",
        "lease loss before/after side effect",
        "M3g/M3h lock contention",
        "missing/corrupt source isolation",
    )

    forbid(
        text,
        "The worker implementation is pending.",
        "The worker reuses the dispatch key as the memory-write key.",
        "The worker reconstructs memory content from trace.",
        "RelaySLP directly mutates RelaySOUL.",
        "C1-2 one-already-claimed-job worker execution is not yet on `main`",
    )

    print("RelayLM Phase 6-C1 worker contract smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
