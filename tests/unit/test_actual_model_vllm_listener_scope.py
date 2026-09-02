from __future__ import annotations

import subprocess
import sys

import pytest

import relaylm.actual_model_vllm_launch_preflight as launch_preflight
from relaylm.actual_model_vllm_launch_preflight import (
    RuntimeListenerEndpoint,
    RuntimeListenerObservation,
    RuntimeOwnershipError,
    launch_owned_vllm_runtime,
    parse_listener_snapshot,
    snapshot_runtime_listeners,
    wait_for_vllm_runtime_readiness,
)


def _expected() -> RuntimeListenerEndpoint:
    return RuntimeListenerEndpoint(host="127.0.0.1", port=8000)


def test_endpoint_scope_ignores_unrelated_pidless_listener() -> None:
    snapshot = (
        "LISTEN 0 4096 127.0.0.1:9000 0.0.0.0:*\n"
        'LISTEN 0 4096 127.0.0.1:7000 0.0.0.0:* users:(("python",pid=41,fd=3))\n'
    )

    assert parse_listener_snapshot(snapshot, expected_endpoint=_expected()) == ()


def test_endpoint_scope_preserves_expected_listener_pid() -> None:
    snapshot = (
        "LISTEN 0 4096 127.0.0.1:9000 0.0.0.0:*\n"
        'LISTEN 0 4096 127.0.0.1:8000 0.0.0.0:* users:(("python",pid=42,fd=3))\n'
    )

    assert parse_listener_snapshot(snapshot, expected_endpoint=_expected()) == (
        RuntimeListenerObservation(endpoint=_expected(), pids=(42,)),
    )


def test_endpoint_scope_fails_closed_when_expected_listener_has_no_pid() -> None:
    with pytest.raises(RuntimeOwnershipError, match="PROCESS_OWNERSHIP_UNPROVEN"):
        parse_listener_snapshot(
            "LISTEN 0 4096 127.0.0.1:8000 0.0.0.0:*\n",
            expected_endpoint=_expected(),
        )


def test_unscoped_parser_remains_globally_strict() -> None:
    with pytest.raises(RuntimeOwnershipError, match="PROCESS_OWNERSHIP_UNPROVEN"):
        parse_listener_snapshot("LISTEN 0 4096 127.0.0.1:9000 0.0.0.0:*\n")


def test_endpoint_snapshot_is_shell_free_and_scoped() -> None:
    calls: list[tuple[object, object]] = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=(
                "LISTEN 0 4096 127.0.0.1:9000 0.0.0.0:*\n"
                'LISTEN 0 4096 127.0.0.1:8000 0.0.0.0:* users:(("python",pid=42,fd=3))\n'
            ),
            stderr="",
        )

    assert snapshot_runtime_listeners(
        expected_endpoint=_expected(),
        run=fake_run,
    ) == (RuntimeListenerObservation(endpoint=_expected(), pids=(42,)),)
    assert calls == [
        (
            (("ss", "-H", "-ltnp"),),
            {"check": True, "capture_output": True, "text": True},
        )
    ]


def test_default_startup_attestation_scopes_snapshot_to_expected_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _expected()
    runtime = launch_owned_vllm_runtime(
        (sys.executable, "-c", "import time; time.sleep(30)"),
        run_id="endpoint-scope-startup",
        expected_listener=expected,
        owner_nonce="endpoint-scope-startup-owner",
    )
    calls: list[RuntimeListenerEndpoint | None] = []

    def fake_snapshot(*, expected_endpoint=None, run=subprocess.run):
        del run
        calls.append(expected_endpoint)
        return (
            RuntimeListenerObservation(
                endpoint=expected,
                pids=(runtime.boundary.root.pid,),
            ),
        )

    monkeypatch.setattr(
        launch_preflight,
        "snapshot_runtime_listeners",
        fake_snapshot,
    )
    try:
        attestation = runtime.attest_startup()
        assert attestation.listener.endpoint == expected
        assert calls == [expected]
    finally:
        runtime.cleanup(listener_snapshot=lambda: ())


def test_default_readiness_scopes_snapshot_to_expected_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _expected()
    runtime = launch_owned_vllm_runtime(
        (sys.executable, "-c", "import time; time.sleep(30)"),
        run_id="endpoint-scope-readiness",
        expected_listener=expected,
        owner_nonce="endpoint-scope-readiness-owner",
    )
    calls: list[RuntimeListenerEndpoint | None] = []

    def fake_snapshot(*, expected_endpoint=None, run=subprocess.run):
        del run
        calls.append(expected_endpoint)
        return (
            RuntimeListenerObservation(
                endpoint=expected,
                pids=(runtime.boundary.root.pid,),
            ),
        )

    monkeypatch.setattr(
        launch_preflight,
        "snapshot_runtime_listeners",
        fake_snapshot,
    )
    try:
        attestation = wait_for_vllm_runtime_readiness(runtime, timeout=0)
        assert attestation.listener.endpoint == expected
        assert calls == [expected]
    finally:
        runtime.cleanup(listener_snapshot=lambda: ())


def test_default_cleanup_scopes_snapshot_and_ignores_unrelated_pidless_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _expected()
    runtime = launch_owned_vllm_runtime(
        (sys.executable, "-c", "import time; time.sleep(30)"),
        run_id="endpoint-scope-cleanup",
        expected_listener=expected,
        owner_nonce="endpoint-scope-cleanup-owner",
    )
    calls: list[RuntimeListenerEndpoint | None] = []

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="LISTEN 0 4096 127.0.0.1:9000 0.0.0.0:*\n",
            stderr="",
        )

    def fake_snapshot(*, expected_endpoint=None, run=subprocess.run):
        calls.append(expected_endpoint)
        return snapshot_runtime_listeners(
            expected_endpoint=expected_endpoint,
            run=fake_run,
        )

    monkeypatch.setattr(
        launch_preflight,
        "snapshot_runtime_listeners",
        fake_snapshot,
    )
    receipt = runtime.cleanup()

    assert receipt.complete is True
    assert receipt.listener_disposition == "absent"
    assert calls == [expected]
