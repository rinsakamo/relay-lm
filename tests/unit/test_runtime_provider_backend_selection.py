from __future__ import annotations

from pathlib import Path

import pytest

from relaylm.actual_model_targets import load_actual_model_repository_snapshot_target
from relaylm.providers.openai_compatible_backend import OpenAICompatibleBackendId
from relaylm.providers.llama_cpp_openai import LlamaCppOpenAICompatibleTwoPassProvider
from relaylm.providers.llama_cpp_backend import LlamaCppTwoPassSerializedInputCounter
from relaylm.budget_runtime import TwoPassCognitiveBudgetRuntimeConfig
from relaylm.providers.vllm_backend import attest_vllm_backend
from relaylm.providers.vllm_reasoning import VLLMReasoningWireControls
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningProbeEvidence,
    attest_vllm_reasoning_capabilities,
)
from relaylm.runtime_assembly import RuntimeAssemblyError, assemble_runtime
from relaylm.runtime_config import ConfigSource, ProviderRuntimeConfig, RuntimeConfigErrorCode
from relaylm.runtime_config_loader import (
    RuntimeConfigOverrides,
    RuntimeConfigResolutionError,
    resolve_runtime_config,
)


def _write_config(
    path: Path,
    *,
    backend: str | None = None,
    llama_capability: bool = False,
    model: str = "model-id",
) -> Path:
    backend_line = "" if backend is None else f"  backend: {backend}\n"
    capability_block = (
        """
  llama_cpp:
    upstream_revision: e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d
    build_info: llama.cpp-10874
    model_alias: model-id
    model_path: /models/model-id.gguf
    model_ftype: Q4_K_M
    artifact_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    chat_template_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    context_limit: 8192
    total_slots: 1
    context_shift_enabled: false
    reasoning_effort_none_supported: true
    native_structured_output_supported: true
    streaming_supported: true
    decoding_controls: [max_output_tokens, temperature, top_p]
    cache_policy: disabled
"""
        if llama_capability
        else ""
    )
    path.write_text(
        """\
format_version: 1
profiles:
  - name: relm
    root: /characters/relm
provider:
  adapter: openai_compatible
"""
        + backend_line
        + f"""\
  base_url: http://127.0.0.1:8000/v1
  model: {model}
"""
        + capability_block,
        encoding="utf-8",
    )
    return path


def test_provider_runtime_config_keeps_adapter_and_backend_as_distinct_identity() -> None:
    generic = ProviderRuntimeConfig(
        adapter="openai_compatible",
        base_url="http://127.0.0.1:8000/v1",
        model="model-id",
    )
    vllm = ProviderRuntimeConfig(
        adapter="openai_compatible",
        backend=OpenAICompatibleBackendId.VLLM,
        base_url="http://127.0.0.1:8000/v1",
        model="model-id",
    )

    assert generic.adapter == "openai_compatible"
    assert generic.backend is OpenAICompatibleBackendId.GENERIC
    assert vllm.adapter == "openai_compatible"
    assert vllm.backend is OpenAICompatibleBackendId.VLLM


def test_backend_input_is_canonicalized_and_diagnostics_store_machine_id(
    tmp_path: Path,
) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(tmp_path / "runtime.yaml", backend="vLLM"),
        environ={},
    )

    assert resolved.config.provider.backend is OpenAICompatibleBackendId.VLLM
    assert resolved.source_for("provider.backend") is ConfigSource.CONFIG_FILE
    assert resolved.effective_diagnostics()["values"]["provider.backend"] == {
        "value": "vllm",
        "source": "config_file",
    }


def test_backend_selection_uses_leaf_precedence_before_canonicalization(
    tmp_path: Path,
) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(tmp_path / "runtime.yaml", backend="LM Studio"),
        overrides=RuntimeConfigOverrides(provider_backend="VLLM"),
        environ={"RELAYLM_PROVIDER_BACKEND": "generic"},
    )

    assert resolved.config.provider.backend is OpenAICompatibleBackendId.VLLM
    assert resolved.source_for("provider.backend") is ConfigSource.CLI


