from __future__ import annotations

import builtins
import importlib
import os
import sys

import pytest

from relaylm.portable_lock import (
    PortableLockUnavailable,
    acquire_portable_lock,
    portable_lock,
    release_portable_lock,
)

pytestmark = pytest.mark.skipif(
    os.name != "posix", reason="real-lock behavior is exercised on POSIX"
)


def test_exclusive_blocking_acquire_and_release(tmp_path):
    path = tmp_path / "lock.bin"
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        with portable_lock(fd, mode="exclusive", blocking=True):
            pass
        # Lock is released on exit; acquiring again must succeed immediately.
        with portable_lock(fd, mode="exclusive", blocking=True):
            pass
    finally:
        os.close(fd)


def test_exclusive_nonblocking_conflict_raises_portable_lock_unavailable(tmp_path):
    path = tmp_path / "lock.bin"
    fd_a = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    fd_b = os.open(path, os.O_RDWR, 0o600)
    try:
        acquire_portable_lock(fd_a, mode="exclusive", blocking=False)
        try:
            with pytest.raises(PortableLockUnavailable):
                acquire_portable_lock(fd_b, mode="exclusive", blocking=False)
        finally:
            release_portable_lock(fd_a)
    finally:
        os.close(fd_a)
        os.close(fd_b)


def test_portable_lock_unavailable_is_also_blocking_io_error(tmp_path):
    # Several migrated call sites narrowly catch `except BlockingIOError` to
    # distinguish "lock busy" from other failures; PortableLockUnavailable
    # must keep satisfying that narrower catch on both platforms.
    assert issubclass(PortableLockUnavailable, BlockingIOError)
    assert issubclass(PortableLockUnavailable, OSError)


def test_shared_nonblocking_allows_two_concurrent_holders(tmp_path):
    path = tmp_path / "lock.bin"
    fd_a = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    fd_b = os.open(path, os.O_RDWR, 0o600)
    try:
        acquire_portable_lock(fd_a, mode="shared", blocking=False)
        try:
            acquire_portable_lock(fd_b, mode="shared", blocking=False)
            release_portable_lock(fd_b)
        finally:
            release_portable_lock(fd_a)
    finally:
        os.close(fd_a)
        os.close(fd_b)


def test_accepts_file_like_object_via_fileno(tmp_path):
    path = tmp_path / "lock.bin"
    with open(path, "a+b") as handle:
        with portable_lock(handle, mode="exclusive", blocking=True):
            pass


def test_invalid_mode_raises_value_error(tmp_path):
    path = tmp_path / "lock.bin"
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        with pytest.raises(ValueError):
            acquire_portable_lock(fd, mode="bogus", blocking=False)
    finally:
        os.close(fd)


def test_module_imports_and_exposes_public_api_when_fcntl_absent(monkeypatch):
    """Simulate the Windows import path: fcntl unavailable, msvcrt absent (as
    it is on this POSIX test host). The module must still import cleanly and
    expose its full public API; only actually taking a lock without a real
    backend should fail, and it must fail with PortableLockUnavailable rather
    than NotImplementedError.
    """

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name in ("fcntl", "msvcrt"):
            raise ImportError(f"simulated missing {name} module")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "relaylm.portable_lock", raising=False)
    monkeypatch.setattr(builtins, "__import__", _blocked_import)
    try:
        module = importlib.import_module("relaylm.portable_lock")
    finally:
        monkeypatch.setattr(builtins, "__import__", real_import)

    try:
        assert module.fcntl is None
        assert module.msvcrt is None
        # Public API surface is present and callable.
        assert callable(module.portable_lock)
        assert callable(module.acquire_portable_lock)
        assert callable(module.release_portable_lock)
        assert issubclass(module.PortableLockUnavailable, OSError)

        with pytest.raises(module.PortableLockUnavailable):
            module.acquire_portable_lock(0, mode="exclusive", blocking=False)
    finally:
        monkeypatch.delitem(sys.modules, "relaylm.portable_lock", raising=False)
        importlib.import_module("relaylm.portable_lock")


def test_windows_backend_selected_when_only_msvcrt_available(monkeypatch):
    """Simulate the Windows platform shape: fcntl absent, a stand-in msvcrt
    module present. The module should import cleanly and route through the
    msvcrt-backed windows path rather than raising NotImplementedError.
    """

    import types

    fake_msvcrt = types.ModuleType("msvcrt")
    fake_msvcrt.LK_LOCK = 1
    fake_msvcrt.LK_NBLCK = 2
    fake_msvcrt.LK_UNLCK = 0

    calls = []

    def _locking(fd, flag, nbytes):
        calls.append((fd, flag, nbytes))

    fake_msvcrt.locking = _locking

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "fcntl":
            raise ImportError("simulated missing fcntl module")
        if name == "msvcrt":
            return fake_msvcrt
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    monkeypatch.delitem(sys.modules, "relaylm.portable_lock", raising=False)
    try:
        module = importlib.import_module("relaylm.portable_lock")
        assert module.fcntl is None
        assert module.msvcrt is fake_msvcrt

        with open(os.devnull, "rb") as handle:
            fd = handle.fileno()
            module.acquire_portable_lock(fd, mode="shared", blocking=True)
            module.release_portable_lock(fd)
        # Shared mode degrades to exclusive locking flag on the msvcrt path,
        # and unlock uses LK_UNLCK on the same byte range.
        assert calls[0] == (fd, fake_msvcrt.LK_LOCK, 1)
        assert calls[1] == (fd, fake_msvcrt.LK_UNLCK, 1)
    finally:
        monkeypatch.setattr(builtins, "__import__", real_import)
        monkeypatch.delitem(sys.modules, "relaylm.portable_lock", raising=False)
        importlib.import_module("relaylm.portable_lock")


_MIGRATED_MODULES = [
    "relaylm.relaymem_slp_queue_storage",
    "relaylm.relaymem_primary_correction",
    "relaylm.relaymem_slp_durable_finalization_store",
    "relaylm.relaymem_slp_durable_finalization_replay",
    "relaylm._relaymem_slp_durable_finalization_replay_impl",
    "relaylm.relaymem_primary_mutation_coordinator",
    "relaylm._relaymem_slp_protected_source_fs",
    "relaylm._relaymem_primary_index_log_recovery_audit_io",
    "relaylm._relaymem_primary_index_log_apply_io",
]


def test_migrated_modules_import_without_fcntl(monkeypatch):
    """Regression test for the Windows-portability bug this PR fixes: none of
    the previously-fcntl-importing modules (nor relaylm.portable_lock itself)
    may unconditionally import fcntl at module scope.
    """

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "fcntl":
            raise ImportError("fcntl is blocked for this test")
        return real_import(name, *args, **kwargs)

    modules_to_reload = ["relaylm.portable_lock", *_MIGRATED_MODULES]
    saved = {name: sys.modules.get(name) for name in modules_to_reload}
    for name in modules_to_reload:
        monkeypatch.delitem(sys.modules, name, raising=False)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)
    try:
        for name in _MIGRATED_MODULES:
            module = importlib.import_module(name)
            assert module is not None
    finally:
        monkeypatch.setattr(builtins, "__import__", real_import)
        for name in modules_to_reload:
            monkeypatch.delitem(sys.modules, name, raising=False)
        for name, original in saved.items():
            if original is not None:
                sys.modules[name] = original
            importlib.import_module(name)
