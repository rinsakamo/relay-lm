from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_OPERATOR_CONTRACT = REPOSITORY_ROOT / "docs/contracts/runtime-operator.md"


def _normalized(text: str) -> str:
    return " ".join(text.split())


def test_runtime_operator_contract_names_two_pass_as_current_product_path() -> None:
    text = RUNTIME_OPERATOR_CONTRACT.read_text(encoding="utf-8")
    normalized = _normalized(text)
    remaining = text.split("## Remaining release-runtime work", maxsplit=1)[1]

    assert "the no-profile release topology default is `two_pass`" in normalized
    assert "historical single-pass" not in remaining
    assert "Actual-model Stage R qualification is deliberately outside" in remaining
