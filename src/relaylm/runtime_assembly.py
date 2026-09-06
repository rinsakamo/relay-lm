from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from relaylm.budget_enforcement import (
    SerializedCognitiveInputTokenCounter,
    TokenCountMode,
)
from relaylm.budget_runtime import (
    CognitiveBudgetRuntimeConfig,
    TwoPassCognitiveBudgetRuntimeConfig,
    TwoPassSerializedInputTokenCounter,
)
from relaylm.cognitive import CognitionExecutionMode
from relaylm.cognitive_profile import CognitiveProfileRegistry, CognitiveProfileRuntime
from relaylm.cognition_execution import CognitionPassRequest, CognitionReasoningMode
from relaylm.continuity import ContinuityContext
from relaylm.providers.lm_studio_reasoning import (
    LMStudioReasoningCapabilityAttestation,
)
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_backend import (
    OpenAICompatibleBackendId,
    decoding_capabilities_for_backend,
)
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningCapabilityAttestation,
)
from relaylm.runtime_config import ProviderRuntimeConfig, RuntimeConfigErrorCode
from relaylm.runtime_config_loader import ResolvedRuntimeConfig
from relaylm.storage.cognitive_package import CognitivePackageDirectory
from relaylm.turn import ContinuityRuntime, EventRetrievalBudget, MemoryRetrievalBudget
from relaylm.two_pass_turn import CognitionExecutionRuntime


TokenCounterFactory = Callable[[ProviderRuntimeConfig], object]
CognitiveBudgetRuntime = CognitiveBudgetRuntimeConfig | TwoPassCognitiveBudgetRuntimeConfig


class RuntimeAssemblyError(ValueError):
    """Safe typed failure while constructing owner-defined runtime objects."""

    def __init__(
        self,
        code: RuntimeConfigErrorCode,
        *,
        field: str | None,
        message: str,
    ) -> None:
        self.code = code
        self.field = field
        prefix = code.value if field is None else f"{code.value}: {field}"
        super().__init__(f"{prefix}: {message}")


@dataclass(frozen=True, slots=True)
class TokenCounterCapability:
    """Registered provider/model counter capability available to release assembly."""

    mode: TokenCountMode
    factory: TokenCounterFactory = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.mode, TokenCountMode):
            raise TypeError("token counter capability mode must be TokenCountMode")
        if not callable(self.factory):
            raise TypeError("token counter capability factory must be callable")


@dataclass(frozen=True, slots=True)
class RuntimeAssembly:
    """Owner-preserving objects needed by the ordinary RelayLM API path."""

    profiles: CognitiveProfileRegistry
    cognition_mode: CognitionExecutionMode = CognitionExecutionMode.TWO_PASS
    pass1_request: CognitionPassRequest | None = None
    pass2_request: CognitionPassRequest | None = None
    memory_budget: MemoryRetrievalBudget | None = None
    event_budget: EventRetrievalBudget | None = None
    cognitive_budget: CognitiveBudgetRuntime | None = None

    def app_kwargs(self) -> dict[str, Any]:
        """Arguments accepted by ``server.create_app`` without semantic rewriting."""

        return {
            "profiles": self.profiles,
            "cognition_mode": self.cognition_mode,
            "pass1_request": self.pass1_request,
            "pass2_request": self.pass2_request,
            "memory_budget": self.memory_budget,
            "event_budget": self.event_budget,
            "cognitive_budget": self.cognitive_budget,
        }


