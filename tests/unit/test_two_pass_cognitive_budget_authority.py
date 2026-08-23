from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_cognitive_turn_contract_declares_per_pass_budget_boundary() -> None:
    contract = (ROOT / "docs/contracts/cognitive-turn.md").read_text(encoding="utf-8")

    assert "count the exact Pass 1 conversation serialization" in contract
    assert "same resolved Pass 1 request" in contract
    assert "count the exact Pass 2 extraction serialization" in contract
    assert "before provider delegation" in contract
    assert "pass2_budget_exceeded" in contract
    assert "does not run a second degradation policy" in contract


def test_shared_two_pass_budget_realization_is_declared_by_both_owners() -> None:
    budget_owner = yaml.safe_load(
        (ROOT / ".ai/authority/cognitive_budget.yaml").read_text(encoding="utf-8")
    )
    turn_owner = yaml.safe_load(
        (ROOT / ".ai/authority/cognitive_turn.yaml").read_text(encoding="utf-8")
    )

    assert "src/relaylm/two_pass_turn.py" in budget_owner["implementation"]
    assert "tests/unit/test_two_pass_cognitive_budget.py" in budget_owner["tests"]
    assert "tests/unit/test_two_pass_cognitive_budget.py" in turn_owner["tests"]
