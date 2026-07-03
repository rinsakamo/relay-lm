from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.analyzer_governance import can_open_runtime_policy
from relaylm.reference_intent_analyzer import (
    INTENT_KINDS,
    REFERENCE_KINDS,
    analyze_reference_intent,
    normalize_reference_intent_artifact,
    reference_intent_public_projection,
    relayint_legacy_reference_kind,
)
from relaylm.relayint import build_relayint_fast_path_dry_run
from relaylm.relayref import build_relayref_dry_run_artifact


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _message(text: str) -> list[dict[str, str]]:
    return [{"role": "user", "content": text}]


def _assert_content_free(value: object) -> None:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    forbidden = [
        "secret private reference",
        "keyword:private body",
        "raw secret user text",
    ]
    for token in forbidden:
        require(token not in serialized, serialized)


def _public(text: str, *, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    artifact = analyze_reference_intent(messages=_message(text), ctx_hints=ctx or {})
    public = reference_intent_public_projection(artifact)
    require(public["schema_version"] == "relaylm.reference_intent_analyzer.v0", public)
    require(public["analyzer_kind"] == "reference_intent_candidate", public)
    require(public["content_free"] is True, public)
    _assert_content_free(public)
    return public


def main() -> None:
    for marker in ("それ", "これ", "あれ", "さっき", "どっち", "どれ"):
        public = _public(marker)
        require(public["unresolved_reference_detected"] is True, (marker, public))
        require(public["clarification_recommended"] is True, (marker, public))

    for marker in ("この件", "前の"):
        public = _public(marker)
        require(public["unresolved_reference_detected"] is True, (marker, public))
        require(public["clarification_recommended"] is True, (marker, public))
        relayint = build_relayint_fast_path_dry_run(
            messages=_message(marker),
            ctx_hints={},
            enabled=True,
        )
        require(isinstance(relayint, dict), relayint)
        require(relayint["detected_reference_kind"] == "pronoun_like", relayint)
        require(relayint["candidate_action"] == "ask_clarification", relayint)

    for marker in ("どっち", "which one"):
        relayint = build_relayint_fast_path_dry_run(
            messages=_message(marker),
            ctx_hints={"current_topic": "keyword:private body"},
            enabled=True,
        )
        require(isinstance(relayint, dict), relayint)
        require(relayint["reference_intent_analyzer"]["reference_kind"] == "ambiguous_choice", relayint)
        require(relayint["ambiguity_detected"] is True, relayint)
        require(relayint["candidate_action"] == "ask_clarification", relayint)
        _assert_content_free(relayint)

    for marker in ("which one", "what was that", "what were we"):
        public = _public(marker)
        require(public["unresolved_reference_detected"] is True, (marker, public))

    for marker in ("前に話した", "覚えてる", "思い出して", "前回", "previous", "remember"):
        public = _public(marker)
        require(public["prior_memory_request_detected"] is True, (marker, public))
        require("prior_memory_request" in public["intent_kinds"], (marker, public))

    for marker in ("続き", "その方向", "それで", "continue"):
        public = _public(marker, ctx={"current_topic": "secret private reference"})
        require(public["continuation_detected"] is True, (marker, public))
        require("continuation" in public["intent_kinds"], (marker, public))
        _assert_content_free(public)

    artifact = analyze_reference_intent(messages=_message("それで"))
    public = reference_intent_public_projection(artifact)
    require(public["source"] in {"locale_marker", "fallback_regex"}, public)
    require(public["source_authoritative"] is False, public)
    require(public["restrictive_only"] is True, public)
    require(public["runtime_policy_open_allowed"] is False, public)
    require(can_open_runtime_policy(artifact["governance"]) is False, artifact)
    require(public["policy_authority"] not in {"broad", "update", "mutation", "open"}, public)

    malformed = normalize_reference_intent_artifact(
        {
            "schema_version": "relaylm.reference_intent_analyzer.v0",
            "analyzer_kind": "reference_intent_candidate",
            "reference_kind": "secret private reference",
            "intent_kinds": ["keyword:private body"],
            "raw_user_text": "raw secret user text",
        }
    )
    malformed_public = reference_intent_public_projection(malformed)
    require(malformed_public["reference_kind"] == "unknown", malformed_public)
    require(malformed_public["intent_kinds"] == ("unknown",), malformed_public)
    require("unknown_enum_value" in malformed_public["validation_error_ids"], malformed_public)
    _assert_content_free(malformed_public)

    malformed_flagged = normalize_reference_intent_artifact(
        {
            "schema_version": "relaylm.reference_intent_analyzer.v0",
            "analyzer_kind": "reference_intent_candidate",
            "reference_kind": "secret private reference",
            "intent_kinds": ["keyword:private body"],
            "prior_memory_request_detected": True,
            "unresolved_reference_detected": True,
            "ambiguity_detected": True,
        }
    )
    malformed_flagged_public = reference_intent_public_projection(malformed_flagged)
    require(malformed_flagged_public["reference_kind"] == "unknown", malformed_flagged_public)
    require(malformed_flagged_public["prior_memory_request_detected"] is False, malformed_flagged_public)
    require(malformed_flagged_public["unresolved_reference_detected"] is False, malformed_flagged_public)
    require(malformed_flagged_public["ambiguity_detected"] is False, malformed_flagged_public)
    require(malformed_flagged_public["candidate_applied"] is False, malformed_flagged_public)
    require(malformed_flagged_public["runtime_policy_open_allowed"] is False, malformed_flagged_public)
    require("invalid_detection_flags_dropped" in malformed_flagged_public["validation_error_ids"], malformed_flagged_public)
    require(relayint_legacy_reference_kind(malformed_flagged) == "none", malformed_flagged)

    for enum_value in REFERENCE_KINDS | INTENT_KINDS:
        require(enum_value.isascii(), enum_value)
        require(enum_value == enum_value.lower(), enum_value)

    relayscn = {
        "scene_state": {"scene_type": "design_talk", "confidence": 0.95, "stability": 0.9},
        "scene_policy": {},
        "persistence_block": False,
        "persistence_block_reasons": [],
    }
    relayref = build_relayref_dry_run_artifact(relayscn_artifact=relayscn, messages=_message("それ"))
    require(relayref["unresolved_reference_detected"] is True, relayref)
    require(relayref["reference_intent_analyzer"]["analyzer_kind"] == "reference_intent_candidate", relayref)

    relayint = build_relayint_fast_path_dry_run(
        messages=_message("前に話したMEMの続き"),
        ctx_hints={"current_topic": "keyword:private body"},
        enabled=True,
    )
    require(isinstance(relayint, dict), relayint)
    require(relayint["explicit_prior_memory_request_detected"] is True, relayint)
    require(relayint["detected_reference_kind"] == "prior_memory_request", relayint)
    require(relayint["reference_intent_analyzer"]["analyzer_kind"] == "reference_intent_candidate", relayint)
    _assert_content_free(relayint)

    print("ok ACG-4 reference/intent analyzer smoke")


if __name__ == "__main__":
    main()
