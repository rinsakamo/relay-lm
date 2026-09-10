from __future__ import annotations

import errno

import pytest

import tools.v2_cognitive_ir_s3_llama_cpp_transaction_listener_safe as safe


class _FakeSocket:
    def __init__(self, result: int) -> None:
        self.result = result
        self.timeout: float | None = None
        self.address: tuple[str, int] | None = None

    def __enter__(self) -> "_FakeSocket":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def connect_ex(self, address: tuple[str, int]) -> int:
        self.address = address
        return self.result


def _install_socket(monkeypatch, result: int) -> list[_FakeSocket]:
    created: list[_FakeSocket] = []

    def factory(*_args, **_kwargs) -> _FakeSocket:
        item = _FakeSocket(result)
        created.append(item)
        return item

    monkeypatch.setattr(safe.socket, "socket", factory)
    return created


def test_listener_absence_accepts_only_connection_refused(monkeypatch) -> None:
    created = _install_socket(monkeypatch, errno.ECONNREFUSED)

    assert safe._port_has_no_listener("127.0.0.1", 1234) is True
    assert len(created) == 1
    assert created[0].timeout == safe.LISTENER_PROBE_TIMEOUT_SECONDS
    assert created[0].address == ("127.0.0.1", 1234)


def test_listener_presence_is_not_released(monkeypatch) -> None:
    _install_socket(monkeypatch, 0)

    assert safe._port_has_no_listener("127.0.0.1", 1234) is False


def test_ambiguous_socket_error_fails_closed(monkeypatch) -> None:
    _install_socket(monkeypatch, errno.EACCES)

    with pytest.raises(safe.transaction.S3TransactionError, match="connect_ex"):
        safe._port_has_no_listener("127.0.0.1", 1234)


def test_compatibility_main_delegates_once_and_restores_predicate(monkeypatch) -> None:
    original = safe.transaction._port_is_free
    calls: list[object] = []

    def delegated(argv=None) -> int:
        calls.append(argv)
        assert safe.transaction._port_is_free is safe._port_has_no_listener
        return 7

    monkeypatch.setattr(safe.transaction, "main", delegated)

    assert safe.main(["--repo-root", "/tmp/repo"]) == 7
    assert calls == [["--repo-root", "/tmp/repo"]]
    assert safe.transaction._port_is_free is original


def test_compatibility_main_restores_predicate_after_failure(monkeypatch) -> None:
    original = safe.transaction._port_is_free

    def delegated(_argv=None) -> int:
        assert safe.transaction._port_is_free is safe._port_has_no_listener
        raise RuntimeError("boom")

    monkeypatch.setattr(safe.transaction, "main", delegated)

    with pytest.raises(RuntimeError, match="boom"):
        safe.main([])
    assert safe.transaction._port_is_free is original
