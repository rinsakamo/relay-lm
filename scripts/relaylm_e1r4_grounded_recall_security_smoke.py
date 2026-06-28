#!/usr/bin/env python3
"""E1-R4 grounded recall public-projection security smoke."""
from __future__ import annotations

from relaylm.relaymem_grounded_recall_response import build_grounded_recall_context

RAW_USER = "CANARY_E1R4_RAW_USER_TEXT_DO_NOT_LEAK favorite color is blue"
RAW_ASSISTANT = "CANARY_E1R4_RAW_ASSISTANT_TEXT_DO_NOT_LEAK got it"
PROTECTED_SOURCE = "CANARY_E1R4_PROTECTED_SOURCE_BODY_DO_NOT_LEAK"
QUEUE_PAYLOAD = "CANARY_E1R4_QUEUE_PAYLOAD_DO_NOT_LEAK"
STORE_ROOT = "/tmp/CANARY_E1R4_STORE_ROOT_DO_NOT_LEAK"
SOURCE_PATH = "/tmp/CANARY_E1R4_SOURCE_PATH_DO_NOT_LEAK"
CLAIM_TOKEN = "CANARY_E1R4_CLAIM_TOKEN_DO_NOT_LEAK"
LEASE_OWNER = "CANARY_E1R4_LEASE_OWNER_DO_NOT_LEAK"
TOKEN_DIGEST = "b" * 64
SOURCE_DIGEST = "c" * 64


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def test_public_projection_content_free() -> None:
    result = build_grounded_recall_context(
        retrieved_memories=[{
            "memory_id": "mem_e1r4_public_projection",
            "revision": TOKEN_DIGEST,
            "character_id": "default",
            "namespace": "e1r4_namespace",
            "lifecycle_state": "active",
            "provenance_source": "user_assertion",
            "fact_text": RAW_USER,
            "raw_user_text": RAW_USER,
            "raw_assistant_text": RAW_ASSISTANT,
            "protected_source_body": PROTECTED_SOURCE,
            "queue_payload": QUEUE_PAYLOAD,
            "store_root": STORE_ROOT,
            "source_path": SOURCE_PATH,
            "claim_token": CLAIM_TOKEN,
            "lease_owner": LEASE_OWNER,
            "token_digest": TOKEN_DIGEST,
            "source_digest": SOURCE_DIGEST,
        }],
        query_text="what is my favorite color?",
        character_id="default",
        namespace="e1r4_namespace",
    )
    require(result.status == "grounding_applied", result)
    context = result.grounded_recall_context
    require(context is not None, result)
    require(RAW_USER in repr(context), context)  # private backend evidence may contain bounded fact text
    public = result.to_log_dict()
    public_repr = repr(public)
    for forbidden in (
        RAW_USER,
        RAW_ASSISTANT,
        PROTECTED_SOURCE,
        QUEUE_PAYLOAD,
        STORE_ROOT,
        SOURCE_PATH,
        CLAIM_TOKEN,
        LEASE_OWNER,
        TOKEN_DIGEST,
        SOURCE_DIGEST,
    ):
        require(forbidden not in public_repr, (forbidden, public))
    require(public["evidence_content_included"] is False, public)
    require(public["runtime_private_evidence_omitted"] is True, public)
    require(public["token_digest_included"] is False, public)
    require(public["source_digest_included"] is False, public)


def test_public_safe_reference_and_missing_provenance() -> None:
    result = build_grounded_recall_context(
        retrieved_memories=[{
            "memory_id": SOURCE_PATH,
            "revision": SOURCE_DIGEST,
            "character_id": "default",
            "namespace": "e1r4_namespace",
            "lifecycle_state": "active",
            "provenance_source": "user_assertion",
            "fact_text": RAW_USER,
        }],
        query_text="what is my favorite color?",
        character_id="default",
        namespace="e1r4_namespace",
    )
    context = result.grounded_recall_context
    require(context is not None, result)
    item = context["evidence_items"][0]
    require(item["memory_ref"] == "memory_ref_1", item)
    require(item["revision_ref"] == "revision_present", item)
    missing = build_grounded_recall_context(
        retrieved_memories=[{
            "memory_id": "mem_e1r4_missing_provenance",
            "revision": 1,
            "character_id": "default",
            "namespace": "e1r4_namespace",
            "lifecycle_state": "active",
            "fact_text": RAW_USER,
        }],
        query_text="what is my favorite color?",
        character_id="default",
        namespace="e1r4_namespace",
    )
    require(missing.status == "provenance_missing", missing)
    require(missing.to_log_dict()["grounded_item_count"] == 0, missing.to_log_dict())
    require(RAW_USER not in repr(missing.grounded_recall_context), missing.grounded_recall_context)


def main() -> None:
    test_public_projection_content_free()
    test_public_safe_reference_and_missing_provenance()
    print("relaylm_e1r4_grounded_recall_security_smoke: ok")


if __name__ == "__main__":
    main()
