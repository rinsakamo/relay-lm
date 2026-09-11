from __future__ import annotations

from relaylm.providers.openai_request_observation import (
    model_facing_request_observation,
    observe_model_facing_request,
)


def test_request_observation_is_noop_without_active_scope() -> None:
    observe_model_facing_request({"model": "gemma-test", "stream": False})


def test_request_observation_receives_exact_body_inside_scope() -> None:
    seen: list[object] = []
    body = {"model": "gemma-test", "messages": [], "stream": False}

    with model_facing_request_observation(seen.append):
        observe_model_facing_request(body)

    assert seen == [body]
    assert seen[0] is body


def test_nested_request_observation_scope_restores_outer_observer() -> None:
    outer: list[object] = []
    inner: list[object] = []
    first = {"model": "first"}
    second = {"model": "second"}
    third = {"model": "third"}

    with model_facing_request_observation(outer.append):
        observe_model_facing_request(first)
        with model_facing_request_observation(inner.append):
            observe_model_facing_request(second)
        observe_model_facing_request(third)

    assert outer == [first, third]
    assert inner == [second]


def test_request_observation_rejects_non_callable_observer() -> None:
    try:
        with model_facing_request_observation(None):  # type: ignore[arg-type]
            raise AssertionError("unreachable")
    except TypeError as exc:
        assert str(exc) == "model-facing request observer must be callable"
    else:
        raise AssertionError("non-callable observer must fail closed")
