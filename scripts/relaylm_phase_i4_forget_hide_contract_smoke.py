#!/usr/bin/env python3
"""Validate the stable Phase I-4A contract skeleton."""
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[1] / "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md"


def main() -> None:
    body = CONTRACT.read_text(encoding="utf-8")
    required = (
        "relaylm_doc_type: contract",
        "relaylm_authority: phase_i4_primary_mem_forget_hide",
        "relaylm_status: target",
        "# Phase I-4A: Auditable Primary MEM Forget / Hide Contract",
        "Decision: Candidate A",
        "relaylm.mem.primary_current_state.v0",
        "## 20. Implementation slices",
        "### I-4B — complete read-only boundary",
        "### I-4C1 — hidden-successor commit ownership",
        "### I-4C2 — exact replay and forward recovery",
        "### I-4D — convergence and exclusion",
        "### I-4E — loopback wrapper and UI",
        "### I-4F — production validation",
        "## 22. Explicit non-claims",
        "I1-G pre-enqueue durability",
    )
    missing = [anchor for anchor in required if anchor not in body]
    assert not missing, f"missing Phase I-4A contract anchors: {missing!r}"

    forbidden = (
        "relaylm_status: current",
        "Forget runtime is implemented",
        "physical deletion is performed",
    )
    present = [anchor for anchor in forbidden if anchor in body]
    assert not present, f"forbidden Phase I-4A claims present: {present!r}"
    print("RelayLM Phase I-4A Forget / Hide contract smoke passed.")


if __name__ == "__main__":
    main()