def assemble_runtime(
    resolved: ResolvedRuntimeConfig,
    *,
    token_counter_capabilities: Mapping[str, TokenCounterCapability] | None = None,
    vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
    lm_studio_reasoning_capability: LMStudioReasoningCapabilityAttestation | None = None,
) -> RuntimeAssembly:
    """Construct current owner objects from one validated runtime configuration.

    Assembly binds every public Cognitive Profile to one Cognitive Package root and
    one effective physical provider/model without reading semantic package content,
    performing generation, or mutating persistence.
    """

    if not isinstance(resolved, ResolvedRuntimeConfig):
        raise TypeError("resolved must be ResolvedRuntimeConfig")
    if vllm_reasoning_capability is not None and not isinstance(
        vllm_reasoning_capability, VLLMReasoningCapabilityAttestation
    ):
        raise TypeError(
            "vllm_reasoning_capability must be VLLMReasoningCapabilityAttestation or None"
        )
    if lm_studio_reasoning_capability is not None and not isinstance(
        lm_studio_reasoning_capability, LMStudioReasoningCapabilityAttestation
    ):
        raise TypeError(
            "lm_studio_reasoning_capability must be "
            "LMStudioReasoningCapabilityAttestation or None"
        )
    if vllm_reasoning_capability is not None and lm_studio_reasoning_capability is not None:
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.INVALID_COMBINATION,
            field="provider.backend",
            message="vLLM and LM Studio reasoning capabilities cannot be attached together",
        )

    config = resolved.config
    runtime = config.runtime
    cognition = runtime.cognition

    if cognition.mode in {
        CognitionExecutionMode.AUTO,
        CognitionExecutionMode.SHADOW_TWO_PASS,
    }:
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.INVALID_COMBINATION,
            field="runtime.cognition.mode",
            message=(
                f"{cognition.mode.value} is not an ordinary release serving mode; "
                "select two_pass or explicit single_pass"
            ),
        )

    if config.provider.backend is OpenAICompatibleBackendId.VLLM:
        if vllm_reasoning_capability is None:
            raise RuntimeAssemblyError(
                RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE,
                field="provider.backend",
                message=(
                    "vLLM backend requires an explicit configured-runtime reasoning "
                    "capability attestation"
                ),
            )
        if lm_studio_reasoning_capability is not None:
            raise RuntimeAssemblyError(
                RuntimeConfigErrorCode.INVALID_COMBINATION,
                field="provider.backend",
                message="LM Studio reasoning capability requires provider.backend=lm_studio",
            )
    elif config.provider.backend is OpenAICompatibleBackendId.LM_STUDIO:
        if vllm_reasoning_capability is not None:
            raise RuntimeAssemblyError(
                RuntimeConfigErrorCode.INVALID_COMBINATION,
                field="provider.backend",
                message="vLLM reasoning capability requires provider.backend=vllm",
            )
        for pass_name, pass_request in (
            ("pass1", cognition.pass1),
            ("pass2", cognition.pass2),
        ):
            if pass_request.reasoning_budget is not None:
                raise RuntimeAssemblyError(
                    RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE,
                    field=f"runtime.cognition.{pass_name}.reasoning_budget",
                    message=(
                        "LM Studio Chat Completions reasoning-token budget is not "
                        "attested by the current provider contract"
                    ),
                )
            if pass_request.reasoning_mode is not None:
                if lm_studio_reasoning_capability is None:
                    raise RuntimeAssemblyError(
                        RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE,
                        field=f"runtime.cognition.{pass_name}.reasoning_mode",
                        message=(
                            "LM Studio explicit reasoning requires a configured-runtime "
                            "reasoning capability attestation"
                        ),
                    )
                if pass_request.reasoning_mode is not CognitionReasoningMode.OFF:
                    raise RuntimeAssemblyError(
                        RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE,
                        field=f"runtime.cognition.{pass_name}.reasoning_mode",
                        message=(
                            "current LM Studio release carriage qualifies only "
                            "provider-neutral reasoning_mode=off"
                        ),
                    )
                if "off" not in lm_studio_reasoning_capability.allowed_options:
                    raise RuntimeAssemblyError(
                        RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE,
                        field=f"runtime.cognition.{pass_name}.reasoning_mode",
                        message=(
                            "loaded LM Studio model does not attest reasoning option off"
                        ),
                    )
    elif config.provider.backend is OpenAICompatibleBackendId.GENERIC:
        if vllm_reasoning_capability is not None or lm_studio_reasoning_capability is not None:
            raise RuntimeAssemblyError(
                RuntimeConfigErrorCode.INVALID_COMBINATION,
                field="provider.backend",
                message="backend-specific reasoning capability requires its matching backend",
            )
    else:
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE,
            field="provider.backend",
            message=(
                "configured OpenAI-compatible backend dialect is not yet available "
                "in runtime assembly"
            ),
        )

    provider_decoding_capabilities = decoding_capabilities_for_backend(
        config.provider.backend
    )

    if runtime.cognitive_budget is not None and (
        runtime.memory_retrieval is not None or runtime.event_retrieval is not None
    ):
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.INVALID_COMBINATION,
            field="runtime.cognitive_budget",
            message=(
                "direct retrieval budgets cannot overlap Cognitive Budget; "
                "Cognitive Budget already assigns retrieval envelopes"
            ),
        )

    if runtime.cognitive_budget is not None:
        for index, profile in enumerate(config.profiles):
            if profile.provider.model is not None:
                raise RuntimeAssemblyError(
                    RuntimeConfigErrorCode.INVALID_COMBINATION,
                    field=f"profiles[{index}].provider.model",
                    message=(
                        "profile-specific physical models cannot share one configured "
                        "Cognitive Budget token-counter capability"
                    ),
                )

    memory_budget = None
    if runtime.memory_retrieval is not None:
        memory_budget = MemoryRetrievalBudget(
            max_chunks=runtime.memory_retrieval.max_chunks,
            max_chars=runtime.memory_retrieval.max_chars,
        )

    event_budget = None
    if runtime.event_retrieval is not None:
        event_budget = EventRetrievalBudget(
            max_events=runtime.event_retrieval.max_events,
            max_chars=runtime.event_retrieval.max_chars,
        )

    cognitive_budget = _assemble_cognitive_budget(
        config.provider,
        runtime.cognitive_budget,
        token_counter_capabilities or {},
        cognition_mode=cognition.mode,
        pass1_request=cognition.pass1,
        pass2_request=cognition.pass2,
        provider_supports_output_limit=(
            "max_output_tokens"
            in provider_decoding_capabilities.supported_controls
        ),
    )

    provider_type = (
        OpenAICompatibleTwoPassProvider
        if cognition.mode is CognitionExecutionMode.TWO_PASS
        else OpenAICompatibleProvider
    )
    profile_runtimes: list[CognitiveProfileRuntime] = []
    for index, profile in enumerate(config.profiles):
        physical_model = profile.provider.model or config.provider.model
        try:
            provider = provider_type(
                base_url=config.provider.base_url,
                model=physical_model,
                api_key=resolved.secrets.provider_api_key,
                decoding_capabilities=provider_decoding_capabilities,
                vllm_reasoning_capability=vllm_reasoning_capability,
                lm_studio_reasoning_capability=lm_studio_reasoning_capability,
            )
        except (TypeError, ValueError) as exc:
            raise RuntimeAssemblyError(
                RuntimeConfigErrorCode.PROVIDER_INVALID,
                field=f"profiles[{index}].provider",
                message="configured profile provider could not be constructed",
            ) from exc

        continuity_runtime = None
        if runtime.continuity is not None:
            continuity_runtime = ContinuityRuntime(
                context=ContinuityContext(max_items=runtime.continuity.max_items),
                lifetime_revisions=runtime.continuity.lifetime_revisions,
            )

        profile_runtimes.append(
            CognitiveProfileRuntime(
                name=profile.name,
                package=CognitivePackageDirectory(profile.root),
                provider=provider,
                physical_model=physical_model,
                continuity_runtime=continuity_runtime,
                cognition_execution_runtime=(
                    CognitionExecutionRuntime()
                    if cognition.mode is CognitionExecutionMode.TWO_PASS
                    else None
                ),
            )
        )

    return RuntimeAssembly(
        profiles=CognitiveProfileRegistry(tuple(profile_runtimes)),
        cognition_mode=cognition.mode,
        pass1_request=(
            cognition.pass1 if cognition.mode is CognitionExecutionMode.TWO_PASS else None
        ),
        pass2_request=(
            cognition.pass2 if cognition.mode is CognitionExecutionMode.TWO_PASS else None
        ),
        memory_budget=memory_budget,
        event_budget=event_budget,
        cognitive_budget=cognitive_budget,
    )


