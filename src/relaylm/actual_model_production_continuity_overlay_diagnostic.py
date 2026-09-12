"""Evaluation-only retained-formation overlay for ordinary production Pass 2.

This diagnostic keeps the production extraction request intact and appends one
explicit, non-authoritative formed-observation overlay. The overlay carries no
Continuity answer: only source-grounded spans and request-local model-facing
provenance, while separate evidence retains the real run-local Event identity.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from relaylm.actual_model_epistemic_formation_diagnostic import (
    DIAGNOSTIC_NAME as FORMATION_DIAGNOSTIC_NAME,
)
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionPassRequest,
    CognitionStructuredOutputMode,
)
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.providers.openai_compatible_two_pass import (
    EXTRACTION_WIRE_SCHEMA,
    _ProviderFacingProvenanceAliases,
    _extraction_request_body,
    _resolve_extraction_structured_output_mode,
)


DIAGNOSTIC_NAME = "production-continuity-retained-formation-overlay"
CONDITION_ID = "stage-r-llama-cpp-production-continuity-overlay-t2-v1"
SCHEMA_VERSION = "relaylm-production-continuity-overlay-v1"
PRIMARY_SCENARIO_ID = "continuity-lifecycle-v1"
PRIMARY_TURN_INDEX = 2
OVERLAY_TAG = "RETAINED_FORMED_OBSERVATIONS"

OVERLAY_NOTICE = (
    "The following source-grounded semantic observations were retained from an earlier "
    "diagnostic. They are empirical observations, not authoritative facts. Consider only "
    "their semantic content while performing the unchanged ordinary extraction task; "
    "they do not prescribe any output."
)


@dataclass(frozen=True, slots=True)
class RetainedFormationItem:
    subject_span: str
    unknown_evidence_span: str
    source_event_id: str


@dataclass(frozen=True, slots=True)
class RetainedFormationBinding:
    artifact_path: str
    sha256: str
    scenario_set_revision: str
    authoritative_t2_content: str
    items: tuple[RetainedFormationItem, ...]


@dataclass(frozen=True, slots=True)
class OverlayRequest:
    body: dict[str, Any]
    baseline_body: dict[str, Any]
    model_overlay: tuple[dict[str, str], ...]
    retained_source_event_id: str
    run_local_source_event_id: str


def expected_retained_source_event_id(scenario_set_revision: str) -> str:
    if not isinstance(scenario_set_revision, str) or not scenario_set_revision.startswith(
        "sha256:"
    ):
        raise ValueError("scenario_set_revision must be current sha256 authority")
    return f"stage-r:{scenario_set_revision}:primary:turn-2"


def load_retained_formation_binding(
    *,
    path: str | Path,
    scenario_set_revision: str,
    authoritative_t2_content: str,
) -> RetainedFormationBinding:
    """Bind retained #2529 evidence to current Stage-R T2 before generation."""

    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise ProviderProtocolError(
            f"retained formation artifact is not a file: {resolved}"
        )
    raw_bytes = resolved.read_bytes()
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderProtocolError(
            f"retained formation artifact is not valid UTF-8 JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ProviderProtocolError("retained formation artifact must be a JSON object")
    if payload.get("diagnostic") != FORMATION_DIAGNOSTIC_NAME:
        raise ProviderProtocolError("retained formation diagnostic identity is invalid")
    if payload.get("mechanical_validation") != "pass":
        raise ProviderProtocolError("retained formation is not mechanically validated")
    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or len(raw_items) != 1:
        raise ProviderProtocolError(
            "retained formation overlay requires exactly one formed observation"
        )
    if not isinstance(authoritative_t2_content, str) or not authoritative_t2_content:
        raise ProviderProtocolError("authoritative T2 content must be non-empty")

    expected_source = expected_retained_source_event_id(scenario_set_revision)
    expected_fields = {
        "subject_span",
        "unknown_evidence_span",
        "source_event_id",
    }
    item_raw = raw_items[0]
    if not isinstance(item_raw, dict) or set(item_raw) != expected_fields:
        raise ProviderProtocolError("retained formation item fields are not exact")
    if not all(
        isinstance(item_raw[field], str) and bool(item_raw[field])
        for field in expected_fields
    ):
        raise ProviderProtocolError("retained formation item fields must be non-empty strings")
    if item_raw["source_event_id"] != expected_source:
        raise ProviderProtocolError(
            "retained formation source_event_id does not match current Stage-R T2 identity"
        )
    if item_raw["subject_span"] not in authoritative_t2_content:
        raise ProviderProtocolError(
            "retained formation subject_span is not an authoritative T2 substring"
        )
    if item_raw["unknown_evidence_span"] not in authoritative_t2_content:
        raise ProviderProtocolError(
            "retained formation unknown_evidence_span is not an authoritative T2 substring"
        )

    item = RetainedFormationItem(
        subject_span=item_raw["subject_span"],
        unknown_evidence_span=item_raw["unknown_evidence_span"],
        source_event_id=item_raw["source_event_id"],
    )
    return RetainedFormationBinding(
        artifact_path=str(resolved),
        sha256=f"sha256:{hashlib.sha256(raw_bytes).hexdigest()}",
        scenario_set_revision=scenario_set_revision,
        authoritative_t2_content=authoritative_t2_content,
        items=(item,),
    )


def _run_local_overlay(
    *,
    extraction_input: CognitionExtractionInput,
    binding: RetainedFormationBinding,
) -> tuple[dict[str, str], ...]:
    cognitive_input = extraction_input.cognitive_input
    current_content = cognitive_input.input.payload.get("content")
    if current_content != binding.authoritative_t2_content:
        raise ProviderProtocolError(
            "production T2 current input does not match authoritative Stage-R T2 content"
        )
    current_event_id = cognitive_input.input.id
    if not isinstance(current_event_id, str) or not current_event_id:
        raise ProviderProtocolError("production T2 current input Event ID is invalid")
    aliases = _ProviderFacingProvenanceAliases.from_cognitive_input(cognitive_input)
    current_event_alias = aliases.alias_sources((current_event_id,))[0]

    normalized: list[dict[str, str]] = []
    for item in binding.items:
        if item.subject_span not in current_content:
            raise ProviderProtocolError(
                "retained subject_span is not a production T2 current-input substring"
            )
        if item.unknown_evidence_span not in current_content:
            raise ProviderProtocolError(
                "retained unknown_evidence_span is not a production T2 current-input substring"
            )
        normalized.append(
            {
                "subject_span": item.subject_span,
                "unknown_evidence_span": item.unknown_evidence_span,
                "source_event_id": current_event_alias,
            }
        )
    return tuple(normalized)


def overlay_payload(model_overlay: tuple[dict[str, str], ...]) -> str:
    payload = {"formed_epistemic_observations": list(model_overlay)}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def apply_overlay_to_production_request_body(
    *,
    baseline_body: dict[str, Any],
    model_overlay: tuple[dict[str, str], ...],
) -> dict[str, Any]:
    """Append exactly one diagnostic block; leave every production field intact."""

    body = copy.deepcopy(baseline_body)
    messages = body.get("messages")
    if not isinstance(messages, list) or len(messages) != 2:
        raise ProviderProtocolError("production extraction request messages are unexpected")
    user_message = messages[1]
    if not isinstance(user_message, dict) or user_message.get("role") != "user":
        raise ProviderProtocolError("production extraction user message is unexpected")
    content = user_message.get("content")
    if not isinstance(content, str) or not content:
        raise ProviderProtocolError("production extraction user content is invalid")
    if f"<{OVERLAY_TAG}>" in content or f"</{OVERLAY_TAG}>" in content:
        raise ProviderProtocolError("production extraction request already contains overlay tag")

    block = (
        f"\n\n<{OVERLAY_TAG}>\n"
        f"{overlay_payload(model_overlay)}\n"
        f"</{OVERLAY_TAG}>\n"
        f"{OVERLAY_NOTICE}"
    )
    user_message["content"] = content + block
    return body


def build_overlay_extraction_request_body(
    *,
    provider: Any,
    extraction_input: CognitionExtractionInput,
    pass_request: CognitionPassRequest | None,
    binding: RetainedFormationBinding,
    reasoning_request: OpenAICompatibleReasoningRequest | None = None,
) -> OverlayRequest:
    """Build production Pass 2 first, then add only the retained-meaning overlay."""

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
            "production Continuity overlay diagnostic requires native Pass 2 structured output"
        )
    baseline = _extraction_request_body(
        model=provider.model,
        extraction_input=extraction_input,
        decoding=decoding_config.to_mapping(),
        structured_output_mode=structured_output_mode,
    )
    baseline.update(provider._llama_cpp_reasoning_fields(effective_reasoning))

    model_overlay = _run_local_overlay(
        extraction_input=extraction_input,
        binding=binding,
    )
    body = apply_overlay_to_production_request_body(
        baseline_body=baseline,
        model_overlay=model_overlay,
    )
    return OverlayRequest(
        body=body,
        baseline_body=baseline,
        model_overlay=model_overlay,
        retained_source_event_id=binding.items[0].source_event_id,
        run_local_source_event_id=extraction_input.cognitive_input.input.id,
    )


def assert_production_schema_unchanged(request: OverlayRequest) -> None:
    """Fail closed if the diagnostic accidentally replaces the production schema."""

    response_format = request.body.get("response_format")
    baseline_response_format = request.baseline_body.get("response_format")
    if response_format != baseline_response_format:
        raise ProviderProtocolError("overlay changed production response_format")
    schema = (
        response_format.get("json_schema", {}).get("schema")
        if isinstance(response_format, dict)
        else None
    )
    if schema != EXTRACTION_WIRE_SCHEMA:
        raise ProviderProtocolError("overlay request no longer uses production extraction schema")
