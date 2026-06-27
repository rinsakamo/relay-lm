"""Phase I-7C public projection leakage/security smoke."""
from __future__ import annotations

import json
import tempfile

from relaylm.relaymem_held_governance import (
    HeldGovernanceRuntimeError,
    persist_held_candidate_evidence,
    preflight_held_governance_decision,
)
from relaylm.relaymem_held_governance_contract import HELD_OUTCOME_CANDIDATE_SCHEMA

SHA_A = "a" * 64
SECRET = "SECRET_USER_TEXT SECRET_MODEL_OUTPUT SECRET_MEMORY_CANDIDATE SECRET_QUEUE_PAYLOAD"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def candidate(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": HELD_OUTCOME_CANDIDATE_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "candidate_id": "held-security-candidate",
        "operation_id": "worker-op-security",
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


def assert_safe(value: dict[str, object]) -> None:
    text = json.dumps(value, sort_keys=True)
    for forbidden in (
        SECRET,
        "source_evidence_digest",
        "candidate_digest",
        "reason_digest",
        "token_digest",
        "source_path",
        "protected_source",
        "primary_page_body",
        "Traceback",
    ):
        require(forbidden not in text, forbidden)
    for key in (
        "source_body_included",
        "model_output_included",
        "memory_content_included",
        "queue_payload_included",
        "primary_page_path_included",
        "store_root_included",
        "queue_root_included",
        "claim_token_included",
        "lease_owner_included",
        "raw_exception_included",
        "worker_started",
        "scheduler_started",
        "automatic_retry_or_release",
    ):
        require(value[key] is False, (key, value))


def main() -> None:
    with tempfile.TemporaryDirectory() as root:
        bad = candidate(payload=SECRET)
        try:
            persist_held_candidate_evidence(root, bad)
        except HeldGovernanceRuntimeError as error:
            require(error.code == "candidate_shape_mismatch", error.code)
        else:
            raise AssertionError("candidate with body payload accepted")

        persist_held_candidate_evidence(root, candidate(source_evidence_present=False))
        result = preflight_held_governance_decision(
            root,
            candidate_id="held-security-candidate",
            action="apply",
            expected_character_id="char-a",
            expected_namespace="ns-a",
            operation_id="i7c-security-op",
            reason="bounded security reason",
        )
        assert_safe(result)
        require(result["status"] == "safe_failure", result)
        require(result["reason_code"] == "source_evidence_missing", result)
        require(result["apply_token"] is None, result)

    print("Phase I-7C held governance security smoke passed")


if __name__ == "__main__":
    main()
