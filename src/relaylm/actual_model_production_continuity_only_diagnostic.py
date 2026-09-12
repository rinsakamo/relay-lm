"""Evaluation-only production-context Continuity-only Pass 2 discriminator.

This diagnostic first builds the unchanged production extraction request and the
existing retained-formation overlay request. It then asks the same canonical
builder for the Continuity-only projection mode and applies the exact same
three-field retained observation. No model-facing prompt is edited after build.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from relaylm.actual_model_production_continuity_overlay_diagnostic import (
    OVERLAY_TAG,
    RetainedFormationBinding,
    apply_overlay_to_production_request_body,
    build_overlay_extraction_request_body,
)
from relaylm.actual_model_request_evidence import canonical_request_body_sha256
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
    CognitionStructuredOutputMode,
)
from relaylm.providers.openai_compatible import (
    ProviderProtocolError,
    _load_cognitive_wire_json,
    _parse_candidate_collections,
    _require_candidate_sources_in_cognitive_input,
)
from relaylm.providers.openai_compatible_extraction_projection import (
    CONTINUITY_ONLY_EXTRACTION_WIRE_SCHEMA,
    EXTRACTION_WIRE_SCHEMA,
    ExtractionProjectionMode,
    continuity_extraction_component,
    extraction_response_component,
    state_extraction_component,
)
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.providers.openai_compatible_two_pass import (
    COMMON_SYSTEM_INSTRUCTION,
    _ProviderFacingProvenanceAliases,
    _common_cognitive_prefix,
    _completion_content_and_metadata,
    _extraction_request_body,
    _normalize_extraction_json_content,
    _resolve_extraction_structured_output_mode,
)


DIAGNOSTIC_NAME = "production-context-continuity-only-extraction"
CONDITION_ID = "stage-r-llama-cpp-production-context-continuity-only-t2-v1"
SCHEMA_VERSION = "relaylm-production-context-continuity-only-v1"


@dataclass(frozen=True, slots=True)
class ContinuityOnlyRequest:
    production_body: dict[str, Any]
    production_overlay_body: dict[str, Any]
    continuity_only_body: dict[str, Any]
    continuity_only_overlay_body: dict[str, Any]
    model_overlay: tuple[dict[str, str], ...]
    retained_source_event_id: str
    run_local_source_event_id: str
    diff_receipt: dict[str, Any]


def build_continuity_only_extraction_request_body(
    *,
    provider: Any,
    extraction_input: CognitionExtractionInput,
    pass_request: CognitionPassRequest | None,
    binding: RetainedFormationBinding,
    reasoning_request: OpenAICompatibleReasoningRequest | None = None,
) -> ContinuityOnlyRequest:
    """Hold production context fixed and remove only new State proposal work."""

    production_overlay = build_overlay_extraction_request_body(
        provider=provider,
        extraction_input=extraction_input,
        pass_request=pass_request,
        binding=binding,
        reasoning_request=reasoning_request,
    )

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
            "Continuity-only diagnostic requires native Pass 2 structured output"
        )

    continuity_only_body = _extraction_request_body(
        model=provider.model,
        extraction_input=extraction_input,
        decoding=decoding_config.to_mapping(),
        structured_output_mode=structured_output_mode,
        projection_mode=ExtractionProjectionMode.CONTINUITY_ONLY,
    )
    continuity_only_body.update(provider._llama_cpp_reasoning_fields(effective_reasoning))
    continuity_only_overlay_body = apply_overlay_to_production_request_body(
        baseline_body=continuity_only_body,
        model_overlay=production_overlay.model_overlay,
    )

    receipt = _validate_and_describe_delta(
        extraction_input=extraction_input,
        production_body=production_overlay.baseline_body,
        production_overlay_body=production_overlay.body,
        continuity_only_body=continuity_only_body,
        continuity_only_overlay_body=continuity_only_overlay_body,
        model_overlay=production_overlay.model_overlay,
    )
    return ContinuityOnlyRequest(
        production_body=production_overlay.baseline_body,
        production_overlay_body=production_overlay.body,
        continuity_only_body=continuity_only_body,
        continuity_only_overlay_body=continuity_only_overlay_body,
        model_overlay=production_overlay.model_overlay,
        retained_source_event_id=production_overlay.retained_source_event_id,
        run_local_source_event_id=production_overlay.run_local_source_event_id,
        diff_receipt=receipt,
    )


def parse_continuity_only_completion(
    envelope: Any,
    *,
    cognitive_input: CognitiveInput,
) -> CognitionExtractionOutput:
    """Parse provider aliases, restore canonical Event IDs, then validate sources."""

    content, completion = _completion_content_and_metadata(envelope)
    wire = _load_cognitive_wire_json(
        _normalize_extraction_json_content(content),
        invalid_message="provider Continuity-only extraction content is not valid JSON",
    )
    if not isinstance(wire, dict) or set(wire) != {"continuity_candidates"}:
        raise ProviderProtocolError(
            "Continuity-only extraction wire output must contain exactly continuity_candidates"
        )
    state_candidates, continuity_candidates = _parse_candidate_collections(
        raw_candidates=[],
        raw_continuity_candidates=wire["continuity_candidates"],
    )
    output = CognitionExtractionOutput(
        state_candidates=state_candidates,
        continuity_candidates=continuity_candidates,
        completion=completion,
    )
    aliases = _ProviderFacingProvenanceAliases.from_cognitive_input(cognitive_input)
    output = aliases.restore_extraction_output(output)
    _require_candidate_sources_in_cognitive_input(output, cognitive_input)
    return output


def _validate_and_describe_delta(
    *,
    extraction_input: CognitionExtractionInput,
    production_body: dict[str, Any],
    production_overlay_body: dict[str, Any],
    continuity_only_body: dict[str, Any],
    continuity_only_overlay_body: dict[str, Any],
    model_overlay: tuple[dict[str, str], ...],
) -> dict[str, Any]:
    source_id = "E0"
    common_prefix = _common_cognitive_prefix(extraction_input.cognitive_input)
    response_component = extraction_response_component(extraction_input)
    continuity_component = continuity_extraction_component(source_id)
    state_component = state_extraction_component(source_id)

    _require_same_nonprojection_fields(production_body, continuity_only_body)
    _require_same_nonprojection_fields(
        production_overlay_body,
        continuity_only_overlay_body,
    )
    production_content = _user_content(production_body)
    production_overlay_content = _user_content(production_overlay_body)
    continuity_only_content = _user_content(continuity_only_body)
    continuity_only_overlay_content = _user_content(continuity_only_overlay_body)

    expected_common = common_prefix + response_component
    for label, content in (
        ("production", production_content),
        ("production overlay", production_overlay_content),
        ("Continuity-only", continuity_only_content),
        ("Continuity-only overlay", continuity_only_overlay_content),
    ):
        if not content.startswith(expected_common):
            raise ProviderProtocolError(f"{label} changed CognitiveInput or Pass 1 framing")
        if continuity_component not in content:
            raise ProviderProtocolError(f"{label} does not reuse canonical Continuity component")

    if state_component not in production_content:
        raise ProviderProtocolError("production request lost canonical State component")
    if state_component in continuity_only_content:
        raise ProviderProtocolError("Continuity-only request still carries State extraction work")

    if production_body["messages"][0] != {
        "role": "system",
        "content": COMMON_SYSTEM_INSTRUCTION,
    }:
        raise ProviderProtocolError("production system instruction changed")
    if continuity_only_body["messages"][0] != production_body["messages"][0]:
        raise ProviderProtocolError("Continuity-only system instruction differs from production")

    production_schema = _response_schema(production_body)
    continuity_schema = _response_schema(continuity_only_body)
    if production_schema != EXTRACTION_WIRE_SCHEMA:
        raise ProviderProtocolError("production request no longer uses canonical combined schema")
    if continuity_schema != CONTINUITY_ONLY_EXTRACTION_WIRE_SCHEMA:
        raise ProviderProtocolError("diagnostic request does not use canonical Continuity-only schema")
    if set(continuity_schema["properties"]) != {"continuity_candidates"}:
        raise ProviderProtocolError("Continuity-only schema contains a non-Continuity output")
    if continuity_schema["properties"]["continuity_candidates"] != production_schema[
        "properties"
    ]["continuity_candidates"]:
        raise ProviderProtocolError("Continuity-only item schema diverged from production")

    if not model_overlay or any(
        set(item) != {"subject_span", "unknown_evidence_span", "source_event_id"}
        for item in model_overlay
    ):
        raise ProviderProtocolError("retained overlay contains non-formation fields")
    if _overlay_tail(production_overlay_content) != _overlay_tail(
        continuity_only_overlay_content
    ):
        raise ProviderProtocolError("Continuity-only request changed retained overlay payload")

    return {
        "format_version": 1,
        "same_system_instruction": True,
        "same_cognitive_input_and_pass1_prefix": True,
        "same_continuity_component": True,
        "same_retained_overlay": True,
        "same_nonprojection_request_fields": True,
        "production_has_state_component": True,
        "continuity_only_has_state_component": False,
        "production_schema_properties": sorted(production_schema["properties"]),
        "continuity_only_schema_properties": sorted(continuity_schema["properties"]),
        "production_request_sha256": canonical_request_body_sha256(production_body),
        "production_overlay_request_sha256": canonical_request_body_sha256(
            production_overlay_body
        ),
        "continuity_only_request_sha256": canonical_request_body_sha256(
            continuity_only_body
        ),
        "continuity_only_overlay_request_sha256": canonical_request_body_sha256(
            continuity_only_overlay_body
        ),
        "removed_model_facing_responsibility": [
            "state_extraction_instruction",
            "state_candidates_output_schema",
        ],
    }


def _require_same_nonprojection_fields(
    production: dict[str, Any],
    diagnostic: dict[str, Any],
) -> None:
    production_copy = copy.deepcopy(production)
    diagnostic_copy = copy.deepcopy(diagnostic)
    production_copy.pop("messages", None)
    diagnostic_copy.pop("messages", None)
    production_copy.pop("response_format", None)
    diagnostic_copy.pop("response_format", None)
    if production_copy != diagnostic_copy:
        raise ProviderProtocolError(
            "Continuity-only request changed non-projection request fields"
        )


def _user_content(body: dict[str, Any]) -> str:
    messages = body.get("messages")
    if not isinstance(messages, list) or len(messages) != 2:
        raise ProviderProtocolError("extraction request messages are unexpected")
    user_message = messages[1]
    if not isinstance(user_message, dict) or user_message.get("role") != "user":
        raise ProviderProtocolError("extraction request user message is unexpected")
    content = user_message.get("content")
    if not isinstance(content, str) or not content:
        raise ProviderProtocolError("extraction request user content is invalid")
    return content


def _response_schema(body: dict[str, Any]) -> dict[str, Any]:
    response_format = body.get("response_format")
    if not isinstance(response_format, dict) or response_format.get("type") != "json_schema":
        raise ProviderProtocolError("extraction request is not native structured output")
    json_schema = response_format.get("json_schema")
    if not isinstance(json_schema, dict) or json_schema.get("strict") is not True:
        raise ProviderProtocolError("extraction request schema is not strict")
    schema = json_schema.get("schema")
    if not isinstance(schema, dict):
        raise ProviderProtocolError("extraction request schema is invalid")
    return schema


def _overlay_tail(content: str) -> str:
    marker = f"\n\n<{OVERLAY_TAG}>\n"
    if marker not in content:
        raise ProviderProtocolError("retained overlay tag is missing")
    return content.split(marker, 1)[1]
