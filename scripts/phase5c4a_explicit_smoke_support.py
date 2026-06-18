"""Explicit-provenance wrappers for Phase 5-C4a smoke fixtures."""
from __future__ import annotations

from typing import Any

from phase5c4a_smoke_support import (  # noqa: F401
    REPO_ROOT,
    build_context,
    cache_entry,
    identity_for,
    write_config,
)
from phase5c4a_smoke_support import payload as _legacy_payload


def payload(
    instructions: list[tuple[str, str]],
    *,
    current: Any = "exact current user sentinel",
    prior: bool = True,
    stream: bool = False,
    selected_instruction_indices: list[int] | None = None,
    include_provenance: bool = True,
) -> dict[str, Any]:
    result = _legacy_payload(
        instructions,
        current=current,
        prior=prior,
        stream=stream,
    )
    if instructions and include_provenance:
        result["relaylm"] = {
            "instruction_evidence": {
                "schema_version": "client_instruction_source.v1",
                "message_indices": (
                    selected_instruction_indices
                    if selected_instruction_indices is not None
                    else list(range(len(instructions)))
                ),
            }
        }
    return result
