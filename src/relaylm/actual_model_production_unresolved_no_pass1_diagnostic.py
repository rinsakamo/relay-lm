"""Evaluation-only unresolved-only Pass 2 discriminator without Pass 1 text.

This diagnostic derives its baseline from the merged unresolved-only builder and
keeps the full CognitiveInput, accepted Continuity context, retained formation,
transport, schema, decoding and reasoning fixed.  The diagnostic variant then
recomposes the user request from canonical extraction components while omitting
only the canonical Pass 1 response component.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
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
from relaylm.actual_model_production_unresolved_only_diagnostic import (
    UnresolvedOnlyRequest,
    build_unresolved_only_extraction_request_body,
    parse_unresolved_only_completion,
)
from relaylm.actual_model_request_evidence import canonical_request_body_sha256
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
)
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_extraction_projection import (
    extraction_response_component,
    unresolved_only_continuity_extraction_component,
    unresolved_only_extraction_intro,
    unresolved_only_extraction_outro,
)
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.providers.openai_compatible_two_pass import _common_cognitive_prefix


DIAGNOSTIC_NAME = "production-context-unresolved-only-no-pass1-extraction"
CONDITION_ID = "stage-r-llama-cpp-production-context-unresolved-only-no-pass1-t2-v1"
SCHEMA_VERSION = "relaylm-production-context-unresolved-only-no-pass1-v1"


@dataclass(frozen=True, slots=True)
class UnresolvedNoPass1Request:
    baseline: UnresolvedOnlyRequest
    no_pass1_body: dict[str, Any]
    no_pass1_overlay_body: dict[str, Any]
    diff_receipt: dict[str, Any]


def build_unresolved_no_pass1_extraction_request_body(
    *,
    provider: Any,
    extraction_input: CognitionExtractionInput,
    pass_request: CognitionPassRequest | None,
    binding: RetainedFormationBinding,
    reasoning_request: OpenAICompatibleReasoningRequest | None = None,
) -> UnresolvedNoPass1Request:
    """Keep #2689 unresolved-only coordinates fixed and omit only Pass 1 text."""

    baseline = build_unresolved_only_extraction_request_body(
        provider=provider,
        extraction_input=extraction_input,
        pass_request=pass_request,
        binding=binding,
        reasoning_request=reasoning_request,
    )
    no_pass1_body = _build_no_pass1_body(
        extraction_input=extraction_input,
        baseline_body=baseline.unresolved_only_body,
    )
    no_pass1_overlay_body = apply_overlay_to_production_request_body(
        baseline_body=no_pass1_body,
        model_overlay=baseline.model_overlay,
    )
    receipt = _validate_and_describe_delta(
        extraction_input=extraction_input,
        baseline=baseline,
        no_pass1_body=no_pass1_body,
        no_pass1_overlay_body=no_pass1_overlay_body,
    )
    return UnresolvedNoPass1Request(
        baseline=baseline,
        no_pass1_body=no_pass1_body,
        no_pass1_overlay_body=no_pass1_overlay_body,
        diff_receipt=receipt,
    )


def parse_unresolved_no_pass1_completion(
    envelope: Any,
    *,
    cognitive_input: CognitiveInput,
) -> CognitionExtractionOutput:
    """Reuse the canonical unresolved-only parser and source validation."""

    return parse_unresolved_only_completion(
        envelope,
        cognitive_input=cognitive_input,
    )


def _build_no_pass1_body(
    *,
    extraction_input: CognitionExtractionInput,
    baseline_body: dict[str, Any],
) -> dict[str, Any]:
    body = copy.deepcopy(baseline_body)
    messages = body.get("messages")
    if not isinstance(messages, list) or len(messages) != 2:
        raise ProviderProtocolError("unresolved-only baseline messages are unexpected")
    user_message = messages[1]
    if not isinstance(user_message, dict) or user_message.get("role") != "user":
        raise ProviderProtocolError("unresolved-only baseline user message is unexpected")

    source_id = extraction_input.originating_event_id
    user_message["content"] = (
        _common_cognitive_prefix(extraction_input.cognitive_input)
        + unresolved_only_extraction_intro()
        + unresolved_only_continuity_extraction_component(source_id)
        + unresolved_only_extraction_outro()
    )
    return body


