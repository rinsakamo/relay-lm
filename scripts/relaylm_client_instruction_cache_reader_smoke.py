#!/usr/bin/env python3
"""Smoke checks for the read-only client instruction cache reader."""

from __future__ import annotations

import builtins
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from unittest import mock

from relaylm.client_instruction_cache_reader import (
    build_client_instruction_cache_read_diagnostics,
    read_client_instruction_cache_candidate,
)

KEY = "a" * 64
OTHER_KEY = "b" * 64


def main() -> None:
    test_default_off_no_filesystem_access()
    test_missing_results()
    test_found_result()
    test_size_limits()
    test_malformed_entries()
    test_path_blocks()
    test_diagnostics_content_free()
    print("client instruction cache reader smoke: ok")


def test_default_off_no_filesystem_access() -> None:
    with (
        mock.patch.object(Path, "exists", side_effect=AssertionError("exists called")),
        mock.patch.object(Path, "lstat", side_effect=AssertionError("lstat called")),
        mock.patch.object(Path, "is_dir", side_effect=AssertionError("is_dir called")),
        mock.patch.object(builtins, "open", side_effect=AssertionError("open called")),
        mock.patch.object(os, "open", side_effect=AssertionError("os.open called")),
    ):
        result = read_client_instruction_cache_candidate(
            root_path="/does/not/matter",
            cache_key_sha256=KEY,
            enabled=False,
        )
    assert result is None


def test_missing_results() -> None:
    result = read_client_instruction_cache_candidate(
        root_path=None,
        cache_key_sha256=KEY,
        enabled=True,
    )
    assert result is not None
    assert result.status == "missing"
    assert result.miss_reason == "cache_root_not_configured"

    with tempfile.TemporaryDirectory() as tmpdir:
        missing_root = Path(tmpdir) / "missing"
        result = read_client_instruction_cache_candidate(
            root_path=missing_root,
            cache_key_sha256=KEY,
            enabled=True,
        )
        assert result is not None
        assert result.status == "missing"
        assert result.miss_reason == "cache_root_missing"

        root = Path(tmpdir) / "root"
        root.mkdir()
        result = read_client_instruction_cache_candidate(
            root_path=root,
            cache_key_sha256=KEY,
            enabled=True,
        )
        assert result is not None
        assert result.status == "missing"
        assert result.miss_reason == "cache_entry_not_found"


def test_found_result() -> None:
    sentinel = "SECRET_ROUTE_MODEL_SENTINEL"
    payload = {"route_model": sentinel, "nested": {"ok": True}}
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        entry = root / f"{KEY}.json"
        other = root / f"{OTHER_KEY}.json"
        entry.write_bytes(raw)
        other.write_bytes(b'{"wrong": true}')
        before = entry.read_bytes()

        with _forbid_write_operations():
            result = read_client_instruction_cache_candidate(
                root_path=root,
                cache_key_sha256=KEY,
                enabled=True,
            )

        assert result is not None
        assert result.status == "found"
        assert result.candidate_entry == payload
        assert result.entry_present is True
        assert result.bytes_read == len(raw)
        assert entry.read_bytes() == before
        assert sentinel not in repr(result)


def test_size_limits() -> None:
    exact = b'{"a":"' + (b"x" * 2) + b'"}'
    assert len(exact) == 10
    too_large = exact + b" "

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        entry = root / f"{KEY}.json"
        entry.write_bytes(exact)
        result = read_client_instruction_cache_candidate(
            root_path=root,
            cache_key_sha256=KEY,
            enabled=True,
            max_entry_bytes=len(exact),
        )
        assert result is not None
        assert result.status == "found"
        assert result.bytes_read == len(exact)

        entry.write_bytes(too_large)
        result = read_client_instruction_cache_candidate(
            root_path=root,
            cache_key_sha256=KEY,
            enabled=True,
            max_entry_bytes=len(exact),
        )
        assert_blocked(result, "cache_entry_read_limit_exceeded")
        assert result is not None
        assert result.bytes_read == len(exact) + 1

        entry.write_bytes(b"[" + (b" " * len(exact)))
        result = read_client_instruction_cache_candidate(
            root_path=root,
            cache_key_sha256=KEY,
            enabled=True,
            max_entry_bytes=len(exact),
        )
        assert_blocked(result, "cache_entry_read_limit_exceeded")


