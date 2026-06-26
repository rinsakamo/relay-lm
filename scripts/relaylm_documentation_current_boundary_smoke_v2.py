#!/usr/bin/env python3
"""Validate integrated I1-GD, O1B, and O1C documentation status."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, *anchors: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    missing = [anchor for anchor in anchors if anchor not in text]
    assert not missing, f"{path}: missing anchors: {missing!r}"


def main() -> None:
    require(
        "docs/PROJECT_STATUS.md",
        "I1-GD retention / orphan reconciliation / isolation lifecycle / cleanup: complete",
        "Scheduler replay lane: O1B one bounded sealed-record discovery/reread/I1-GC adapter complete",
        "Scheduler queue lane: O1C one bounded discovery/reread/scope/C2 adapter complete",
        "Scheduler remaining production: O1D through O1F unimplemented",
    )
    require(
        "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md",
        "### I1-GD — complete",
        "### O1B — complete",
        "### O1C — complete",
        "### O1D through O1F — unimplemented",
    )
    print("Integrated documentation boundary smoke passed")


if __name__ == "__main__":
    main()
