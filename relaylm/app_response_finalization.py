"""Durable finalization gate helpers and stream close/error helpers.

Extracted from `relaylm.app` to keep the app module focused on route
wiring and runtime orchestration. Behavior, status codes, and gate
semantics are unchanged from the inline implementation this replaces.
"""
from __future__ import annotations

from fastapi.responses import JSONResponse

from relaylm.app_request_validation import openai_error
from relaylm.config import RelayLMConfig


def durable_finalization_gate_relevant(config: RelayLMConfig) -> bool:
    return bool(
        config.relaymem_slp_durable_finalization_enabled
        or config.relaymem_slp_durable_finalization_apply_enabled
        or not config.relaymem_slp_durable_finalization_dry_run_only
    )


def durable_finalization_gate_valid(config: RelayLMConfig) -> bool:
    enabled = config.relaymem_slp_durable_finalization_enabled
    dry_run_only = config.relaymem_slp_durable_finalization_dry_run_only
    apply_enabled = config.relaymem_slp_durable_finalization_apply_enabled
    return (
        (not enabled and dry_run_only and not apply_enabled)
        or (enabled and dry_run_only and not apply_enabled)
        or (enabled and not dry_run_only and apply_enabled)
    )


def durable_finalization_apply_mode(config: RelayLMConfig) -> bool:
    return bool(
        config.relaymem_slp_durable_finalization_enabled
        and not config.relaymem_slp_durable_finalization_dry_run_only
        and config.relaymem_slp_durable_finalization_apply_enabled
    )


async def close_stream_iterator(body_iter: object) -> None:
    close = getattr(body_iter, "aclose", None)
    if not callable(close):
        return
    try:
        await close()
    except Exception:
        pass


def durable_finalization_server_error() -> JSONResponse:
    """Return one content-free error when protected release admission fails."""

    return openai_error(
        status_code=500,
        message="RelayLM could not safely finalize this response.",
        error_type="server_error",
    )
