#!/usr/bin/env python3
"""Validate the Phase I-4A target contract and completed I-4B foundation."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md"


def require(body: str, *anchors: str) -> None:
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"missing Phase I-4A contract anchors: {missing!r}"


def forbid(body: str, *anchors: str) -> None:
    present = [anchor for anchor in anchors if anchor in body]
    assert not present, f"forbidden Phase I-4A claims present: {present!r}"


def main() -> None:
    body = CONTRACT.read_text(encoding="utf-8")
    require(
        body,
        "relaylm_doc_type: contract",
        "relaylm_authority: phase_i4_primary_mem_forget_hide",
        "relaylm_status: target",
        "Defined target contract; hidden-lifecycle apply remains unimplemented.",
        "Forget            user-facing explicit operation",
        "hidden            canonical current retrieval-ineligible lifecycle state",
        "Forget tombstone  immutable runtime-private audit/recovery artifact",
        "Decision: Candidate A",
        "A bare sidecar boolean",
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
        "I-4B — complete read-only boundary",
        "I-4C1 — hidden-successor commit ownership",
        "I-4C2 — exact replay and forward recovery",
        "I-4D — convergence and exclusion",
        "I-4E — loopback wrapper and UI",
        "I-4F — production validation",
        "restore",
        "unhide",
        "GDPR, privacy-law, or other legal-erasure compliance",
        "I1-G pre-enqueue durability",
        "I-4B validation proves only the read-only resolver/shared-fence/preflight-token-history boundary",
    )
    forbid(
        body,
        "relaylm_status: current",
        "Forget runtime is implemented",
        "physical deletion is performed",
        "restore is implemented",
        "production hidden-successor apply or tombstone finalization;\n- production M2/RelayCTX hidden-state exclusion;\n- loopback mutation routes or SOUL Lab Forget UI;\n\n## Completed",
    )
    print("RelayLM Phase I-4A Forget / Hide contract smoke passed.")


if __name__ == "__main__":
    main()
