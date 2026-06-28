#!/usr/bin/env python3
"""E1-R3 speaker-provenance formation summary smoke."""
from __future__ import annotations

from relaylm.relaymem_provenance_formation_summary import (
    build_relaymem_primary_formation_summary,
)

USER_FACT = "CANARY_E1R3_USER_FACT_DO_NOT_LEAK"
ASSISTANT_ACK = "CANARY_E1R3_ASSISTANT_ACK_DO_NOT_LEAK got it"
ASSISTANT_SPEC = "CANARY_E1R3_ASSISTANT_SPEC_DO_NOT_LEAK maybe this is related"
ASSISTANT_DECORATION = "CANARY_E1R3_ASSISTANT_DECORATION_DO_NOT_LEAK I will describe it more vividly"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def scene(**extra: object) -> dict[str, object]:
    value: dict[str, object] = {
        "scene_state": {"scene_type": "home", "confidence": 0.99},
        "scene_policy": {"relaymem_retrieval_scope": "project_context"},
        "persistence_block": False,
        "persistence_block_reasons": [],
    }
    value.update(extra)
    return value


def build(messages: object, **extra: object):
    kwargs = {
        "character_id": "default",
        "namespace": "e1r3_namespace",
        "source_event_kind": "turn",
        "source_lineage_fingerprint": "a" * 64,
        "relayscn_scene_policy_artifact": scene(),
        "trust_admission_evidence": {
            "trust_owner": "route_owned",
            "admission_status": "accepted",
        },
        "governed_messages": messages,
        "enabled": True,
        "dry_run_only": False,
    }
    kwargs.update(extra)
    return build_relaymem_primary_formation_summary(**kwargs)


def assert_public_content_free(value: object) -> None:
    public = repr(value)
    for forbidden in (
        USER_FACT,
        ASSISTANT_ACK,
        ASSISTANT_SPEC,
        ASSISTANT_DECORATION,
        "a" * 64,
    ):
        require(forbidden not in public, (forbidden, public))


def test_user_fact_and_acknowledgement() -> None:
    result = build([
        {"role": "user", "content": USER_FACT},
        {"role": "assistant", "content": ASSISTANT_ACK},
    ])
    require(result.status == "formed", result)
    payload = result.memory_candidate_payload
    summary = result.formation_summary
    require(payload is not None and payload["summary_text"] == USER_FACT, payload)
    require(ASSISTANT_ACK not in payload["summary_text"], payload)
    require(summary is not None, summary)
    require(len(summary["user_assertion_evidence"]) == 1, summary)
    require(len(summary["assistant_acknowledgement_evidence"]) == 1, summary)
    require(summary["assistant_text_promoted_to_user_fact"] is False, summary)
    assert_public_content_free(result.to_log_dict())


def test_assistant_speculation_not_promoted() -> None:
    result = build([
        {"role": "user", "content": USER_FACT},
        {"role": "assistant", "content": ASSISTANT_SPEC},
    ])
    require(result.status == "formed", result)
    payload = result.memory_candidate_payload
    summary = result.formation_summary
    require(payload is not None and ASSISTANT_SPEC not in payload["summary_text"], payload)
    require(summary is not None, summary)
    non_factual = summary["assistant_speculation_or_non_factual_evidence"]
    require(len(non_factual) == 1 and non_factual[0]["role"] == "assistant", non_factual)
    require(non_factual[0]["speculation_marker_present"] is True, non_factual)


def test_assistant_decoration_not_authority() -> None:
    result = build([
        {"role": "user", "content": USER_FACT},
        {"role": "assistant", "content": ASSISTANT_DECORATION},
    ])
    payload = result.memory_candidate_payload
    summary = result.formation_summary
    require(result.status == "formed", result)
    require(payload is not None and payload["source_message_indexes"] == [0], payload)
    require(ASSISTANT_DECORATION not in payload["summary_text"], payload)
    require(summary is not None, summary)
    require(summary["memory_candidate_payload"]["factual_source"] == "user_assertion_only", summary)


def test_route_scene_and_browser_trust() -> None:
    result = build([
        {"role": "user", "content": USER_FACT},
        {"role": "assistant", "content": ASSISTANT_ACK},
    ])
    summary = result.formation_summary
    require(summary is not None, summary)
    require(len(summary["scene_qualification_evidence"]) == 1, summary)
    require(len(summary["trust_admission_evidence"]) == 1, summary)
    browser_scene = scene(trusted_home_scene_admission="apply")
    blocked = build(
        [{"role": "user", "content": USER_FACT}],
        relayscn_scene_policy_artifact=browser_scene,
    )
    require(blocked.status == "blocked_browser_owned_trust", blocked)
    require(blocked.memory_candidate_payload is None, blocked)


def test_missing_or_ambiguous_provenance_blocks() -> None:
    missing = build([{"content": USER_FACT}])
    require(missing.status == "source_role_missing", missing)
    ambiguous = build([{"role": "tool", "content": USER_FACT}])
    require(ambiguous.status == "blocked_ambiguous_provenance", ambiguous)
    no_user = build([{"role": "assistant", "content": ASSISTANT_SPEC}])
    require(no_user.status == "blocked_no_user_assertion", no_user)
    dry = build([{"role": "user", "content": USER_FACT}], dry_run_only=True)
    require(dry.status == "dry_run_ready", dry)


def main() -> None:
    test_user_fact_and_acknowledgement()
    test_assistant_speculation_not_promoted()
    test_assistant_decoration_not_authority()
    test_route_scene_and_browser_trust()
    test_missing_or_ambiguous_provenance_blocks()
    print("relaylm_e1r3_provenance_formation_summary_smoke: ok")


if __name__ == "__main__":
    main()
