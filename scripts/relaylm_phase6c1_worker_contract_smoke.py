#!/usr/bin/env python3
"""Validate the current SLP claimed-worker and queued-job boundaries."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/contracts/slp/primary-worker.md"


def require(text: str, *anchors: str) -> None:
    missing = [anchor for anchor in anchors if anchor not in text]
    if missing:
        raise AssertionError(f"missing primary-worker contract anchors: {missing!r}")


def forbid(text: str, *anchors: str) -> None:
    present = [anchor for anchor in anchors if anchor in text]
    if present:
        raise AssertionError(f"forbidden primary-worker contract claims: {present!r}")


def main() -> int:
    text = CONTRACT.read_text(encoding="utf-8")

    require(
        text,
        "relaylm_doc_type: contract",
        "This contract owns the exact current Phase 6-C1 boundary",
        "relaymem.slp_primary_worker_source.v0",
        "content-free durable queue",
        "missing/corrupt durable source after restart fails closed",
        "before M3e publication checkpoint",
        "before M3g reconciliation apply checkpoint",
        "dispatch_idempotency_key",
        "memory-write idempotency",
        "transient resource contention",
        "verified reconciliation partial progress",
        "manual confirmation",
        "uncertain/corrupt/diverged store state",
        "RelayMEM Primary compose function",
        "never become terminal success",
        "C2/runner/scheduler layers remain separate",
    )

    require(
        text,
        "before M3g reconciliation apply checkpoint",
        "after index publication before log publication",
        "Lease loss prevents new stale-worker effects",
        "M3g index-before-log apply",
        "missing/corrupt durable source after restart fails closed",
    )

    forbid(
        text,
        "The worker implementation is pending.",
        "The worker reuses the dispatch key as the memory-write key.",
        "The worker reconstructs memory content from trace.",
        "RelaySLP directly mutates RelaySOUL.",
        "C1-2 one-already-claimed-job worker execution is not yet on `main`",
    )

    print("RelayLM primary-worker contract smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
