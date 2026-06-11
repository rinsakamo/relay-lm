"""RelayINT fast-path dry-run intent diagnostics."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal
from relaylm.relayref import build_relayref_dry_run_artifact

from relaylm.token_budget import estimate_text_tokens


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
QUICK_CLARIFICATION_RESPONSE_TEMPLATES = (
    "どの話のことか、もう少しだけ教えて。",
    "その話として探す前に、前回の要点をもう一度教えて。",
)


SAFE_CTX_KEYS = {
    "ctx_handoff_guess",
    "current_topic",
    "active_question",
    "referable_items",
    "unresolved_slots",
    "next_expected_action",
}


def build_relayint_reference_repair_dry_run(
    *,
    relayscn_artifact: Mapping[str, Any] | None,
    messages: Sequence[Mapping[str, Any]] | None = None,
    ctx_hints: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build input-side reference/context repair diagnostics.

    This is a compatibility wrapper around the historical RelayREF dry-run
    artifact. The behavior remains unchanged while Phase 4 moves input-side
    unresolved reference handling toward RelayINT terminology.
    """

    artifact = build_relayref_dry_run_artifact(
        relayscn_artifact=relayscn_artifact,
        messages=messages,
        ctx_hints=ctx_hints,
    )
    artifact["relayint_alias"] = True
    artifact["source_compat_module"] = "relayref"
    return artifact


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
    request_compatibility_gate: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build a gated, content-free quick clarification apply plan.

    MVP-47 is Phase 4 plan-only / preflight-only. The plan never calls an LLM,
    never executes MEM lookup, never mutates backend payloads, and never enables
    user-visible response mutation.
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
    compatibility_gate = (
        dict(request_compatibility_gate)
        if isinstance(request_compatibility_gate, Mapping)
        else build_relayint_request_compatibility_gate(None)
    )
    request_compatible = compatibility_gate.get("compatible") is True
    clarification_type = (
        relayint_quick_clarification_preflight.get("clarification_type")
        if preflight_present
        else None
    )
    generated_response_kind = _quick_clarification_response_kind(clarification_type)
    response_template_id = _quick_clarification_response_template_id(
        generated_response_kind
    )
    response_chars = _quick_clarification_response_template_chars(response_template_id)

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
    if not request_compatible:
        for reason in _string_list(compatibility_gate.get("block_reasons")):
            if reason not in block_reasons:
                block_reasons.append(reason)
    if response_template_id == "none" or response_chars == 0:
        block_reasons.append("response_template_missing")
    if response_chars > response_max_chars:
        block_reasons.append("response_max_chars_exceeded")
    block_reasons.append("phase4_plan_only")

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
        "response_short_circuit_allowed": False,
        "short_circuit_applied": False,
        "generated_response_kind": generated_response_kind if apply_allowed else "none",
        "response_template_id": response_template_id if apply_allowed else "none",
        "response_chars": response_chars if apply_allowed else 0,
        "content_free_template": True,
        "request_compatibility_gate": compatibility_gate,
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
        "backend_payload_mutation_applied": False,
        "response_mutation_allowed": False,
        "user_visible_apply_allowed": False,
    }


def _quick_clarification_response_template_chars(template_id: str | None) -> int:
    # Phase 4 keeps this plan content-free and diagnostics-only. Track only the
    # bounded template length that a future apply phase would need for safety
    # gates; do not materialize user-visible clarification text here.
    if template_id == "generic_prior_memory_reentry.ja.v0":
        return 25
    if template_id in {
        "generic_reference_clarification.ja.v0",
        "generic_open_clarification.ja.v0",
    }:
        return 19
    return 0


