from __future__ import annotations

from typing import Any

from relaylm.actual_model_vllm_capacity import (
    VLLMCapacityFootprintObservation,
    vllm_capacity_pass_request_id,
)
from relaylm.actual_model_vllm_host import VLLMScreeningCondition
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
)
from relaylm.providers.openai_compatible_budget import (
    OpenAICompatibleSerializedInputCounter,
    OpenAICompatibleTwoPassSerializedInputCounter,
)


class VLLMCapacityAcquisitionError(ValueError):
    """A vLLM capacity-acquisition trajectory cannot be measured truthfully."""


class VLLMCapacityMeasurementProvider:
    """Measure exact production inputs immediately before real provider delegation.

    The wrapper never serializes prompts itself. It delegates counting to the
    existing OpenAI-compatible serialized-input counters, binds each successful
    count to the selected screening condition/scenario/pass coordinate, records
    that content-free observation, and only then invokes the real provider.
    Consequently an upstream provider failure cannot erase a footprint already
    proven by the serving tokenizer, while calls that were never reached are
    never fabricated.
    """

    def __init__(
        self,
        *,
        delegate: Any,
        condition: VLLMScreeningCondition,
        scenario_id: str,
        single_pass_counter: OpenAICompatibleSerializedInputCounter | Any | None = None,
        two_pass_counter: OpenAICompatibleTwoPassSerializedInputCounter | Any | None = None,
    ) -> None:
        if not isinstance(condition, VLLMScreeningCondition):
            raise TypeError("condition must be VLLMScreeningCondition")
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ValueError("scenario_id must be a non-empty string")
        if condition.pass_requests.mode == "single_pass":
            if single_pass_counter is None:
                raise VLLMCapacityAcquisitionError(
                    "single-pass capacity measurement requires a single-pass counter"
                )
            if two_pass_counter is not None:
                raise VLLMCapacityAcquisitionError(
                    "single-pass capacity measurement must not receive a two-pass counter"
                )
        elif condition.pass_requests.mode == "two_pass":
            if two_pass_counter is None:
                raise VLLMCapacityAcquisitionError(
                    "two-pass capacity measurement requires a two-pass counter"
                )
            if single_pass_counter is not None:
                raise VLLMCapacityAcquisitionError(
                    "two-pass capacity measurement must not receive a single-pass counter"
                )
        else:
            raise VLLMCapacityAcquisitionError(
                "unsupported screening pass-request topology"
            )
        self.delegate = delegate
        self.condition = condition
        self.scenario_id = scenario_id
        self.single_pass_counter = single_pass_counter
        self.two_pass_counter = two_pass_counter
        self._observations: list[VLLMCapacityFootprintObservation] = []
        self._single_turns = 0
        self._conversation_turns = 0
        self._extraction_turns = 0

    @property
    def observations(self) -> tuple[VLLMCapacityFootprintObservation, ...]:
        return tuple(self._observations)

    async def generate(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitiveOutput:
        expected = self.condition.pass_requests.single_request
        if self.condition.pass_requests.mode != "single_pass" or expected is None:
            raise VLLMCapacityAcquisitionError(
                "single-pass generation does not match selected screening topology"
            )
        _require_pass_request(pass_request=pass_request, expected=expected)
        counter = self.single_pass_counter
        assert counter is not None
        turn_index = self._single_turns + 1
        count = counter.count_serialized_input(
            cognitive_input,
            pass_request=pass_request,
        )
        self._record(
            topology="single_pass",
            pass_id="single_pass",
            turn_index=turn_index,
            pass_request=expected,
            total_input_tokens=count.total_input_tokens,
            required_input_framing_tokens=count.required_input_framing_tokens,
            count_mode=count.mode,
        )
        self._single_turns = turn_index
        output = await self.delegate.generate(
            cognitive_input,
            pass_request=pass_request,
        )
        if not isinstance(output, CognitiveOutput):
            raise TypeError("provider generate must return CognitiveOutput")
        return output

    async def generate_conversation(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionConversationOutput:
        expected = self.condition.pass_requests.pass1
        if self.condition.pass_requests.mode != "two_pass" or expected is None:
            raise VLLMCapacityAcquisitionError(
                "conversation generation does not match selected screening topology"
            )
        _require_pass_request(pass_request=pass_request, expected=expected)
        counter = self.two_pass_counter
        assert counter is not None
        if self._conversation_turns != self._extraction_turns:
            raise VLLMCapacityAcquisitionError(
                "next Pass 1 cannot start before the prior Pass 2 trajectory completes"
            )
        turn_index = self._conversation_turns + 1
        count = counter.count_conversation_input(
            cognitive_input,
            pass_request=pass_request,
        )
        self._record(
            topology="two_pass",
            pass_id="pass1",
            turn_index=turn_index,
            pass_request=expected,
            total_input_tokens=count.total_input_tokens,
            required_input_framing_tokens=count.required_input_framing_tokens,
            count_mode=count.mode,
        )
        self._conversation_turns = turn_index
        output = await self.delegate.generate_conversation(
            cognitive_input,
            pass_request=pass_request,
        )
        if not isinstance(output, CognitionConversationOutput):
            raise TypeError(
                "provider generate_conversation must return CognitionConversationOutput"
            )
        return output

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionExtractionOutput:
        expected = self.condition.pass_requests.pass2
        if self.condition.pass_requests.mode != "two_pass" or expected is None:
            raise VLLMCapacityAcquisitionError(
                "extraction generation does not match selected screening topology"
            )
        _require_pass_request(pass_request=pass_request, expected=expected)
        if self._conversation_turns != self._extraction_turns + 1:
            raise VLLMCapacityAcquisitionError(
                "Pass 2 measurement requires exactly one completed Pass 1"
            )
        counter = self.two_pass_counter
        assert counter is not None
        turn_index = self._extraction_turns + 1
        count = counter.count_extraction_input(
            extraction_input,
            pass_request=pass_request,
        )
        self._record(
            topology="two_pass",
            pass_id="pass2",
            turn_index=turn_index,
            pass_request=expected,
            total_input_tokens=count.total_input_tokens,
            required_input_framing_tokens=count.required_input_framing_tokens,
            count_mode=count.mode,
        )
        self._extraction_turns = turn_index
        output = await self.delegate.generate_extraction(
            extraction_input,
            pass_request=pass_request,
        )
        if not isinstance(output, CognitionExtractionOutput):
            raise TypeError(
                "provider generate_extraction must return CognitionExtractionOutput"
            )
        return output

    async def aclose(self) -> None:
        close = getattr(self.delegate, "aclose", None)
        if callable(close):
            await close()

    def _record(
        self,
        *,
        topology: str,
        pass_id: str,
        turn_index: int,
        pass_request: CognitionPassRequest,
        total_input_tokens: int,
        required_input_framing_tokens: int,
        count_mode: Any,
    ) -> None:
        self._observations.append(
            VLLMCapacityFootprintObservation(
                condition_id=self.condition.condition_id,
                topology=topology,
                pass_id=pass_id,
                scenario_id=self.scenario_id,
                turn_index=turn_index,
                pass_request_id=vllm_capacity_pass_request_id(pass_request),
                total_input_tokens=total_input_tokens,
                required_input_framing_tokens=required_input_framing_tokens,
                count_mode=count_mode,
            )
        )


def _require_pass_request(
    *,
    pass_request: CognitionPassRequest | None,
    expected: CognitionPassRequest,
) -> None:
    if pass_request != expected:
        raise VLLMCapacityAcquisitionError(
            "provider pass request does not match selected screening pass request"
        )
