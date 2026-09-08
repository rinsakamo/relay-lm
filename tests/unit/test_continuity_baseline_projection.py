from __future__ import annotations

import asyncio
import json

import httpx

from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.state import STATE_CLASS_DEFINITIONS


_ACCEPTED_CONTENT = json.dumps(
    {
        "continuity": {
            "kind": "active_task",
            "key": "prepare_release_notes",
            "value": "prepare the release notes",
            "epistemic_role": "user_assertion",
        }
    },
    ensure_ascii=False,
    separators=(",", ":"),
    sort_keys=True,
)


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(
            ContextItem(
                content=_ACCEPTED_CONTENT,
                sources=("evt-accepted",),
            ),
            ContextItem(
                content="Earlier assistant wording",
                sources=("evt-assistant",),
                actor="assistant",
            ),
        ),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "Keep going; that task is unchanged."},
            event_id="evt-now",
            timestamp="2026-09-08T00:00:00+00:00",
        ),
    )


def test_pass2_repeats_only_accepted_continuity_as_comparison_baseline() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        prompt = body["messages"][1]["content"]
        if "<PASS>\nCONVERSATION" in prompt:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {"content": "Okay."},
                            "finish_reason": "stop",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "state_candidates": [],
                                    "continuity_candidates": [],
                                }
                            )
                        },
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
            conversation = await provider.generate_conversation(_cognitive_input())
            await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=_cognitive_input(),
                    assistant_response=conversation.response,
                )
            )

    asyncio.run(run())

    assert len(seen) == 2
    conversation_prompt = seen[0]["messages"][1]["content"]
    extraction_prompt = seen[1]["messages"][1]["content"]
    marker_open = "<ACCEPTED_CONTINUITY_BASELINE_JSON>\n"
    marker_close = "\n</ACCEPTED_CONTINUITY_BASELINE_JSON>"

    assert marker_open not in conversation_prompt
    assert extraction_prompt.count(marker_open) == 1
    assert extraction_prompt.count(marker_close) == 1

    baseline_text = extraction_prompt.split(marker_open, 1)[1].split(marker_close, 1)[0]
    assert json.loads(baseline_text) == [
        {
            "content": _ACCEPTED_CONTENT,
            "sources": ["evt-accepted"],
        }
    ]
    assert "Earlier assistant wording" not in baseline_text
    assert "comparison-only duplicate" in extraction_prompt
    assert "new Event source alone does not make an unchanged accepted meaning an update" in extraction_prompt
