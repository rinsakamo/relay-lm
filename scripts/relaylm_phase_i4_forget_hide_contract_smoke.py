#!/usr/bin/env python3
"""Validate stable Phase I-4A target semantics."""
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[1] / "docs/architecture/phase_i4_primary_mem_forget_hide_contract.md"


def main() -> None:
    body = CONTRACT.read_text(encoding="utf-8")
    required = (
        "relaylm_status: target",
        "Explicit user operation targeting one exact current active logical memory.",
        "Durable current lifecycle state produced by successful Forget.",
        "Immutable runtime-private audit/recovery artifact proving the exact active-to-hidden transition and convergence.",
        "Decision: Candidate A",
        "relaylm.mem.primary_current_state.v0",
        "No Correct and Forget operation may both consume the same current revision.",
        "relaylm.lab.memory_forget_preflight_request.v0",
        "relaylm.lab.memory_forget_apply_request.v0",
        "relaylm.lab.memory_forget_history.v0",
        "## 19. Fault matrix",
        "after prepared artifact",
        "after hidden successor",
        "after index / before log",
        "### I-4B — complete read-only boundary",
        "### I-4C1 — hidden-successor commit ownership",
        "### I-4C2 — exact replay and forward recovery",
        "### I-4D — convergence and exclusion",
        "### I-4E — loopback wrapper and UI",
        "### I-4F — production validation",
        "I-4B validation proves only the read-only resolver/shared-fence/preflight-token-history boundary.",
        "## 22. Explicit non-claims",
    )
    missing = [anchor for anchor in required if anchor not in body]
    assert not missing, f"missing Phase I-4A contract anchors: {missing!r}"
    assert "relaylm_status: current" not in body
    print("RelayLM Phase I-4A Forget / Hide contract smoke passed.")


if __name__ == "__main__":
    main()
