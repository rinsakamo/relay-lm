"""RelayINT fast-path dry-run intent diagnostics."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal


ReferenceKind = Literal["none", "pronoun_like", "continuation", "prior_memory_request"]
CandidateAction = Literal[
    "continue_without_clarification",
    "ask_clarification",
    "current_context_only",
    "recall_then_answer_candidate",
]


PRONOUN_LIKE_TERMS = ("それ", "これ", "前の", "さっき", "この件")
CONTINUATION_TERMS = ("続き", "その方向", "それで")
PRIOR_MEMORY_TERMS = ("前に話した", "覚えてる", "思い出して", "前回", "前のスレッド")


SAFE_CTX_KEYS = {
    "ctx_handoff_guess",
    "current_topic",
    "active_question",
    "referable_items",
    "unresolved_slots",
    "next_expected_action",
}


def build_relayint_fast_path_dry_run(
    *,
    messages: Sequence[Mapping[str, Any]],
    ctx_hints: Mapping[str, Any] | None = None,
    enabled: bool = False,
    high_confidence_threshold: float = 0.80,
    low_confidence_threshold: float = 0.55,
) -> dict[str, Any] | None:
    """Build content-free RelayINT fast-path intent diagnostics.

    The MVP-45 fast path is deterministic and diagnostics-only. It does not call
    an LLM, execute MEM lookup, mutate payloads/responses, or copy raw user text
    into the returned artifact.
    """

    if not enabled:
        return None

    latest_user_text = _latest_user_text(messages)
    ctx_summary = _ctx_metadata_summary(ctx_hints or {})
    prior_memory_count = _count_terms(latest_user_text, PRIOR_MEMORY_TERMS)
    continuation_count = _count_terms(latest_user_text, CONTINUATION_TERMS)
    pronoun_count = _count_terms(latest_user_text, PRONOUN_LIKE_TERMS)
    explicit_prior_memory = prior_memory_count > 0
    reference_terms_count = prior_memory_count + continuation_count + pronoun_count
    detected_reference_kind = _detected_reference_kind(
        prior_memory_count=prior_memory_count,
        continuation_count=continuation_count,
        pronoun_count=pronoun_count,
    )
    ctx_signal_present = bool(ctx_summary["ctx_signal_present"])
    ambiguity_detected = _ambiguity_detected(
        detected_reference_kind=detected_reference_kind,
        ctx_signal_present=ctx_signal_present,
        explicit_prior_memory=explicit_prior_memory,
    )
    mem_query_needed = explicit_prior_memory
    candidate_action = _candidate_action(
        detected_reference_kind=detected_reference_kind,
        explicit_prior_memory=explicit_prior_memory,
        ambiguity_detected=ambiguity_detected,
        ctx_signal_present=ctx_signal_present,
    )
    confidence_score = _confidence_score(
        detected_reference_kind=detected_reference_kind,
        explicit_prior_memory=explicit_prior_memory,
        ambiguity_detected=ambiguity_detected,
        ctx_signal_present=ctx_signal_present,
    )
    confidence_bucket = _confidence_bucket(
        confidence_score,
        high_confidence_threshold=high_confidence_threshold,
        low_confidence_threshold=low_confidence_threshold,
    )
    llm_path_reasons = _llm_path_reasons(
        ambiguity_detected=ambiguity_detected,
        confidence_bucket=confidence_bucket,
        detected_reference_kind=detected_reference_kind,
    )
    decision_reasons = _decision_reasons(
        detected_reference_kind=detected_reference_kind,
        explicit_prior_memory=explicit_prior_memory,
        ambiguity_detected=ambiguity_detected,
        mem_query_needed=mem_query_needed,
        ctx_signal_present=ctx_signal_present,
    )

    return {
        "schema_version": "relayint_fast_path_dry_run.v0",
        "enabled": True,
        "dry_run_only": True,
        "content_free": True,
        "llm_called": False,
        "mem_lookup_executed": False,
        "backend_payload_mutation_allowed": False,
        "response_mutation_allowed": False,
        "detected_reference_kind": detected_reference_kind,
        "reference_terms_detected_count": reference_terms_count,
        "explicit_prior_memory_request_detected": explicit_prior_memory,
        "candidate_action": candidate_action,
        "mem_query_needed_candidate": mem_query_needed,
        "confidence_bucket": confidence_bucket,
        "ambiguity_detected": ambiguity_detected,
        "llm_path_would_call": bool(llm_path_reasons),
        "llm_path_reason": llm_path_reasons,
        "decision_reasons": decision_reasons,
        "latest_user_message_present": bool(latest_user_text),
        "latest_user_message_chars": len(latest_user_text),
        "latest_user_message_is_short": 0 < len(latest_user_text) <= 24,
        "ctx_working_metadata": ctx_summary,
        "safety_gates": {
            "content_free": True,
            "llm_call_allowed": False,
            "mem_lookup_allowed": False,
            "backend_payload_mutation_allowed": False,
            "response_mutation_allowed": False,
        },
    }


def build_relayint_quick_clarification_preflight(
    *,
    relayint_fast_path_dry_run: Mapping[str, Any] | None,
    relayscn_scene_policy_artifact: Mapping[str, Any] | None = None,
    enabled: bool = False,
    dry_run_only: bool = True,
) -> dict[str, Any] | None:
    """Build content-free RelayINT quick clarification preflight diagnostics.

    MVP-46 only plans whether a quick clarification could be prepared. It does
    not generate user-visible clarification text, call an LLM, execute MEM
    lookup, mutate backend payloads, or mutate responses.
    """

    if not enabled or not isinstance(relayint_fast_path_dry_run, Mapping):
        return None

    source_candidate_action = relayint_fast_path_dry_run.get("candidate_action")
    scene_gate = _quick_clarification_scene_gate(relayscn_scene_policy_artifact)
    quick_clarification_allowed = scene_gate["quick_clarification_allowed"] is True
    preflight_applicable = (
        source_candidate_action == "ask_clarification" and quick_clarification_allowed
    )
    source_schema_version = relayint_fast_path_dry_run.get("schema_version")
    ctx_metadata = relayint_fast_path_dry_run.get("ctx_working_metadata")
    if not isinstance(ctx_metadata, Mapping):
        ctx_metadata = {}

    candidate_label_kinds = _quick_clarification_candidate_label_kinds(
        relayint_fast_path_dry_run=relayint_fast_path_dry_run,
        ctx_metadata=ctx_metadata,
        preflight_applicable=preflight_applicable,
    )
    clarification_type = _quick_clarification_type(
        relayint_fast_path_dry_run=relayint_fast_path_dry_run,
        candidate_label_kinds=candidate_label_kinds,
        preflight_applicable=preflight_applicable,
    )

    return {
        "schema_version": "relayint_quick_clarification_preflight.v0",
        "enabled": True,
        "dry_run_only": dry_run_only,
        "content_free": True,
        "source_artifact_schema_version": (
            source_schema_version if isinstance(source_schema_version, str) else None
        ),
        "source_candidate_action": (
            source_candidate_action if isinstance(source_candidate_action, str) else None
        ),
        "preflight_applicable": preflight_applicable,
        "clarification_type": clarification_type,
        "candidate_count": len(candidate_label_kinds),
        "candidate_labels_are_content_free": True,
        "candidate_label_kinds": candidate_label_kinds,
        "suggested_response_mode": (
            "quick_clarification_candidate"
            if preflight_applicable
            else "no_quick_clarification"
        ),
        "scene_gate": scene_gate,
        "quick_clarification_block_reasons": scene_gate["block_reasons"],
        "safety_gates": {
            "content_free": True,
            "llm_call_allowed": False,
            "mem_lookup_allowed": False,
            "backend_payload_mutation_allowed": False,
            "response_mutation_allowed": False,
            "user_visible_apply_allowed": False,
        },
        "llm_called": False,
        "mem_lookup_executed": False,
        "backend_payload_mutation_allowed": False,
        "response_mutation_allowed": False,
        "user_visible_apply_allowed": False,
    }


def build_relayint_quick_clarification_apply_plan(
    *,
    relayint_quick_clarification_preflight: Mapping[str, Any] | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    stream_enabled: bool = False,
    response_max_chars: int = 120,
) -> dict[str, Any] | None:
    """Build a gated, content-free quick clarification apply plan.

    MVP-47 keeps the response short-circuit default-off. The plan never calls an
    LLM, never executes MEM lookup, and never mutates backend payloads.
    """

    if not enabled:
        return None

    preflight_present = isinstance(relayint_quick_clarification_preflight, Mapping)
    source_schema_version = (
        relayint_quick_clarification_preflight.get("schema_version")
        if preflight_present
        else None
    )
    source_preflight_applicable = (
        relayint_quick_clarification_preflight.get("preflight_applicable") is True
        if preflight_present
        else False
    )
    scene_gate = (
        relayint_quick_clarification_preflight.get("scene_gate")
        if preflight_present
        else None
    )
    scene_allows = (
        isinstance(scene_gate, Mapping)
        and scene_gate.get("quick_clarification_allowed") is True
    )
    clarification_type = (
        relayint_quick_clarification_preflight.get("clarification_type")
        if preflight_present
        else None
    )
    generated_response_kind = _quick_clarification_response_kind(clarification_type)
    response_template_id = _quick_clarification_response_template_id(
        generated_response_kind
    )
    response_text = quick_clarification_response_text_for_template(response_template_id)
    response_chars = len(response_text) if response_template_id != "none" else 0

    block_reasons: list[str] = []
    if not preflight_present:
        block_reasons.append("preflight_missing")
    if preflight_present and not source_preflight_applicable:
        block_reasons.append("preflight_not_applicable")
    if preflight_present and not scene_allows:
        block_reasons.append("scene_gate_blocked")
        if isinstance(scene_gate, Mapping):
            for reason in _string_list(scene_gate.get("block_reasons")):
                if reason not in block_reasons:
                    block_reasons.append(reason)
    if dry_run_only:
        block_reasons.append("dry_run_only")
    if stream_enabled:
        block_reasons.append("streaming_not_supported")
    if response_template_id == "none" or response_chars == 0:
        block_reasons.append("response_template_missing")
    if response_chars > response_max_chars:
        block_reasons.append("response_max_chars_exceeded")

    apply_allowed = not block_reasons
    return {
        "schema_version": "relayint_quick_clarification_apply_plan.v0",
        "enabled": True,
        "dry_run_only": dry_run_only,
        "content_free": True,
        "source_artifact_schema_version": (
            source_schema_version if isinstance(source_schema_version, str) else None
        ),
        "source_preflight_applicable": source_preflight_applicable,
        "apply_allowed": apply_allowed,
        "apply_block_reasons": block_reasons,
        "response_short_circuit_allowed": apply_allowed,
        "short_circuit_applied": False,
        "generated_response_kind": generated_response_kind if apply_allowed else "none",
        "response_template_id": response_template_id if apply_allowed else "none",
        "response_chars": response_chars if apply_allowed else 0,
        "content_free_template": True,
        "safety_gates": {
            "content_free": True,
            "llm_call_allowed": False,
            "mem_lookup_allowed": False,
            "backend_payload_mutation_allowed": False,
            "response_mutation_allowed": apply_allowed,
            "user_visible_apply_allowed": apply_allowed,
        },
        "llm_called": False,
        "mem_lookup_executed": False,
        "backend_payload_mutation_allowed": False,
        "backend_payload_mutation_applied": False,
        "response_mutation_allowed": apply_allowed,
        "user_visible_apply_allowed": apply_allowed,
    }


def quick_clarification_response_text_for_template(template_id: str | None) -> str:
    if template_id == "generic_prior_memory_reentry.ja.v0":
        return "その話として探す前に、前回の要点をもう一度教えて。"
    if template_id in {
        "generic_reference_clarification.ja.v0",
        "generic_open_clarification.ja.v0",
    }:
        return "どの話のことか、もう少しだけ教えて。"
    return ""


def _latest_user_text(messages: Sequence[Mapping[str, Any]]) -> str:
    for message in reversed(messages):
        if not isinstance(message, Mapping) or message.get("role") != "user":
            continue
        return _content_text(message.get("content"))
    return ""


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, Sequence) and not isinstance(content, str):
        parts: list[str] = []
        for item in content:
            if (
                isinstance(item, Mapping)
                and item.get("type") == "text"
                and isinstance(item.get("text"), str)
            ):
                parts.append(item["text"])
        return "\n".join(parts)
    return ""


def _count_terms(text: str, terms: Sequence[str]) -> int:
    return sum(1 for term in terms if term in text)


def _detected_reference_kind(
    *,
    prior_memory_count: int,
    continuation_count: int,
    pronoun_count: int,
) -> ReferenceKind:
    if prior_memory_count > 0:
        return "prior_memory_request"
    if continuation_count > 0:
        return "continuation"
    if pronoun_count > 0:
        return "pronoun_like"
    return "none"


def _ambiguity_detected(
    *,
    detected_reference_kind: ReferenceKind,
    ctx_signal_present: bool,
    explicit_prior_memory: bool,
) -> bool:
    if detected_reference_kind == "none" or explicit_prior_memory:
        return False
    return not ctx_signal_present


def _candidate_action(
    *,
    detected_reference_kind: ReferenceKind,
    explicit_prior_memory: bool,
    ambiguity_detected: bool,
    ctx_signal_present: bool,
) -> CandidateAction:
    if explicit_prior_memory:
        return "recall_then_answer_candidate"
    if ambiguity_detected:
        return "ask_clarification"
    if detected_reference_kind in {"continuation", "pronoun_like"} and ctx_signal_present:
        return "continue_without_clarification"
    return "current_context_only"


def _confidence_score(
    *,
    detected_reference_kind: ReferenceKind,
    explicit_prior_memory: bool,
    ambiguity_detected: bool,
    ctx_signal_present: bool,
) -> float:
    if explicit_prior_memory:
        return 0.82
    if ambiguity_detected:
        return 0.48
    if detected_reference_kind in {"continuation", "pronoun_like"} and ctx_signal_present:
        return 0.84
    if detected_reference_kind == "none":
        return 0.74
    return 0.60


def _confidence_bucket(
    confidence_score: float,
    *,
    high_confidence_threshold: float,
    low_confidence_threshold: float,
) -> str:
    if confidence_score >= high_confidence_threshold:
        return "high"
    if confidence_score < low_confidence_threshold:
        return "low"
    return "medium"


def _llm_path_reasons(
    *,
    ambiguity_detected: bool,
    confidence_bucket: str,
    detected_reference_kind: ReferenceKind,
) -> list[str]:
    reasons: list[str] = []
    if ambiguity_detected:
        reasons.append("ambiguous_reference_without_ctx_working_signal")
    if confidence_bucket == "low":
        reasons.append("low_confidence_fast_path")
    if detected_reference_kind == "prior_memory_request":
        reasons.append("prior_memory_request_needs_retrieval_planning")
    return reasons


def _decision_reasons(
    *,
    detected_reference_kind: ReferenceKind,
    explicit_prior_memory: bool,
    ambiguity_detected: bool,
    mem_query_needed: bool,
    ctx_signal_present: bool,
) -> list[str]:
    reasons = [f"reference_kind:{detected_reference_kind}"]
    if explicit_prior_memory:
        reasons.append("explicit_prior_memory_request")
    if mem_query_needed:
        reasons.append("mem_query_candidate_only_no_lookup")
    if ambiguity_detected:
        reasons.append("clarification_candidate_due_to_ambiguity")
    if ctx_signal_present:
        reasons.append("ctx_working_signal_present")
    return reasons


def _ctx_metadata_summary(ctx_hints: Mapping[str, Any]) -> dict[str, Any]:
    safe_keys = [
        key
        for key in ctx_hints.keys()
        if isinstance(key, str) and key in SAFE_CTX_KEYS
    ]
    referable_items = ctx_hints.get("referable_items")
    unresolved_slots = ctx_hints.get("unresolved_slots")
    referable_item_count = len(referable_items) if isinstance(referable_items, list) else 0
    usable_referable_item_count = _usable_referable_item_count(referable_items)
    unresolved_slot_count = len(unresolved_slots) if isinstance(unresolved_slots, list) else 0
    ctx_handoff_guess = ctx_hints.get("ctx_handoff_guess")
    ctx_handoff_guess_present = (
        isinstance(ctx_handoff_guess, Mapping) and len(ctx_handoff_guess) > 0
    )
    usable_string_keys = [
        key
        for key in ("current_topic", "active_question", "next_expected_action")
        if _usable_string(ctx_hints.get(key))
    ]
    usable_ctx_field_count = len(usable_string_keys) + (
        1 if usable_referable_item_count > 0 else 0
    )
    ctx_signal_present = usable_ctx_field_count > 0
    return {
        "ctx_metadata_present": bool(ctx_hints),
        "ctx_signal_present": ctx_signal_present,
        "trusted_ctx_signal_present": ctx_signal_present,
        "recognized_ctx_field_present": ctx_signal_present,
        "safe_key_count": len(safe_keys),
        "usable_ctx_field_count": usable_ctx_field_count,
        "ctx_signal_key_count": usable_ctx_field_count,
        "referable_item_count": referable_item_count,
        "usable_referable_item_count": usable_referable_item_count,
        "unresolved_slot_count": unresolved_slot_count,
        "ctx_handoff_guess_present": ctx_handoff_guess_present,
        "ctx_handoff_guess_confirmation_candidate": ctx_handoff_guess_present,
    }


def _quick_clarification_candidate_label_kinds(
    *,
    relayint_fast_path_dry_run: Mapping[str, Any],
    ctx_metadata: Mapping[str, Any],
    preflight_applicable: bool,
) -> list[str]:
    if not preflight_applicable:
        return []

    kinds: list[str] = []
    if ctx_metadata.get("ctx_handoff_guess_confirmation_candidate") is True:
        kinds.append("topic_anchor")
    if _positive_int(ctx_metadata.get("usable_referable_item_count")) or _positive_int(
        ctx_metadata.get("referable_item_count")
    ):
        kinds.append("referable_item")
    if relayint_fast_path_dry_run.get("explicit_prior_memory_request_detected") is True:
        kinds.append("prior_memory")
    if not kinds:
        kinds.append("unknown")
    return kinds


def _quick_clarification_type(
    *,
    relayint_fast_path_dry_run: Mapping[str, Any],
    candidate_label_kinds: Sequence[str],
    preflight_applicable: bool,
) -> str:
    if not preflight_applicable:
        return "none"
    if relayint_fast_path_dry_run.get("explicit_prior_memory_request_detected") is True:
        return "prior_memory_reentry"
    if any(kind in {"topic_anchor", "referable_item"} for kind in candidate_label_kinds):
        return "reference_confirmation"
    return "open_clarification"


def _quick_clarification_scene_gate(
    relayscn_scene_policy_artifact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    scene_state: Mapping[str, Any] = {}
    scene_policy: Mapping[str, Any] = {}
    if isinstance(relayscn_scene_policy_artifact, Mapping):
        raw_scene_state = relayscn_scene_policy_artifact.get("scene_state")
        raw_scene_policy = relayscn_scene_policy_artifact.get("scene_policy")
        if isinstance(raw_scene_state, Mapping):
            scene_state = raw_scene_state
        if isinstance(raw_scene_policy, Mapping):
            scene_policy = raw_scene_policy

    scene_type = scene_state.get("scene_type")
    scene_type = scene_type if isinstance(scene_type, str) else "unknown"
    scene_policy_confirmation_required = scene_policy.get("user_confirmation_required") is True
    scene_state_confirmation_required = scene_state.get("user_confirmation_required") is True
    user_confirmation_required = (
        scene_policy_confirmation_required or scene_state_confirmation_required
    )
    recovery_mode = scene_type == "recovery" or scene_state.get("recovery_mode") is True
    block_reasons: list[str] = []
    if scene_type == "recovery":
        block_reasons.append("scene_type_is_recovery")
    if recovery_mode:
        block_reasons.append("recovery_mode_enabled")
    if user_confirmation_required:
        block_reasons.append("user_confirmation_required")
    return {
        "scene_type": scene_type,
        "recovery_mode": recovery_mode,
        "user_confirmation_required": user_confirmation_required,
        "quick_clarification_allowed": not block_reasons,
        "block_reasons": block_reasons,
    }


def _quick_clarification_response_kind(clarification_type: Any) -> str:
    if clarification_type == "prior_memory_reentry":
        return "generic_prior_memory_reentry"
    if clarification_type == "reference_confirmation":
        return "generic_reference_clarification"
    if clarification_type == "open_clarification":
        return "generic_open_clarification"
    return "none"


def _quick_clarification_response_template_id(generated_response_kind: str) -> str:
    if generated_response_kind == "generic_prior_memory_reentry":
        return "generic_prior_memory_reentry.ja.v0"
    if generated_response_kind == "generic_reference_clarification":
        return "generic_reference_clarification.ja.v0"
    if generated_response_kind == "generic_open_clarification":
        return "generic_open_clarification.ja.v0"
    return "none"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and value > 0


def _usable_referable_item_count(referable_items: Any) -> int:
    if not isinstance(referable_items, list):
        return 0
    usable_fields = ("label", "kind", "id", "topic_anchor", "text", "name")
    count = 0
    for item in referable_items:
        if not isinstance(item, Mapping):
            continue
        if any(_usable_string(item.get(field)) for field in usable_fields):
            count += 1
    return count


def _usable_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
