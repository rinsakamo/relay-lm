from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from relaylm.budget_enforcement import (
    SerializedCognitiveInputTokenCounter,
    SerializedInputTokenCount,
    TokenCountMode,
)
from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_budget import (
    OpenAICompatibleSerializedInputCounter,
)
from relaylm.state import STATE_CLASS_DEFINITIONS, StateRecord


def _cognitive_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(
            StateRecord(
                state_id="s1",
                state_class="user.preference",
                key="tea",
                value="likes",
                sources=("old",),
            ),
        ),
        context=(
            ContextItem(
                content="Earlier assistant utterance",
                sources=("evt-old",),
                actor="assistant",
            ),
        ),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "紅茶が好き"},
            event_id="evt-now",
            timestamp="2026-08-17T00:00:00+00:00",
        ),
    )


def _raises(error: type[Exception], action: Callable[[], object]) -> bool:
    try:
        action()
    except error:
        return True
    except Exception:
        return False
    return False


async def evaluate_openai_serialized_counter() -> EvaluationScenarioResult:
    counted: list[dict[str, Any]] = []
    sent: list[dict[str, Any]] = []

    def exact_count(model_input: Mapping[str, Any]) -> SerializedInputTokenCount:
        counted.append(dict(model_input))
        return SerializedInputTokenCount(
            total_input_tokens=321,
            required_input_framing_tokens=123,
            mode=TokenCountMode.EXACT,
        )

    cognitive_input = _cognitive_input()
    counter = OpenAICompatibleSerializedInputCounter(
        model="gemma",
        count_input=exact_count,
    )
    exact = counter.count_serialized_input(cognitive_input)
    provider_requests_after_counting = len(sent)

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        wire = {"utterance": "了解。", "state_candidates": []}
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(wire, ensure_ascii=False)}}
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleProvider(
            base_url="http://lm.test/v1",
            model="gemma",
            http_client=client,
        )
        await provider.generate(cognitive_input)

    sent_model_input = {key: value for key, value in sent[0].items() if key != "stream"}

    def conservative_count(model_input: Mapping[str, Any]) -> SerializedInputTokenCount:
        counted.append(dict(model_input))
        return SerializedInputTokenCount(
            total_input_tokens=10,
            required_input_framing_tokens=4,
            mode=TokenCountMode.CONSERVATIVE_ESTIMATE,
        )

    protocol_counter = OpenAICompatibleSerializedInputCounter(
        model="gemma",
        count_input=conservative_count,
    )
    conservative = protocol_counter.count_serialized_input(cognitive_input)

    invalid_rejections = (
        _raises(
            ValueError,
            lambda: OpenAICompatibleSerializedInputCounter(
                model=" ",
                count_input=exact_count,
            ),
        ),
        _raises(
            TypeError,
            lambda: OpenAICompatibleSerializedInputCounter(
                model="gemma",
                count_input=42,  # type: ignore[arg-type]
            ),
        ),
        _raises(
            TypeError,
            lambda: OpenAICompatibleSerializedInputCounter(
                model="gemma",
                count_input=lambda _: 10,  # type: ignore[arg-type,return-value]
            ).count_serialized_input(cognitive_input),
        ),
    )

    checks = (
        EvaluationCheck(
            check_id="counter_matches_buffered_model_input_shape",
            boundary="provider_adapter",
            passed=(
                provider_requests_after_counting == 0
                and len(sent) == 1
                and counted[0] == sent_model_input
                and "stream" not in counted[0]
                and "stream" in sent[0]
            ),
            expected=True,
            observed=counted[0] == sent_model_input,
        ),
        EvaluationCheck(
            check_id="counter_implements_serialized_counter_protocol",
            boundary="provider_adapter",
            passed=isinstance(
                protocol_counter,
                SerializedCognitiveInputTokenCounter,
            ),
            expected=True,
            observed=isinstance(
                protocol_counter,
                SerializedCognitiveInputTokenCounter,
            ),
        ),
        EvaluationCheck(
            check_id="caller_supplied_count_is_preserved",
            boundary="provider_adapter",
            passed=(
                exact.total_input_tokens == 321
                and exact.required_input_framing_tokens == 123
                and exact.mode is TokenCountMode.EXACT
                and conservative.total_input_tokens == 10
                and conservative.required_input_framing_tokens == 4
                and conservative.mode is TokenCountMode.CONSERVATIVE_ESTIMATE
            ),
            expected="exact,conservative_estimate",
            observed=f"{exact.mode.value},{conservative.mode.value}",
        ),
        EvaluationCheck(
            check_id="invalid_configuration_and_untyped_result_are_rejected",
            boundary="provider_adapter",
            passed=all(invalid_rejections),
            expected=3,
            observed=sum(invalid_rejections),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="openai_serialized_counter",
        checks=checks,
        metrics={
            "provider_generation_count": len(sent),
            "counting_callback_count": len(counted),
            "stream_field_exclusion_count": int(
                "stream" in sent[0] and "stream" not in counted[0]
            ),
            "invalid_input_rejection_count": sum(invalid_rejections),
        },
    )
