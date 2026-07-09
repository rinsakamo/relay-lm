"""Durable finalization gate helpers and stream close/error helpers.

Extracted from `relaylm.app` to keep the app module focused on route
wiring and runtime orchestration. Behavior, status codes, and gate
semantics are unchanged from the inline implementation this replaces.

Also home to ``get_shared_http_client``: this module has no dependency on
``relaylm.app`` or ``relaylm.managed_chat_runtime``, so both of those
modules can import from it without creating an import cycle (``app.py``
imports ``managed_chat_runtime``, which needs the shared-client accessor).
"""
from __future__ import annotations

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from relaylm.app_request_validation import openai_error
from relaylm.config import RelayLMConfig

HTTP_CLIENT_STATE_ATTR = "http_client"


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


def get_shared_http_client(app: FastAPI) -> httpx.AsyncClient:
    """Return the app's shared backend ``httpx.AsyncClient``.

    In production, ``relaylm.app``'s lifespan creates this client on
    startup and closes it on shutdown, so it is normally already present on
    ``app.state`` by the time a request arrives. Some test setups
    instantiate the app without running its lifespan (e.g.
    ``TestClient(app)`` used without a context manager), so this lazily
    creates and stores a single instance on first use if lifespan hasn't
    already done so.

    This check-then-create is safe without an explicit lock: both branches
    run synchronously with no ``await`` in between, so under asyncio's
    cooperative single-threaded model no other coroutine can interleave
    between the check and the assignment.
    """
    client = getattr(app.state, HTTP_CLIENT_STATE_ATTR, None)
    if client is None:
        client = httpx.AsyncClient()
        setattr(app.state, HTTP_CLIENT_STATE_ATTR, client)
    return client


async def close_stream_iterator(body_iter: object) -> None:
    """Best-effort close of an abandoned backend response/stream iterator.

    ``body_iter`` here is typically a freshly-returned, never-iterated
    async generator pipeline (``open_chat_completion_stream``'s result,
    possibly wrapped by one or more stream runtime wrappers). Python's
    generator semantics make closing such a generator *before it has ever
    been started* a silent no-op -- no code runs, including ``finally``
    blocks -- so calling ``aclose()`` alone would never actually release
    the underlying backend connection in that case.

    Priming with a single ``__anext__()`` step first ensures every level of
    the (possibly nested) generator pipeline is parked at its own ``yield``
    before we close it, so the subsequent ``aclose()`` cascades through
    every level's cleanup and reaches the backend response close. Discarding
    that one primed chunk is safe here: every caller of this helper is
    already abandoning the whole stream in favor of a different response.
    """
    anext_ = getattr(body_iter, "__anext__", None)
    if callable(anext_):
        try:
            await anext_()
        except StopAsyncIteration:
            return  # Already fully drained/closed itself.
        except Exception:
            pass  # Fall through to the best-effort aclose() below.
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
