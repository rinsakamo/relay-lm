#!/usr/bin/env python3
"""Validate stable Phase I-4A contract semantics after I-4F completion."""
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[1] / "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md"


def main() -> None:
    body = CONTRACT.read_text(encoding="utf-8")
    required = (
        "relaylm_status: current",
        "Current master contract. Phase I-4 is complete through I-4F.",
        "Explicit user operation targeting one exact current active logical memory.",
        "Durable current lifecycle state produced by successful Forget.",
        "Immutable runtime-private audit/recovery artifact proving the exact active-to-hidden transition and convergence.",
        "relaylm.mem.primary_current_state.v0",
        "No Correct and Forget operation may both consume the same current revision.",
        "relaylm.lab.memory_forget_preflight_request.v0",
        "relaylm.lab.memory_forget_apply_request.v0",
        "relaylm.lab.memory_forget_history.v0",
        "## 12. Fault matrix",
        "after prepared artifact",
        "after hidden successor",
        "after index / before log",
        "I-4B — complete read-only boundary",
        "I-4C1 — complete hidden-successor commit ownership",
        "I-4C2 — complete exact replay and forward recovery",
        "I-4D — complete convergence and exclusion",
        "I-4E — complete loopback wrapper and UI",
        "I-4F — complete production validation",
        "## 14. Explicit non-claims",
    )
    missing = [anchor for anchor in required if anchor not in body]
    assert not missing, f"missing Phase I-4A contract anchors: {missing!r}"
    assert "I-4E remains unimplemented" not in body
    assert "I-4F remains unimplemented" not in body
    print("RelayLM Phase I-4A Forget / Hide contract smoke passed.")


if __name__ == "__main__":
    main()
