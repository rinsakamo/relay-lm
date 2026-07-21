#!/usr/bin/env python3
"""Pin the Subjective MEM storage-authority and commit-finalization boundary."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs/adr/0005-subjective-mem-storage-authority.md"
CONTRACT = ROOT / "docs/contracts/subjective-mem-storage-authority-and-commit-protocol.md"
INDEX = ROOT / "docs/contracts/README.md"

ADR_REQUIRED = (
    "relaylm_authority: decision_to_adopt_subjective_mem_storage_authority",
    "relaylm_decision_status: accepted",
    "Markdown owns committed Subjective MEM content and canonical lifecycle-visible state.",
    "A matching durable operations receipt finalizes publication but does not own memory semantics.",
    "Rebuildable cache state is never canonical merely because it persists.",
    "Operations state owns non-rebuildable operational facts, not a second memory body or lifecycle representation.",
    "Recovery is digest- and revision-driven and fails closed on a foreign image.",
    "PR #578 remains experiment evidence and is not merged as production code.",
)

CONTRACT_REQUIRED = (
    "relaylm_authority: subjective_mem_storage_authority_commit_finalization_and_recovery_contract",
    "This is the normative **target logical contract**",
    "A projection is rebuildable and disposable.",
    "It never owns a second editable memory body, second current-revision selector, or second canonical lifecycle representation.",
    "The receipt is the commit-finalization marker. Markdown remains the semantic and lifecycle authority.",
    "A canonical post-image without its receipt is `recovery_pending`, not normally published.",
    "Recovery must not call an LLM or re-run subjective formation to invent a replacement post-image.",
    "### Current digest equals the pre-image",
    "### Current digest equals the post-image",
    "### Current digest equals neither image",
    "Forget publishes a new canonical hidden successor",
    "Restore publishes a new canonical active successor",
    "Purge is not an ordinary reversible lifecycle transition.",
    "Permanent dual-read, dual-write, precedence fallback, or conflict resolution between two live canonical stores is prohibited.",
    "No platform is implied supported by this target contract alone.",
    "- treating the rebuildable projection as canonical.",
)

INDEX_REQUIRED = (
    "[Subjective MEM Storage Authority and Commit Protocol Contract](subjective-mem-storage-authority-and-commit-protocol.md)",
    "Markdown owns committed memory semantics and lifecycle-visible state while a matching operations receipt finalizes publication",
    "treats PR #578 as feasibility evidence only",
)

FORBIDDEN = (
    "../architecture/phase_i4e_primary_restore_apply.md",
    "Restore remains a canonical lifecycle state",
    "SQLite owns committed Subjective MEM content",
    "cache refresh is the semantic commit event",
    "PR #578 is production authority",
)


def validate(adr: str, contract: str, index: str) -> list[str]:
    failures: list[str] = []
    for marker in ADR_REQUIRED:
        if marker not in adr:
            failures.append(f"ADR missing authority marker: {marker}")
    for marker in CONTRACT_REQUIRED:
        if marker not in contract:
            failures.append(f"contract missing authority marker: {marker}")
    for marker in INDEX_REQUIRED:
        if marker not in index:
            failures.append(f"contract index missing marker: {marker}")
    for marker in FORBIDDEN:
        if marker in adr or marker in contract or marker in index:
            failures.append(f"retired or contradictory marker present: {marker}")

    authority_order = (
        "### Canonical memory documents",
        "### Rebuildable projection",
        "### Durable operations ledger",
        "### Governed evidence authority",
    )
    positions = [contract.find(marker) for marker in authority_order]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        failures.append("storage authority classes are missing or out of order")

    recovery_order = (
        "### Current digest equals the pre-image",
        "### Current digest equals the post-image",
        "### Current digest equals neither image",
        "### Receipt exists but post-image is unverifiable",
    )
    positions = [contract.find(marker) for marker in recovery_order]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        failures.append("recovery outcomes are missing or out of order")

    if "operation_kind: create | correct | forget | restore | consolidate | pin | unpin" not in contract:
        failures.append("prepared-intent operation taxonomy drift")
    if contract.count("Projection refresh is not the semantic commit event.") != 1:
        failures.append("projection non-authority statement is missing or duplicated")
    if "A complete authoritative backup must include canonical Markdown and the durable operations store." not in adr:
        failures.append("ADR backup authority pair is missing")
    if "An authoritative backup set includes:" not in contract:
        failures.append("contract backup boundary is missing")
    return failures


def self_test(adr: str, contract: str, index: str) -> list[str]:
    failures: list[str] = []
    probes = (
        (
            adr.replace(
                "A matching durable operations receipt finalizes publication but does not own memory semantics.",
                "The cache finalizes publication.",
            ),
            contract,
            index,
            "ADR receipt authority drift",
        ),
        (
            adr,
            contract.replace(
                "The receipt is the commit-finalization marker. Markdown remains the semantic and lifecycle authority.",
                "The operations database is the semantic authority.",
            ),
            index,
            "contract semantic-authority drift",
        ),
        (
            adr,
            contract.replace("### Current digest equals neither image", "### Unknown recovery result"),
            index,
            "foreign-image recovery removal",
        ),
        (
            adr,
            contract,
            index.replace(
                "[Subjective MEM Storage Authority and Commit Protocol Contract](subjective-mem-storage-authority-and-commit-protocol.md)",
                "Subjective MEM storage notes",
            ),
            "contract index unlink",
        ),
    )
    for mutated_adr, mutated_contract, mutated_index, label in probes:
        if not validate(mutated_adr, mutated_contract, mutated_index):
            failures.append(f"self-test failed to detect {label}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    adr = ADR.read_text(encoding="utf-8")
    contract = CONTRACT.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    failures = validate(adr, contract, index)
    if args.self_test:
        failures.extend(self_test(adr, contract, index))
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1
    suffix = " + self-test" if args.self_test else ""
    print(f"subjective-mem storage authority contract{suffix}: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