def test_malformed_entries() -> None:
    cases: list[tuple[bytes, str]] = [
        (b"", "cache_entry_malformed_json"),
        (b"\xff", "cache_entry_malformed_utf8"),
        (b"{", "cache_entry_malformed_json"),
        (b'{"a": 1, "a": 2}', "cache_entry_duplicate_json_key"),
        (b'{"a": {"b": 1, "b": 2}}', "cache_entry_duplicate_json_key"),
        (b'{"a": NaN}', "cache_entry_nonstandard_number"),
        (b'{"a": Infinity}', "cache_entry_nonstandard_number"),
        (b"[]", "cache_entry_not_object"),
        (b"null", "cache_entry_not_object"),
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        entry = root / f"{KEY}.json"
        for raw, reason in cases:
            entry.write_bytes(raw)
            result = read_client_instruction_cache_candidate(
                root_path=root,
                cache_key_sha256=KEY,
                enabled=True,
            )
            assert_blocked(result, reason)


def test_path_blocks() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        root = base / "root"
        root.mkdir()

        for invalid_key in ("z" * 64, "A" * 64, f"{KEY}.json"):
            result = read_client_instruction_cache_candidate(
                root_path=root,
                cache_key_sha256=invalid_key,
                enabled=True,
            )
            assert_blocked(result, "cache_key_invalid")

        root_file = base / "root-file"
        root_file.write_text("not a directory", encoding="utf-8")
        result = read_client_instruction_cache_candidate(
            root_path=root_file,
            cache_key_sha256=KEY,
            enabled=True,
        )
        assert_blocked(result, "cache_root_not_directory")

        root_symlink = base / "root-link"
        root_symlink.symlink_to(root, target_is_directory=True)
        result = read_client_instruction_cache_candidate(
            root_path=root_symlink,
            cache_key_sha256=KEY,
            enabled=True,
        )
        assert_blocked(result, "cache_root_symlink_blocked")

        target = base / "target.json"
        target.write_text("{}", encoding="utf-8")
        entry_link = root / f"{KEY}.json"
        entry_link.symlink_to(target)
        result = read_client_instruction_cache_candidate(
            root_path=root,
            cache_key_sha256=KEY,
            enabled=True,
        )
        assert_blocked(result, "cache_path_symlink_blocked")
        entry_link.unlink()

        parent = base / "parent"
        real_root = base / "real-root"
        real_root.mkdir()
        parent.mkdir()
        (parent / "link").symlink_to(real_root, target_is_directory=True)
        result = read_client_instruction_cache_candidate(
            root_path=parent / "link",
            cache_key_sha256=KEY,
            enabled=True,
        )
        assert_blocked(result, "cache_root_symlink_blocked")

        entry_dir = root / f"{KEY}.json"
        entry_dir.mkdir()
        result = read_client_instruction_cache_candidate(
            root_path=root,
            cache_key_sha256=KEY,
            enabled=True,
        )
        assert_blocked(result, "cache_entry_not_regular_file")
        entry_dir.rmdir()

        if hasattr(os, "mkfifo"):
            fifo = root / f"{KEY}.json"
            try:
                os.mkfifo(fifo)
            except OSError:
                pass
            else:
                result = read_client_instruction_cache_candidate(
                    root_path=root,
                    cache_key_sha256=KEY,
                    enabled=True,
                )
                assert_blocked(result, "cache_entry_not_regular_file")
                fifo.unlink()


def test_diagnostics_content_free() -> None:
    sentinel = "SECRET_JSON_SENTINEL"
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        entry = root / f"{KEY}.json"
        entry.write_text(
            json.dumps({"hash": KEY, "route_model": sentinel}),
            encoding="utf-8",
        )
        result = read_client_instruction_cache_candidate(
            root_path=root,
            cache_key_sha256=KEY,
            enabled=True,
        )
        diagnostics = build_client_instruction_cache_read_diagnostics(result)
        assert diagnostics is not None
        assert diagnostics["status"] == "found"
        assert diagnostics["entry_parsed"] is True
        assert diagnostics["read_only"] is True

        rendered = repr(diagnostics)
        forbidden = (
            str(root),
            f"{KEY}.json",
            KEY,
            sentinel,
            "route_model",
            "SECRET",
        )
        for value in forbidden:
            assert value not in rendered

    disabled = build_client_instruction_cache_read_diagnostics(None)
    assert disabled is not None
    assert disabled["enabled"] is False
    assert disabled["read_attempted"] is False


@contextmanager
def _forbid_write_operations() -> Iterator[None]:
    def fail(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("write operation called")

    with (
        mock.patch.object(os, "mkdir", side_effect=fail),
        mock.patch.object(os, "makedirs", side_effect=fail),
        mock.patch.object(os, "rename", side_effect=fail),
        mock.patch.object(os, "unlink", side_effect=fail),
        mock.patch.object(os, "chmod", side_effect=fail),
    ):
        yield


def assert_blocked(result: Any, reason: str) -> None:
    assert result is not None
    assert result.status == "blocked"
    assert reason in result.blocked_reasons


if __name__ == "__main__":
    main()
