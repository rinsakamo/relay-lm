"""RelayINT request-local reference/intent diagnostics."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from relaylm.reference_intent_analyzer import (
    CONTINUATION_MARKERS,
    PRIOR_MEMORY_REQUEST_MARKERS,
    UNRESOLVED_REFERENCE_MARKERS,
    analyze_reference_intent,
    reference_intent_public_projection,
    relayint_legacy_reference_kind,
)
from relaylm.token_budget import estimate_text_tokens

ReferenceKind = Literal["none", "pronoun_like", "continuation", "prior_memory_request"]
CandidateAction = Literal[
    "continue_without_clarification",
    "ask_clarification",
    "current_context_only",
    "recall_then_answer_candidate",
]

PRONOUN_LIKE_TERMS = UNRESOLVED_REFERENCE_MARKERS
CONTINUATION_TERMS = CONTINUATION_MARKERS
PRIOR_MEMORY_TERMS = PRIOR_MEMORY_REQUEST_MARKERS
QUICK_CLARIFICATION_RESPONSE_TEMPLATES = (
    "どの話のことか、もう少しだけ教えて。",
    "その話として探す前に、前回の要点をもう一度教えて。",
)
SAFE_CTX_KEYS = {"ctx_handoff_guess", "current_topic", "active_question", "referable_items", "unresolved_slots", "next_expected_action"}
LOW_SCENE_CONFIDENCE_THRESHOLD = 0.70
LOW_SCENE_STABILITY_THRESHOLD = 0.65


def build_relayint_reference_intent_artifact(*, relayscn_artifact: Mapping[str, Any] | None, messages: Sequence[Mapping[str, Any]] | None = None, ctx_hints: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build a RelayINT-native runtime-private reference/intent artifact."""
    messages = messages or []
    ctx_hints = ctx_hints or {}
    parsed_scene = _parse_relayscn_artifact(relayscn_artifact)
    ctx_summary = _ctx_metadata_summary(ctx_hints)
    reference_intent = analyze_reference_intent(messages=messages, ctx_hints=ctx_hints, source="heuristic")
    reference_projection = reference_intent_public_projection(reference_intent)
    detected_reference_kind = relayint_legacy_reference_kind(reference_intent)
    prior_memory = bool(reference_intent["prior_memory_request_detected"])
    unresolved = bool(reference_intent["unresolved_reference_detected"])
    continuation = bool(reference_intent["continuation_detected"])
    ctx_signal_present = bool(ctx_summary["ctx_signal_present"])
    fail_closed = _scene_fail_closed(parsed_scene)
    ambiguity = bool(reference_intent.get("ambiguity_detected")) or fail_closed or _ambiguity_detected(detected_reference_kind=detected_reference_kind, ctx_signal_present=ctx_signal_present, explicit_prior_memory=prior_memory)
    reference_terms_count = int(reference_intent.get("reference_terms_detected_count", 0))
    reference_present = bool(unresolved or continuation or prior_memory or reference_terms_count > 0)
    mem_query_needed = prior_memory
    candidate_action = _candidate_action(detected_reference_kind=detected_reference_kind, explicit_prior_memory=prior_memory, ambiguity_detected=ambiguity, ctx_signal_present=ctx_signal_present)
    if fail_closed and not prior_memory:
        candidate_action = "ask_clarification" if reference_present else "current_context_only"
    confidence_bucket = _confidence_bucket(_confidence_score(detected_reference_kind=detected_reference_kind, explicit_prior_memory=prior_memory, ambiguity_detected=ambiguity, ctx_signal_present=ctx_signal_present), high_confidence_threshold=0.80, low_confidence_threshold=0.55)
    resolution_state = _reference_resolution_state(reference_present=reference_present, prior_memory_request=prior_memory, ambiguity_detected=ambiguity, unresolved_reference=unresolved, ctx_signal_present=ctx_signal_present)
    scene_gate = _relayint_scene_gate(parsed_scene)
    reason_ids = _dedupe_reasons([*_string_list(reference_projection.get("reason_ids")), *_string_list(reference_projection.get("validation_error_ids")), *scene_gate["block_reasons"], *_decision_reasons(detected_reference_kind=detected_reference_kind, explicit_prior_memory=prior_memory, ambiguity_detected=ambiguity, mem_query_needed=mem_query_needed, ctx_signal_present=ctx_signal_present)])
    projection = _relayint_projection(reference_present=reference_present, reference_resolved=resolution_state == "resolved_in_current_context", ambiguity_present=ambiguity, prior_memory_request_detected=prior_memory, mem_query_needed_candidate=mem_query_needed, confidence_band=confidence_bucket, action=candidate_action, reason_ids=reason_ids, reference_intent_projection=reference_projection)
    mode_reasons = _legacy_mode_reasons(parsed_scene=parsed_scene, unresolved_reference=unresolved, ambiguity_detected=ambiguity, reason_ids=reason_ids)
    mode = "suggest_reflect" if mode_reasons else "none"
    return {
        "schema_version": "relayint.intent.v1",
        "runtime_private": True,
        "diagnostics_only": True,
        "content_free": True,
        "request_local": True,
        "source": "heuristic",
        "llm_called": False,
        "mem_lookup_executed": False,
        "backend_payload_mutation_allowed": False,
        "response_mutation_allowed": False,
        "apply_allowed": False,
        "auto_resume_allowed": False,
        "reference_present": reference_present,
        "unresolved_reference_detected": unresolved,
        "continuation_detected": continuation,
        "prior_memory_request_detected": prior_memory,
        "ambiguity_detected": ambiguity,
        "reference_resolution_state": resolution_state,
        "candidate_action": candidate_action,
        "mem_query_needed_candidate": mem_query_needed,
        "mem_query_allowed": False,
        "confidence_bucket": confidence_bucket,
        "reason_ids": reason_ids,
        "scene_gate": scene_gate,
        "safety_gates": {"content_free": True, "llm_call_allowed": False, "mem_lookup_allowed": False, "backend_payload_mutation_allowed": False, "response_mutation_allowed": False, "memory_mutation_allowed": False, "soul_mutation_allowed": False},
        "reference_intent_analyzer": reference_projection,
        "relayint_projection": projection,
        "projection": projection,
        "mode": mode,
        "mode_reasons": mode_reasons,
        "context_rewrite": {"candidate": mode != "none", "applied": False, "auto_resume_allowed": False},
        "forced_sleep_candidate": _build_forced_sleep_candidate(parsed_scene["scene_policy"]),
    }