def _validate_and_describe_delta(
    *,
    extraction_input: CognitionExtractionInput,
    baseline: UnresolvedOnlyRequest,
    no_pass1_body: dict[str, Any],
    no_pass1_overlay_body: dict[str, Any],
) -> dict[str, Any]:
    source_id = extraction_input.originating_event_id
    cognitive_prefix = _common_cognitive_prefix(extraction_input.cognitive_input)
    response_component = extraction_response_component(extraction_input)
    unresolved_projection = (
        unresolved_only_extraction_intro()
        + unresolved_only_continuity_extraction_component(source_id)
        + unresolved_only_extraction_outro()
    )

    baseline_content = _user_content(baseline.unresolved_only_body)
    baseline_overlay_content = _user_content(baseline.unresolved_only_overlay_body)
    no_pass1_content = _user_content(no_pass1_body)
    no_pass1_overlay_content = _user_content(no_pass1_overlay_body)

    expected_baseline = cognitive_prefix + response_component + unresolved_projection
    expected_no_pass1 = cognitive_prefix + unresolved_projection
    if baseline_content != expected_baseline:
        raise ProviderProtocolError(
            "unresolved-only baseline no longer matches canonical component composition"
        )
    if no_pass1_content != expected_no_pass1:
        raise ProviderProtocolError(
            "no-Pass1 request changed more than the Pass 1 response component"
        )
    if response_component not in baseline_content:
        raise ProviderProtocolError("unresolved-only baseline lost Pass 1 response component")
    if response_component in no_pass1_content or "<PASS_1_RESPONSE_JSON>" in no_pass1_content:
        raise ProviderProtocolError("no-Pass1 request still carries Pass 1 response content")

    if baseline.unresolved_only_body["messages"][0] != no_pass1_body["messages"][0]:
        raise ProviderProtocolError("no-Pass1 system instruction changed")
    _require_same_nonprojection_fields(baseline.unresolved_only_body, no_pass1_body)
    _require_same_nonprojection_fields(
        baseline.unresolved_only_overlay_body,
        no_pass1_overlay_body,
    )
    if _response_schema(baseline.unresolved_only_body) != _response_schema(no_pass1_body):
        raise ProviderProtocolError("no-Pass1 response schema changed")
    if _overlay_tail(baseline_overlay_content) != _overlay_tail(no_pass1_overlay_content):
        raise ProviderProtocolError("no-Pass1 request changed retained overlay")

    baseline_prefix = baseline_content[: len(cognitive_prefix)]
    no_pass1_prefix = no_pass1_content[: len(cognitive_prefix)]
    if baseline_prefix != cognitive_prefix or no_pass1_prefix != cognitive_prefix:
        raise ProviderProtocolError("no-Pass1 request changed serialized CognitiveInput")

    return {
        "format_version": 1,
        "same_system_instruction": True,
        "same_cognitive_input": True,
        "same_accepted_continuity_context": True,
        "same_unresolved_projection_component": True,
        "same_retained_overlay": True,
        "same_response_schema": True,
        "same_nonprojection_request_fields": True,
        "baseline_has_pass1_response_component": True,
        "no_pass1_has_pass1_response_component": False,
        "baseline_unresolved_only_request_sha256": canonical_request_body_sha256(
            baseline.unresolved_only_body
        ),
        "baseline_unresolved_only_overlay_request_sha256": canonical_request_body_sha256(
            baseline.unresolved_only_overlay_body
        ),
        "no_pass1_request_sha256": canonical_request_body_sha256(no_pass1_body),
        "no_pass1_overlay_request_sha256": canonical_request_body_sha256(
            no_pass1_overlay_body
        ),
        "removed_model_facing_responsibility": ["pass1_response_component"],
    }
