from __future__ import annotations

import pytest

from relaylm.budget import (
    BudgetDegradationPolicy,
    BudgetPlan,
    CountCharacterEnvelope,
    CountEnvelope,
    TotalBudgetConfig,
)
from relaylm.budget_enforcement import TokenCountMode
from relaylm.runtime_config import (
    CONFIG_PRECEDENCE,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    RUNTIME_CONFIG_FORMAT_VERSION,
    RUNTIME_CONFIG_PATH_ENV,
    UNKNOWN_FIELD_POLICY,
    CognitiveProfileConfig,
    ConfigSource,
    ContinuityRuntimeSettings,
    EffectiveConfigSecret,
    EventRetrievalRuntimeConfig,
    ExplicitCognitiveBudgetConfig,
    MemoryRetrievalRuntimeConfig,
    ProviderRuntimeConfig,
    RuntimeConfig,
    RuntimeConfigErrorCode,
    RuntimePolicyConfig,
    RuntimeSecretInputs,
    SecretEnvReference,
    ServerRuntimeConfig,
    TokenCounterCapabilityConfig,
)
from relaylm.runtime_config_loader import (
    RuntimeConfigOverrides,
    RuntimeConfigResolutionError,
    resolve_runtime_config,
)


def _empty_policy() -> BudgetDegradationPolicy:
    return BudgetDegradationPolicy(
        initial_plan=BudgetPlan(
            canonical_state=CountEnvelope(max_items=0, floor_items=0),
            working_context=CountCharacterEnvelope(
                max_items=0,
                floor_items=0,
                max_chars=0,
                floor_chars=0,
            ),
            retrieved_memory=CountCharacterEnvelope(
                max_items=0,
                floor_items=0,
                max_chars=0,
                floor_chars=0,
            ),
            event_evidence=CountCharacterEnvelope(
                max_items=0,
                floor_items=0,
                max_chars=0,
                floor_chars=0,
            ),
        ),
        steps=(),
    )


def test_runtime_configuration_version_and_discovery_are_explicit() -> None:
    assert RUNTIME_CONFIG_FORMAT_VERSION == 1
    assert RUNTIME_CONFIG_PATH_ENV == "RELAYLM_CONFIG"
    assert UNKNOWN_FIELD_POLICY == "error"


def test_runtime_configuration_precedence_is_leaf_level_and_deterministic() -> None:
    assert CONFIG_PRECEDENCE == (
        ConfigSource.CLI,
        ConfigSource.ENV,
        ConfigSource.CONFIG_FILE,
        ConfigSource.CANONICAL_DEFAULT,
    )


def test_runtime_config_rejects_coerced_or_unsupported_format_version() -> None:
    kwargs = {
        "profiles": (
            CognitiveProfileConfig(name="relm", root="/characters/relm"),
        ),
        "provider": ProviderRuntimeConfig(
            adapter="openai_compatible",
            base_url="http://127.0.0.1:1234/v1",
            model="example-model",
        ),
    }
    with pytest.raises(TypeError, match="format_version must be integer 1"):
        RuntimeConfig(format_version=True, **kwargs)
    with pytest.raises(ValueError, match="unsupported runtime format_version: 2"):
        RuntimeConfig(format_version=2, **kwargs)


def test_current_release_server_defaults_preserve_loopback_exposure() -> None:
    server = ServerRuntimeConfig()

    assert DEFAULT_SERVER_HOST == "127.0.0.1"
    assert DEFAULT_SERVER_PORT == 8090
    assert server.host == DEFAULT_SERVER_HOST
    assert server.port == DEFAULT_SERVER_PORT


def test_provider_config_accepts_only_current_adapter_and_secret_reference() -> None:
    provider = ProviderRuntimeConfig(
        adapter="openai_compatible",
        base_url="http://127.0.0.1:1234/v1",
        model="example-model",
        api_key=SecretEnvReference(env="OPENAI_API_KEY"),
    )

    assert provider.api_key == SecretEnvReference(env="OPENAI_API_KEY")
    with pytest.raises(ValueError, match="unsupported provider adapter"):
        ProviderRuntimeConfig(
            adapter="invented_adapter",
            base_url="http://127.0.0.1:1234/v1",
            model="example-model",
        )
    with pytest.raises(ValueError, match="environment variable name"):
        SecretEnvReference(env="not valid")


