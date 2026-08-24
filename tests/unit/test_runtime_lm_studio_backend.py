from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from relaylm.cognitive import CognitionExecutionMode
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.runtime_assembly import RuntimeAssemblyError, assemble_runtime
from relaylm.runtime_config import RuntimeConfigErrorCode
from relaylm.runtime_config_loader import resolve_runtime_config


def _write_config(
    path: Path,
    *,
    mode: str | None = None,
    pass1_reasoning_mode: str | None = None,
) -> Path:
    cognition_lines: list[str] = []
    if mode is not None:
        cognition_lines.extend(["  cognition:", f"    mode: {mode}"])
    if pass1_reasoning_mode is not None:
        if not cognition_lines:
            cognition_lines.extend(["  cognition:", "    mode: two_pass"])
        cognition_lines.extend(
            [
                "    pass1:",
                f'      reasoning_mode: "{pass1_reasoning_mode}"',
            ]
        )
    runtime = ""
    if cognition_lines:
        runtime = "runtime:\n" + "\n".join(cognition_lines) + "\n"
    path.write_text(
        """\
format_version: 1
character:
  directory: /characters/relm
provider:
  adapter: openai_compatible
  backend: lm_studio
  base_url: http://127.0.0.1:1234/v1
  model: model-id
"""
        + runtime,
        encoding="utf-8",
    )
    return path


def test_lm_studio_default_two_pass_assembles_without_backend_specific_reasoning_wire(
    tmp_path: Path,
) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(tmp_path / "runtime.yaml"),
        environ={},
    )

    assembly = assemble_runtime(resolved)
    try:
        assert assembly.cognition_mode is CognitionExecutionMode.TWO_PASS
        assert isinstance(assembly.provider, OpenAICompatibleTwoPassProvider)
        assert resolved.config.provider.backend.value == "lm_studio"
    finally:
        asyncio.run(assembly.provider.aclose())


def test_lm_studio_explicit_single_pass_assembles_without_backend_specific_reasoning_wire(
    tmp_path: Path,
) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(tmp_path / "runtime.yaml", mode="single_pass"),
        environ={},
    )

    assembly = assemble_runtime(resolved)
    try:
        assert assembly.cognition_mode is CognitionExecutionMode.SINGLE_PASS
        assert isinstance(assembly.provider, OpenAICompatibleProvider)
        assert not isinstance(assembly.provider, OpenAICompatibleTwoPassProvider)
        assert resolved.config.provider.backend.value == "lm_studio"
    finally:
        asyncio.run(assembly.provider.aclose())


def test_lm_studio_explicit_reasoning_override_fails_before_generation(
    tmp_path: Path,
) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(
            tmp_path / "runtime.yaml",
            pass1_reasoning_mode="off",
        ),
        environ={},
    )

    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(resolved)

    assert caught.value.code is RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE
    assert caught.value.field == "runtime.cognition.pass1.reasoning_mode"
    assert "LM Studio" in str(caught.value)
