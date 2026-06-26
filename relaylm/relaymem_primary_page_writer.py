"""Public RelayMEM M3e atomic Primary MEM page-writer boundary."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._relaymem_primary_page_writer_impl import (
    apply_relaymem_primary_page_write as _apply_active_page_write,
)
from ._relaymem_primary_lifecycle_page_writer import (
    apply_hidden_lifecycle_page_write,
    is_hidden_lifecycle_handoff,
)


def apply_relaymem_primary_page_write(
    *,
    writer_handoff_artifact: Mapping[str, Any] | None,
    root_path: str | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
) -> dict[str, Any]:
    """Validate and atomically publish active or strict hidden Primary pages."""

    if is_hidden_lifecycle_handoff(writer_handoff_artifact):
        return apply_hidden_lifecycle_page_write(
            writer_handoff_artifact=writer_handoff_artifact,
            root_path=root_path,
            enabled=enabled,
            dry_run_only=dry_run_only,
            apply_enabled=apply_enabled,
        )
    return _apply_active_page_write(
        writer_handoff_artifact=writer_handoff_artifact,
        root_path=root_path,
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
    )


__all__ = ["apply_relaymem_primary_page_write"]