def test_missing_backend_preserves_existing_generic_openai_compatible_path() -> None:
    resolved = resolve_runtime_config(
        environ={
            "RELAYLM_PROFILE_NAME": "relm",
            "RELAYLM_PROFILE_ROOT": "/characters/relm",
            "RELAYLM_PROVIDER_BASE_URL": "http://127.0.0.1:1234/v1",
            "RELAYLM_PROVIDER_MODEL": "model-id",
        }
    )

    assert resolved.config.provider.backend is OpenAICompatibleBackendId.GENERIC
    assert resolved.source_for("provider.backend") is ConfigSource.CANONICAL_DEFAULT


def test_unknown_backend_fails_closed_without_fuzzy_matching(tmp_path: Path) -> None:
    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(
            config_path=_write_config(tmp_path / "runtime.yaml", backend="lmstudio"),
            environ={},
        )

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_VALUE
    assert caught.value.field == "provider.backend"


def test_llama_cpp_backend_is_selectable_from_file_env_and_cli_precedence(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        backend="llama.cpp",
        llama_capability=True,
    )
    resolved = resolve_runtime_config(
        config_path=config_path,
        overrides=RuntimeConfigOverrides(provider_backend="llama-cpp"),
        environ={"RELAYLM_PROVIDER_BACKEND": "generic"},
    )

    assert resolved.config.provider.backend is OpenAICompatibleBackendId.LLAMA_CPP
    assert resolved.config.provider.llama_cpp is not None
    assert resolved.source_for("provider.backend") is ConfigSource.CLI

    env_resolved = resolve_runtime_config(
        environ={
            "RELAYLM_PROFILE_NAME": "relm",
            "RELAYLM_PROFILE_ROOT": "/characters/relm",
            "RELAYLM_PROVIDER_BASE_URL": "http://127.0.0.1:1234/v1",
            "RELAYLM_PROVIDER_MODEL": "model-id",
            "RELAYLM_PROVIDER_BACKEND": "llama_cpp",
        }
    )
    assert env_resolved.config.provider.backend is OpenAICompatibleBackendId.LLAMA_CPP


def test_llama_cpp_assembly_selects_dedicated_provider_and_diagnostics(
    tmp_path: Path,
) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(
            tmp_path / "runtime.yaml",
            backend="llama_cpp",
            llama_capability=True,
        ),
        environ={},
    )

    assembly = assemble_runtime(resolved)
    profile = assembly.profiles.resolve("relm")
    assert profile is not None
    assert isinstance(profile.provider, LlamaCppOpenAICompatibleTwoPassProvider)
    assert profile.provider.llama_cpp_capability is not None
    assert assembly.provider_diagnostics["backend"] == "llama_cpp"
    assert assembly.provider_diagnostics["cache_policy"] == "disabled"
    assert assembly.provider_diagnostics["token_counter"]["mode"] == "exact"
    assert "model_path" in assembly.provider_diagnostics["runtime_identity"]

    import asyncio

    asyncio.run(profile.provider.aclose())


def test_llama_cpp_backend_requires_explicit_capability_attestation(
    tmp_path: Path,
) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(tmp_path / "runtime.yaml", backend="llama_cpp"),
        environ={},
    )

    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(resolved)

    assert caught.value.code is RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE
    assert caught.value.field == "provider.llama_cpp"


def test_llama_cpp_capability_model_mismatch_fails_closed(tmp_path: Path) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(
            tmp_path / "runtime.yaml",
            backend="llama_cpp",
            llama_capability=True,
            model="other-model",
        ),
        environ={},
    )

    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(resolved)

    assert caught.value.code is RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE
    assert caught.value.field == "provider.model"


def test_llama_cpp_registers_exact_two_pass_counter_for_cognitive_budget(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        backend="llama_cpp",
        llama_capability=True,
    )
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + """
runtime:
  cognition:
    mode: two_pass
    pass1:
      max_output_tokens: 128
    pass2:
      max_output_tokens: 128
      structured_output_mode: native
  cognitive_budget:
    total:
      model_context_window: 8192
      reserved_output_tokens: 128
    policy:
      initial_plan:
        canonical_state: {max_items: 8, floor_items: 2}
        working_context: {max_items: 4, floor_items: 1, max_chars: 2000, floor_chars: 500}
        retrieved_memory: {max_items: 4, floor_items: 0, max_chars: 1600, floor_chars: 0}
        event_evidence: {max_items: 4, floor_items: 0, max_chars: 1600, floor_chars: 0}
      steps: []
    token_counter:
      capability: llama_cpp.chat-input.serialized-input.v1
      mode: exact
""",
        encoding="utf-8",
    )

    resolved = resolve_runtime_config(config_path=config_path, environ={})
    assembly = assemble_runtime(resolved)

    assert isinstance(assembly.cognitive_budget, TwoPassCognitiveBudgetRuntimeConfig)
    assert isinstance(
        assembly.cognitive_budget.token_counter,
        LlamaCppTwoPassSerializedInputCounter,
    )
    assert assembly.cognitive_budget.token_counter.capability.counter_capability == (
        "llama_cpp.chat-input.serialized-input.v1"
    )


