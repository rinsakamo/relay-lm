"""Provider-neutral transport helpers for evaluation-only Continuity diagnostics.

The helpers in this module deliberately stop at the model-facing diagnostic
boundary.  They do not participate in production cognition serialization,
Continuity validation, materialization, lifecycle handling, or scoring.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from relaylm.cognition_execution import CognitionExtractionOutput
from relaylm.providers.openai_compatible import (
    ProviderProtocolError,
    WIRE_SCHEMA,
    _parse_candidate_collections,
)


FIXED_SLOT_DIAGNOSTIC_FORMAT_VERSION = 1
FIXED_SLOT_SCHEMA_NAME = "relaylm_fixed_continuity_slot_diagnostic"
FIXED_SLOT_ORDER = ("referent", "unresolved", "active_task")


def _slot_schema(kind: str) -> dict[str, Any]:
    candidate = copy.deepcopy(
        WIRE_SCHEMA["properties"]["continuity_candidates"]["items"]
    )
    candidate["properties"]["kind"] = {"type": "string", "enum": [kind]}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["decision", "transitions"],
        "properties": {
            "decision": {"type": "string", "enum": ["none", "emit"]},
            "transitions": {
                "type": "array",
                "items": candidate,
            },
        },
    }


FIXED_SLOT_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["state_candidates", "continuity_decisions"],
    "properties": {
        "state_candidates": copy.deepcopy(
            WIRE_SCHEMA["properties"]["state_candidates"]
        ),
        "continuity_decisions": {
            "type": "object",
            "additionalProperties": False,
            "required": list(FIXED_SLOT_ORDER),
            "properties": {
                kind: _slot_schema(kind) for kind in FIXED_SLOT_ORDER
            },
        },
    },
}


_OLD_EMIT_LINE = "Emit `state_candidates`, then `continuity_candidates`."
_OLD_SHAPE = (
    "Exact top-level shape:\n"
    "`{\"state_candidates\":[],\"continuity_candidates\":[]}`\n\n"
    "Return exactly one JSON object with no extra keys."
)
_FIXED_SLOT_EMIT_LINE = (
    "Emit `state_candidates`, then `continuity_decisions` using the fixed per-kind "
    "diagnostic transport described below."
)
_FIXED_SLOT_TRANSPORT = """FIXED-SLOT DIAGNOSTIC TRANSPORT:
- All State and Continuity semantic rules above remain unchanged. This transport changes only how Continuity decisions are made mechanically explicit for diagnosis.
- Return `continuity_decisions` with exactly the three required keys `referent`, `unresolved`, and `active_task`; evaluate every slot exactly once.
- Each slot has exactly `decision` and `transitions`.
- Use `decision: \"none\"` with `transitions: []` when that kind has no justified transition after applying the existing Continuity rules.
- Use `decision: \"emit\"` with one or more ordinary Continuity wire transitions when that kind has justified `set` or `resolve` transitions.
- Every transition retains the ordinary Continuity wire fields and its `kind` must equal the containing slot kind.
- Do not emit a placeholder transition merely to fill a slot; `none` is the explicit no-candidate decision.

Exact diagnostic top-level shape:
`{\"state_candidates\":[],\"continuity_decisions\":{\"referent\":{\"decision\":\"none\",\"transitions\":[]},\"unresolved\":{\"decision\":\"none\",\"transitions\":[]},\"active_task\":{\"decision\":\"none\",\"transitions\":[]}}}`

