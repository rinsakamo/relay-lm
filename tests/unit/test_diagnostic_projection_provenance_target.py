from __future__ import annotations

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


def test_projection_provenance_target_delegates_exactly_once(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_main():
        calls.append(tuple(sys.argv[1:]))
        return 7

    monkeypatch.setattr(
        target,
        "_load_target",
        lambda: SimpleNamespace(main=fake_main),
    )

    assert target.main(["--descriptor", "example.json"]) == 7
    assert calls == [("--descriptor", "example.json")]
