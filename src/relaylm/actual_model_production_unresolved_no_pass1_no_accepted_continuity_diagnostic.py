"""Evaluation-only #2715 discriminator without accepted Continuity context.

The baseline is the merged #2700 unresolved-only/no-Pass1 request. The
treatment starts from the already-canonical compiled T2 CognitiveInput and
removes only its leading projected accepted-Continuity ContextItems. State
selection and every other CognitiveInput field therefore remain fixed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any

from relaylm.actual_model_production_continuity_only_diagnostic import (
    _overlay_tail,
    _require_same_nonprojection_fields,
    _response_schema,
    _user_content,
)
from relaylm.actual_model_production_continuity_overlay_diagnostic import (
    RetainedFormationBinding,
    apply_overlay_to_production_request_body,
)
from relaylm.actual_model_production_unresolved_no_pass1_diagnostic import (
    UnresolvedNoPass1Request,
    _build_no_pass1_body,
    build_unresolved_no_pass1_extraction_request_body,
    parse_unresolved_no_pass1_completion,
)
from relaylm.actual_model_request_evidence import canonical_request_body_sha256
from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
)
from relaylm.continuity import CONTINUITY_EPISTEMIC_ROLES, CONTINUITY_KINDS
from relaylm.providers.openai_compatible import (
    ProviderProtocolError,
    serialize_cognitive_input,
)
from relaylm.providers.openai_compatible_extraction_projection import (
    unresolved_only_continuity_extraction_component,
    unresolved_only_extraction_intro,
    unresolved_only_extraction_outro,
)
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.providers.openai_compatible_two_pass import _common_cognitive_prefix


DIAGNOSTIC_NAME = (
    "production-context-unresolved-only-no-pass1-no-accepted-continuity"
)
CONDITION_ID = (
    "stage-r-llama-cpp-production-context-unresolved-only-no-pass1-"
    "no-accepted-continuity-t2-v1"
)
SCHEMA_VERSION = (
    "relaylm-production-context-unresolved-only-no-pass1-"
    "no-accepted-continuity-v1"
)


@dataclass(frozen=True, slots=True)
class UnresolvedNoPass1NoAcceptedContinuityRequest:
    baseline: UnresolvedNoPass1Request
    treatment_cognitive_input: CognitiveInput
    treatment_body: dict[str, Any]
    treatment_overlay_body: dict[str, Any]
    baseline_cognitive_input: dict[str, Any]
    treatment_cognitive_input_serialized: dict[str, Any]
    removed_context_items: tuple[dict[str, Any], ...]
    diff_receipt: dict[str, Any]


def build_unresolved_no_pass1_no_accepted_continuity_request_body(
    *,
    provider: Any,
    extraction_input: CognitionExtractionInput,
    pass_request: CognitionPassRequest | None,
    binding: RetainedFormationBinding,
    reasoning_request: OpenAICompatibleReasoningRequest | None = None,
) -> UnresolvedNoPass1NoAcceptedContinuityRequest:
    """Hold #2700 fixed and remove only projected accepted Continuity context."""

    baseline = build_unresolved_no_pass1_extraction_request_body(
        provider=provider,
        extraction_input=extraction_input,
        pass_request=pass_request,
        binding=binding,
        reasoning_request=reasoning_request,
    )
    treatment_cognitive_input, removed_items = _without_accepted_continuity_context(
        extraction_input.cognitive_input
    )
    treatment_extraction_input = CognitionExtractionInput(
        cognitive_input=treatment_cognitive_input,
        assistant_response=extraction_input.assistant_response,
    )
    treatment_body = _build_no_pass1_body(
        extraction_input=treatment_extraction_input,
        baseline_body=baseline.no_pass1_body,
    )
    treatment_overlay_body = apply_overlay_to_production_request_body(
        baseline_body=treatment_body,
        model_overlay=baseline.baseline.model_overlay,
    )
    baseline_serialized = serialize_cognitive_input(extraction_input.cognitive_input)
    treatment_serialized = serialize_cognitive_input(treatment_cognitive_input)
    removed_serialized = tuple(_serialize_context_item(item) for item in removed_items)
    receipt = _validate_and_describe_delta(
        extraction_input=extraction_input,
        baseline=baseline,
        treatment_cognitive_input=treatment_cognitive_input,
        treatment_body=treatment_body,
        treatment_overlay_body=treatment_overlay_body,
        baseline_serialized=baseline_serialized,
        treatment_serialized=treatment_serialized,
        removed_serialized=removed_serialized,
    )
    return UnresolvedNoPass1NoAcceptedContinuityRequest(
        baseline=baseline,
        treatment_cognitive_input=treatment_cognitive_input,
        treatment_body=treatment_body,
        treatment_overlay_body=treatment_overlay_body,
        baseline_cognitive_input=baseline_serialized,
        treatment_cognitive_input_serialized=treatment_serialized,
        removed_context_items=removed_serialized,
        diff_receipt=receipt,
    )


