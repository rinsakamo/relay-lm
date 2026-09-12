"""Evaluation-only production-context unresolved-only Pass 2 discriminator.

This diagnostic builds on the canonical Continuity-only discriminator. It keeps
production context, accepted Continuity, Pass 1 response, retained formation,
transport, schema item shape, decoding and reasoning fixed, then removes only
referent/active_task projection responsibility from the diagnostic Pass 2.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from relaylm.actual_model_production_continuity_only_diagnostic import (
    ContinuityOnlyRequest,
    _overlay_tail,
    _require_same_nonprojection_fields,
    _response_schema,
    _user_content,
    build_continuity_only_extraction_request_body,
    parse_continuity_only_completion,
)
from relaylm.actual_model_production_continuity_overlay_diagnostic import (
    RetainedFormationBinding,
    apply_overlay_to_production_request_body,
)
from relaylm.actual_model_request_evidence import canonical_request_body_sha256
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
    CognitionStructuredOutputMode,
)
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_extraction_projection import (
    CONTINUITY_ONLY_EXTRACTION_WIRE_SCHEMA,
    ExtractionProjectionMode,
    continuity_extraction_component,
    extraction_response_component,
    unresolved_only_continuity_extraction_component,
)
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.providers.openai_compatible_two_pass import (
    _common_cognitive_prefix,
    _extraction_request_body,
    _resolve_extraction_structured_output_mode,
)


DIAGNOSTIC_NAME = "production-context-unresolved-only-extraction"
CONDITION_ID = "stage-r-llama-cpp-production-context-unresolved-only-t2-v1"
SCHEMA_VERSION = "relaylm-production-context-unresolved-only-v1"


@dataclass(frozen=True, slots=True)
class UnresolvedOnlyRequest:
    production_body: dict[str, Any]
    production_overlay_body: dict[str, Any]
    continuity_only_body: dict[str, Any]
    continuity_only_overlay_body: dict[str, Any]
    unresolved_only_body: dict[str, Any]
    unresolved_only_overlay_body: dict[str, Any]
    model_overlay: tuple[dict[str, str], ...]
    retained_source_event_id: str
    run_local_source_event_id: str
    diff_receipt: dict[str, Any]


def build_unresolved_only_extraction_request_body(
    *,
    provider: Any,
    extraction_input: CognitionExtractionInput,
    pass_request: CognitionPassRequest | None,
    binding: RetainedFormationBinding,
    reasoning_request: OpenAICompatibleReasoningRequest | None = None,
) -> UnresolvedOnlyRequest:
    """Hold production context fixed and remove only other-kind projection work."""

    continuity = build_continuity_only_extraction_request_body(
        provider=provider,
        extraction_input=extraction_input,
        pass_request=pass_request,
        binding=binding,
        reasoning_request=reasoning_request,
    )
    unresolved_body = _build_unresolved_only_body(
        provider=provider,
        extraction_input=extraction_input,
        pass_request=pass_request,
        reasoning_request=reasoning_request,
    )
    unresolved_overlay_body = apply_overlay_to_production_request_body(
        baseline_body=unresolved_body,
        model_overlay=continuity.model_overlay,
    )
    receipt = _validate_and_describe_delta(
        extraction_input=extraction_input,
        continuity=continuity,
        unresolved_body=unresolved_body,
        unresolved_overlay_body=unresolved_overlay_body,
    )
    return UnresolvedOnlyRequest(
        production_body=continuity.production_body,
        production_overlay_body=continuity.production_overlay_body,
        continuity_only_body=continuity.continuity_only_body,
        continuity_only_overlay_body=continuity.continuity_only_overlay_body,
        unresolved_only_body=unresolved_body,
        unresolved_only_overlay_body=unresolved_overlay_body,
        model_overlay=continuity.model_overlay,
        retained_source_event_id=continuity.retained_source_event_id,
        run_local_source_event_id=continuity.run_local_source_event_id,
        diff_receipt=receipt,
    )


def parse_unresolved_only_completion(
    envelope: Any,
    *,
    cognitive_input: CognitiveInput,
) -> CognitionExtractionOutput:
    """Reuse canonical Continuity parsing, then enforce diagnostic responsibility."""

    output = parse_continuity_only_completion(
        envelope,
        cognitive_input=cognitive_input,
    )
    non_unresolved = [
        candidate.kind
        for candidate in output.continuity_candidates
        if candidate.kind != "unresolved"
    ]
    if non_unresolved:
        raise ProviderProtocolError(
            "unresolved-only diagnostic returned non-unresolved Continuity candidate"
        )
    return output


def _build_unresolved_only_body(
    *,
    provider: Any,
    extraction_input: CognitionExtractionInput,
    pass_request: CognitionPassRequest | None,
    reasoning_request: OpenAICompatibleReasoningRequest | None,
) -> dict[str, Any]:
    decoding_config, effective_reasoning = provider._resolve_llama_cpp_pass_request(
        pass_request=pass_request,
        reasoning_request=reasoning_request,
    )
    structured_output_mode = _resolve_extraction_structured_output_mode(
        pass_request=pass_request,
        provider=provider,
    )
    if structured_output_mode is not CognitionStructuredOutputMode.NATIVE:
        raise ProviderProtocolError(
            "unresolved-only diagnostic requires native Pass 2 structured output"
        )
    body = _extraction_request_body(
        model=provider.model,
        extraction_input=extraction_input,
        decoding=decoding_config.to_mapping(),
        structured_output_mode=structured_output_mode,
        projection_mode=ExtractionProjectionMode.UNRESOLVED_ONLY,
    )
    body.update(provider._llama_cpp_reasoning_fields(effective_reasoning))
    return body


def _validate_and_describe_delta(
    *,
    extraction_input: CognitionExtractionInput,
    continuity: ContinuityOnlyRequest,
    unresolved_body: dict[str, Any],
    unresolved_overlay_body: dict[str, Any],
) -> dict[str, Any]:
    source_id = "E0"
    expected_common = _common_cognitive_prefix(extraction_input.cognitive_input) + (
        extraction_response_component(extraction_input)
    )
    full_component = continuity_extraction_component(source_id)
    unresolved_component = unresolved_only_continuity_extraction_component(source_id)

    _require_same_nonprojection_fields(continuity.continuity_only_body, unresolved_body)
    _require_same_nonprojection_fields(
        continuity.continuity_only_overlay_body,
        unresolved_overlay_body,
    )
    continuity_content = _user_content(continuity.continuity_only_body)
    continuity_overlay_content = _user_content(continuity.continuity_only_overlay_body)
    unresolved_content = _user_content(unresolved_body)
    unresolved_overlay_content = _user_content(unresolved_overlay_body)

    for label, content in (
        ("Continuity-only", continuity_content),
        ("Continuity-only overlay", continuity_overlay_content),
        ("unresolved-only", unresolved_content),
        ("unresolved-only overlay", unresolved_overlay_content),
    ):
        if not content.startswith(expected_common):
            raise ProviderProtocolError(f"{label} changed CognitiveInput or Pass 1 framing")

    if full_component not in continuity_content:
        raise ProviderProtocolError("Continuity-only request lost canonical full component")
    if unresolved_component not in unresolved_content:
        raise ProviderProtocolError("unresolved-only request lost canonical unresolved component")
    if full_component in unresolved_content:
        raise ProviderProtocolError("unresolved-only request still carries full kind competition")

    for forbidden in (
        "`referent`: a specific subject",
        "`active_task`: an unfinished action",
        "Emit every distinct useful Continuity meaning",
        "For each Continuity kind",
        "  - Referent:",
        "  - Active task:",
    ):
        if forbidden in unresolved_component:
            raise ProviderProtocolError(
                "unresolved-only request still carries competing-kind responsibility"
            )

    if unresolved_body["messages"][0] != continuity.continuity_only_body["messages"][0]:
        raise ProviderProtocolError(
            "unresolved-only system instruction differs from Continuity-only"
        )

    continuity_schema = _response_schema(continuity.continuity_only_body)
    unresolved_schema = _response_schema(unresolved_body)
    if continuity_schema != CONTINUITY_ONLY_EXTRACTION_WIRE_SCHEMA:
        raise ProviderProtocolError("Continuity-only schema changed before factor cut")
    if unresolved_schema != continuity_schema:
        raise ProviderProtocolError(
            "unresolved-only item schema diverged from Continuity-only schema"
        )

    if _overlay_tail(continuity_overlay_content) != _overlay_tail(
        unresolved_overlay_content
    ):
        raise ProviderProtocolError("unresolved-only request changed retained overlay")

    continuity_nonprojection = copy.deepcopy(continuity.continuity_only_body)
    unresolved_nonprojection = copy.deepcopy(unresolved_body)
    continuity_nonprojection.pop("messages", None)
    unresolved_nonprojection.pop("messages", None)
    continuity_nonprojection.pop("response_format", None)
    unresolved_nonprojection.pop("response_format", None)
    if continuity_nonprojection != unresolved_nonprojection:
        raise ProviderProtocolError("unresolved-only changed non-projection request fields")

    return {
        "format_version": 1,
        "same_system_instruction": True,
        "same_cognitive_input_and_pass1_prefix": True,
        "same_accepted_continuity_context": True,
        "same_retained_overlay": True,
        "same_nonprojection_request_fields": True,
        "same_continuity_candidate_item_schema": True,
        "continuity_only_has_full_kind_component": True,
        "unresolved_only_has_full_kind_component": False,
        "unresolved_only_keeps_unresolved_component": True,
        "production_request_sha256": canonical_request_body_sha256(
            continuity.production_body
        ),
        "production_overlay_request_sha256": canonical_request_body_sha256(
            continuity.production_overlay_body
        ),
        "continuity_only_request_sha256": canonical_request_body_sha256(
            continuity.continuity_only_body
        ),
        "continuity_only_overlay_request_sha256": canonical_request_body_sha256(
            continuity.continuity_only_overlay_body
        ),
        "unresolved_only_request_sha256": canonical_request_body_sha256(
            unresolved_body
        ),
        "unresolved_only_overlay_request_sha256": canonical_request_body_sha256(
            unresolved_overlay_body
        ),
        "removed_model_facing_responsibility": [
            "referent_projection_instruction",
            "active_task_projection_instruction",
            "multi_kind_decision_competition",
        ],
    }
