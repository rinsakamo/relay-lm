from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionCompletionMetadata,
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
)
from relaylm.providers.llama_cpp_backend import (
    LlamaCppCapabilityAttestation,
    llama_cpp_reasoning_fields,
    resolve_llama_cpp_pass_request,
    resolve_llama_cpp_structured_output_mode,
)
from relaylm.providers.llama_cpp_reasoning import (
    LlamaCppReasoningCapabilityAttestation,
    realize_llama_cpp_reasoning_request,
)
from relaylm.providers.openai_compatible import (
    ProviderProtocolError,
    _iter_sse_data,
    _parse_stream_event,
    _provider_http_error,
)
from relaylm.providers.openai_compatible_decoding import OpenAICompatibleDecodingConfig
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest
from relaylm.providers.openai_compatible_two_pass import (
    OpenAICompatibleTwoPassProvider,
    _ProviderFacingProvenanceAliases,
    _conversation_request_body,
    _extraction_request_body,
    _parse_conversation_completion,
    _parse_extraction_completion,
    _require_candidate_sources_in_cognitive_input,
    _require_plain_pass1,
)
from relaylm.providers.openai_request_observation import observe_model_facing_request


class LlamaCppOpenAICompatibleTwoPassProvider(OpenAICompatibleTwoPassProvider):
    """llama.cpp realization of the canonical OpenAI-compatible two-pass provider.

    Prompt meaning, provenance aliasing, parsers, Pass-2 projection and Turn
    authority remain owned by the generic two-pass implementation. This class
    owns only llama.cpp wire realization: explicit capability resolution,
    cache-off carriage, reasoning-OFF carriage, and streaming transport.
    """

    def __init__(
        self,
        *,
        llama_cpp_reasoning_capability: LlamaCppReasoningCapabilityAttestation
        | None = None,
        llama_cpp_capability: LlamaCppCapabilityAttestation | None = None,
        **kwargs: Any,
    ) -> None:
        if llama_cpp_capability is not None and not isinstance(
            llama_cpp_capability, LlamaCppCapabilityAttestation
        ):
            raise TypeError(
                "llama_cpp_capability must be LlamaCppCapabilityAttestation or None"
            )
        if llama_cpp_reasoning_capability is None:
            if llama_cpp_capability is None:
                raise TypeError(
                    "llama_cpp_capability or llama_cpp_reasoning_capability is required"
                )
            llama_cpp_reasoning_capability = llama_cpp_capability.reasoning_capability
        if not isinstance(
            llama_cpp_reasoning_capability, LlamaCppReasoningCapabilityAttestation
        ):
            raise TypeError(
                "llama_cpp_reasoning_capability must be "
                "LlamaCppReasoningCapabilityAttestation"
            )
        if llama_cpp_capability is not None and kwargs.get("decoding_capabilities") is None:
            kwargs["decoding_capabilities"] = llama_cpp_capability.decoding_capabilities
        super().__init__(**kwargs)
        if llama_cpp_reasoning_capability.request_model != self.model:
            raise ValueError(
                "llama.cpp reasoning capability request_model must match provider model"
            )
        if (
            llama_cpp_capability is not None
            and llama_cpp_capability.request_model != self.model
        ):
            raise ValueError(
                "llama.cpp capability request_model must match provider model"
            )
        if (
            llama_cpp_capability is not None
            and llama_cpp_capability.reasoning_capability
            != llama_cpp_reasoning_capability
        ):
            raise ValueError(
                "llama.cpp reasoning and runtime capability identities must match"
            )
        self.llama_cpp_reasoning_capability = llama_cpp_reasoning_capability
        self.llama_cpp_capability = llama_cpp_capability

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
            streaming=False,
        )
        body = _conversation_request_body(
            model=self.model,
            cognitive_input=cognitive_input,
            stream=False,
            decoding=decoding_config.to_mapping(),
        )
        body.update(self._llama_cpp_reasoning_fields(effective_reasoning))
        body["cache_prompt"] = False
        envelope = await self._post_two_pass(body=body, boundary="conversation")
        return _parse_conversation_completion(envelope)

    async def stream_generate_conversation(
        self,
        cognitive_input: CognitiveInput,
        emit_response_delta: Callable[[str], Awaitable[None]],
        *,
        pass_request: CognitionPassRequest | None = None,
        reasoning_request: OpenAICompatibleReasoningRequest | None = None,
    ) -> CognitionConversationOutput:
        """Stream llama.cpp Pass 1 with the same backend-specific wire policy."""

        _require_plain_pass1(pass_request)
        decoding_config, effective_reasoning = self._resolve_llama_cpp_pass_request(
            pass_request=pass_request,
            reasoning_request=reasoning_request,
            streaming=True,
        )
        body = _conversation_request_body(
            model=self.model,
            cognitive_input=cognitive_input,
            stream=True,
            decoding=decoding_config.to_mapping(),
        )
        body.update(self._llama_cpp_reasoning_fields(effective_reasoning))
        body["cache_prompt"] = False
        response_text = ""
        saw_done = False
        saw_finish = False
        terminal_finish_reason: str | None = None

        try:
            observe_model_facing_request(body)
            async with self._client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            ) as response:
                if not response.is_success:
                    await response.aread()
                    raise _provider_http_error(
                        response,
                        prefix="upstream llama.cpp conversation streaming request failed",
                        api_key=self.api_key,
                    )
                async for data in _iter_sse_data(response):
                    if data == "[DONE]":
                        saw_done = True
                        break
                    if saw_finish:
                        raise ProviderProtocolError(
                            "upstream stream sent data after finish_reason"
                        )
                    content, finish_reason = _parse_stream_event(data)
                    if content is not None:
                        response_text += content
                        if content:
                            await emit_response_delta(content)
                    if finish_reason is not None:
                        saw_finish = True
                        terminal_finish_reason = finish_reason
        except ProviderProtocolError:
            raise
        except (httpx.HTTPError, UnicodeDecodeError, ValueError) as exc:
            raise ProviderProtocolError(
                f"upstream llama.cpp conversation streaming request failed: {exc}"
            ) from exc

        if not saw_done and not saw_finish:
            raise ProviderProtocolError(
                "upstream llama.cpp conversation stream ended before completion"
            )
        if not response_text.strip():
            raise ProviderProtocolError(
                "upstream llama.cpp conversation stream contained no visible response"
            )
        return CognitionConversationOutput(
            response=response_text,
            completion=CognitionCompletionMetadata(
                finish_reason=terminal_finish_reason,
            ),
        )

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
            streaming=False,
        )
        structured_output_mode = self._resolve_llama_cpp_structured_output_mode(
            pass_request
        )
        aliases = _ProviderFacingProvenanceAliases.from_cognitive_input(
            extraction_input.cognitive_input
        )
        body = _extraction_request_body(
            model=self.model,
            extraction_input=extraction_input,
            decoding=decoding_config.to_mapping(),
            structured_output_mode=structured_output_mode,
            lifecycle_channel_separation=True,
        )
        body.update(self._llama_cpp_reasoning_fields(effective_reasoning))
        body["cache_prompt"] = False
        envelope = await self._post_two_pass(body=body, boundary="extraction")
        output = aliases.restore_extraction_output(_parse_extraction_completion(envelope))
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
        streaming: bool = False,
    ) -> tuple[OpenAICompatibleDecodingConfig, OpenAICompatibleReasoningRequest | None]:
        if self.llama_cpp_capability is not None:
            return resolve_llama_cpp_pass_request(
                pass_request=pass_request,
                reasoning_request=reasoning_request,
                decoding_config=self.decoding_config,
                capability=self.llama_cpp_capability,
                streaming=streaming,
            )
        if streaming is False and pass_request is None:
            return self.decoding_config, reasoning_request
        if not isinstance(pass_request, CognitionPassRequest):
            raise TypeError("pass_request must be CognitionPassRequest or None")
        if reasoning_request is not None:
            raise ValueError(
                "pass_request and provider reasoning_request cannot both be supplied"
            )
        from relaylm.cognition_execution import (
            normalize_cognition_execution_capabilities,
            resolve_pass_request,
        )

        capabilities = normalize_cognition_execution_capabilities(
            structured_output=True,
            streaming=True,
            reasoning_modes=(
                ("off",)
                if self.llama_cpp_reasoning_capability.reasoning_effort_none_supported
                else ()
            ),
            bounded_reasoning_budget=False,
            decoding_controls=tuple(
                sorted(
                    control
                    for control in self.decoding_capabilities.supported_controls
                    if control in {"temperature", "top_p", "max_output_tokens"}
                )
            ),
        )
        resolve_pass_request(request=pass_request, capabilities=capabilities).require_supported()
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

    def _resolve_llama_cpp_structured_output_mode(
        self,
        pass_request: CognitionPassRequest | None,
    ):
        if self.llama_cpp_capability is not None:
            return resolve_llama_cpp_structured_output_mode(
                pass_request=pass_request,
                capability=self.llama_cpp_capability,
            )
        # Existing evaluation callers explicitly provide the reasoning attestation;
        # preserve their already-qualified native extraction path.
        from relaylm.providers.openai_compatible_two_pass import (
            _resolve_extraction_structured_output_mode,
        )

        return _resolve_extraction_structured_output_mode(
            pass_request=pass_request,
            provider=self,
        )

    def _llama_cpp_reasoning_fields(
        self,
        request: OpenAICompatibleReasoningRequest | None,
    ) -> dict[str, object]:
        if self.llama_cpp_capability is not None:
            return llama_cpp_reasoning_fields(request, self.llama_cpp_capability)
        if request is None:
            return {}
        return realize_llama_cpp_reasoning_request(
            request=request,
            capability=self.llama_cpp_reasoning_capability,
        ).to_request_fields()