def parse_unresolved_no_pass1_no_accepted_continuity_completion(
    envelope: Any,
    *,
    cognitive_input: CognitiveInput,
) -> CognitionExtractionOutput:
    """Reuse the canonical unresolved-only parser/source validation."""

    return parse_unresolved_no_pass1_completion(
        envelope,
        cognitive_input=cognitive_input,
    )


def _without_accepted_continuity_context(
    cognitive_input: CognitiveInput,
) -> tuple[CognitiveInput, tuple[ContextItem, ...]]:
    context = cognitive_input.context
    prefix_length = 0
    while prefix_length < len(context) and context[prefix_length].actor is None:
        _require_canonical_projected_continuity_item(context[prefix_length])
        prefix_length += 1

    if prefix_length == 0:
        raise ProviderProtocolError(
            "canonical T2 CognitiveInput has no projected accepted Continuity prefix"
        )

    remaining = context[prefix_length:]
    if any(item.actor not in {"user", "assistant"} for item in remaining):
        raise ProviderProtocolError(
            "canonical T2 working context boundary is not structurally exact"
        )

    removed = context[:prefix_length]
    treatment = replace(cognitive_input, context=remaining)
    _require_same_noncontext_cognitive_input(cognitive_input, treatment)
    return treatment, removed


def _require_canonical_projected_continuity_item(item: ContextItem) -> None:
    if item.actor is not None:
        raise ProviderProtocolError("accepted Continuity projection must have actor=None")
    if not item.sources:
        raise ProviderProtocolError(
            "accepted Continuity projection must preserve non-empty sources"
        )
    try:
        payload = json.loads(item.content)
    except json.JSONDecodeError as exc:
        raise ProviderProtocolError(
            "accepted Continuity projection is not canonical JSON"
        ) from exc
    if not isinstance(payload, dict) or set(payload) != {"continuity"}:
        raise ProviderProtocolError(
            "accepted Continuity projection must contain only continuity"
        )
    continuity = payload["continuity"]
    if not isinstance(continuity, dict) or set(continuity) != {
        "kind",
        "key",
        "value",
        "epistemic_role",
    }:
        raise ProviderProtocolError(
            "accepted Continuity projection has unexpected semantic fields"
        )
    if continuity["kind"] not in CONTINUITY_KINDS:
        raise ProviderProtocolError(
            "accepted Continuity projection has unsupported kind"
        )
    key = continuity["key"]
    if not isinstance(key, str) or not key.strip():
        raise ProviderProtocolError(
            "accepted Continuity projection key must be non-empty"
        )
    if continuity["epistemic_role"] not in CONTINUITY_EPISTEMIC_ROLES:
        raise ProviderProtocolError(
            "accepted Continuity projection has unsupported epistemic_role"
        )


def _require_same_noncontext_cognitive_input(
    baseline: CognitiveInput,
    treatment: CognitiveInput,
) -> None:
    for field_name in (
        "identity",
        "state_classes",
        "state",
        "input",
        "knowledge",
        "memory",
        "event_evidence",
    ):
        if getattr(baseline, field_name) != getattr(treatment, field_name):
            raise ProviderProtocolError(
                f"no-accepted-Continuity treatment changed CognitiveInput.{field_name}"
            )


def _serialize_context_item(item: ContextItem) -> dict[str, Any]:
    return {
        "content": item.content,
        "sources": list(item.sources),
        "actor": item.actor,
    }


