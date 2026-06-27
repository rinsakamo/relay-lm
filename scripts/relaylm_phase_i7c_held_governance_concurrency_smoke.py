"""Phase I-7C held governance conflict/concurrency smoke."""
from __future__ import annotations

import tempfile

from relaylm.relaymem_held_governance import (
    apply_held_governance_decision,
    persist_held_candidate_evidence,
    preflight_held_governance_decision,
)
from relaylm.relaymem_held_governance_contract import HELD_OUTCOME_CANDIDATE_SCHEMA

SHA_A = "a" * 64
SHA_B = "b" * 64


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def candidate(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": HELD_OUTCOME_CANDIDATE_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "candidate_id": "held-race-candidate",
        "operation_id": "worker-op-race",
        "character_id": "char-a",
        "namespace": "ns-a",
        "scope": "primary_formation",
        "status": "held",
        "queue_state": "claimed",
        "source_authority": "primary_worker_outcome",
        "source_evidence_digest": SHA_A,
        "source_evidence_present": True,
        "source_evidence_corrupt": False,
        "source_evidence_ambiguous": False,
        "source_content_included": False,
        "related_primary_memory_id": None,
        "related_primary_expected_revision": None,
        "related_primary_physical_id": None,
    }
    value.update(updates)
    return value


def preflight(root: str, op: str) -> dict[str, object]:
    return preflight_held_governance_decision(
        root,
        candidate_id="held-race-candidate",
        action="apply",
        expected_character_id="char-a",
        expected_namespace="ns-a",
        operation_id=op,
        reason="bounded race reason",
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as root:
        persist_held_candidate_evidence(root, candidate())
        a = preflight(root, "i7c-race-a")
        b = preflight(root, "i7c-race-b")
        require(a["status"] == b["status"] == "ready", (a, b))
        winner = apply_held_governance_decision(
            root,
            candidate_id="held-race-candidate",
            action="apply",
            expected_character_id="char-a",
            expected_namespace="ns-a",
            operation_id="i7c-race-a",
            reason="bounded race reason",
            apply_token=str(a["apply_token"]),
        )
        require(winner["status"] == "applied", winner)
        loser = apply_held_governance_decision(
            root,
            candidate_id="held-race-candidate",
            action="apply",
            expected_character_id="char-a",
            expected_namespace="ns-a",
            operation_id="i7c-race-b",
            reason="bounded race reason",
            apply_token=str(b["apply_token"]),
        )
        require(loser["status"] == "operation_conflict", loser)

        persist_held_candidate_evidence(root, candidate(source_evidence_digest=SHA_B))
        stale = preflight(root, "i7c-race-a")
        require(stale["status"] == "stale_candidate", stale)
        require(stale["source_body_included"] is False, stale)

    print("Phase I-7C held governance concurrency smoke passed")


if __name__ == "__main__":
    main()
