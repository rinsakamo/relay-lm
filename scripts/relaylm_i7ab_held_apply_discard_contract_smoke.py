"""I-7A/B held Apply / Discard contract smoke."""
from __future__ import annotations

from relaylm.relaymem_held_governance_contract import HELD_OUTCOME_CANDIDATE_SCHEMA
from relaylm.relaymem_held_governance_preflight import (
    preflight_held_apply,
    preflight_held_discard,
)

SHA_A = "a" * 64


def _candidate(**updates):
    value = {
        "schema_version": HELD_OUTCOME_CANDIDATE_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "candidate_id": "held-candidate-smoke",
        "operation_id": "held-operation-smoke",
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


def _public(result):
    public = result.to_public_dict()
    serialized = repr(public)
    assert "SECRET_USER_TEXT" not in serialized
    assert "SECRET_MODEL_OUTPUT" not in serialized
    assert public["content_free"] is True
    assert public["runtime_private_evidence_omitted"] is True
    assert public["source_body_included"] is False
    assert public["model_output_included"] is False
    assert public["memory_content_included"] is False
    assert public["queue_payload_included"] is False
    assert public["queue_state_mutated"] is False
    assert public["primary_mem_mutated"] is False
    assert public["worker_started"] is False
    assert public["scheduler_started"] is False
    assert public["automatic_retry_or_release"] is False
    return public


def main() -> None:
    apply_ready = _public(preflight_held_apply(
        _candidate(),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ))
    assert apply_ready["status"] == "ready"
    assert apply_ready["schema_version"] == "relaylm.lab.held_apply_preflight.v0"
    assert apply_ready["effects"]["held_item_adopted_contract"] is True

    discard_ready = _public(preflight_held_discard(
        _candidate(),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ))
    assert discard_ready["status"] == "ready"
    assert discard_ready["schema_version"] == "relaylm.lab.held_discard_preflight.v0"
    assert discard_ready["effects"]["held_item_discarded_contract"] is True

    assert preflight_held_apply(
        _candidate(status="blocked"),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ).reason_code == "candidate_blocked_not_held"
    assert preflight_held_apply(
        _candidate(status="failed"),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ).reason_code == "candidate_failed_not_held"
    assert preflight_held_apply(
        _candidate(status="recovery_required"),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ).reason_code == "candidate_recovery_required_not_held"
    assert preflight_held_apply(
        _candidate(status="corrupt"),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ).reason_code == "candidate_corrupt_not_held"
    assert preflight_held_apply(
        _candidate(status="applied"),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ).reason_code == "already_applied"
    assert preflight_held_discard(
        _candidate(status="discarded"),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ).reason_code == "already_discarded"
    assert preflight_held_apply(
        _candidate(status="terminal_succeeded"),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ).reason_code == "candidate_terminal_succeeded"
    assert preflight_held_apply(
        _candidate(status="terminal_failed"),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ).reason_code == "candidate_terminal_failed"
    assert preflight_held_apply(
        _candidate(source_evidence_present=False),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ).reason_code == "source_evidence_missing"
    assert preflight_held_apply(
        _candidate(source_evidence_corrupt=True),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ).reason_code == "source_evidence_corrupt"
    assert preflight_held_apply(
        _candidate(character_id="char-b"),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ).reason_code == "wrong_character"
    assert preflight_held_apply(
        _candidate(namespace="ns-b"),
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ).reason_code == "wrong_namespace"

    bad = _candidate()
    bad["payload"] = "SECRET_USER_TEXT SECRET_MODEL_OUTPUT"
    _public(preflight_held_apply(
        bad,
        expected_character_id="char-a",
        expected_namespace="ns-a",
        expected_scope="primary_formation",
    ))

    print("I-7A/B held Apply / Discard contract smoke passed")


if __name__ == "__main__":
    main()
