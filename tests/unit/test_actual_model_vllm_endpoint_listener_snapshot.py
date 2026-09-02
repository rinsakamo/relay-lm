from __future__ import annotations

import pytest

from relaylm.actual_model_vllm_launch_preflight import (
    RuntimeListenerEndpoint,
    RuntimeOwnershipError,
    parse_listener_snapshot_for_endpoint,
)


def test_expected_endpoint_absent_ignores_unrelated_pidless_listener() -> None:
    expected = RuntimeListenerEndpoint(host="127.0.0.1", port=8000)

    listeners = parse_listener_snapshot_for_endpoint(
        "LISTEN 0 4096 127.0.0.1:9000 0.0.0.0:*\n",
        expected_listener=expected,
    )

    assert listeners == ()


def test_expected_endpoint_present_with_pid_is_retained() -> None:
    expected = RuntimeListenerEndpoint(host="127.0.0.1", port=8000)

    listeners = parse_listener_snapshot_for_endpoint(
        'LISTEN 0 4096 127.0.0.1:8000 0.0.0.0:* users:(("python",pid=42,fd=3))\n',
        expected_listener=expected,
    )

    assert len(listeners) == 1
    assert listeners[0].endpoint == expected
    assert listeners[0].pids == (42,)


def test_expected_endpoint_present_without_pid_fails_closed() -> None:
    expected = RuntimeListenerEndpoint(host="127.0.0.1", port=8000)

    with pytest.raises(RuntimeOwnershipError) as exc_info:
        parse_listener_snapshot_for_endpoint(
            "LISTEN 0 4096 127.0.0.1:8000 0.0.0.0:*\n",
            expected_listener=expected,
        )

    assert exc_info.value.code == "PROCESS_OWNERSHIP_UNPROVEN"


def test_unrelated_owned_listener_is_irrelevant_to_expected_endpoint() -> None:
    expected = RuntimeListenerEndpoint(host="127.0.0.1", port=8000)

    listeners = parse_listener_snapshot_for_endpoint(
        'LISTEN 0 4096 127.0.0.1:9000 0.0.0.0:* users:(("python",pid=99,fd=7))\n',
        expected_listener=expected,
    )

    assert listeners == ()
