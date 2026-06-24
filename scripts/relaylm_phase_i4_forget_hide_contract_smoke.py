#!/usr/bin/env python3
"""Validate the Phase I-4A Forget / Hide documentation contract only."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require(body: str, *anchors: str) -> None:
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"missing Phase I-4A contract anchors: {missing!r}"


def forbid(body: str, *anchors: str) -> None:
    present = [anchor for anchor in anchors if anchor in body]
    assert not present, f"forbidden Phase I-4A claims present: {present!r}"


def main() -> None:
    body = read(CONTRACT)
    require(
        body,
        "relaylm_doc_type: contract",
        "relaylm_authority: phase_i4_primary_mem_forget_hide",
        "relaylm_status: target",
        "Defined target contract; runtime unimplemented.",
        "**Forget**",
        "**`hidden`**",
        "**Forget tombstone**",
        "Decision: Candidate A",
        "Rejected: Candidate B as independent authority",
        "relaylm.mem.primary_current_state.v0",
        "revision 2 active\n  -> Forget\nrevision 3 hidden",
        "/forget/preflight?namespace=...",
        "/forget?namespace=...",
        "/forget-history?namespace=...",
        "relaylm.lab.memory_forget_preflight_request.v0",
        "relaylm.lab.memory_forget_preflight.v0",
        "relaylm.lab.memory_forget_apply_request.v0",
        "relaylm.lab.memory_forget_apply.v0",
        "relaylm.lab.memory_forget_history.v0",
        "relaylm.mem.forget_prepared.v0",
        "relaylm.mem.forget_tombstone.v0",
        "expected_lifecycle_state: active",
        "target_lifecycle_state: hidden",
        "ordinary_retrieval_excluded: true",
        "physical_deletion: false",
        "historical_used_memory_unchanged: true",
        "already_hidden",
        "response_lost",
        "after index apply / before log apply",
        "I-4B — resolver, shared fence, and read-only contracts",
        "I-4C — atomic lifecycle apply and audit artifacts",
        "I-4D — convergence, M2 exclusion, and historical projection",
        "I-4E — loopback wrapper and SOUL Lab UI",
        "I-4F — fault, security, and fresh-conversation validation",
        "restore or unhide",
        "GDPR, privacy-law, or other legal erasure compliance",
        "I1-G pre-enqueue durability",
    )
    forbid(
        body,
        "relaylm_status: current",
        "Forget runtime is implemented",
        "physical deletion is performed",
        "restore is implemented",
    )
    print("RelayLM Phase I-4A Forget / Hide contract smoke passed.")


if __name__ == "__main__":
    main()
