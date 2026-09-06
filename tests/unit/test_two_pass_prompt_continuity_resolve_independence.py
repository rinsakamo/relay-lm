from __future__ import annotations

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_two_pass import _extraction_request_body
from relaylm.state import STATE_CLASS_DEFINITIONS


def test_pass2_prompt_keeps_continuity_resolve_kind_local() -> None:
    cognitive_input = CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "The question is resolved and the task is done."},
            event_id="evt-now",
            timestamp="2026-08-28T00:00:00+00:00",
        ),
    )
    request = _extraction_request_body(
        model="gemma",
        extraction_input=CognitionExtractionInput(
            cognitive_input=cognitive_input,
            assistant_response="Understood.",
        ),
        decoding={},
    )

    messages = request["messages"]
    assert isinstance(messages, list)
    content = messages[1]["content"]
    assert isinstance(content, str)

    assert (
        "scan `referent`, `unresolved`, and `active_task` independently in that order"
        in content
    )
    assert (
        "For every kind, decide `set`, no candidate, or `resolve`; finish all three kind "
        "decisions before concluding the array is empty."
        in content
    )
    assert (
        "Resolving an `unresolved` or `active_task` meaning does not by itself resolve a related `referent`."
        in content
    )
    assert (
        "One kind's unchanged/no-candidate decision never suppresses a distinct transition for another kind."
        in content
    )
    assert (
        "Completion or resolution of work about a referent, discovery of new facts about it, or an expectation that it may not be mentioned next does not end the referent."
        in content
    )
    assert (
        "Resolve a `referent` only when the current Input explicitly replaces, dismisses, or invalidates the reference target itself; do not infer referent resolution from completion of related `unresolved` or `active_task` meanings."
        in content
    )
