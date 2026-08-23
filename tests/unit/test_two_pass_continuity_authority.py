from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_cognitive_turn_contract_matches_response_first_continuity_clock() -> None:
    contract = (ROOT / "docs/contracts/cognitive-turn.md").read_text(encoding="utf-8")

    assert (
        "For `two_pass`, successful ordinary-turn completion is the complete accepted "
        "Pass 1 response after its Assistant Event is committed."
        in contract
    )
    assert (
        "Pass 2 may apply Continuity candidates at that already-advanced revision "
        "without advancing the lifecycle a second time."
        in contract
    )
    assert (
        "A failed or stale Pass 2 applies no proposal-driven Continuity mutation"
        in contract
    )
    assert "advance Continuity lifecycle exactly once / expire due items" in contract
    assert "successful-turn Continuity lifecycle revision / expiry remains" in contract
    assert "the post-conversation Continuity lifecycle snapshot" in contract

    assert "Pass 1 never mutates Continuity." not in contract
    assert (
        "Pass 2 may apply the existing Continuity lifecycle only at its guarded "
        "extraction commit boundary."
        not in contract
    )
    assert "Continuity Context    unchanged by failed Pass 2" not in contract
