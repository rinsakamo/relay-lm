"""Phase I-7C held governance runtime smoke."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from relaylm.relaymem_held_governance import (
    apply_held_governance_decision,
    discard_held_candidate,
    list_held_governance_history,
    persist_held_candidate_evidence,
    preflight_held_governance_decision,
)
from relaylm.relaymem_held_governance_contract import HELD_OUTCOME_CANDIDATE_SCHEMA

SHA_A = "a" * 64
CHARACTER = "char-a"
NAMESPACE = "ns-a"
SCOPE = "primary_formation"
CANARY = "SECRET_USER_TEXT SECRET_MODEL_OUTPUT SECRET_MEMORY_CANDIDATE"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def candidate(candidate_id: str = "held-candidate-smoke", **updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": HELD_OUTCOME_CANDIDATE_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "candidate_id": candidate_id,
        "operation_id": "worker-op-smoke",
        "character_id": CHARACTER,
        "namespace": NAMESPACE,
        "scope": SCOPE,
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


def assert_public_safe(value: dict[str, object]) -> None:
    serialized = json.dumps(value, sort_keys=True)
    for forbidden in (
        CANARY,
        "source_evidence_digest",
        "candidate_digest",
        "reason_digest",
        "token_digest",
        "source_path",
        "protected_source",
    ):
        require(forbidden not in serialized, forbidden)
    require(value["content_free"] is True, value)
    require(value["runtime_private_evidence_omitted"] is True, value)
    require(value["source_body_included"] is False, value)
    require(value["model_output_included"] is False, value)
    require(value["memory_content_included"] is False, value)
    require(value["queue_payload_included"] is False, value)
    require(value["queue_state_mutated"] is False, value)
    require(value["primary_mem_mutated"] is False, value)
    require(value["worker_started"] is False, value)
    require(value["scheduler_started"] is False, value)
    require(value["automatic_retry_or_release"] is False, value)


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        persist_held_candidate_evidence(root, candidate())
        preflight = preflight_held_governance_decision(
            root,
            candidate_id="held-candidate-smoke",
            action="apply",
            expected_character_id=CHARACTER,
            expected_namespace=NAMESPACE,
            expected_scope=SCOPE,
            operation_id="i7c-apply-op",
            reason="operator reviewed held outcome",
        )
        assert_public_safe(preflight)
        require(preflight["schema"] == "relaylm.lab.held_governance_preflight.v0", preflight)
        require(preflight["status"] == "ready", preflight)
        require(isinstance(preflight["apply_token"], str), preflight)
        token = str(preflight["apply_token"])

        applied = apply_held_governance_decision(
            root,
            candidate_id="held-candidate-smoke",
            action="apply",
            expected_character_id=CHARACTER,
            expected_namespace=NAMESPACE,
            expected_scope=SCOPE,
            operation_id="i7c-apply-op",
            reason="operator reviewed held outcome",
            apply_token=token,
        )
        assert_public_safe(applied)
        require(applied["schema"] == "relaylm.lab.held_governance_receipt.v0", applied)
        require(applied["status"] == "applied", applied)
        require(applied["idempotent_replay"] is False, applied)

        replay = apply_held_governance_decision(
            root,
            candidate_id="held-candidate-smoke",
            action="apply",
            expected_character_id=CHARACTER,
            expected_namespace=NAMESPACE,
            expected_scope=SCOPE,
            operation_id="i7c-apply-op",
            reason="operator reviewed held outcome",
            apply_token=token,
        )
        assert_public_safe(replay)
        require(replay["status"] == "already_applied", replay)
        require(replay["idempotent_replay"] is True, replay)

        conflict = preflight_held_governance_decision(
            root,
            candidate_id="held-candidate-smoke",
            action="discard",
            expected_character_id=CHARACTER,
            expected_namespace=NAMESPACE,
            expected_scope=SCOPE,
            operation_id="i7c-discard-after-apply",
            reason="conflicting action",
        )
        assert_public_safe(conflict)
        require(conflict["status"] == "operation_conflict", conflict)

        persist_held_candidate_evidence(root, candidate("held-candidate-discard"))
        discard_pf = preflight_held_governance_decision(
            root,
            candidate_id="held-candidate-discard",
            action="discard",
            expected_character_id=CHARACTER,
            expected_namespace=NAMESPACE,
            operation_id="i7c-discard-op",
            reason="discard held outcome",
        )
        require(discard_pf["status"] == "ready", discard_pf)
        discarded = discard_held_candidate(
            root,
            candidate_id="held-candidate-discard",
            expected_character_id=CHARACTER,
            expected_namespace=NAMESPACE,
            operation_id="i7c-discard-op",
            reason="discard held outcome",
            apply_token=str(discard_pf["apply_token"]),
        )
        assert_public_safe(discarded)
        require(discarded["status"] == "discarded", discarded)

        history = list_held_governance_history(root, candidate_id="held-candidate-discard")
        serialized_history = json.dumps(history, sort_keys=True)
        require(history["schema"] == "relaylm.lab.held_governance_history.v0", history)
        require(history["count"] == 1, history)
        require(CANARY not in serialized_history, history)

    print("Phase I-7C held governance runtime smoke passed")


if __name__ == "__main__":
    main()
