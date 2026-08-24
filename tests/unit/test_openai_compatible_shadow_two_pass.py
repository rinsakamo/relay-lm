from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.shadow_turn import run_user_turn_shadow_two_pass


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind and honest.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    character = CharacterDirectory(root)
    character.save_state(CanonicalState())
    return character


def _empty_turn_interpretation() -> dict[str, list[str]]:
    return {
        "user_meaning": [],
        "change_signals": [],
        "self_meaning": [],
        "assistant_effects": [],
        "unresolved": [],
        "continuity_signals": [],
    }


def test_shadow_two_pass_reuses_one_openai_adapter_with_relaylm_owned_extraction(
    tmp_path: Path,
) -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        system_prompt = body["messages"][0]["content"]
        if "RelayLM combined cognitive IR contract" in system_prompt:
            wire = {
                "utterance": "canonical",
                "state_candidates": [],
                "continuity_candidates": [],
            }
        else:
            wire = {
                "turn_interpretation": _empty_turn_interpretation(),
                "state_candidates": [],
                "continuity_candidates": [],
            }
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(wire, ensure_ascii=False)}}
                ]
            },
        )

    async def run() -> None:
        character = _make_character(tmp_path)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleTwoPassProvider(
                base_url="http://lm.test/v1",
                model="gemma",
                http_client=client,
            )
            result = await run_user_turn_shadow_two_pass(
                character=character,
                provider=provider,
                content="hello",
            )
            shadow = await result.shadow
            assert shadow.output is not None

    asyncio.run(run())

    assert len(seen) == 2
    assert [body["model"] for body in seen] == ["gemma", "gemma"]
    assert "response_format" not in seen[0]
    assert "response_format" not in seen[1]
    assert "RelayLM combined cognitive IR contract" in seen[0]["messages"][0]["content"]
    assert "cognitive substrate of a persistent character" in seen[1]["messages"][0]["content"]
    assert "<PASS>\nEXTRACTION" in seen[1]["messages"][1]["content"]
    assert "turn_interpretation" in seen[1]["messages"][1]["content"]
