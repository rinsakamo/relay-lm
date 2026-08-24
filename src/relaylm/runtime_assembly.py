from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from relaylm.budget_enforcement import (
    SerializedCognitiveInputTokenCounter,
    TokenCountMode,
)
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitionExecutionMode
from relaylm.cognition_execution import CognitionPassRequest
from relaylm.continuity import ContinuityContext
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_backend import OpenAICompatibleBackendId
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningCapabilityAttestation,
)
from relaylm.runtime_config import (
    ProviderRuntimeConfig,
    RuntimeConfigErrorCode,
)
from relaylm.runtime_config_loader import ResolvedRuntimeConfig
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import (
    ContinuityRuntime,
    EventRetrievalBudget,
    MemoryRetrievalBudget,
)
from relaylm.two_pass_turn import CognitionExecutionRuntime


TokenCounterFactory = Callable[
    [ProviderRuntimeConfig],
    SerializedCognitiveInputTokenCounter,
]


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
    """Registered provider/model counter capability available to release assembly.

    ``mode`` is capability metadata used to prove agreement with the explicit
    configuration before any semantic content is counted. ``factory`` receives
    only non-secret provider configuration and must return an implementation of
    the existing #1387 serialized-input counter protocol.
    """

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

    character: CharacterDirectory
    provider: OpenAICompatibleProvider = field(repr=False)
    cognition_mode: CognitionExecutionMode = CognitionExecutionMode.TWO_PASS
    cognition_execution_runtime: CognitionExecutionRuntime | None = field(
        default=None,
        repr=False,
    )
    pass1_request: CognitionPassRequest | None = None
    pass2_request: CognitionPassRequest | None = None
    memory_budget: MemoryRetrievalBudget | None = None
    event_budget: EventRetrievalBudget | None = None
    continuity_runtime: ContinuityRuntime | None = None
    cognitive_budget: CognitiveBudgetRuntimeConfig | None = None

    def app_kwargs(self) -> dict[str, Any]:
        """Arguments accepted by ``server.create_app`` without semantic rewriting."""

        return {
            "character": self.character,
            "provider": self.provider,
            "cognition_mode": self.cognition_mode,
            "cognition_execution_runtime": self.cognition_execution_runtime,
            "pass1_request": self.pass1_request,
            "pass2_request": self.pass2_request,
            "memory_budget": self.memory_budget,
            "event_budget": self.event_budget,
            "continuity_runtime": self.continuity_runtime,
            "cognitive_budget": self.cognitive_budget,
        }


def assemble_runtime(
    resolved: ResolvedRuntimeConfig,
    *,
    token_counter_capabilities: Mapping[str, TokenCounterCapability] | None = None,
    vllm_reasoning_capability: VLLMReasoningCapabilityAttestation | None = None,
) -> RuntimeAssembly:
    """Construct current owner objects from one validated RCFG2 result.

    This function performs no Character semantic reads, network calls, provider
    generation, profile selection, or persistence mutation.
    """

    if not isinstance(resolved, ResolvedRuntimeConfig):
        raise TypeError("resolved must be ResolvedRuntimeConfig")
    if vllm_reasoning_capability is not None and not isinstance(
        vllm_reasoning_capability, VLLMReasoningCapabilityAttestation
    ):
        raise TypeError(
            "vllm_reasoning_capability must be VLLMReasoningCapabilityAttestation or None"
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

    if (
        cognition.mode is CognitionExecutionMode.TWO_PASS
        and runtime.cognitive_budget is not None
    ):
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.INVALID_COMBINATION,
            field="runtime.cognitive_budget",
            message=(
                "the existing Cognitive Budget is single-pass authority and cannot "
                "be guessed into two-pass per-pass totals before #1388 calibration"
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
    elif vllm_reasoning_capability is not None:
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.INVALID_COMBINATION,
            field="provider.backend",
            message="vLLM reasoning capability requires provider.backend=vllm",
        )
    elif config.provider.backend is not OpenAICompatibleBackendId.GENERIC:
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE,
            field="provider.backend",
            message=(
                "configured OpenAI-compatible backend dialect is not yet available "
                "in runtime assembly"
            ),
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

    continuity_runtime = None
    if runtime.continuity is not None:
        continuity_runtime = ContinuityRuntime(
            context=ContinuityContext(max_items=runtime.continuity.max_items),
            lifetime_revisions=runtime.continuity.lifetime_revisions,
        )

    cognitive_budget = _assemble_cognitive_budget(
        config.provider,
        runtime.cognitive_budget,
        token_counter_capabilities or {},
    )

    provider_type = (
        OpenAICompatibleTwoPassProvider
        if cognition.mode is CognitionExecutionMode.TWO_PASS
        else OpenAICompatibleProvider
    )
    try:
        provider = provider_type(
            base_url=config.provider.base_url,
            model=config.provider.model,
            api_key=resolved.secrets.provider_api_key,
            vllm_reasoning_capability=vllm_reasoning_capability,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeAssemblyError(
            RuntimeConfigErrorCode.PROVIDER_INVALID,
            field="provider",
            message="configured provider could not be constructed",
        ) from exc

    character = CharacterDirectory(config.character.directory)
    cognition_execution_runtime = (
        CognitionExecutionRuntime()
        if cognition.mode is CognitionExecutionMode.TWO_PASS
        else None
    )

    return RuntimeAssembly(
        character=character,
        provider=provider,
        cognition_mode=cognition.mode,
        cognition_execution_runtime=cognition_execution_runtime,
        pass1_request=(
            cognition.pass1 if cognition.mode is CognitionExecutionMode.TWO_PASS else None
        ),
        pass2_request=(
            cognition.pass2 if cognition.mode is CognitionExecutionMode.TWO_PASS else None
        ),
        memory_budget=memory_budget,
        event_budget=event_budget,
        continuity_runtime=continuity_runtime,
        cognitive_budget=cognitive_budget,
    )


def _assemble_cognitive_budget(
    provider_config: ProviderRuntimeConfig,
    explicit_config: object,
    capabilities: Mapping[str, TokenCounterCapability],
) -> CognitiveBudgetRuntimeConfig | None:
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
