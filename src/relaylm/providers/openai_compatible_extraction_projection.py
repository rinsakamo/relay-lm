from __future__ import annotations

import copy
import json
from enum import StrEnum
from typing import Any

from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.providers.openai_compatible import WIRE_SCHEMA


class ExtractionProjectionMode(StrEnum):
    """Canonical Pass 2 projection responsibility carried by one request."""

    PRODUCTION = "production"
    CONTINUITY_ONLY = "continuity_only"


def _candidate_collection_schema(name: str) -> dict[str, Any]:
    return copy.deepcopy(WIRE_SCHEMA["properties"][name])


EXTRACTION_WIRE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "state_candidates",
        "continuity_candidates",
    ],
    "properties": {
        "state_candidates": _candidate_collection_schema("state_candidates"),
        "continuity_candidates": _candidate_collection_schema("continuity_candidates"),
    },
}

CONTINUITY_ONLY_EXTRACTION_WIRE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["continuity_candidates"],
    "properties": {
        "continuity_candidates": copy.deepcopy(
            EXTRACTION_WIRE_SCHEMA["properties"]["continuity_candidates"]
        ),
    },
}


def extraction_response_component(extraction_input: CognitionExtractionInput) -> str:
    response_json = json.dumps(
        {"content": extraction_input.assistant_response},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"""EXTRACTION

<PASS_1_RESPONSE_JSON>
{response_json}
</PASS_1_RESPONSE_JSON>

"""


def production_extraction_intro() -> str:
    return """Interpret this originating turn as this character, then project only grounded State and bounded Continuity proposals.
Emit `state_candidates`, then `continuity_candidates`.

Projection rules:
"""


def continuity_only_extraction_intro() -> str:
    return """Interpret this originating turn as this character, then project only bounded Continuity proposals.
Emit `continuity_candidates`.

Projection rules:
"""


def state_extraction_component(source_id: str) -> str:
    like_example = json.dumps(
        {
            "state_class": "user.preference",
            "key": "coffee",
            "op": "set",
            "value": "likes",
            "sources": [source_id],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    preferred_example = json.dumps(
        {
            "state_class": "user.preference",
            "key": "preferred_beverage",
            "op": "set",
            "value": "coffee",
            "sources": [source_id],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    remove_example = json.dumps(
        {
            "state_class": "user.preference",
            "key": "coffee",
            "op": "remove",
            "value": None,
            "sources": [source_id],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"""- Durable State gate: emit State only when the current Input presents the candidate meaning as sufficiently asserted, committed, or otherwise established for persistent current understanding.
- Evaluate newly established durable State independently before Continuity proposals.
- First-introduction durable State does not require a pre-existing accepted State record.
- Tentative, hypothetical, merely possible, guessed, hedged, or explicitly self-uncertain meaning stays uncommitted: emit no durable State for that meaning.
- Apply this gate by meaning regardless of language or state_class; do not use surface keywords or grammatical patterns as the gate.
- Epistemic uncertainty is not degree_hint; degree_hint remains semantic intensity only. A later resolved assertion may establish State normally.
- State wire: `{{state_class,key,op,value,sources}}`. `state_class` must be a key in CognitiveInput.state_classes. `op` is `set` or `remove`. For `set`, value is a string or `{{\"semantic\":string,\"degree_hint\":0..1}}`; degree_hint is intensity, not confidence. For `remove`, value is null; remove only for explicit revocation, cancellation, denial, correction, or termination.
- State `key` is the stable subject or dimension within its `state_class`; `value` is the accepted semantic value for that key. Preserve an established class/key pair when current State already provides one rather than inventing a synonym.
- State examples demonstrate representation only; never copy example values, keys, or claims unless current evidence supports that exact meaning:
  - Liking a subject: `{like_example}`
  - A preference dimension whose value is the subject: `{preferred_example}`
  - Explicit revocation of an accepted subject preference: `{remove_example}`
- Continuity-specific instructions, including `emit only`, apply only within `continuity_candidates` and never suppress an otherwise-grounded `state_candidates` proposal.
"""


def continuity_extraction_component(source_id: str) -> str:
    referent_example = json.dumps(
        {
            "kind": "referent",
            "key": "current_document",
            "op": "set",
            "value": "the draft",
            "sources": [source_id],
            "epistemic_role": "user_assertion",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    unresolved_example = json.dumps(
        {
            "kind": "unresolved",
            "key": "document_author",
            "op": "set",
            "value": "author not yet known",
            "sources": [source_id],
            "epistemic_role": "user_assertion",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    active_task_example = json.dumps(
        {
            "kind": "active_task",
            "key": "verify_document_author",
            "op": "set",
            "value": "verify the document author",
            "sources": [source_id],
            "epistemic_role": "user_assertion",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"""- Continuity wire: `{{kind,key,op,value,sources,epistemic_role}}`. `op` is `set` or `resolve`; set value is finite JSON and resolve value is null. Carry Continuity only when it is useful for upcoming coherence.
- Continuity is an explicit cross-turn aid, not a summary of salient content.
- Continuity meanings (classify independently):
  - `referent`: a specific subject or entity that upcoming dialogue may refer back to.
  - `unresolved`: an explicit open question or unknown value that remains to be resolved.
  - `active_task`: an unfinished action, process, or goal expected to continue.
- Emit every distinct useful Continuity meaning present; do not choose only one best kind.
- New items use a short stable semantic `key`; exact first-introduction wording is not globally canonical.
- A subject mentioned only as the current turn's topic is not a referent candidate; a bare intention to discuss or continue it does not establish cross-turn reference.
- Emit a new `referent` only when the current Input explicitly establishes a cross-turn pointer, alias, or future-reference plan.
- A Context item whose content is a `continuity` JSON record is an already accepted temporary Continuity item, not a new proposal or prior assistant utterance.
- For each Continuity kind, compare the current Input with the accepted item independently: `set` for a new meaning, `resolve` for a current resolution, and no candidate for an unchanged meaning.
- Never copy an accepted item's prior `sources` into a new transition; every transition caused by the current turn uses the current Input Event ID.
- Continuity transition decision:
  - new useful meaning -> emit `set` with a new stable key.
  - unchanged accepted meaning -> emit no candidate.
  - changed or resolved accepted meaning -> reuse its existing lifecycle key.
- Evaluate resolution or completion independently for each Continuity kind.
- Resolving an `unresolved` or `active_task` meaning does not by itself resolve a related `referent`.
- If that referent meaning is unchanged, emit no referent candidate.
- Completion or resolution of work about a referent, discovery of new facts about it, or an expectation that it may not be mentioned next does not end the referent.
- Resolve a `referent` only when the current Input explicitly replaces, dismisses, or invalidates the reference target itself; do not infer referent resolution from completion of related `unresolved` or `active_task` meanings.
- Before concluding there are no Continuity candidates, check `unresolved` independently: if this turn newly establishes an explicit open question or unknown value, emit a new `unresolved` set when no accepted unresolved item already represents that open issue, even when related accepted `referent` or `active_task` meanings are unchanged.
- An explicitly maintained unknown value is itself an `unresolved` meaning when no accepted unresolved item already represents it. Do not require a new `active_task`, a question form, or a change to an existing task before emitting it.
- Unchanged accepted `referent` or `active_task` meanings do not suppress a distinct newly established `unresolved` meaning.
- If related accepted referent/task meanings are unchanged and the current Event newly establishes an unknown value with no accepted unresolved item, emit only the new `unresolved` set as applicable.
- A `referent` identifies the reference target; new descriptive facts about the same target do not supersede it unless the referential target itself changes.
- For ordinary-turn Continuity, every new set/resolve transition must include the current Input Event ID `{source_id}` in `sources`; prior Continuity/context sources describe existing context but cannot substitute for current evidence of a new transition.
- Resolve only when the current turn actually resolves or completes an existing item; reuse that item's `kind` + `key`, set value to null, and ground the resolution in the current Input Event.
- Continuity examples demonstrate representation only; never copy their keys, values, or claims unless current evidence supports that exact meaning:
  - Referent: `{referent_example}`
  - Unresolved transition example: `{unresolved_example}`
  - Active task: `{active_task_example}`
- Never use `resolve` as `kind`; keep `kind` as `referent`, `unresolved`, or `active_task`.
- `kind` and `epistemic_role` are separate enum axes; `unresolved` is a `kind` only and must never be used as `epistemic_role`.
- `epistemic_role` must be exactly `user_assertion`, `assistant_inference`, or `assistant_commitment`.
- `sources` are non-empty Event IDs present in CognitiveInput; never invent IDs. Pass 1 response is interpretive context only and must never self-certify user facts/preferences/goals/experience, external truth, prior events, or source provenance.
"""


def production_extraction_outro() -> str:
    return """
Exact top-level shape:
`{\"state_candidates\":[],\"continuity_candidates\":[]}`

Return exactly one JSON object with no extra keys."""


def continuity_only_extraction_outro() -> str:
    return """
Exact top-level shape:
`{\"continuity_candidates\":[]}`

Return exactly one JSON object with no extra keys."""


def build_extraction_pass_suffix(
    extraction_input: CognitionExtractionInput,
    *,
    mode: ExtractionProjectionMode = ExtractionProjectionMode.PRODUCTION,
) -> str:
    source_id = extraction_input.originating_event_id
    common = extraction_response_component(extraction_input)
    continuity = continuity_extraction_component(source_id)
    if mode is ExtractionProjectionMode.PRODUCTION:
        return (
            common
            + production_extraction_intro()
            + state_extraction_component(source_id)
            + continuity
            + production_extraction_outro()
        )
    if mode is ExtractionProjectionMode.CONTINUITY_ONLY:
        return (
            common
            + continuity_only_extraction_intro()
            + continuity
            + continuity_only_extraction_outro()
        )
    raise TypeError("unsupported extraction projection mode")


def extraction_wire_schema(mode: ExtractionProjectionMode) -> dict[str, Any]:
    if mode is ExtractionProjectionMode.PRODUCTION:
        return EXTRACTION_WIRE_SCHEMA
    if mode is ExtractionProjectionMode.CONTINUITY_ONLY:
        return CONTINUITY_ONLY_EXTRACTION_WIRE_SCHEMA
    raise TypeError("unsupported extraction projection mode")


def extraction_schema_name(mode: ExtractionProjectionMode) -> str:
    if mode is ExtractionProjectionMode.PRODUCTION:
        return "relaylm_structured_cognition_output"
    if mode is ExtractionProjectionMode.CONTINUITY_ONLY:
        return "relaylm_continuity_only_extraction_output"
    raise TypeError("unsupported extraction projection mode")
