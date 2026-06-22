#!/usr/bin/env python3
"""Validate the Phase 6-C1 worker contract's critical integration boundaries."""

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
        "relaymem.slp_primary_worker_source.v0",
        "The canonical B2/B3 durable queue record is intentionally content-free.",
        "M3a classifies whether governed evidence may produce a Primary MEM candidate. It is not a content extractor.",
        "If the process restarts and the exact protected source bundle is unavailable, the job must not execute from queue metadata alone.",
        "before M3e page publication",
        "before M3g index/log apply",
        "dispatch_idempotency_key",
        "memory-write idempotency key",
        "primary_reconciliation_apply_lock_unavailable",
        "retry_class = transient_lock_contention",
        "recovery_classification = retry_reconciliation",
        "failure_class = manual_confirmation_required",
        "failure_class = recovery_isolation_required",
        "Current B3 cannot generate `dead_letter`",
        "execute_relaymem_primary_pipeline",
        "C1-5 restart-complete protected source persistence",
    )

    require(
        text,
        "after M3e page publication and before M3f",
        "after M3g index publication and before log publication",
        "lease loss after side effect -> no stale terminal commit",
        "M3g exclusive-lock contention -> bounded retry release",
        "M3h shared-lock contention -> bounded retry release",
        "source-bundle unavailable after restart -> explicit safe block",
    )

    forbid(
        text,
        "reuse the dispatch key as the memory-write key",
        "reconstruct memory content from trace",
        "automatic retry for corruption",
        "RelaySLP directly mutates RelaySOUL",
    )

    print("RelayLM Phase 6-C1 worker contract smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