def _assemble_cognitive_budget(
    provider_config: ProviderRuntimeConfig,
    explicit_config: object,
    capabilities: Mapping[str, TokenCounterCapability],
    *,
    cognition_mode: CognitionExecutionMode,
    pass1_request: CognitionPassRequest,
    pass2_request: CognitionPassRequest,
    provider_supports_output_limit: bool,
) -> CognitiveBudgetRuntime | None:
    if explicit_config is None:
        return None

    from relaylm.runtime_config import ExplicitCognitiveBudgetConfig

    if not isinstance(explicit_config, ExplicitCognitiveBudgetConfig):
        raise TypeError("cognitive budget must be ExplicitCognitiveBudgetConfig")

    declared = explicit_config.token_counter
    capability = capabilities.get(declared.capability)
    if capability is None:
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE,
            field="runtime.cognitive_budget.token_counter.capability",
            message="configured serialized-input counter capability is unavailable",
        )
    if capability.mode is not declared.mode:
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE,
            field="runtime.cognitive_budget.token_counter.mode",
            message="configured token-count mode does not match registered capability",
        )

    try:
        counter = capability.factory(provider_config)
    except Exception as exc:
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE,
            field="runtime.cognitive_budget.token_counter.capability",
            message="configured serialized-input counter capability could not be constructed",
        ) from exc

    if cognition_mode is CognitionExecutionMode.TWO_PASS:
        _require_budgeted_pass_output_limit(
            pass_name="pass1",
            request=pass1_request,
            reserved_output_tokens=explicit_config.total.reserved_output_tokens,
            provider_supports_output_limit=provider_supports_output_limit,
        )
        _require_budgeted_pass_output_limit(
            pass_name="pass2",
            request=pass2_request,
            reserved_output_tokens=explicit_config.total.reserved_output_tokens,
            provider_supports_output_limit=provider_supports_output_limit,
        )
        if not isinstance(counter, TwoPassSerializedInputTokenCounter):
            raise RuntimeAssemblyError(
                RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE,
                field="runtime.cognitive_budget.token_counter.capability",
                message=(
                    "two-pass cognition requires a two-pass serialized-input counter capability"
                ),
            )
        return TwoPassCognitiveBudgetRuntimeConfig(
            pass1_total=explicit_config.total,
            pass2_total=explicit_config.total,
            policy=explicit_config.policy,
            token_counter=counter,
        )

    if not isinstance(counter, SerializedCognitiveInputTokenCounter):
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE,
            field="runtime.cognitive_budget.token_counter.capability",
            message="registered token-counter factory returned an incompatible implementation",
        )
    return CognitiveBudgetRuntimeConfig(
        total=explicit_config.total,
        policy=explicit_config.policy,
        token_counter=counter,
    )


def _require_budgeted_pass_output_limit(
    *,
    pass_name: str,
    request: CognitionPassRequest,
    reserved_output_tokens: int,
    provider_supports_output_limit: bool,
) -> None:
    limit = request.max_output_tokens
    field = f"runtime.cognition.{pass_name}.max_output_tokens"
    if limit is None:
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.INVALID_COMBINATION,
            field=field,
            message=(
                "budgeted two-pass cognition requires an explicit provider hard output limit"
            ),
        )
    if not provider_supports_output_limit:
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE,
            field=field,
            message="configured provider backend cannot attest hard output-limit carriage",
        )
    if limit > reserved_output_tokens:
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.INVALID_COMBINATION,
            field=field,
            message=(
                "max_output_tokens must not exceed cognitive_budget.total.reserved_output_tokens"
            ),
        )
