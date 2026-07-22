"""Unit tests for EV-1 canonical encoding, digest, and ID primitives."""
from __future__ import annotations

import pytest

from relaylm.evidence_common import (
    canonical_digest,
    canonical_json_bytes,
    new_opaque_id,
    sha256_hex,
    utf8_text_digest,
)


def test_canonical_json_bytes_sorts_keys_deterministically() -> None:
    a = canonical_json_bytes({"b": 1, "a": 2})
    b = canonical_json_bytes({"a": 2, "b": 1})
    assert a == b
    assert a == b'{"a":2,"b":1}'


def test_canonical_json_bytes_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValueError):
        canonical_json_bytes({"x": float("nan")})
    with pytest.raises(ValueError):
        canonical_json_bytes({"x": float("inf")})


def test_canonical_digest_is_deterministic_and_order_independent() -> None:
    assert canonical_digest({"a": 1, "b": 2}) == canonical_digest({"b": 2, "a": 1})
    assert canonical_digest({"a": 1}) != canonical_digest({"a": 2})


def test_utf8_text_digest_no_normalization() -> None:
    # NFC vs NFD forms of the same visual character must not collide,
    # because digesting is defined over the exact UTF-8 scalar sequence.
    nfc = "é"  # é
    nfd = "é"  # e + combining acute accent
    assert utf8_text_digest(nfc) != utf8_text_digest(nfd)
    assert utf8_text_digest("hello") == sha256_hex("hello".encode("utf-8"))


def test_new_opaque_id_is_unique_and_content_free() -> None:
    canary = "super-secret-canary-content"
    ids = {new_opaque_id("sourceevent") for _ in range(20)}
    assert len(ids) == 20
    for identifier in ids:
        assert identifier.startswith("sourceevent_")
        assert canary not in identifier
        assert canary.encode().hex() not in identifier
