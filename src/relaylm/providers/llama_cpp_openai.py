from __future__ import annotations

from typing import Any

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
    CognitionConversationOutput,
    normalize_cognition_execution_capabilities,
    resolve_pass_request,
)
from relaylm.providers.llama_cpp_reasoning import (
    LlamaCppReasoningCapabilityAttestation,
    realize_llama_cpp_reasoning_request,
)
from relaylm.providers.openai_compatible_decoding import OpenAICompatibleDecodingConfig
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.providers.openai_compatible_two_pass import (
    OpenAICompatibleTwoPassProvider,
    _conversation_request_body,
    _extraction_request_body,
    _parse_conversation_completion,
    _parse_extraction_completion,
    _require_candidate_sources_in_cognitive_input,
    _require_plain_pass1,
    _resolve_extraction_structured_output_mode,
)


class LlamaCppOpenAICompatibleTwoPassProvider(OpenAICompatibleTwoPassProvider):
    """llama.cpp realization of the canonical OpenAI-compatible two-pass provider.

    The semantic prompts, parsers, source checks and native JSON-Schema transport
    remain owned by ``OpenAICompatibleTwoPassProvider``. This class only supplies
    the backend-specific reasoning capability and exact request field.
    """

    def __init__(
        self,
        *,
        llama_cpp_reasoning_capability: LlamaCppReasoningCapabilityAttestation,
        **kwargs: Any,
    ) -> None:
        if not isinstance(
            llama_cpp_reasoning_capability, LlamaCppReasoningCapabilityAttestation
        ):
            raise TypeError(
                "llama_cpp_reasoning_capability must be "
                "LlamaCppReasoningCapabilityAttestation"
            )
        super().__init__(**kwargs)
        if llama_cpp_reasoning_capability.request_model != self.model:
            raise ValueError(
                "llama.cpp reasoning capability request_model must match provider model"
            )
        self.llama_cpp_reasoning_capability = llama_cpp_reasoning_capability

    async def generate_conversation(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
    ) -> CognitionConversationOutput:
        _require_plain_pass1(pass_request)
        decoding_config, effective_reasoning = self._resolve_llama_cpp_pass_request(
            pass_request=pass_request,
            reasoning_request=reasoning_request,
        )
        body = _conversation_request_body(
            model=self.model,
            cognitive_input=cognitive_input,
            stream=False,
            decoding=decoding_config.to_mapping(),
        )
        body.update(self._llama_cpp_reasoning_fields(effective_reasoning))
        envelope = await self._post_two_pass(body=body, boundary="conversation")
        return _parse_conversation_completion(envelope)

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
    ) -> CognitionExtractionOutput:
        decoding_config, effective_reasoning = self._resolve_llama_cpp_pass_request(
            pass_request=pass_request,
            reasoning_request=reasoning_request,
        )
        structured_output_mode = _resolve_extraction_structured_output_mode(
            pass_request=pass_request,
            provider=self,
        )
        body = _extraction_request_body(
            model=self.model,
            extraction_input=extraction_input,
            decoding=decoding_config.to_mapping(),
            structured_output_mode=structured_output_mode,
        )
        body.update(self._llama_cpp_reasoning_fields(effective_reasoning))
        envelope = await self._post_two_pass(body=body, boundary="extraction")
        output = _parse_extraction_completion(envelope)
        _require_candidate_sources_in_cognitive_input(
            output,
            extraction_input.cognitive_input,
        )
        return output

    def _resolve_llama_cpp_pass_request(
        self,
        *,
        pass_request: CognitionPassRequest | None,
        reasoning_request: OpenAICompatibleReasoningRequest | None,
    ) -> tuple[OpenAICompatibleDecodingConfig, OpenAICompatibleReasoningRequest | None]:
        if pass_request is None:
            return self.decoding_config, reasoning_request
        if not isinstance(pass_request, CognitionPassRequest):
            raise TypeError("pass_request must be CognitionPassRequest or None")
        if reasoning_request is not None:
            raise ValueError(
                "pass_request and provider reasoning_request cannot both be supplied"
            )

        capabilities = normalize_cognition_execution_capabilities(
            structured_output=True,
            streaming=False,
            reasoning_modes=("off",)
            if self.llama_cpp_reasoning_capability.enable_thinking_supported
            else (),
            bounded_reasoning_budget=False,
            decoding_controls=tuple(
                sorted(
                    control
                    for control in self.decoding_capabilities.supported_controls
                    if control in {"temperature", "top_p", "max_output_tokens"}
                )
            ),
        )
        resolve_pass_request(
            request=pass_request,
            capabilities=capabilities,
        ).require_supported()

        decoding = OpenAICompatibleDecodingConfig(
            temperature=pass_request.temperature,
            top_p=pass_request.top_p,
            seed=self.decoding_config.seed,
            max_output_tokens=pass_request.max_output_tokens,
        )
        self.decoding_capabilities.require(decoding)
        if pass_request.reasoning_mode is None:
            return decoding, None
        return decoding, OpenAICompatibleReasoningRequest(
            mode=pass_request.reasoning_mode.value,
            token_budget=pass_request.reasoning_budget,
        )

    def _llama_cpp_reasoning_fields(
        self,
        request: OpenAICompatibleReasoningRequest | None,
    ) -> dict[str, object]:
        if request is None:
            return {}
        return realize_llama_cpp_reasoning_request(
            request=request,
            capability=self.llama_cpp_reasoning_capability,
        ).to_request_fields()
