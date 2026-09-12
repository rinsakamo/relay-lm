from __future__ import annotations

import json

import pytest

from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_extraction_lifecycle import (
    build_lifecycle_separated_extraction_pass_suffix,
    separate_accepted_continuity_for_extraction,
)
from relaylm.providers.openai_compatible_extraction_projection import (
    ExtractionProjectionMode,
)
from relaylm.providers.openai_compatible_two_pass import (
    _ProviderFacingProvenanceAliases,
    _common_provider_cognitive_prefix,
    _conversation_request_body,
    _extraction_request_body,
)
from relaylm.state import STATE_CLASS_DEFINITIONS, StateRecord


def _accepted(*, kind: str, key: str, value: str) -> ContextItem:
    return ContextItem(
        content=json.dumps(
            {
                "continuity": {
                    "kind": kind,
                    "key": key,
                    "value": value,
                    "epistemic_role": "user_assertion",
                }
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        sources=(f"source-{key}",),
    )


def _working_context() -> tuple[ContextItem, ...]:
    return (
        ContextItem(
            content="Earlier user message.",
            sources=("event-user",),
            actor="user",
        ),
        ContextItem(
            content="Earlier assistant reply.",
            sources=("event-assistant",),
            actor="assistant",
        ),
    )


def _cognitive_input(
    *,
    context: tuple[ContextItem, ...] | None = None,
) -> CognitiveInput:
    if context is None:
        context = (
            _accepted(kind="referent", key="current_parcel", value="the parcel"),
            _accepted(kind="active_task", key="inspect_parcel", value="inspect it"),
        ) + _working_context()
    return CognitiveInput(
        identity=Identity("Synthetic lifecycle-channel identity."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(
            StateRecord(
                state_id="state-1",
                state_class="user.fact",
                key="parcel_location",
                value="on the table",
                sources=("event-user",),
            ),
        ),
        context=context,
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "The parcel is still closed."},
            event_id="event-current",
            timestamp="2026-01-01T00:00:00+00:00",
        ),
    )


def _extraction(cognitive_input: CognitiveInput | None = None) -> CognitionExtractionInput:
    return CognitionExtractionInput(
        cognitive_input=cognitive_input or _cognitive_input(),
        assistant_response="We still do not know what is inside.",
    )


def test_separation_preserves_state_and_non_lifecycle_working_context() -> None:
    baseline = _cognitive_input()
    projection = separate_accepted_continuity_for_extraction(baseline)

    assert projection.cognitive_input.state == baseline.state
    assert projection.cognitive_input.state_classes == baseline.state_classes
    assert projection.cognitive_input.identity == baseline.identity
    assert projection.cognitive_input.input == baseline.input
    assert projection.cognitive_input.memory == baseline.memory
    assert projection.cognitive_input.event_evidence == baseline.event_evidence
    assert projection.cognitive_input.context == _working_context()
    assert [item.kind for item in projection.accepted_items] == [
        "referent",
        "active_task",
    ]
    assert projection.grouped_mapping() == {
        "referent": [
            {
                "kind": "referent",
                "key": "current_parcel",
                "value": "the parcel",
                "sources": ["source-current_parcel"],
                "epistemic_role": "user_assertion",
            }
        ],
        "unresolved": [],
        "active_task": [
            {
                "kind": "active_task",
                "key": "inspect_parcel",
                "value": "inspect it",
                "sources": ["source-inspect_parcel"],
                "epistemic_role": "user_assertion",
            }
        ],
    }


def test_lifecycle_suffix_orders_discovery_before_read_only_lifecycle_reconciliation() -> None:
    extraction = _extraction()
    projection = separate_accepted_continuity_for_extraction(
        extraction.cognitive_input
    )
    projected_extraction = CognitionExtractionInput(
        cognitive_input=projection.cognitive_input,
        assistant_response=extraction.assistant_response,
    )

    suffix = build_lifecycle_separated_extraction_pass_suffix(
        projected_extraction,
        mode=ExtractionProjectionMode.PRODUCTION,
        accepted_items=projection.accepted_items,
    )

    discovery = suffix.index("first discover current-turn Continuity meanings")
    lifecycle = suffix.index("<ACCEPTED_CONTINUITY_LIFECYCLE_JSON>")
    reconciliation = suffix.index("For each Continuity kind, compare the current Input")
    assert discovery < lifecycle < reconciliation
    assert '"referent":[{"kind":"referent","key":"current_parcel"' in suffix
    assert '"unresolved":[]' in suffix
    assert '"active_task":[{"kind":"active_task","key":"inspect_parcel"' in suffix
    assert "read-only accepted prior lifecycle state" in suffix
    assert "Prior items of other kinds must not suppress discovery" in suffix


def test_production_pass2_uses_separated_view_while_pass1_stays_canonical() -> None:
    cognitive_input = _cognitive_input()
    extraction = _extraction(cognitive_input)
    aliases = _ProviderFacingProvenanceAliases.from_cognitive_input(cognitive_input)
    provider_input = aliases.alias_cognitive_input(cognitive_input)
    provider_projection = separate_accepted_continuity_for_extraction(provider_input)

    conversation = _conversation_request_body(
        model="synthetic-model",
        cognitive_input=cognitive_input,
        stream=False,
        decoding={"temperature": 0, "top_p": 1},
    )
    legacy = _extraction_request_body(
        model="synthetic-model",
        extraction_input=extraction,
        decoding={"temperature": 0, "top_p": 1},
    )
    production = _extraction_request_body(
        model="synthetic-model",
        extraction_input=extraction,
        decoding={"temperature": 0, "top_p": 1},
        lifecycle_channel_separation=True,
    )

    conversation_content = conversation["messages"][1]["content"]
    legacy_content = legacy["messages"][1]["content"]
    production_content = production["messages"][1]["content"]

    provider_prefix = _common_provider_cognitive_prefix(provider_input)
    projected_provider_prefix = _common_provider_cognitive_prefix(
        provider_projection.cognitive_input
    )
    assert conversation_content.startswith(provider_prefix)
    assert legacy_content.startswith(provider_prefix)
    assert production_content.startswith(projected_provider_prefix)
    assert "source-current_parcel" not in conversation_content
    assert "source-inspect_parcel" not in production_content
    assert "current_parcel" in conversation_content
    assert "current_parcel" in legacy_content
    assert "current_parcel" in production_content
    assert "Earlier user message." in production_content
    assert "Earlier assistant reply." in production_content
    assert "parcel_location" in production_content
    assert "<ACCEPTED_CONTINUITY_LIFECYCLE_JSON>" in production_content


def test_no_accepted_continuity_keeps_context_and_emits_empty_kind_buckets() -> None:
    cognitive_input = _cognitive_input(context=_working_context())
    projection = separate_accepted_continuity_for_extraction(cognitive_input)
    assert projection.cognitive_input == cognitive_input
    assert projection.accepted_items == ()
    assert projection.grouped_mapping() == {
        "referent": [],
        "unresolved": [],
        "active_task": [],
    }


def test_noncanonical_actorless_context_fails_closed() -> None:
    cognitive_input = _cognitive_input(
        context=(
            ContextItem(content="not continuity JSON", sources=("event-x",)),
        )
        + _working_context()
    )
    with pytest.raises(
        ProviderProtocolError,
        match="accepted Continuity projection is not canonical JSON",
    ):
        separate_accepted_continuity_for_extraction(cognitive_input)


def test_actorless_item_after_working_context_fails_closed() -> None:
    cognitive_input = _cognitive_input(
        context=_working_context()
        + (_accepted(kind="unresolved", key="late_item", value="unknown"),)
    )
    with pytest.raises(
        ProviderProtocolError,
        match="working-context boundary is not structurally exact",
    ):
        separate_accepted_continuity_for_extraction(cognitive_input)