def build_relayint_reference_repair_dry_run(*, relayscn_artifact: Mapping[str, Any] | None, messages: Sequence[Mapping[str, Any]] | None = None, ctx_hints: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Deprecated function name retained as a RelayINT-native entrypoint."""
    return build_relayint_reference_intent_artifact(relayscn_artifact=relayscn_artifact, messages=messages, ctx_hints=ctx_hints)


def build_relayint_fast_path_dry_run(*, messages: Sequence[Mapping[str, Any]], ctx_hints: Mapping[str, Any] | None = None, enabled: bool = False, high_confidence_threshold: float = 0.80, low_confidence_threshold: float = 0.55) -> dict[str, Any] | None:
    if not enabled:
        return None
    latest_user_text = _latest_user_text(messages)
    ctx_summary = _ctx_metadata_summary(ctx_hints or {})
    reference_intent = analyze_reference_intent(messages=messages, ctx_hints=ctx_hints or {})
    detected_reference_kind = relayint_legacy_reference_kind(reference_intent)
    explicit_prior_memory = bool(reference_intent["prior_memory_request_detected"])
    reference_terms_count = int(reference_intent["reference_terms_detected_count"])
    ctx_signal_present = bool(ctx_summary["ctx_signal_present"])
    analyzer_ambiguity_detected = bool(reference_intent.get("ambiguity_detected"))
    legacy_ambiguity_detected = _ambiguity_detected(detected_reference_kind=detected_reference_kind, ctx_signal_present=ctx_signal_present, explicit_prior_memory=explicit_prior_memory)
    ambiguity_detected = analyzer_ambiguity_detected or legacy_ambiguity_detected
    mem_query_needed = explicit_prior_memory
    candidate_action = _candidate_action(detected_reference_kind=detected_reference_kind, explicit_prior_memory=explicit_prior_memory, ambiguity_detected=ambiguity_detected, ctx_signal_present=ctx_signal_present)
    confidence_score = _confidence_score(detected_reference_kind=detected_reference_kind, explicit_prior_memory=explicit_prior_memory, ambiguity_detected=ambiguity_detected, ctx_signal_present=ctx_signal_present)
    confidence_bucket = _confidence_bucket(confidence_score, high_confidence_threshold=high_confidence_threshold, low_confidence_threshold=low_confidence_threshold)
    llm_path_reasons = _llm_path_reasons(ambiguity_detected=ambiguity_detected, confidence_bucket=confidence_bucket, detected_reference_kind=detected_reference_kind)
    decision_reasons = _decision_reasons(detected_reference_kind=detected_reference_kind, explicit_prior_memory=explicit_prior_memory, ambiguity_detected=ambiguity_detected, mem_query_needed=mem_query_needed, ctx_signal_present=ctx_signal_present)
    if reference_terms_count > 0:
        decision_reasons.append("reference_intent_analyzer_candidate")
    if analyzer_ambiguity_detected:
        decision_reasons.append("reference_intent_analyzer_ambiguity")
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
        "reference_intent_analyzer": reference_intent_public_projection(reference_intent),
        "safety_gates": {"content_free": True, "llm_call_allowed": False, "mem_lookup_allowed": False, "backend_payload_mutation_allowed": False, "response_mutation_allowed": False},
    }


def build_relayint_quick_clarification_preflight(*, relayint_fast_path_dry_run: Mapping[str, Any] | None, relayscn_scene_policy_artifact: Mapping[str, Any] | None = None, enabled: bool = False, dry_run_only: bool = True) -> dict[str, Any] | None:
    if not enabled or not isinstance(relayint_fast_path_dry_run, Mapping):
        return None
    source_candidate_action = relayint_fast_path_dry_run.get("candidate_action")
    scene_gate = _quick_clarification_scene_gate(relayscn_scene_policy_artifact)
    preflight_applicable = source_candidate_action == "ask_clarification" and scene_gate["quick_clarification_allowed"] is True
    ctx_metadata = relayint_fast_path_dry_run.get("ctx_working_metadata") if isinstance(relayint_fast_path_dry_run.get("ctx_working_metadata"), Mapping) else {}
    candidate_label_kinds = _quick_clarification_candidate_label_kinds(relayint_fast_path_dry_run=relayint_fast_path_dry_run, ctx_metadata=ctx_metadata, preflight_applicable=preflight_applicable)
    clarification_type = _quick_clarification_type(relayint_fast_path_dry_run=relayint_fast_path_dry_run, candidate_label_kinds=candidate_label_kinds, preflight_applicable=preflight_applicable)
    return {
        "schema_version": "relayint_quick_clarification_preflight.v0",
        "enabled": True,
        "dry_run_only": dry_run_only,
        "content_free": True,
        "source_artifact_schema_version": relayint_fast_path_dry_run.get("schema_version") if isinstance(relayint_fast_path_dry_run.get("schema_version"), str) else None,
        "source_candidate_action": source_candidate_action if isinstance(source_candidate_action, str) else None,
        "preflight_applicable": preflight_applicable,
        "clarification_type": clarification_type,
        "candidate_count": len(candidate_label_kinds),
        "candidate_labels_are_content_free": True,
        "candidate_label_kinds": candidate_label_kinds,
        "suggested_response_mode": "quick_clarification_candidate" if preflight_applicable else "no_quick_clarification",
        "scene_gate": scene_gate,
        "quick_clarification_block_reasons": scene_gate["block_reasons"],
        "safety_gates": {"content_free": True, "llm_call_allowed": False, "mem_lookup_allowed": False, "backend_payload_mutation_allowed": False, "response_mutation_allowed": False, "user_visible_apply_allowed": False},
        "llm_called": False,
        "mem_lookup_executed": False,
        "backend_payload_mutation_allowed": False,
        "response_mutation_allowed": False,
        "user_visible_apply_allowed": False,
    }


def build_relayint_quick_clarification_apply_plan(*, relayint_quick_clarification_preflight: Mapping[str, Any] | None, enabled: bool = False, dry_run_only: bool = True, stream_enabled: bool = False, response_max_chars: int = 120, request_compatibility_gate: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    if not enabled:
        return None
    preflight_present = isinstance(relayint_quick_clarification_preflight, Mapping)
    compatibility_gate = dict(request_compatibility_gate) if isinstance(request_compatibility_gate, Mapping) else build_relayint_request_compatibility_gate(None)
    scene_gate = relayint_quick_clarification_preflight.get("scene_gate") if preflight_present else None
    clarification_type = relayint_quick_clarification_preflight.get("clarification_type") if preflight_present else None
    generated_response_kind = _quick_clarification_response_kind(clarification_type)
    response_template_id = _quick_clarification_response_template_id(generated_response_kind)
    response_chars = _quick_clarification_response_template_chars(response_template_id)
    source_preflight_applicable = relayint_quick_clarification_preflight.get("preflight_applicable") is True if preflight_present else False
    block_reasons: list[str] = []
    if not preflight_present:
        block_reasons.append("preflight_missing")
    if preflight_present and not source_preflight_applicable:
        block_reasons.append("preflight_not_applicable")
    if preflight_present and not (isinstance(scene_gate, Mapping) and scene_gate.get("quick_clarification_allowed") is True):
        block_reasons.append("scene_gate_blocked")
        if isinstance(scene_gate, Mapping):
            block_reasons.extend(reason for reason in _string_list(scene_gate.get("block_reasons")) if reason not in block_reasons)
    if dry_run_only:
        block_reasons.append("dry_run_only")
    if stream_enabled:
        block_reasons.append("streaming_not_supported")
    if compatibility_gate.get("compatible") is not True:
        block_reasons.extend(reason for reason in _string_list(compatibility_gate.get("block_reasons")) if reason not in block_reasons)
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
        "source_artifact_schema_version": relayint_quick_clarification_preflight.get("schema_version") if preflight_present and isinstance(relayint_quick_clarification_preflight.get("schema_version"), str) else None,
        "source_preflight_applicable": source_preflight_applicable,
        "apply_allowed": apply_allowed,
        "apply_block_reasons": block_reasons,
        "response_short_circuit_allowed": False,
        "short_circuit_applied": False,
        "generated_response_kind": generated_response_kind if apply_allowed else "none",
        "response_template_id": response_template_id if apply_allowed else "none",
        "response_chars": response_chars if apply_allowed else 0,
        "request_compatibility_gate": compatibility_gate,
        "safety_gates": {"content_free": True, "llm_call_allowed": False, "mem_lookup_allowed": False, "backend_payload_mutation_allowed": False, "response_mutation_allowed": False, "user_visible_apply_allowed": False},
        "llm_called": False,
        "mem_lookup_executed": False,
        "backend_payload_mutation_allowed": False,
        "backend_payload_mutation_applied": False,
        "response_mutation_allowed": False,
        "user_visible_apply_allowed": False,
    }


def build_relayint_request_compatibility_gate(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    response_format_present = "response_format" in payload and payload.get("response_format") is not None
    tools = payload.get("tools")
    functions = payload.get("functions")
    tools_count = len(tools) if isinstance(tools, list) else 0
    functions_count = len(functions) if isinstance(functions, list) else 0
    n_requested_count, n_block_reason = _n_request_constraint(payload.get("n"))
    max_completion_tokens = _token_limit_constraint(payload, "max_completion_tokens", too_small_reason="max_completion_tokens_too_small")
    max_tokens = _token_limit_constraint(payload, "max_tokens", too_small_reason="max_tokens_too_small")
    modalities_gate = _modalities_constraint(payload)
    numeric_limits = [limit for limit in (max_completion_tokens["limit"], max_tokens["limit"]) if isinstance(limit, int | float)]
    block_reasons: list[str] = []
    for condition, reason in (
        (response_format_present, "response_format_requested"),
        (tools_count > 0, "tools_requested"),
        (_request_choice_present(payload, "tool_choice"), "tool_choice_requested"),
        (functions_count > 0, "functions_requested"),
        (_request_choice_present(payload, "function_call"), "function_call_requested"),
        (n_block_reason is not None, n_block_reason),
        (payload.get("logprobs") is True, "logprobs_requested"),
        ("top_logprobs" in payload and payload.get("top_logprobs") is not None, "top_logprobs_requested"),
        ("stop" in payload and payload.get("stop") is not None, "stop_sequence_requested"),
    ):
        if condition and isinstance(reason, str):
            block_reasons.append(reason)
    for gate in (max_completion_tokens, max_tokens, modalities_gate):
        for reason in gate["block_reasons"]:
            if reason not in block_reasons:
                block_reasons.append(reason)
    return {"compatible": not block_reasons, "response_format_present": response_format_present, "tools_count": tools_count, "tool_choice_present": _request_choice_present(payload, "tool_choice"), "functions_count": functions_count, "function_call_present": _request_choice_present(payload, "function_call"), "n_requested_count": n_requested_count, "max_completion_tokens_present": max_completion_tokens["present"], "max_tokens_present": max_tokens["present"], "max_output_token_limit": min(numeric_limits) if numeric_limits else None, "logprobs_requested": payload.get("logprobs") is True, "top_logprobs_requested": "top_logprobs" in payload and payload.get("top_logprobs") is not None, "stop_present": "stop" in payload and payload.get("stop") is not None, "modalities_present": modalities_gate["modalities_present"], "modalities_count": modalities_gate["modalities_count"], "audio_modality_requested": modalities_gate["audio_modality_requested"], "audio_options_present": modalities_gate["audio_options_present"], "block_reasons": block_reasons}


def _relayint_projection(*, reference_present: bool, reference_resolved: bool, ambiguity_present: bool, prior_memory_request_detected: bool, mem_query_needed_candidate: bool, confidence_band: str, action: str, reason_ids: Sequence[str], reference_intent_projection: Mapping[str, Any]) -> dict[str, Any]:
    raw_count = reference_intent_projection.get("reference_terms_detected_count")
    ambiguity_candidate_count = raw_count if isinstance(raw_count, int) and raw_count > 1 and ambiguity_present else 1 if ambiguity_present else 0
    return {"schema_version": "relayint.projection.v1", "content_free": True, "diagnostics_only": True, "llm_called": False, "mem_lookup_executed": False, "backend_payload_mutation_allowed": False, "response_mutation_allowed": False, "reference_present": reference_present, "reference_resolved": reference_resolved, "ambiguity_present": ambiguity_present, "ambiguity_candidate_count": ambiguity_candidate_count, "prior_memory_request_detected": prior_memory_request_detected, "mem_query_needed_candidate": mem_query_needed_candidate, "mem_query_allowed": False, "confidence_band": confidence_band, "action": action, "reason_ids": list(reason_ids)}


def _parse_relayscn_artifact(relayscn_artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(relayscn_artifact, Mapping):
        return {"malformed": True, "scene_state": {"scene_type": "unknown", "confidence": 0.0, "stability": 0.0}, "scene_policy": {}, "persistence_block": True, "persistence_block_reasons": ["malformed_relayscn_artifact"]}
    scene_state = relayscn_artifact.get("scene_state")
    scene_policy = relayscn_artifact.get("scene_policy")
    return {"malformed": not isinstance(scene_state, Mapping) or not isinstance(scene_policy, Mapping), "scene_state": dict(scene_state) if isinstance(scene_state, Mapping) else {}, "scene_policy": dict(scene_policy) if isinstance(scene_policy, Mapping) else {}, "persistence_block": relayscn_artifact.get("persistence_block"), "persistence_block_reasons": _string_list(relayscn_artifact.get("persistence_block_reasons"))}


def _relayint_scene_gate(parsed_scene: Mapping[str, Any]) -> dict[str, Any]:
    scene_state = parsed_scene.get("scene_state") if isinstance(parsed_scene.get("scene_state"), Mapping) else {}
    scene_type = scene_state.get("scene_type") if isinstance(scene_state, Mapping) else None
    confidence = _coerce_probability(scene_state.get("confidence") if isinstance(scene_state, Mapping) else None, default=0.0)
    stability = _coerce_probability(scene_state.get("stability") if isinstance(scene_state, Mapping) else None, default=0.0)
    block_reasons: list[str] = []
    if parsed_scene.get("malformed") is True:
        block_reasons.append("malformed_relayscn_artifact")
    if scene_type == "recovery":
        block_reasons.append("recovery_scene")
    if not isinstance(scene_type, str) or not scene_type or scene_type == "unknown":
        block_reasons.append("unknown_scene")
    if confidence < LOW_SCENE_CONFIDENCE_THRESHOLD:
        block_reasons.append("scene_confidence_below_threshold")
    if stability < LOW_SCENE_STABILITY_THRESHOLD:
        block_reasons.append("scene_stability_below_threshold")
    return {"content_free": True, "source": "relayscn_scene_policy_artifact", "scene_type": scene_type if isinstance(scene_type, str) else "unknown", "scene_confidence_band": _confidence_bucket(confidence, high_confidence_threshold=0.80, low_confidence_threshold=0.55), "scene_stability_band": _confidence_bucket(stability, high_confidence_threshold=0.80, low_confidence_threshold=0.55), "restrictive_only": bool(block_reasons), "block_reasons": _dedupe_reasons(block_reasons)}


def _scene_fail_closed(parsed_scene: Mapping[str, Any]) -> bool:
    return bool(_relayint_scene_gate(parsed_scene)["block_reasons"])


def _legacy_mode_reasons(*, parsed_scene: Mapping[str, Any], unresolved_reference: bool, ambiguity_detected: bool, reason_ids: Sequence[str]) -> list[str]:
    reasons = list(_relayint_scene_gate(parsed_scene)["block_reasons"])
    if unresolved_reference:
        reasons.append("unresolved_reference_detected")
    if ambiguity_detected:
        reasons.append("ambiguous_reference_detected")
    reasons.extend(reason for reason in reason_ids if reason.startswith(("invalid_", "unknown_")))
    return _dedupe_reasons(reasons)


def _reference_resolution_state(*, reference_present: bool, prior_memory_request: bool, ambiguity_detected: bool, unresolved_reference: bool, ctx_signal_present: bool) -> str:
    if prior_memory_request:
        return "prior_memory_requested"
    if not reference_present:
        return "none"
    if ambiguity_detected:
        return "ambiguous"
    if unresolved_reference and not ctx_signal_present:
        return "unresolved"
    return "resolved_in_current_context" if ctx_signal_present else "none"


def _latest_user_text(messages: Sequence[Mapping[str, Any]]) -> str:
    for message in reversed(messages):
        if isinstance(message, Mapping) and message.get("role") == "user":
            return _content_text(message.get("content"))
    return ""


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, Sequence) and not isinstance(content, str):
        return "\n".join(item["text"] for item in content if isinstance(item, Mapping) and item.get("type") == "text" and isinstance(item.get("text"), str))
    return ""


def _ambiguity_detected(*, detected_reference_kind: ReferenceKind | str, ctx_signal_present: bool, explicit_prior_memory: bool) -> bool:
    return False if detected_reference_kind == "none" or explicit_prior_memory else not ctx_signal_present


def _candidate_action(*, detected_reference_kind: ReferenceKind | str, explicit_prior_memory: bool, ambiguity_detected: bool, ctx_signal_present: bool) -> CandidateAction:
    if explicit_prior_memory:
        return "recall_then_answer_candidate"
    if ambiguity_detected:
        return "ask_clarification"
    if detected_reference_kind in {"continuation", "pronoun_like"} and ctx_signal_present:
        return "continue_without_clarification"
    return "current_context_only"


def _confidence_score(*, detected_reference_kind: ReferenceKind | str, explicit_prior_memory: bool, ambiguity_detected: bool, ctx_signal_present: bool) -> float:
    if explicit_prior_memory:
        return 0.82
    if ambiguity_detected:
        return 0.48
    if detected_reference_kind in {"continuation", "pronoun_like"} and ctx_signal_present:
        return 0.84
    if detected_reference_kind == "none":
        return 0.74
    return 0.60


def _confidence_bucket(confidence_score: float, *, high_confidence_threshold: float, low_confidence_threshold: float) -> str:
    if confidence_score >= high_confidence_threshold:
        return "high"
    if confidence_score < low_confidence_threshold:
        return "low"
    return "medium"


def _llm_path_reasons(*, ambiguity_detected: bool, confidence_bucket: str, detected_reference_kind: ReferenceKind | str) -> list[str]:
    reasons: list[str] = []
    if ambiguity_detected:
        reasons.append("ambiguous_reference_without_ctx_working_signal")
    if confidence_bucket == "low":
        reasons.append("low_confidence_fast_path")
    if detected_reference_kind == "prior_memory_request":
        reasons.append("prior_memory_request_needs_retrieval_planning")
    return reasons


def _decision_reasons(*, detected_reference_kind: ReferenceKind | str, explicit_prior_memory: bool, ambiguity_detected: bool, mem_query_needed: bool, ctx_signal_present: bool) -> list[str]:
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
    referable_items = ctx_hints.get("referable_items")
    unresolved_slots = ctx_hints.get("unresolved_slots")
    referable_item_count = len(referable_items) if isinstance(referable_items, list) else 0
    usable_referable_item_count = _usable_referable_item_count(referable_items)
    usable_string_keys = [key for key in ("current_topic", "active_question", "next_expected_action") if _usable_string(ctx_hints.get(key))]
    usable_ctx_field_count = len(usable_string_keys) + (1 if usable_referable_item_count > 0 else 0)
    ctx_handoff_guess = ctx_hints.get("ctx_handoff_guess")
    ctx_handoff_guess_present = isinstance(ctx_handoff_guess, Mapping) and len(ctx_handoff_guess) > 0
    return {"ctx_metadata_present": bool(ctx_hints), "ctx_signal_present": usable_ctx_field_count > 0, "trusted_ctx_signal_present": usable_ctx_field_count > 0, "recognized_ctx_field_present": usable_ctx_field_count > 0, "safe_key_count": len([key for key in ctx_hints if isinstance(key, str) and key in SAFE_CTX_KEYS]), "usable_ctx_field_count": usable_ctx_field_count, "ctx_signal_key_count": usable_ctx_field_count, "referable_item_count": referable_item_count, "usable_referable_item_count": usable_referable_item_count, "unresolved_slot_count": len(unresolved_slots) if isinstance(unresolved_slots, list) else 0, "ctx_handoff_guess_present": ctx_handoff_guess_present, "ctx_handoff_guess_confirmation_candidate": ctx_handoff_guess_present}


def _quick_clarification_candidate_label_kinds(*, relayint_fast_path_dry_run: Mapping[str, Any], ctx_metadata: Mapping[str, Any], preflight_applicable: bool) -> list[str]:
    if not preflight_applicable:
        return []
    kinds: list[str] = []
    if ctx_metadata.get("ctx_handoff_guess_confirmation_candidate") is True:
        kinds.append("topic_anchor")
    if _positive_int(ctx_metadata.get("usable_referable_item_count")) or _positive_int(ctx_metadata.get("referable_item_count")):
        kinds.append("referable_item")
    if relayint_fast_path_dry_run.get("explicit_prior_memory_request_detected") is True:
        kinds.append("prior_memory")
    return kinds or ["unknown"]


def _quick_clarification_type(*, relayint_fast_path_dry_run: Mapping[str, Any], candidate_label_kinds: Sequence[str], preflight_applicable: bool) -> str:
    if not preflight_applicable:
        return "none"
    if relayint_fast_path_dry_run.get("explicit_prior_memory_request_detected") is True:
        return "prior_memory_reentry"
    if any(kind in {"topic_anchor", "referable_item"} for kind in candidate_label_kinds):
        return "reference_confirmation"
    return "open_clarification"


def _quick_clarification_scene_gate(relayscn_scene_policy_artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    scene_state: Mapping[str, Any] = {}
    scene_policy: Mapping[str, Any] = {}
    if isinstance(relayscn_scene_policy_artifact, Mapping):
        if isinstance(relayscn_scene_policy_artifact.get("scene_state"), Mapping):
            scene_state = relayscn_scene_policy_artifact["scene_state"]
        if isinstance(relayscn_scene_policy_artifact.get("scene_policy"), Mapping):
            scene_policy = relayscn_scene_policy_artifact["scene_policy"]
    scene_type = scene_state.get("scene_type") if isinstance(scene_state.get("scene_type"), str) else "unknown"
    user_confirmation_required = scene_policy.get("user_confirmation_required") is True or scene_state.get("user_confirmation_required") is True
    recovery_mode = scene_type == "recovery" or scene_state.get("recovery_mode") is True
    block_reasons: list[str] = []
    if scene_type == "recovery":
        block_reasons.append("scene_type_is_recovery")
    if recovery_mode:
        block_reasons.append("recovery_mode_enabled")
    if user_confirmation_required:
        block_reasons.append("user_confirmation_required")
    return {"scene_type": scene_type, "recovery_mode": recovery_mode, "user_confirmation_required": user_confirmation_required, "quick_clarification_allowed": not block_reasons, "block_reasons": block_reasons}


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
            non_text_modality_requested = False
            for modality in modalities:
                if not isinstance(modality, str) or not modality.strip():
                    block_reasons.append("unsupported_modalities_value")
                    continue
                normalized = modality.strip().lower()
                if normalized == "audio":
                    audio_modality_requested = True
                    non_text_modality_requested = True
                elif normalized != "text":
                    non_text_modality_requested = True
            if audio_modality_requested:
                block_reasons.append("audio_modality_requested")
            elif non_text_modality_requested:
                block_reasons.append("non_text_modality_requested")
    audio_options_present = "audio" in payload and payload.get("audio") is not None
    if audio_options_present:
        block_reasons.append("audio_options_requested")
    return {"modalities_present": modalities_present, "modalities_count": modalities_count, "audio_modality_requested": audio_modality_requested, "audio_options_present": audio_options_present, "block_reasons": _dedupe_reasons(block_reasons)}


def _token_limit_constraint(payload: Mapping[str, Any], key: str, *, too_small_reason: str) -> dict[str, Any]:
    if key not in payload or payload.get(key) is None:
        return {"present": False, "limit": None, "block_reasons": []}
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        return {"present": True, "limit": value if isinstance(value, int | float) and not isinstance(value, bool) else None, "block_reasons": ["unsupported_token_limit"]}
    block_reasons = ["token_limit_requested"]
    if value < _quick_clarification_response_token_floor():
        block_reasons.append(too_small_reason)
    return {"present": True, "limit": value, "block_reasons": block_reasons}


def _quick_clarification_response_token_floor() -> int:
    estimates = [estimate_text_tokens(template).estimated_tokens for template in QUICK_CLARIFICATION_RESPONSE_TEMPLATES]
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
    value = payload.get(key)
    return False if value is None or (isinstance(value, str) and value == "none") else key in payload


def _quick_clarification_response_kind(clarification_type: Any) -> str:
    return {"prior_memory_reentry": "generic_prior_memory_reentry", "reference_confirmation": "generic_reference_clarification", "open_clarification": "generic_open_clarification"}.get(clarification_type, "none")


def _quick_clarification_response_template_id(generated_response_kind: str) -> str:
    return {"generic_prior_memory_reentry": "generic_prior_memory_reentry.ja.v0", "generic_reference_clarification": "generic_reference_clarification.ja.v0", "generic_open_clarification": "generic_open_clarification.ja.v0"}.get(generated_response_kind, "none")


def _quick_clarification_response_template_chars(template_id: str | None) -> int:
    if template_id == "generic_prior_memory_reentry.ja.v0":
        return 25
    if template_id in {"generic_reference_clarification.ja.v0", "generic_open_clarification.ja.v0"}:
        return 19
    return 0


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
    return sum(1 for item in referable_items if isinstance(item, Mapping) and any(_usable_string(item.get(field)) for field in usable_fields))


def _usable_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _coerce_probability(value: Any, *, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, int | float):
        numeric = float(value)
        if 0.0 <= numeric <= 1.0:
            return numeric
    return default


def _build_forced_sleep_candidate(scene_policy: Mapping[str, Any]) -> dict[str, Any]:
    slp_mode = scene_policy.get("slp_mode") if isinstance(scene_policy, Mapping) else None
    candidate = slp_mode in {"forced", "forced_or_recently_attempted"}
    return {"candidate": candidate, "slp_mode": slp_mode if isinstance(slp_mode, str) else None, "apply_allowed": False, "reason": "relayscn_slp_mode" if candidate else None}


def _dedupe_reasons(reasons: Sequence[str]) -> list[str]:
    deduped: list[str] = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)
    return deduped
