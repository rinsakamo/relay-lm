#!/usr/bin/env python3
"""Smoke coverage for ACG-6 RelaySCN scene-wiki classifier boundary."""

from __future__ import annotations

import copy
import inspect
import json

from relaylm.analyzer_governance import can_open_runtime_policy
from relaylm.pipeline_ordering import build_p0_pipeline_order_projection
from relaylm.scene_classifier import (
    SCENE_TYPES,
    build_scene_classifier_candidate,
    scene_classifier_public_projection,
)
from relaylm.scene_wiki_matcher import match_scene_wiki_definition, scene_wiki_match_public_projection
from relaylm.relayscn import build_relayscn_scene_policy_artifact


def _assert(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _serialized(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _assert_content_free(value: object) -> None:
    serialized = _serialized(value)
    for token in (
        "secret scene body",
        "private user text",
        "keyword:private body",
        "free-form rationale",
        "secret private scene",
        "SECRET_SCENE_MARKDOWN",
    ):
        _assert(token not in serialized, serialized)


def main() -> None:
    signature = inspect.signature(build_relayscn_scene_policy_artifact)
    _assert("relayemo_artifact" not in signature.parameters, signature)

    structured = build_scene_classifier_candidate(
        candidate={
            "source": "llm_candidate",
            "source_language": "ja",
            "candidate_scene_type": "implementation_work",
            "candidate_scene_id": "repo_fix",
            "candidate_scene_family": "implementation",
            "confidence": 0.82,
            "stability": 0.73,
        }
    )
    _assert(structured["analyzer_kind"] == "scene_policy_candidate", structured)
    _assert(structured["candidate_scene_type"] in SCENE_TYPES, structured)
    _assert(structured["candidate_scene_type"] == "implementation_work", structured)
    _assert(structured["content_free"] is True, structured)
    _assert_content_free(structured)

    free_form = build_scene_classifier_candidate(
        candidate={
            "source": "llm_candidate",
            "candidate_scene_type": "secret private scene",
            "candidate_scene_family": "keyword:private body",
            "confidence": 0.99,
            "stability": 0.99,
            "raw_user_text": "private user text",
            "scene_markdown": "SECRET_SCENE_MARKDOWN",
            "rationale": "free-form rationale",
        }
    )
    free_public = scene_classifier_public_projection(free_form)
    _assert(free_form["candidate_scene_type"] == "unknown", free_form)
    _assert(free_public["candidate_scene_type"] == "unknown", free_public)
    _assert(free_form["can_open_runtime_policy"] is False, free_form)
    _assert("unrecognized_scene_type" in free_public["validation_error_ids"], free_public)
    _assert_content_free(free_form)
    _assert_content_free(free_public)

    llm_open_attempt = build_scene_classifier_candidate(
        candidate={
            "source": "llm_candidate",
            "source_authoritative": True,
            "candidate_applied": True,
            "candidate_scene_type": "implementation_work",
            "policy_authority": "broad",
            "restrictive_only": False,
            "confidence": 0.95,
            "stability": 0.95,
        }
    )
    _assert(llm_open_attempt["source_authoritative"] is False, llm_open_attempt)
    _assert(llm_open_attempt["policy_authority"] in {"none", "restrictive"}, llm_open_attempt)
    _assert(llm_open_attempt["restrictive_only"] is True, llm_open_attempt)
    _assert(llm_open_attempt["can_open_runtime_policy"] is False, llm_open_attempt)
    _assert(can_open_runtime_policy(llm_open_attempt["governance"]) is False, llm_open_attempt)

    llm_policy_artifact = build_relayscn_scene_policy_artifact(
        payload={"scene_classifier_candidate": llm_open_attempt}
    )
    _assert(
        llm_policy_artifact["scene_policy"]["relaymem_retrieval_scope"] == "current_context_only",
        llm_policy_artifact,
    )
    _assert(llm_policy_artifact["scene_policy"]["relaymem_update_gate"] == "blocked", llm_policy_artifact)
    _assert(llm_policy_artifact["scene_classifier_candidate_public"]["can_open_runtime_policy"] is False, llm_policy_artifact)

    safety_candidate = build_scene_classifier_candidate(
        candidate={
            "source": "heuristic",
            "candidate_scene_type": "medical_or_safety",
            "policy_authority": "open",
            "confidence": 0.91,
            "stability": 0.88,
        }
    )
    safety_policy = build_relayscn_scene_policy_artifact(
        payload={"scene_classifier_candidate": safety_candidate}
    )
    _assert(safety_candidate["can_open_runtime_policy"] is False, safety_candidate)
    _assert(safety_policy["scene_policy"]["policy_authority"] == "heuristic_restrictive", safety_policy)
    _assert(safety_policy["scene_policy"]["relaymem_retrieval_scope"] == "minimal_or_evidence_only", safety_policy)
    _assert(safety_policy["scene_policy"]["relaymem_update_gate"] == "blocked", safety_policy)

    explicit_wins = build_relayscn_scene_policy_artifact(
        payload={
            "metadata": {
                "relayscn": {
                    "scene_state": {
                        "schema_version": "relayscn.scene_state.v0",
                        "scene_type": "review_work",
                        "confidence": 0.93,
                        "stability": 0.89,
                    }
                }
            },
            "scene_classifier_candidate": {
                "source": "llm_candidate",
                "candidate_scene_type": "medical_or_safety",
                "confidence": 0.99,
                "stability": 0.99,
            },
        }
    )
    _assert(explicit_wins["scene_state_source"] == "request_metadata", explicit_wins)
    _assert(explicit_wins["scene_state"]["scene_type"] == "review_work", explicit_wins)
    _assert(explicit_wins["scene_policy"]["relaymem_retrieval_scope"] == "current_project_only", explicit_wins)

    definitions = [
        {
            "scene_id": "repo_review",
            "scene_type": "review_work",
            "scene_family": "implementation",
            "aliases": ["pull_request_review", "code_review"],
            "authority": "explicit_scene_definition",
            "enabled": True,
            "body": "secret scene body",
        }
    ]
    before_definitions = copy.deepcopy(definitions)
    match = match_scene_wiki_definition(
        candidate_scene_type="review_work",
        candidate_scene_id="pull_request_review",
        candidate_scene_family="implementation",
        scene_definitions=definitions,
    )
    match_public = scene_wiki_match_public_projection(match)
    _assert(match["matched_scene_wiki_id"] == "repo_review", match)
    _assert(match["match_strength"] == "strong", match)
    _assert(match_public["matched_scene_wiki_id"] == "repo_review", match_public)
    _assert(definitions == before_definitions, "scene-wiki matcher must not mutate definitions")
    _assert_content_free(match)
    _assert_content_free(match_public)

    wiki_candidate = build_scene_classifier_candidate(
        candidate={
            "source": "llm_candidate",
            "candidate_scene_type": "review_work",
            "candidate_scene_id": "repo_review",
            "candidate_scene_family": "implementation",
            "confidence": 0.40,
            "stability": 0.40,
        },
        scene_wiki_definitions=definitions,
    )
    _assert(wiki_candidate["matched_scene_wiki_id"] == "repo_review", wiki_candidate)
    _assert(wiki_candidate["match_strength"] == "strong", wiki_candidate)
    wiki_policy = build_relayscn_scene_policy_artifact(
        payload={
            "scene_classifier_candidate": wiki_candidate,
            "scene_wiki_definitions": definitions,
        }
    )
    _assert(wiki_policy["scene_policy"]["policy_authority"] == "heuristic_non_authoritative", wiki_policy)
    _assert(wiki_policy["scene_policy"]["relaymem_retrieval_scope"] == "current_context_only", wiki_policy)
    _assert_content_free(wiki_policy["scene_classifier_candidate_public"])

    confirmed = build_scene_classifier_candidate(
        candidate={
            "source": "confirmed_user_action",
            "source_authoritative": True,
            "candidate_applied": True,
            "candidate_scene_type": "review_work",
            "policy_authority": "bounded",
            "restrictive_only": False,
            "confidence": 0.95,
            "stability": 0.90,
        }
    )
    confirmed_policy = build_relayscn_scene_policy_artifact(
        payload={"scene_classifier_candidate": confirmed}
    )
    _assert(confirmed["can_open_runtime_policy"] is True, confirmed)
    _assert(confirmed_policy["scene_state_source"] == "confirmed_user_action", confirmed_policy)
    _assert(confirmed_policy["scene_state"]["source_authoritative"] is True, confirmed_policy)
    _assert(confirmed_policy["scene_policy"]["relaymem_retrieval_scope"] == "current_project_only", confirmed_policy)

    order_projection = build_p0_pipeline_order_projection(
        relayrel_projection={"schema_version": "relayrel.relationship_projection.v0", "content_free": True},
        relayscn_scene_policy_artifact=llm_policy_artifact,
        relayemo_artifact={"user_affect_estimate_is_estimate": True},
        relaymem_retrieval_artifact={"relayscn_policy_consumed": True, "content_free": True},
        actual_app_rewired=True,
    )
    order = order_projection["request_path_order"]
    _assert(order.index("relayrel_relationship_projection") < order.index("relayscn_scene_policy"), order_projection)
    _assert(order.index("relayscn_scene_policy") < order.index("relayemo_input"), order_projection)

    public_payload = {
        "free_form": free_public,
        "wiki": wiki_policy["scene_classifier_candidate_public"],
        "confirmed": confirmed_policy["scene_classifier_candidate_public"],
    }
    _assert_content_free(public_payload)

    print("relaylm_acg6_scene_wiki_classifier_smoke: PASS")


if __name__ == "__main__":
    main()
