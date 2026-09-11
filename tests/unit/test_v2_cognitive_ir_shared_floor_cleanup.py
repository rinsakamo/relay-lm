from __future__ import annotations

import inspect
from types import SimpleNamespace

import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction as tx


def test_cleanup_release_accepts_immediate_bindability(monkeypatch) -> None:
    monkeypatch.setattr(tx, "_port_is_free", lambda host, port: True)
    monkeypatch.setattr(tx, "_listening_socket_present", lambda port: True)

    result = tx._wait_until_listener_released(
        "127.0.0.1",
        1234,
        timeout_seconds=0.0,
        poll_seconds=0.0,
    )

    assert result["released"] is True
    assert result["evidence"] == "bindable"
    assert result["attempts"] == 1


def test_cleanup_release_accepts_listener_absence_when_bind_temporarily_blocked(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tx, "_port_is_free", lambda host, port: False)
    monkeypatch.setattr(tx, "_listening_socket_present", lambda port: False)

    result = tx._wait_until_listener_released(
        "127.0.0.1",
        1234,
        timeout_seconds=0.0,
        poll_seconds=0.0,
    )

    assert result["released"] is True
    assert result["evidence"] == "listener_absent"
    assert result["last_bindable"] is False
    assert result["last_listener_present"] is False


def test_cleanup_release_waits_through_transient_listener(monkeypatch) -> None:
    states = iter((True, False))
    monkeypatch.setattr(tx, "_port_is_free", lambda host, port: False)
    monkeypatch.setattr(tx, "_listening_socket_present", lambda port: next(states))
    monkeypatch.setattr(tx.time, "sleep", lambda seconds: None)

    result = tx._wait_until_listener_released(
        "127.0.0.1",
        1234,
        timeout_seconds=1.0,
        poll_seconds=0.0,
    )

    assert result["released"] is True
    assert result["evidence"] == "listener_absent"
    assert result["attempts"] == 2


def test_cleanup_release_fails_closed_when_listener_never_releases(monkeypatch) -> None:
    monkeypatch.setattr(tx, "_port_is_free", lambda host, port: False)
    monkeypatch.setattr(tx, "_listening_socket_present", lambda port: True)

    result = tx._wait_until_listener_released(
        "127.0.0.1",
        1234,
        timeout_seconds=0.0,
        poll_seconds=0.0,
    )

    assert result["released"] is False
    assert result["evidence"] == "cleanup_release_timeout"
    assert result["attempts"] == 1
    assert result["last_listener_present"] is True


def test_cleanup_does_not_claim_release_when_owned_process_did_not_terminate(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        tx,
        "_terminate_owned_process",
        lambda process: {
            "terminated": False,
            "exit_code": None,
            "signal_path": "sigkill",
            "forced": True,
        },
    )

    def unexpected_wait(*args, **kwargs):
        raise AssertionError("listener release must not be polled before termination")

    monkeypatch.setattr(tx, "_wait_until_listener_released", unexpected_wait)

    result = tx._cleanup_owned_server(SimpleNamespace(), port=1234)

    assert result["terminated"] is False
    assert result["listener_release"]["released"] is False
    assert result["listener_release"]["evidence"] == "owned_process_not_terminated"


def test_pre_run_port_admission_remains_exact_immediate_bindability_gate() -> None:
    source = inspect.getsource(tx.main)
    assert 'if not _port_is_free("127.0.0.1", args.port):' in source
    assert '"127.0.0.1:1234 is occupied before calibration"' in source
