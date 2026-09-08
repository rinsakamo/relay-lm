from fractions import Fraction

import pytest

from tools.relay_theory_causal_substitution import (
    CausalModel,
    Mechanism,
    causal_behavior_partition,
    causal_partition_is_representative_independent,
    condition_joint,
    confounded_xy_model,
    constant_distribution,
    direct_xy_model,
    evaluate_model,
    hard_intervention_table,
    hard_intervene,
    interventional_signature,
    joint_probability,
    rename_mechanism_labels,
    reverse_yx_model,
    run_causal_substitution_comparison,
    soft_intervene,
    stochastic_root_mechanism,
    substitute_mechanism,
    untouched_mechanisms_preserved,
    validate_causal_model,
)


def test_causal_substitution_comparison_passes() -> None:
    results = run_causal_substitution_comparison()

    assert [result.name for result in results] == [
        "OBSERVATIONAL_EQUIVALENCE_DOES_NOT_IMPLY_INTERVENTIONAL_EQUIVALENCE",
        "INTERVENTION_IS_NOT_CONDITIONING",
        "COMMON_CAUSE_AND_DIRECT_CAUSE_DIFFER_UNDER_SUBSTITUTION",
        "INTERVENTION_TARGET_IDENTITY_SURVIVES",
        "HARD_AND_STOCHASTIC_MECHANISM_REPLACEMENT_DIFFER",
        "MECHANISM_SUBSTITUTION_IS_LOCAL",
        "INTERVENTION_TABLE_IS_DERIVED_FROM_WIRING_AND_SUBSTITUTION",
        "CAUSAL_BEHAVIOR_QUOTIENT_IS_LABEL_GAUGE_AND_REPRESENTATIVE_INDEPENDENT",
        "FIXED_SUBSTITUTION_RECOVERS_ONE_EXACT_STOCHASTIC_LAW",
    ]
    assert all(result.passed for result in results)


def test_observational_equivalence_does_not_imply_interventional_equivalence() -> None:
    direct = direct_xy_model()
    reverse = reverse_yx_model()

    assert evaluate_model(direct) == evaluate_model(reverse)
    assert evaluate_model(hard_intervene(direct, "X", "0")) != evaluate_model(
        hard_intervene(reverse, "X", "0")
    )


def test_intervention_is_not_observational_conditioning_under_confounding() -> None:
    model = confounded_xy_model()
    observational = evaluate_model(model)
    conditioned = condition_joint(observational, {"X": "1"})
    intervened = evaluate_model(hard_intervene(model, "X", "1"))

    assert joint_probability(conditioned, {"Y": "1"}) == 1
    assert joint_probability(intervened, {"Y": "1"}) == Fraction(1, 2)


def test_direct_and_common_cause_models_share_joint_law_but_not_substitution_behavior() -> None:
    direct = direct_xy_model()
    confounded = confounded_xy_model()

    assert evaluate_model(direct) == evaluate_model(confounded)
    assert interventional_signature(direct, ("X", "Y")) != interventional_signature(
        confounded, ("X", "Y")
    )


def test_intervention_target_identity_changes_behavior() -> None:
    model = direct_xy_model()

    do_x = evaluate_model(hard_intervene(model, "X", "0"))
    do_y = evaluate_model(hard_intervene(model, "Y", "0"))

    assert do_x != do_y
    assert joint_probability(do_x, {"X": "0", "Y": "0"}) == 1
    assert joint_probability(do_y, {"Y": "0"}) == 1
    assert joint_probability(do_y, {"X": "1"}) == Fraction(1, 2)


def test_hard_and_soft_mechanism_replacement_are_distinct_exact_operations() -> None:
    model = direct_xy_model()
    soft_root = stochastic_root_mechanism("X", Fraction(1, 2), label="soft-x")

    hard = evaluate_model(hard_intervene(model, "X", "1"))
    soft = evaluate_model(soft_intervene(model, "X", soft_root))

    assert hard != soft
    assert joint_probability(hard, {"X": "1", "Y": "1"}) == 1
    assert joint_probability(soft, {"X": "1", "Y": "1"}) == Fraction(1, 2)
    assert joint_probability(soft, {"X": "0", "Y": "0"}) == Fraction(1, 2)


def test_substitution_preserves_untouched_mechanisms_and_exogenous_law() -> None:
    before = direct_xy_model()
    after = hard_intervene(before, "X", "0")

    assert untouched_mechanisms_preserved(before, after, "X")
    assert before.exogenous == after.exogenous
    assert before.mechanisms[1] == after.mechanisms[1]
    assert before.mechanisms[0] != after.mechanisms[0]


def test_intervention_table_is_derived_from_mechanisms_and_substitution() -> None:
    model = direct_xy_model()
    table = dict(hard_intervention_table(model, ("X", "Y")))

    assert set(table) == {("X", "0"), ("X", "1"), ("Y", "0"), ("Y", "1")}
    assert table[("X", "0")] == evaluate_model(hard_intervene(model, "X", "0"))
    assert table[("Y", "1")] == evaluate_model(hard_intervene(model, "Y", "1"))


def test_mechanism_labels_are_gauge_but_intervention_distinctions_survive() -> None:
    direct = direct_xy_model()
    renamed = rename_mechanism_labels(
        direct,
        {"X": "alpha", "Y": "beta"},
        name="renamed-direct",
    )
    reverse = reverse_yx_model()
    models = (direct, renamed, reverse)
    partition = causal_behavior_partition(models, ("X", "Y"))

    assert evaluate_model(direct) == evaluate_model(renamed)
    assert interventional_signature(direct, ("X", "Y")) == interventional_signature(
        renamed, ("X", "Y")
    )
    assert partition[direct.name] == partition[renamed.name]
    assert partition[direct.name] != partition[reverse.name]
    assert causal_partition_is_representative_independent(
        models, partition, ("X", "Y")
    )


def test_fixed_substitution_recovers_one_exact_stochastic_joint_law() -> None:
    law = evaluate_model(hard_intervene(direct_xy_model(), "X", "0"))

    assert law == (((("X", "0"), ("Y", "0")), Fraction(1)),)


def test_substitution_rejects_wrong_target_replacement() -> None:
    model = direct_xy_model()
    wrong = Mechanism("Y", (), (((), constant_distribution("0")),), "wrong-target")

    with pytest.raises(ValueError, match="target must match"):
        substitute_mechanism(model, "X", wrong)


def test_causal_model_validation_rejects_future_parent_dependency() -> None:
    model = CausalModel(
        "cyclic-order",
        (),
        (
            Mechanism(
                "X",
                ("Y",),
                (
                    (("0",), constant_distribution("0")),
                    (("1",), constant_distribution("1")),
                ),
                "x-from-future-y",
            ),
            Mechanism("Y", (), (((), constant_distribution("0")),), "y-root"),
        ),
    )

    with pytest.raises(ValueError, match="earlier endogenous"):
        validate_causal_model(model)
