#!/usr/bin/env python3
"""Validate stable Phase I-4A target semantics and the I-4B boundary."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md"


def main() -> None:
    body = CONTRACT.read_text(encoding="utf-8")
    required = (
        "relaylm_doc_type: contract",
        "relaylm_authority: phase_i4_primary_mem_forget_hide",
        "relaylm_status: target",
        "Defined target contract; hidden-lifecycle apply remains unimplemented.",
        "Decision: Candidate A",
        "relaylm.mem.primary_current_state.v0",
        "The hidden successor page is lifecycle authority.",
        "The tombstone is audit/recovery evidence",
        "No Correct and Forget operation may both consume the same current revision.",
        "### I-4B — complete read-only boundary",
        "### I-4C1 — hidden-successor commit ownership",
        "### I-4C2 — exact replay and forward recovery",
        "### I-4D — convergence and exclusion",
        "### I-4E — loopback wrapper and UI",
        "### I-4F — production validation",
        "I-4D is the user-visible semantic commit.",
        "production hidden-successor apply or tombstone finalization",
        "production M2/RelayCTX hidden-state exclusion",
        "loopback mutation routes or SOUL Lab Forget UI",
        "GDPR, privacy-law, or other legal-erasure compliance",
        "I1-G pre-enqueue durability",
    )
    missing = [anchor for anchor in required if anchor not in body]
    assert not missing, f"missing Phase I-4A contract anchors: {missing!r}"

    forbidden = (
        "relaylm_status: current",
        "Forget runtime is implemented",
        "physical deletion is performed",
        "restore is implemented",
    )
    present = [anchor for anchor in forbidden if anchor in body]
    assert not present, f"forbidden Phase I-4A claims present: {present!r}"
    print("RelayLM Phase I-4A Forget / Hide contract smoke passed.")


if __name__ == "__main__":
    main()