def test_provider_config_rejects_credentials_embedded_in_base_url() -> None:
    credential = "provider-password"

    with pytest.raises(ValueError, match="base_url must not contain credentials") as caught:
        ProviderRuntimeConfig(
            adapter="openai_compatible",
            base_url=f"https://user:{credential}@provider.example/v1",
            model="example-model",
        )

    assert credential not in str(caught.value)


def test_runtime_resolution_types_provider_base_url_credential_failure() -> None:
    credential = "provider-password"

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(
            environ={
                "RELAYLM_PROFILE_NAME": "relm",
                "RELAYLM_PROFILE_ROOT": "/characters/relm",
                "RELAYLM_PROVIDER_BASE_URL": (
                    f"https://user:{credential}@provider.example/v1"
                ),
                "RELAYLM_PROVIDER_MODEL": "example-model",
            }
        )

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_VALUE
    assert caught.value.field == "provider.base_url"
    assert credential not in str(caught.value)


def test_selected_file_rejects_provider_base_url_credentials_before_override(
    tmp_path,
) -> None:
    credential = "file-provider-password"
    config_path = tmp_path / "runtime.yaml"
    config_path.write_text(
        "\n".join(
            [
                "format_version: 1",
                "profiles:",
                "  - name: relm",
                "    root: /config/character",
                "provider:",
                "  adapter: openai_compatible",
                f"  base_url: https://user:{credential}@provider.example/v1",
                "  model: config-model",
                "",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(
            config_path=config_path,
            overrides=RuntimeConfigOverrides(
                provider_base_url="https://clean.example/v1",
            ),
            environ={},
        )

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_VALUE
    assert caught.value.field == "provider.base_url"
    assert credential not in str(caught.value)


def test_runtime_policy_has_no_uncalibrated_profile_or_cognitive_defaults() -> None:
    policy = RuntimePolicyConfig()

    assert policy.calibration_profile is None
    assert policy.memory_retrieval is None
    assert policy.event_retrieval is None
    assert policy.continuity is None
    assert policy.cognitive_budget is None


def test_existing_runtime_controls_remain_explicit_inputs() -> None:
    policy = RuntimePolicyConfig(
        memory_retrieval=MemoryRetrievalRuntimeConfig(max_chunks=3, max_chars=900),
        event_retrieval=EventRetrievalRuntimeConfig(max_events=4, max_chars=1200),
        continuity=ContinuityRuntimeSettings(max_items=5, lifetime_revisions=6),
    )

    assert policy.memory_retrieval.max_chunks == 3
    assert policy.event_retrieval.max_events == 4
    assert policy.continuity.max_items == 5
    assert policy.continuity.lifetime_revisions == 6


def test_explicit_cognitive_budget_carries_owner_types_and_counter_mode() -> None:
    configured = ExplicitCognitiveBudgetConfig(
        total=TotalBudgetConfig(
            model_context_window=8192,
            reserved_output_tokens=1024,
        ),
        policy=_empty_policy(),
        token_counter=TokenCounterCapabilityConfig(
            capability="example.counter",
            mode=TokenCountMode.EXACT,
        ),
    )

    assert configured.total.model_context_window == 8192
    assert configured.policy.steps == ()
    assert configured.token_counter.mode is TokenCountMode.EXACT


def test_secret_material_is_process_local_and_redacted_from_repr() -> None:
    inputs = RuntimeSecretInputs(provider_api_key="api-key-value")
    secret = EffectiveConfigSecret(
        configured=True,
        source=ConfigSource.ENV,
        material_source=ConfigSource.ENV,
    )

    assert inputs.provider_api_key == "api-key-value"
    assert "api-key-value" not in repr(inputs)
    assert secret.configured is True
    assert secret.source is ConfigSource.ENV
    assert secret.material_source is ConfigSource.ENV
    assert not hasattr(secret, "value")
    assert "api-key-value" not in repr(secret)


def test_error_taxonomy_contains_preflight_without_semantic_error_categories() -> None:
    assert {code.value for code in RuntimeConfigErrorCode} == {
        "discovery_error",
        "read_error",
        "parse_error",
        "unsupported_format_version",
        "unknown_field",
        "invalid_type",
        "invalid_value",
        "missing_required",
        "invalid_combination",
        "secret_unavailable",
        "capability_unavailable",
        "character_invalid",
        "provider_invalid",
    }
