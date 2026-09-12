from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from relaylm.cognitive import CognitiveInput, ContextItem, EventEvidenceItem
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_two_pass import (
    OpenAICompatibleTwoPassProvider,
    _conversation_request_body,
    _extraction_request_body,
)
from relaylm.state import STATE_CLASS_DEFINITIONS, StateRecord


def _accepted_continuity(source_id: str) -> ContextItem:
    return ContextItem(
        content=json.dumps(
            {
                "continuity": {
                    "kind": "referent",
                    "key": "current_note",
                    "value": "the blue note",
                    "epistemic_role": "user_assertion",
                }
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        sources=(source_id,),
    )


def _cognitive_input(
    *,
    current_id: str,
    prior_id: str,
    evidence_id: str,
) -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(
            StateRecord(
                state_id="state-name",
                state_class="user.identity",
                key="name",
                value="ユウ",
                sources=(prior_id,),
            ),
        ),
        context=(
            _accepted_continuity(prior_id),
            ContextItem(
                content="Earlier user message.",
                sources=(prior_id,),
                actor="user",
            ),
        ),
        event_evidence=(
            EventEvidenceItem(
                event_id=evidence_id,
                event_type="message",
                actor="user",
                timestamp="2026-09-01T00:00:00+00:00",
                content="Recorded occurrence.",
            ),
        ),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "僕の名前はユウト。青いノートの話を続けよう。"},
            event_id=current_id,
            timestamp="2026-09-12T00:00:00+00:00",
        ),
    )


def _request_pair(cognitive_input: CognitiveInput) -> tuple[dict[str, object], dict[str, object]]:
    pass1 = _conversation_request_body(
        model="gemma",
        cognitive_input=cognitive_input,
        stream=False,
        decoding={"temperature": 0, "top_p": 1},
    )
    pass2 = _extraction_request_body(
        model="gemma",
        extraction_input=CognitionExtractionInput(
            cognitive_input=cognitive_input,
            assistant_response="ユウトさん、青いノートの話を続けましょう。",
        ),
        decoding={"temperature": 0, "top_p": 1},
        lifecycle_channel_separation=True,
    )
    return pass1, pass2


def test_two_pass_request_bytes_are_invariant_to_real_event_ids() -> None:
    first = _cognitive_input(
        current_id="run-a-current",
        prior_id="run-a-prior",
        evidence_id="run-a-evidence",
    )
    second = _cognitive_input(
        current_id="run-b-current",
        prior_id="run-b-prior",
        evidence_id="run-b-evidence",
    )

    first_pass1, first_pass2 = _request_pair(first)
    second_pass1, second_pass2 = _request_pair(second)

    assert first_pass1 == second_pass1
    assert first_pass2 == second_pass2


def test_two_pass_model_facing_requests_do_not_expose_real_event_ids() -> None:
    cognitive_input = _cognitive_input(
        current_id="real-current-event",
        prior_id="real-prior-event",
        evidence_id="real-evidence-event",
    )
    pass1, pass2 = _request_pair(cognitive_input)

    pass1_text = json.dumps(pass1, ensure_ascii=False, sort_keys=True)
    pass2_text = json.dumps(pass2, ensure_ascii=False, sort_keys=True)
    for real_id in ("real-current-event", "real-prior-event", "real-evidence-event"):
        assert real_id not in pass1_text
        assert real_id not in pass2_text

    assert '"event_id":"E0"' in pass1["messages"][1]["content"]
    assert "current Input Event ID `E0`" in pass2["messages"][1]["content"]


def test_two_pass_extraction_restores_alias_sources_to_real_event_ids() -> None:
    cognitive_input = _cognitive_input(
        current_id="real-current-event",
        prior_id="real-prior-event",
        evidence_id="real-evidence-event",
    )
    seen_request: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_request.update(json.loads(request.content.decode("utf-8")))
        wire = {
            "state_candidates": [
                {
                    "state_class": "user.identity",
                    "key": "name",
                    "op": "set",
                    "value": "ユウト",
                    "sources": ["E0"],
                }
            ],
            "continuity_candidates": [],
        }
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": json.dumps(wire, ensure_ascii=False)},
                        "finish_reason": "stop",
                    }
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            return await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=cognitive_input,
                    assistant_response="ユウトさん、了解です。",
                )
            )

    output = asyncio.run(run())

    assert output.state_candidates[0].sources == ("real-current-event",)
    request_text = json.dumps(seen_request, ensure_ascii=False, sort_keys=True)
    assert "real-current-event" not in request_text
    assert "real-prior-event" not in request_text
    assert "real-evidence-event" not in request_text


def test_two_pass_extraction_rejects_unknown_provider_alias() -> None:
    cognitive_input = _cognitive_input(
        current_id="real-current-event",
        prior_id="real-prior-event",
        evidence_id="real-evidence-event",
    )

    def handler(_: httpx.Request) -> httpx.Response:
        wire = {
            "state_candidates": [
                {
                    "state_class": "user.identity",
                    "key": "name",
                    "op": "set",
                    "value": "ユウト",
                    "sources": ["E999"],
                }
            ],
            "continuity_candidates": [],
        }
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": json.dumps(wire, ensure_ascii=False)},
                        "finish_reason": "stop",
                    }
                ]
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=cognitive_input,
                    assistant_response="ユウトさん、了解です。",
                )
            )

    with pytest.raises(ProviderProtocolError, match="provenance alias"):
        asyncio.run(run())
