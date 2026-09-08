from tools.relay_theory_causal_substitution import run_causal_substitution_comparison


def test_causal_comparison_verdicts_are_strict_booleans() -> None:
    results = run_causal_substitution_comparison()

    assert results
    assert all(type(result.passed) is bool for result in results)
    assert all(result.passed for result in results)
