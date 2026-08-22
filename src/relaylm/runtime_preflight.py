from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from urllib.parse import urlsplit

from relaylm.runtime_assembly import (
    RuntimeAssembly,
    TokenCounterCapability,
    assemble_runtime,
)
from relaylm.runtime_config import RuntimeConfigErrorCode
from relaylm.runtime_config_loader import ResolvedRuntimeConfig
from relaylm.storage.filesystem import CharacterDataError, CharacterDirectory


class RuntimePreflightError(ValueError):
    """Safe typed failure while checking one resolved release runtime."""

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
class PreparedRuntime:
    """One resolved, non-generative-preflighted runtime ready for doctor/serve."""

    resolved: ResolvedRuntimeConfig
    assembly: RuntimeAssembly
    checks: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "checks", MappingProxyType(dict(self.checks)))

    def doctor_report(self) -> dict[str, object]:
        return {
            "status": "ok",
            "checks": dict(sorted(self.checks.items())),
            "effective_config": self.resolved.effective_diagnostics(),
        }


def prepare_runtime(
    resolved: ResolvedRuntimeConfig,
    *,
    token_counter_capabilities: Mapping[str, TokenCounterCapability] | None = None,
) -> PreparedRuntime:
    """Validate release-operability without provider calls or semantic writes."""

    if not isinstance(resolved, ResolvedRuntimeConfig):
        raise TypeError("resolved must be ResolvedRuntimeConfig")

    _validate_provider_configuration(resolved)
    character = CharacterDirectory(resolved.config.character.directory)
    _validate_character_readability(character)
    _validate_persistence_writability(character)
    assembly = assemble_runtime(
        resolved,
        token_counter_capabilities=token_counter_capabilities,
    )
    return PreparedRuntime(
        resolved=resolved,
        assembly=assembly,
        checks={
            "configuration": "ok",
            "character": "ok",
            "persistence": "ok",
            "provider": "ok",
            "runtime_assembly": "ok",
        },
    )


def _validate_provider_configuration(resolved: ResolvedRuntimeConfig) -> None:
    provider = resolved.config.provider
    try:
        parsed = urlsplit(provider.base_url)
        _ = parsed.port
    except ValueError as exc:
        raise RuntimePreflightError(
            RuntimeConfigErrorCode.PROVIDER_INVALID,
            field="provider.base_url",
            message="provider base URL is malformed",
        ) from exc
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise RuntimePreflightError(
            RuntimeConfigErrorCode.PROVIDER_INVALID,
            field="provider.base_url",
            message="provider base URL must use http or https and include a host",
        )
    if "?" in provider.base_url or "#" in provider.base_url:
        raise RuntimePreflightError(
            RuntimeConfigErrorCode.PROVIDER_INVALID,
            field="provider.base_url",
            message="provider base URL must not include a query or fragment",
        )


def _validate_character_readability(character: CharacterDirectory) -> None:
    root = character.root
    if not root.is_dir():
        raise RuntimePreflightError(
            RuntimeConfigErrorCode.CHARACTER_INVALID,
            field="character.directory",
            message="selected Character Package directory is unavailable",
        )
    try:
        character.load_config()
        character.load_identity()
        character.load_state()
        tuple(character.iter_events())
        character.load_memory_markdown()
    except CharacterDataError as exc:
        raise RuntimePreflightError(
            RuntimeConfigErrorCode.CHARACTER_INVALID,
            field="character.directory",
            message="selected Character Package is invalid or unreadable",
        ) from exc


def _validate_persistence_writability(character: CharacterDirectory) -> None:
    root = character.root
    memory = character.memory_path
    if memory.exists() and not memory.is_dir():
        raise RuntimePreflightError(
            RuntimeConfigErrorCode.CHARACTER_INVALID,
            field="character.directory",
            message="Character persistence path is not a directory",
        )

    directory = memory if memory.exists() else root
    if not os.access(directory, os.W_OK | os.X_OK):
        raise RuntimePreflightError(
            RuntimeConfigErrorCode.CHARACTER_INVALID,
            field="character.directory",
            message="Character persistence directory is not writable",
        )

    for path in (
        character.events_path,
        character.state_path,
        character.memory_markdown_path,
    ):
        if path.exists() and not os.access(path, os.W_OK):
            raise RuntimePreflightError(
                RuntimeConfigErrorCode.CHARACTER_INVALID,
                field="character.directory",
                message="an existing Character persistence file is not writable",
            )