def _validate_and_describe_delta(
    *,
    extraction_input: CognitionExtractionInput,
    baseline: UnresolvedNoPass1Request,
    treatment_cognitive_input: CognitiveInput,
    treatment_body: dict[str, Any],
    treatment_overlay_body: dict[str, Any],
    baseline_serialized: dict[str, Any],
    treatment_serialized: dict[str, Any],
    removed_serialized: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    baseline_cognitive_input = extraction_input.cognitive_input
    source_id = "E0"
    projection = (
        unresolved_only_extraction_intro()
        + unresolved_only_continuity_extraction_component(source_id)
        + unresolved_only_extraction_outro()
    )
    baseline_prefix = _common_cognitive_prefix(baseline_cognitive_input)
    treatment_prefix = _common_cognitive_prefix(treatment_cognitive_input)
    baseline_content = _user_content(baseline.no_pass1_body)
    baseline_overlay_content = _user_content(baseline.no_pass1_overlay_body)
    treatment_content = _user_content(treatment_body)
    treatment_overlay_content = _user_content(treatment_overlay_body)

    if baseline_content != baseline_prefix + projection:
        raise ProviderProtocolError(
            "#2700 no-Pass1 baseline no longer matches canonical composition"
        )
    if treatment_content != treatment_prefix + projection:
        raise ProviderProtocolError(
            "no-accepted-Continuity treatment changed more than CognitiveInput context"
        )
    if (
        "<PASS_1_RESPONSE_JSON>" in baseline_content
        or "<PASS_1_RESPONSE_JSON>" in treatment_content
    ):
        raise ProviderProtocolError(
            "B discriminator must preserve the #2700 no-Pass1 condition"
        )
    if baseline.no_pass1_body["messages"][0] != treatment_body["messages"][0]:
        raise ProviderProtocolError(
            "no-accepted-Continuity treatment changed system instruction"
        )
    _require_same_nonprojection_fields(baseline.no_pass1_body, treatment_body)
    _require_same_nonprojection_fields(
        baseline.no_pass1_overlay_body,
        treatment_overlay_body,
    )
    if _response_schema(baseline.no_pass1_body) != _response_schema(treatment_body):
        raise ProviderProtocolError(
            "no-accepted-Continuity treatment changed response schema"
        )
    if _overlay_tail(baseline_overlay_content) != _overlay_tail(
        treatment_overlay_content
    ):
        raise ProviderProtocolError(
            "no-accepted-Continuity treatment changed retained overlay"
        )
    _require_same_noncontext_cognitive_input(
        baseline_cognitive_input,
        treatment_cognitive_input,
    )
    if not removed_serialized:
        raise ProviderProtocolError("no accepted Continuity ContextItems were removed")

    baseline_context = baseline_serialized.get("context")
    treatment_context = treatment_serialized.get("context")
    if not isinstance(baseline_context, list) or not isinstance(
        treatment_context, list
    ):
        raise ProviderProtocolError("serialized CognitiveInput context must be an array")
    removed_count = len(removed_serialized)
    if baseline_context[removed_count:] != treatment_context:
        raise ProviderProtocolError(
            "serialized working context changed after accepted Continuity removal"
        )

    return {
        "format_version": 1,
        "same_system_instruction": True,
        "same_selected_state": True,
        "same_noncontext_cognitive_input": True,
        "same_working_context_suffix": True,
        "same_unresolved_projection_component": True,
        "same_retained_overlay": True,
        "same_response_schema": True,
        "same_nonprojection_request_fields": True,
        "baseline_has_pass1_response_component": False,
        "treatment_has_pass1_response_component": False,
        "removed_accepted_continuity_context_count": removed_count,
        "removed_accepted_continuity_context": list(removed_serialized),
        "baseline_no_pass1_request_sha256": canonical_request_body_sha256(
            baseline.no_pass1_body
        ),
        "baseline_no_pass1_overlay_request_sha256": canonical_request_body_sha256(
            baseline.no_pass1_overlay_body
        ),
        "treatment_request_sha256": canonical_request_body_sha256(treatment_body),
        "treatment_overlay_request_sha256": canonical_request_body_sha256(
            treatment_overlay_body
        ),
        "removed_model_facing_responsibility": ["accepted_continuity_context"],
    }
