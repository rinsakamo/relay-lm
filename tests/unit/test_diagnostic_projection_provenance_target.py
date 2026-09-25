from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import tools.diagnostic_projection_provenance_target as target


def test_projection_provenance_target_identity_matches_registered_contract() -> None:
    assert target.TARGET_NAME == "diagnostic:3006-projection-provenance"
    assert target.EXPECTED_ATTEMPT_ID == "layer0-projection-provenance-20260925-a"
    assert (
        target.EXPECTED_DESCRIPTOR_GENERATION
        == "provenance-measured-descriptor-20260925-b"
    )
    assert target.QUEUE_LEASE_FD_ENV == "RELAYLM_PHYSICAL_QUEUE_LEASE_FD"


def test_projection_provenance_target_delegates_exactly_once(monkeypatch) -> None:
    calls: list[tuple[tuple[str, ...], str | None]] = []

    def fake_main():
        calls.append(
            (
                tuple(sys.argv[1:]),
                os.environ.get(target.QUEUE_LEASE_FD_ENV),
            )
        )
        return 7

    monkeypatch.setattr(
        target,
        "_load_target",
        lambda: SimpleNamespace(main=fake_main),
    )
    monkeypatch.setattr(target, "_require_inherited_queue_lease_fd", lambda: 9)

    assert target.main(["--descriptor", "example.json"]) == 7
    assert calls == [(("--descriptor", "example.json"), "9")]
    assert target.QUEUE_LEASE_FD_ENV not in os.environ


def test_projection_provenance_target_fails_without_queue_lease(monkeypatch) -> None:
    monkeypatch.setattr(
        target,
        "_load_target",
        lambda: SimpleNamespace(main=lambda: 0),
    )
    def blocked():
        raise target.ProjectionProvenanceTargetError("queue lease missing")
    monkeypatch.setattr(target, "_require_inherited_queue_lease_fd", blocked)

    try:
        target.main([])
    except target.ProjectionProvenanceTargetError:
        pass
    else:
        raise AssertionError("target accepted execution without canonical queue lease")