def test_llama_cpp_budget_rejects_output_limit_above_reserved_capacity(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        backend="llama_cpp",
        llama_capability=True,
    )
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + """
runtime:
  cognition:
    mode: two_pass
    pass1: {max_output_tokens: 128}
    pass2: {max_output_tokens: 128}
  cognitive_budget:
    total:
      model_context_window: 8192
      reserved_output_tokens: 64
    policy:
      initial_plan:
        canonical_state: {max_items: 8, floor_items: 2}
        working_context: {max_items: 4, floor_items: 1, max_chars: 2000, floor_chars: 500}
        retrieved_memory: {max_items: 4, floor_items: 0, max_chars: 1600, floor_chars: 0}
        event_evidence: {max_items: 4, floor_items: 0, max_chars: 1600, floor_chars: 0}
      steps: []
    token_counter:
      capability: llama_cpp.chat-input.serialized-input.v1
      mode: exact
""",
        encoding="utf-8",
    )

    resolved = resolve_runtime_config(config_path=config_path, environ={})
    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(resolved)

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_COMBINATION
    assert caught.value.field == "runtime.cognition.pass1.max_output_tokens"


def test_llama_cpp_single_pass_fails_closed_without_generic_fallback(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        backend="llama_cpp",
        llama_capability=True,
    )
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + "\nruntime:\n  cognition:\n    mode: single_pass\n",
        encoding="utf-8",
    )
    resolved = resolve_runtime_config(config_path=config_path, environ={})

    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(resolved)

    assert caught.value.code is RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE
    assert caught.value.field == "runtime.cognition.mode"


def test_selected_backend_without_runtime_realizer_fails_before_generation(
    tmp_path: Path,
) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(tmp_path / "runtime.yaml", backend="vllm"),
        environ={},
    )

    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(resolved)

    assert caught.value.code is RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE
    assert caught.value.field == "provider.backend"


def test_vllm_backend_requires_and_consumes_explicit_attested_realizer(
    tmp_path: Path,
) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(tmp_path / "runtime.yaml", backend="vllm"),
        environ={},
    )
    target = load_actual_model_repository_snapshot_target(
        Path(__file__).resolve().parents[2]
        / "evaluation/actual_model/targets/gemma-4-12b-it-qat-w4a16-vllm-v1.json"
    )
    backend = attest_vllm_backend(
        request_model="model-id",
        version_response={"version": "0.27.1"},
        models_response={
            "object": "list",
            "data": [{"id": "model-id", "object": "model"}],
        },
    )

    def probe(controls, *, activation=False, template=()):
        return VLLMReasoningProbeEvidence(
            wire_controls=controls,
            http_status=200,
            accepted=True,
            effect_proven=True,
            repeatable=True,
            activation_applied=activation,
            template_kwargs=template,
        )

    capability = attest_vllm_reasoning_capabilities(
        backend_attestation=backend,
        target=target,
        reasoning_parser="gemma4",
        template_thinking_control="enable_thinking",
        off_probe=probe(VLLMReasoningWireControls(reasoning_effort="none")),
        bounded_probe=probe(
            VLLMReasoningWireControls(thinking_token_budget=64),
            activation=True,
            template=(("enable_thinking", True),),
        ),
    )

    assembly = assemble_runtime(
        resolved,
        vllm_reasoning_capability=capability,
    )
    profile = assembly.profiles.resolve("relm")
    assert profile is not None
    try:
        assert profile.provider.vllm_reasoning_capability is capability
    finally:
        import asyncio

        asyncio.run(profile.provider.aclose())
