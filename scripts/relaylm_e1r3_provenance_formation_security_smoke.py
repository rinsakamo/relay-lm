#!/usr/bin/env python3
"""E1-R3 content-leakage and lifecycle-compatibility smoke."""
from __future__ import annotations

from relaylm.relaymem_provenance_formation_summary import (
    FORMATION_SUMMARY_SCHEMA,
    build_relaymem_primary_formation_summary,
)

USER_CANARY = "CANARY_E1R3_PRIVATE_USER_TEXT"
ASSISTANT_CANARY = "CANARY_E1R3_PRIVATE_ASSISTANT_TEXT"
PROTECTED_BODY_CANARY = "CANARY_E1R3_PROTECTED_SOURCE_BODY"
QUEUE_CANARY = "slp-dispatch-v0-CANARY_E1R3_QUEUE"
STORE_ROOT_CANARY = "/tmp/CANARY_E1R3_STORE_ROOT"
SOURCE_PATH_CANARY = "protected-source-v0-CANARY_E1R3_PATH.json"
CLAIM_TOKEN_CANARY = "claim-token-CANARY_E1R3"
LEASE_OWNER_CANARY = "lease-owner-CANARY_E1R3"
TOKEN_DIGEST_CANARY = "token-digest-CANARY_E1R3"
SOURCE_DIGEST_CANARY = "b" * 64


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def scene() -> dict[str, object]:
    return {
        "scene_state": {"scene_type": "home", "confidence": 0.99},
        "scene_policy": {"relaymem_retrieval_scope": "project_context"},
        "persistence_block": False,
        "persistence_block_reasons": [],
    }


def assert_projection_content_free(value: object) -> None:
    public = repr(value)
    for forbidden in (
        USER_CANARY,
        ASSISTANT_CANARY,
        PROTECTED_BODY_CANARY,
        QUEUE_CANARY,
        STORE_ROOT_CANARY,
        SOURCE_PATH_CANARY,
        CLAIM_TOKEN_CANARY,
        LEASE_OWNER_CANARY,
        TOKEN_DIGEST_CANARY,
        SOURCE_DIGEST_CANARY,
        "Traceback",
    ):
        require(forbidden not in public, (forbidden, public))


def test_projection_is_content_free() -> None:
    result = build_relaymem_primary_formation_summary(
        character_id="default",
        namespace="e1r3_namespace",
        source_event_kind="turn",
        source_lineage_fingerprint=SOURCE_DIGEST_CANARY,
        protected_source_identity={
            "protected_source_body": PROTECTED_BODY_CANARY,
            "queue_payload": QUEUE_CANARY,
            "store_root": STORE_ROOT_CANARY,
            "source_path": SOURCE_PATH_CANARY,
            "claim_token": CLAIM_TOKEN_CANARY,
            "lease_owner": LEASE_OWNER_CANARY,
            "token_digest": TOKEN_DIGEST_CANARY,
        },
        relayscn_scene_policy_artifact=scene(),
        governed_messages=[
            {"role": "user", "content": USER_CANARY},
            {"role": "assistant", "content": ASSISTANT_CANARY},
        ],
        enabled=True,
        dry_run_only=False,
    )
    require(result.status == "formed", result)
    require(result.formation_summary is not None, result)
    require(result.formation_summary["schema_version"] == FORMATION_SUMMARY_SCHEMA, result)
    assert_projection_content_free(result.to_log_dict())
    public = result.to_log_dict()
    require(public["raw_text_included"] is False, public)
    require(public["raw_messages_included"] is False, public)
    require(public["protected_source_body_included"] is False, public)
    require(public["queue_payload_included"] is False, public)
    require(public["store_root_included"] is False, public)
    require(public["source_path_included"] is False, public)
    require(public["claim_token_included"] is False, public)
    require(public["lease_owner_included"] is False, public)
    require(public["token_digest_included"] is False, public)
    require(public["source_digest_included"] is False, public)


def test_fail_closed_and_lifecycle_boundary_strings() -> None:
    blocked = build_relaymem_primary_formation_summary(
        character_id="default",
        namespace="e1r3_namespace",
        source_event_kind="turn",
        source_lineage_fingerprint="not-a-digest",
        relayscn_scene_policy_artifact=scene(),
        governed_messages=[{"role": "user", "content": USER_CANARY}],
    )
    require(blocked.status == "source_digest_mismatch", blocked)
    require(blocked.memory_candidate_payload is None, blocked)
    assert_projection_content_free(blocked.to_log_dict())

    lifecycle_words = (
        "hidden",
        "prepared",
        "recovery_required",
        "corrupt",
        "prior physical revision",
    )
    public = repr(blocked.to_log_dict())
    for word in lifecycle_words:
        require(word not in public, public)


def main() -> None:
    test_projection_is_content_free()
    test_fail_closed_and_lifecycle_boundary_strings()
    print("relaylm_e1r3_provenance_formation_security_smoke: ok")


if __name__ == "__main__":
    main()
