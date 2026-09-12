from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any


ModelFacingRequestObserver = Callable[[Mapping[str, Any]], None]

_MODEL_FACING_REQUEST_OBSERVER: ContextVar[ModelFacingRequestObserver | None] = ContextVar(
    "relaylm_openai_model_facing_request_observer",
    default=None,
)


@contextmanager
def model_facing_request_observation(
    observer: ModelFacingRequestObserver,
) -> Iterator[None]:
    """Activate one scoped, non-mutating observer for exact request bodies.

    The provider transport remains authoritative. Observation is process-local to
    the current context, changes no provider/client object, and is a no-op when
    no observer is active.
    """

    if not callable(observer):
        raise TypeError("model-facing request observer must be callable")
    token = _MODEL_FACING_REQUEST_OBSERVER.set(observer)
    try:
        yield
    finally:
        _MODEL_FACING_REQUEST_OBSERVER.reset(token)


def observe_model_facing_request(request_body: Mapping[str, Any]) -> None:
    """Notify the active observer immediately before provider transport."""

    observer = _MODEL_FACING_REQUEST_OBSERVER.get()
    if observer is not None:
        observer(request_body)