Return exactly one JSON object with no extra keys."""


def fixed_slot_prompt(production_prompt: str) -> str:
    """Apply only the fixed-slot diagnostic transport to a production prompt."""

    if production_prompt.count(_OLD_EMIT_LINE) != 1:
        raise ProviderProtocolError(
            "fixed-slot diagnostic cannot identify production candidate emit instruction"
        )
    if production_prompt.count(_OLD_SHAPE) != 1:
        raise ProviderProtocolError(
            "fixed-slot diagnostic cannot identify production extraction top-level shape"
        )
    return production_prompt.replace(
        _OLD_EMIT_LINE,
        _FIXED_SLOT_EMIT_LINE,
        1,
    ).replace(
        _OLD_SHAPE,
        _FIXED_SLOT_TRANSPORT,
        1,
    )


def apply_fixed_slot_transport(body: dict[str, Any]) -> dict[str, Any]:
    """Return a request body with the provider-neutral fixed-slot transport."""

    messages = body.get("messages")
    if not isinstance(messages, list) or len(messages) != 2:
        raise ProviderProtocolError(
            "fixed-slot diagnostic expected production two-message extraction request"
        )
    user_message = messages[1]
    if not isinstance(user_message, dict) or not isinstance(
        user_message.get("content"), str
    ):
        raise ProviderProtocolError(
            "fixed-slot diagnostic expected production extraction user prompt"
        )
    user_message["content"] = fixed_slot_prompt(user_message["content"])
    body["response_format"] = {
        "type": "json_schema",
        "json_schema": {
            "name": FIXED_SLOT_SCHEMA_NAME,
            "strict": True,
            "schema": FIXED_SLOT_EXTRACTION_SCHEMA,
        },
    }
    return body


def parse_fixed_slot_wire(
    *,
    wire: object,
    completion: object,
) -> tuple[CognitionExtractionOutput, dict[str, object]]:
    """Flatten fixed slots into the existing canonical extraction grammar."""

    if not isinstance(wire, dict) or set(wire) != {
        "state_candidates",
        "continuity_decisions",
    }:
        raise ProviderProtocolError(
            "fixed-slot extraction must contain exactly state_candidates and "
            "continuity_decisions"
        )
    decisions = wire["continuity_decisions"]
    if not isinstance(decisions, dict) or set(decisions) != set(FIXED_SLOT_ORDER):
        raise ProviderProtocolError(
            "fixed-slot continuity_decisions must contain exactly referent, "
            "unresolved, and active_task"
        )

    flattened: list[object] = []
    normalized_decisions: dict[str, object] = {}
    for kind in FIXED_SLOT_ORDER:
        slot = decisions[kind]
        if not isinstance(slot, dict) or set(slot) != {"decision", "transitions"}:
            raise ProviderProtocolError(
                f"fixed-slot {kind} decision must contain exactly decision and transitions"
            )
        decision = slot["decision"]
        transitions = slot["transitions"]
        if decision not in {"none", "emit"} or not isinstance(transitions, list):
            raise ProviderProtocolError(
                f"fixed-slot {kind} decision/transitions have invalid types"
            )
        if decision == "none" and transitions:
            raise ProviderProtocolError(
                f"fixed-slot {kind} none decision must have empty transitions"
            )
        if decision == "emit" and not transitions:
            raise ProviderProtocolError(
                f"fixed-slot {kind} emit decision must have non-empty transitions"
            )
        for transition in transitions:
            if not isinstance(transition, dict) or transition.get("kind") != kind:
                raise ProviderProtocolError(
                    f"fixed-slot {kind} transition kind must match its containing slot"
                )
        flattened.extend(transitions)
        normalized_decisions[kind] = {
            "decision": decision,
            "transitions": transitions,
        }

    state_candidates, continuity_candidates = _parse_candidate_collections(
        raw_candidates=wire["state_candidates"],
        raw_continuity_candidates=flattened,
    )
    output = CognitionExtractionOutput(
        state_candidates=state_candidates,
        continuity_candidates=continuity_candidates,
        completion=completion,
    )
    return output, normalized_decisions


LABEL_INVARIANCE_DIAGNOSTIC_FORMAT_VERSION = 1
LABEL_INVARIANCE_SCHEMA_NAME = "relaylm_continuity_label_invariance_diagnostic"
CANONICAL_UNRESOLVED_KIND = "unresolved"
SHADOW_OPEN_QUESTION_KIND = "open_question"
SHADOW_SLOT_ORDER = ("referent", SHADOW_OPEN_QUESTION_KIND, "active_task")
_COGNITIVE_INPUT_OPEN = "<COGNITIVE_INPUT>\n"
_COGNITIVE_INPUT_CLOSE = "\n</COGNITIVE_INPUT>\n\n<PASS>\n"
_PASS_1_CLOSE = "</PASS_1_RESPONSE_JSON>\n\n"


def _label_invariance_schema() -> dict[str, Any]:
    schema = copy.deepcopy(FIXED_SLOT_EXTRACTION_SCHEMA)
    decisions = schema["properties"]["continuity_decisions"]
    properties = decisions["properties"]
    open_question_slot = properties[CANONICAL_UNRESOLVED_KIND]
    open_question_slot["properties"]["transitions"]["items"]["properties"][
        "kind"
    ] = {
        "type": "string",
        "enum": [SHADOW_OPEN_QUESTION_KIND],
    }
    decisions["required"] = list(SHADOW_SLOT_ORDER)
    decisions["properties"] = {
        "referent": properties["referent"],
        SHADOW_OPEN_QUESTION_KIND: open_question_slot,
        "active_task": properties["active_task"],
    }
    return schema


LABEL_INVARIANCE_EXTRACTION_SCHEMA = _label_invariance_schema()


def alias_projected_continuity_context(content: str) -> str:
    """Alias only an already-projected canonical unresolved context record."""

    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return content
    if not isinstance(payload, dict):
        return content
    continuity = payload.get("continuity")
    if (
        not isinstance(continuity, dict)
        or continuity.get("kind") != CANONICAL_UNRESOLVED_KIND
    ):
        return content
    aliased = copy.deepcopy(payload)
    aliased["continuity"]["kind"] = SHADOW_OPEN_QUESTION_KIND
    return json.dumps(aliased, ensure_ascii=False, separators=(",", ":"))


def alias_cognitive_input_json(serialized: object) -> object:
    """Alias accepted projected context, leaving the current Input untouched."""

    if not isinstance(serialized, dict):
        raise ProviderProtocolError(
            "label-invariance diagnostic expected serialized CognitiveInput object"
        )
    aliased = copy.deepcopy(serialized)
    context = aliased.get("context")
    if not isinstance(context, list):
        raise ProviderProtocolError(
            "label-invariance diagnostic expected serialized CognitiveInput context list"
        )
    for item in context:
        if not isinstance(item, dict) or not isinstance(item.get("content"), str):
            raise ProviderProtocolError(
                "label-invariance diagnostic expected serialized ContextItem objects"
            )
        item["content"] = alias_projected_continuity_context(item["content"])
    return aliased


def label_alias_prompt(fixed_prompt: str) -> str:
    """Alias the diagnostic model-facing coordinate without rewriting evidence."""

    if not fixed_prompt.startswith(_COGNITIVE_INPUT_OPEN):
        raise ProviderProtocolError(
            "label-invariance diagnostic cannot identify CognitiveInput boundary"
        )
    try:
        serialized_text, after_cognitive = fixed_prompt[
            len(_COGNITIVE_INPUT_OPEN) :
        ].split(_COGNITIVE_INPUT_CLOSE, 1)
        pass_1_prefix, static_instructions = after_cognitive.split(_PASS_1_CLOSE, 1)
    except ValueError as exc:
        raise ProviderProtocolError(
            "label-invariance diagnostic cannot identify fixed-slot prompt boundaries"
        ) from exc
    try:
        serialized = json.loads(serialized_text)
    except json.JSONDecodeError as exc:
        raise ProviderProtocolError(
            "label-invariance diagnostic CognitiveInput is not valid JSON"
        ) from exc

    aliased_serialized = alias_cognitive_input_json(serialized)
    current_input = aliased_serialized.get("input")
    source_id = (
        current_input.get("event_id")
        if isinstance(current_input, dict)
        and isinstance(current_input.get("event_id"), str)
        else None
    )
    source_sentinel = "__RELAYLM_LABEL_INVARIANCE_CURRENT_EVENT_ID__"
    if source_sentinel in static_instructions:
        raise ProviderProtocolError(
            "label-invariance diagnostic source sentinel collides with prompt"
        )
    protected_instructions = static_instructions
    if source_id is not None:
        protected_instructions = protected_instructions.replace(
            source_id,
            source_sentinel,
        )
    aliased_instructions = protected_instructions.replace(
        "Unresolved",
        "Open-question",
    ).replace(CANONICAL_UNRESOLVED_KIND, SHADOW_OPEN_QUESTION_KIND)
    if source_id is not None:
        aliased_instructions = aliased_instructions.replace(source_sentinel, source_id)
    return (
        _COGNITIVE_INPUT_OPEN
        + json.dumps(aliased_serialized, ensure_ascii=False, separators=(",", ":"))
        + _COGNITIVE_INPUT_CLOSE
        + pass_1_prefix
        + _PASS_1_CLOSE
        + aliased_instructions
    )


def apply_label_alias_to_request_body(body: dict[str, Any]) -> dict[str, Any]:
    """Apply the shadow name to an already fixed-slot request body."""

    messages = body.get("messages")
    if not isinstance(messages, list) or len(messages) != 2:
        raise ProviderProtocolError(
            "label-invariance diagnostic expected fixed-slot request messages"
        )
    user_message = messages[1]
    if not isinstance(user_message, dict) or not isinstance(
        user_message.get("content"), str
    ):
        raise ProviderProtocolError(
            "label-invariance diagnostic expected fixed-slot user prompt"
        )
    user_message["content"] = label_alias_prompt(user_message["content"])
    body["response_format"] = {
        "type": "json_schema",
        "json_schema": {
            "name": LABEL_INVARIANCE_SCHEMA_NAME,
            "strict": True,
            "schema": LABEL_INVARIANCE_EXTRACTION_SCHEMA,
        },
    }
    return body


def parse_label_alias_wire(
    *,
    wire: object,
    completion: object,
) -> tuple[CognitionExtractionOutput, dict[str, object]]:
    """Translate the shadow wire to canonical unresolved before parsing/scoring."""

    if not isinstance(wire, dict) or set(wire) != {
        "state_candidates",
        "continuity_decisions",
    }:
        raise ProviderProtocolError(
            "label-invariance extraction must contain exactly state_candidates and "
            "continuity_decisions"
        )
    decisions = wire["continuity_decisions"]
    if not isinstance(decisions, dict) or set(decisions) != set(SHADOW_SLOT_ORDER):
        raise ProviderProtocolError(
            "label-invariance continuity_decisions must contain exactly referent, "
            "open_question, and active_task"
        )

    shadow_decisions = copy.deepcopy(decisions)
    open_question_slot = decisions[SHADOW_OPEN_QUESTION_KIND]
    if isinstance(open_question_slot, dict):
        transitions = open_question_slot.get("transitions")
        if isinstance(transitions, list):
            for transition in transitions:
                if (
                    not isinstance(transition, dict)
                    or transition.get("kind") != SHADOW_OPEN_QUESTION_KIND
                ):
                    raise ProviderProtocolError(
                        "label-invariance open_question transition kind must match its "
                        "containing slot"
                    )

    canonical_wire = copy.deepcopy(wire)
    canonical_decisions = canonical_wire["continuity_decisions"]
    canonical_slot = canonical_decisions.pop(SHADOW_OPEN_QUESTION_KIND)
    canonical_decisions[CANONICAL_UNRESOLVED_KIND] = canonical_slot
    canonical_wire["continuity_decisions"] = {
        "referent": canonical_decisions["referent"],
        CANONICAL_UNRESOLVED_KIND: canonical_decisions[CANONICAL_UNRESOLVED_KIND],
        "active_task": canonical_decisions["active_task"],
    }
    if isinstance(canonical_slot, dict):
        transitions = canonical_slot.get("transitions")
        if isinstance(transitions, list):
            for transition in transitions:
                if isinstance(transition, dict):
                    transition["kind"] = CANONICAL_UNRESOLVED_KIND

    output, _ = parse_fixed_slot_wire(
        wire=canonical_wire,
        completion=completion,
    )
    return output, shadow_decisions
