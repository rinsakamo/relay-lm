from __future__ import annotations

from pathlib import Path

import pytest

from relaylm.providers.openai_compatible_backend import OpenAICompatibleBackendId
from relaylm.runtime_assembly import RuntimeAssemblyError, assemble_runtime
from relaylm.runtime_config import ConfigSource, ProviderRuntimeConfig, RuntimeConfigErrorCode
from relaylm.runtime_config_loader import (
    RuntimeConfigOverrides,
    RuntimeConfigResolutionError,
    resolve_runtime_config,
)


def _write_config(path: Path, *, backend: str | None = None) -> Path:
    backend_line = "" if backend is None else f"  backend: {backend}\n"
    path.write_text(
        """\
format_version: 1
character:
  directory: /characters/relm
provider:
  adapter: openai_compatible
"""
        + backend_line
        + """\
  base_url: http://127.0.0.1:8000/v1
  model: model-id
""",
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
            "RELAYLM_CHARACTER_DIR": "/characters/relm",
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
