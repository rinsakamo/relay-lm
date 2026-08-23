from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_OPERATOR_CONTRACT = REPOSITORY_ROOT / "docs/contracts/runtime-operator.md"


def test_runtime_operator_contract_discloses_current_two_pass_release_gap() -> None:
    text = RUNTIME_OPERATOR_CONTRACT.read_text(encoding="utf-8")
    remaining = text.split("## Remaining release-runtime work", maxsplit=1)[1]

    assert "historical single-pass" in remaining
    assert "qualified two-pass" in remaining