def build_relayint_request_compatibility_gate(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Summarize structured/tool request constraints without copying values."""

    payload = payload or {}
    response_format_present = (
        "response_format" in payload and payload.get("response_format") is not None
    )
    tools = payload.get("tools")
    tools_count = len(tools) if isinstance(tools, list) else 0
    tool_choice_present = _request_choice_present(payload, "tool_choice")
    functions = payload.get("functions")
    functions_count = len(functions) if isinstance(functions, list) else 0
    function_call_present = _request_choice_present(payload, "function_call")
    n_requested_count, n_block_reason = _n_request_constraint(payload.get("n"))
    max_completion_tokens = _token_limit_constraint(
        payload,
        "max_completion_tokens",
        too_small_reason="max_completion_tokens_too_small",
    )
    max_tokens = _token_limit_constraint(
        payload,
        "max_tokens",
        too_small_reason="max_tokens_too_small",
    )
    numeric_limits = [
        limit
        for limit in (max_completion_tokens["limit"], max_tokens["limit"])
        if isinstance(limit, int | float)
    ]
    max_output_token_limit = min(numeric_limits) if numeric_limits else None
    logprobs_requested = payload.get("logprobs") is True
    top_logprobs_requested = "top_logprobs" in payload and payload.get("top_logprobs") is not None
    stop_present = "stop" in payload and payload.get("stop") is not None
    modalities_gate = _modalities_constraint(payload)

    block_reasons: list[str] = []
    if response_format_present:
        block_reasons.append("response_format_requested")
    if tools_count > 0:
        block_reasons.append("tools_requested")
    if tool_choice_present:
        block_reasons.append("tool_choice_requested")
    if functions_count > 0:
        block_reasons.append("functions_requested")
    if function_call_present:
        block_reasons.append("function_call_requested")
    if n_block_reason is not None:
        block_reasons.append(n_block_reason)
    for reason in max_completion_tokens["block_reasons"]:
        if reason not in block_reasons:
            block_reasons.append(reason)
    for reason in max_tokens["block_reasons"]:
        if reason not in block_reasons:
            block_reasons.append(reason)
    if logprobs_requested:
        block_reasons.append("logprobs_requested")
    if top_logprobs_requested:
        block_reasons.append("top_logprobs_requested")
    if stop_present:
        block_reasons.append("stop_sequence_requested")
    for reason in modalities_gate["block_reasons"]:
        if reason not in block_reasons:
            block_reasons.append(reason)

    return {
        "compatible": not block_reasons,
        "response_format_present": response_format_present,
        "tools_count": tools_count,
        "tool_choice_present": tool_choice_present,
        "functions_count": functions_count,
        "function_call_present": function_call_present,
        "n_requested_count": n_requested_count,
        "max_completion_tokens_present": max_completion_tokens["present"],
        "max_tokens_present": max_tokens["present"],
        "max_output_token_limit": max_output_token_limit,
        "logprobs_requested": logprobs_requested,
        "top_logprobs_requested": top_logprobs_requested,
        "stop_present": stop_present,
        "modalities_present": modalities_gate["modalities_present"],
        "modalities_count": modalities_gate["modalities_count"],
        "audio_modality_requested": modalities_gate["audio_modality_requested"],
        "audio_options_present": modalities_gate["audio_options_present"],
        "block_reasons": block_reasons,
    }


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




def _modalities_constraint(payload: Mapping[str, Any]) -> dict[str, Any]:
    modalities_present = "modalities" in payload and payload.get("modalities") is not None
    modalities_count = 0
    audio_modality_requested = False
    block_reasons: list[str] = []

    if modalities_present:
        modalities = payload.get("modalities")
        if not isinstance(modalities, list) or not modalities:
            block_reasons.append("unsupported_modalities_value")
        else:
            modalities_count = len(modalities)
            unsupported_value = False
            non_text_modality_requested = False
            for modality in modalities:
                if not isinstance(modality, str) or not modality.strip():
                    unsupported_value = True
                    continue
                normalized = modality.strip().lower()
                if normalized == "audio":
                    audio_modality_requested = True
                    non_text_modality_requested = True
                elif normalized != "text":
                    non_text_modality_requested = True
            if unsupported_value:
                block_reasons.append("unsupported_modalities_value")
            if audio_modality_requested:
                block_reasons.append("audio_modality_requested")
            elif non_text_modality_requested:
                block_reasons.append("non_text_modality_requested")

    audio_options_present = "audio" in payload and payload.get("audio") is not None
    if audio_options_present:
        block_reasons.append("audio_options_requested")

    return {
        "modalities_present": modalities_present,
        "modalities_count": modalities_count,
        "audio_modality_requested": audio_modality_requested,
        "audio_options_present": audio_options_present,
        "block_reasons": block_reasons,
    }

def _token_limit_constraint(
    payload: Mapping[str, Any],
    key: str,
    *,
    too_small_reason: str,
) -> dict[str, Any]:
    if key not in payload or payload.get(key) is None:
        return {"present": False, "limit": None, "block_reasons": []}

    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        return {
            "present": True,
            "limit": value if isinstance(value, int | float) and not isinstance(value, bool) else None,
            "block_reasons": ["unsupported_token_limit"],
        }

    block_reasons = ["token_limit_requested"]
    if value < _quick_clarification_response_token_floor():
        block_reasons.append(too_small_reason)
    return {"present": True, "limit": value, "block_reasons": block_reasons}


def _quick_clarification_response_token_floor() -> int:
    estimates = [
        estimate_text_tokens(template).estimated_tokens
        for template in QUICK_CLARIFICATION_RESPONSE_TEMPLATES
    ]
    return max(estimates) if estimates else 0

def _n_request_constraint(value: Any) -> tuple[int | float | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, bool):
        return None, "unsupported_n_value"
    if isinstance(value, int | float):
        if value > 1:
            return value, "multiple_choices_requested"
        if value == 1:
            return value, None
        return value, "unsupported_n_value"
    return None, "unsupported_n_value"

def _request_choice_present(payload: Mapping[str, Any], key: str) -> bool:
    if key not in payload:
        return False
    value = payload.get(key)
    if value is None:
        return False
    if isinstance(value, str) and value == "none":
        return False
    return True

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
