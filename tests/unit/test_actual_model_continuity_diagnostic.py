from __future__ import annotations

import json

import pytest

from relaylm.actual_model_continuity_diagnostic import (
    SHADOW_OPEN_QUESTION_KIND,
    alias_projected_continuity_context,
    apply_fixed_slot_transport,
    label_alias_prompt,
    parse_label_alias_wire,
)
from relaylm.cognition_execution import CognitionCompletionMetadata
from relaylm.providers.openai_compatible import ProviderProtocolError


def _transition(*, op: str = "set") -> dict[str, object]:
    return {
        "kind": SHADOW_OPEN_QUESTION_KIND,
        "key": "document_author",
        "op": op,
        "value": None if op == "resolve" else "author not yet known",
        "sources": ["evt-now"],
        "epistemic_role": "user_assertion",
    }


def _wire(*, op: str = "set") -> dict[str, object]:
    return {
        "state_candidates": [],
        "continuity_decisions": {
            "referent": {"decision": "none", "transitions": []},
            SHADOW_OPEN_QUESTION_KIND: {
                "decision": "emit",
                "transitions": [_transition(op=op)],
            },
            "active_task": {"decision": "none", "transitions": []},
        },
    }


@pytest.mark.parametrize("op", ["set", "resolve"])
def test_shadow_set_and_resolve_return_canonical_unresolved(op: str) -> None:
    output, shadow = parse_label_alias_wire(
        wire=_wire(op=op),
        completion=CognitionCompletionMetadata(finish_reason="stop"),
    )

    assert len(output.continuity_candidates) == 1
    candidate = output.continuity_candidates[0]
    assert candidate.kind == "unresolved"
    assert candidate.op == op
    if op == "resolve":
        assert candidate.has_value is False
    else:
        assert candidate.value == "author not yet known"
    assert shadow[SHADOW_OPEN_QUESTION_KIND]["transitions"][0]["kind"] == (
        SHADOW_OPEN_QUESTION_KIND
    )


def test_alias_is_bounded_to_projected_continuity_context() -> None:
    projected = json.dumps(
        {
            "continuity": {
                "kind": "unresolved",
                "key": "document_author",
                "value": "author not yet known",
            }
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    untouched = json.dumps(
        {
            "event": {
                "content": "The user-authored word unresolved stays literal."
            }
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    aliased = json.loads(alias_projected_continuity_context(projected))
    assert aliased["continuity"]["kind"] == SHADOW_OPEN_QUESTION_KIND
    assert alias_projected_continuity_context(untouched) == untouched


def test_prompt_does_not_rewrite_current_input_or_pass1() -> None:
    body = {
        "messages": [
            {"role": "system", "content": "system"},
            {
                "role": "user",
                "content": (
                    "<COGNITIVE_INPUT>\n"
                    + json.dumps(
                        {
                            "input": {
                                "event_id": "evt-now",
                                "content": "Keep unresolved literal.",
                            },
                            "context": [],
                        },
                        separators=(",", ":"),
                    )
                    + "\n</COGNITIVE_INPUT>\n\n<PASS>\n"
                    + "<PASS_1_RESPONSE_JSON>\n"
                    + "{\"content\":\"Pass 1 says unresolved.\"}\n"
                    + "</PASS_1_RESPONSE_JSON>\n\n"
                    + "Emit `state_candidates`, then `continuity_candidates`.\n\n"
                    + "Exact top-level shape:\n"
                    + "`{\"state_candidates\":[],\"continuity_candidates\":[]}`\n\n"
                    + "Return exactly one JSON object with no extra keys.\n"
                    + "Use unresolved set and resolve only in the diagnostic slot."
                ),
            },
        ]
    }
    fixed = apply_fixed_slot_transport(body)
    prompt = fixed["messages"][1]["content"]

    aliased = label_alias_prompt(prompt)
    assert "Keep unresolved literal." in aliased
    assert "Pass 1 says unresolved." in aliased
    assert "open_question set" in aliased
    assert "unresolved set" not in aliased


def test_invalid_shadow_shape_and_transition_fail_closed() -> None:
    invalid = _wire()
    invalid["continuity_decisions"]["open_question"]["transitions"] = [
        _transition()
    ]
    invalid["continuity_decisions"]["open_question"]["transitions"][0][
        "kind"
    ] = "unresolved"
    with pytest.raises(ProviderProtocolError, match="transition kind must match"):
        parse_label_alias_wire(
            wire=invalid,
            completion=CognitionCompletionMetadata(),
        )

    missing_alias = _wire()
    missing_alias["continuity_decisions"]["unresolved"] = missing_alias[
        "continuity_decisions"
    ].pop("open_question")
    with pytest.raises(ProviderProtocolError, match="exactly referent"):
        parse_label_alias_wire(
            wire=missing_alias,
            completion=CognitionCompletionMetadata(),
        )
