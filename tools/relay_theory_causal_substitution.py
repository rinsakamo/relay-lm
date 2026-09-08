"""Exact finite observational/interventional Grand Null apparatus for #2364.

Research falsification only. This bounded binary causal-model implementation is
an executable test fixture, not Relay Theory ontology and not RelayLM runtime
authority. It distinguishes one composed observational law from the mechanism
factorisation used to regenerate laws after declared local substitutions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import product

from tools.relay_theory_scheduler_nondeterminism import Distribution, exact_distribution

Assignment = tuple[tuple[str, str], ...]
JointLaw = tuple[tuple[Assignment, Fraction], ...]
MechanismTable = tuple[tuple[tuple[str, ...], Distribution], ...]


@dataclass(frozen=True)
class Exogenous:
    name: str
    distribution: Distribution


@dataclass(frozen=True)
class Mechanism:
    target: str
    parents: tuple[str, ...]
    table: MechanismTable
    label: str = ""


@dataclass(frozen=True)
class CausalModel:
    name: str
    exogenous: tuple[Exogenous, ...]
    mechanisms: tuple[Mechanism, ...]


@dataclass(frozen=True)
class CausalResult:
    name: str
    passed: bool
    detail: str


def _binary_distribution(probability_one: Fraction) -> Distribution:
    if not isinstance(probability_one, Fraction):
        raise TypeError("probability must be fractions.Fraction")
    if probability_one < 0 or probability_one > 1:
        raise ValueError("probability must lie in [0, 1]")
    return exact_distribution({"0": 1 - probability_one, "1": probability_one})


def fair_binary() -> Distribution:
    return _binary_distribution(Fraction(1, 2))


def constant_distribution(value: str) -> Distribution:
    if value not in {"0", "1"}:
        raise ValueError("binary value must be '0' or '1'")
    return exact_distribution({value: Fraction(1)})


def deterministic_mechanism(
    target: str,
    parents: tuple[str, ...],
    mapping: Mapping[tuple[str, ...], str],
    *,
    label: str = "",
) -> Mechanism:
    table = tuple(
        (inputs, constant_distribution(output))
        for inputs, output in sorted(mapping.items())
    )
    return Mechanism(target, parents, table, label)


def copy_mechanism(target: str, parent: str, *, label: str = "") -> Mechanism:
    return deterministic_mechanism(
        target,
        (parent,),
        {("0",): "0", ("1",): "1"},
        label=label,
    )


def constant_mechanism(target: str, value: str, *, label: str = "") -> Mechanism:
    return Mechanism(target, (), (((), constant_distribution(value)),), label)


def stochastic_root_mechanism(
    target: str, probability_one: Fraction, *, label: str = ""
) -> Mechanism:
    return Mechanism(target, (), (((), _binary_distribution(probability_one)),), label)


def _canonical_assignment(values: Mapping[str, str]) -> Assignment:
    return tuple(sorted(values.items()))


def _validate_binary_distribution(distribution: Distribution) -> Distribution:
    distribution = exact_distribution(dict(distribution))
    if any(value not in {"0", "1"} for value, _ in distribution):
        raise ValueError("bounded causal mechanisms require binary outcomes")
    return distribution


def validate_causal_model(model: CausalModel) -> None:
    if not model.mechanisms:
        raise ValueError("causal model must contain at least one endogenous mechanism")

    exogenous_names = [item.name for item in model.exogenous]
    if len(exogenous_names) != len(set(exogenous_names)):
        raise ValueError("exogenous names must be unique")
    for item in model.exogenous:
        _validate_binary_distribution(item.distribution)

    targets = [mechanism.target for mechanism in model.mechanisms]
    if len(targets) != len(set(targets)):
        raise ValueError("mechanism targets must be unique")
    if set(exogenous_names) & set(targets):
        raise ValueError("exogenous and endogenous names must be disjoint")

    available = set(exogenous_names)
    for mechanism in model.mechanisms:
        if len(mechanism.parents) != len(set(mechanism.parents)):
            raise ValueError("mechanism parents must be unique")
        if any(parent not in available for parent in mechanism.parents):
            raise ValueError("mechanism parents must be exogenous or earlier endogenous variables")

        expected_inputs = set(product(("0", "1"), repeat=len(mechanism.parents)))
        actual_inputs: set[tuple[str, ...]] = set()
        for inputs, distribution in mechanism.table:
            if len(inputs) != len(mechanism.parents):
                raise ValueError("mechanism input arity must match parent arity")
            if any(value not in {"0", "1"} for value in inputs):
                raise ValueError("mechanism inputs must be binary")
            if inputs in actual_inputs:
                raise ValueError("mechanism table inputs must be unique")
            actual_inputs.add(inputs)
            _validate_binary_distribution(distribution)
        if actual_inputs != expected_inputs:
            raise ValueError("mechanism table must be total over binary parent inputs")
        available.add(mechanism.target)


def _mechanism_distribution(
    mechanism: Mechanism, assignment: Mapping[str, str]
) -> Distribution:
    key = tuple(assignment[parent] for parent in mechanism.parents)
    table = dict(mechanism.table)
    return _validate_binary_distribution(table[key])


def evaluate_model(model: CausalModel) -> JointLaw:
    """Compose exact exogenous states and local mechanisms into a visible joint law."""
    validate_causal_model(model)
    states: list[tuple[dict[str, str], Fraction]] = [({}, Fraction(1))]

    for exogenous in model.exogenous:
        next_states: list[tuple[dict[str, str], Fraction]] = []
        for assignment, mass in states:
            for value, local_mass in exogenous.distribution:
                updated = dict(assignment)
                updated[exogenous.name] = value
                next_states.append((updated, mass * local_mass))
        states = next_states

    for mechanism in model.mechanisms:
        next_states = []
        for assignment, mass in states:
            for value, local_mass in _mechanism_distribution(mechanism, assignment):
                updated = dict(assignment)
                updated[mechanism.target] = value
                next_states.append((updated, mass * local_mass))
        states = next_states

    visible_names = {mechanism.target for mechanism in model.mechanisms}
    accumulated: dict[Assignment, Fraction] = {}
    for assignment, mass in states:
        visible = _canonical_assignment(
            {name: value for name, value in assignment.items() if name in visible_names}
        )
        accumulated[visible] = accumulated.get(visible, Fraction(0)) + mass

    if sum(accumulated.values(), Fraction(0)) != 1:
        raise ValueError("evaluated joint law must normalize exactly")
    return tuple(sorted(accumulated.items(), key=repr))


def joint_probability(law: JointLaw, evidence: Mapping[str, str]) -> Fraction:
    total = Fraction(0)
    for assignment, mass in law:
        values = dict(assignment)
        if all(values.get(name) == value for name, value in evidence.items()):
            total += mass
    return total


def condition_joint(law: JointLaw, evidence: Mapping[str, str]) -> JointLaw:
    denominator = joint_probability(law, evidence)
    if denominator == 0:
        raise ValueError("cannot condition on zero-probability evidence")
    return tuple(
        (assignment, mass / denominator)
        for assignment, mass in law
        if all(dict(assignment).get(name) == value for name, value in evidence.items())
    )


def _target_index(model: CausalModel, target: str) -> int:
    for index, mechanism in enumerate(model.mechanisms):
        if mechanism.target == target:
            return index
    raise ValueError(f"unknown intervention target {target!r}")


def substitute_mechanism(
    model: CausalModel,
    target: str,
    replacement: Mechanism,
    *,
    name: str | None = None,
) -> CausalModel:
    """Replace one local mechanism while preserving all untouched mechanisms/laws."""
    validate_causal_model(model)
    index = _target_index(model, target)
    if replacement.target != target:
        raise ValueError("replacement mechanism target must match substituted target")
    mechanisms = list(model.mechanisms)
    mechanisms[index] = replacement
    result = replace(model, name=name or model.name, mechanisms=tuple(mechanisms))
    validate_causal_model(result)
    return result


def hard_intervene(
    model: CausalModel, target: str, value: str, *, name: str | None = None
) -> CausalModel:
    return substitute_mechanism(
        model,
        target,
        constant_mechanism(target, value, label=f"do({target}={value})"),
        name=name,
    )


def soft_intervene(
    model: CausalModel,
    target: str,
    replacement: Mechanism,
    *,
    name: str | None = None,
) -> CausalModel:
    return substitute_mechanism(model, target, replacement, name=name)


def untouched_mechanisms_preserved(
    before: CausalModel, after: CausalModel, target: str
) -> bool:
    if before.exogenous != after.exogenous:
        return False
    before_map = {item.target: item for item in before.mechanisms if item.target != target}
    after_map = {item.target: item for item in after.mechanisms if item.target != target}
    return before_map == after_map


def hard_intervention_table(
    model: CausalModel, targets: Sequence[str]
) -> tuple[tuple[tuple[str, str], JointLaw], ...]:
    return tuple(
        ((target, value), evaluate_model(hard_intervene(model, target, value)))
        for target in targets
        for value in ("0", "1")
    )


def interventional_signature(
    model: CausalModel,
    targets: Sequence[str],
    soft_replacements: Sequence[tuple[str, Mechanism]] = (),
) -> tuple[object, ...]:
    hard = hard_intervention_table(model, targets)
    soft = tuple(
        (
            (target, replacement.parents, replacement.table),
            evaluate_model(soft_intervene(model, target, replacement)),
        )
        for target, replacement in soft_replacements
    )
    return evaluate_model(model), hard, soft


def causal_behavior_partition(
    models: Sequence[CausalModel],
    targets: Sequence[str],
    soft_replacements: Sequence[tuple[str, Mechanism]] = (),
) -> dict[str, str]:
    if len({model.name for model in models}) != len(models):
        raise ValueError("model names must be unique")
    signatures: list[tuple[object, ...]] = []
    partition: dict[str, str] = {}
    for model in models:
        signature = interventional_signature(model, targets, soft_replacements)
        try:
            index = signatures.index(signature)
        except ValueError:
            signatures.append(signature)
            index = len(signatures) - 1
        partition[model.name] = f"b{index}"
    return partition


def causal_partition_is_representative_independent(
    models: Sequence[CausalModel],
    partition: Mapping[str, str],
    targets: Sequence[str],
    soft_replacements: Sequence[tuple[str, Mechanism]] = (),
) -> bool:
    by_name = {model.name: model for model in models}
    if set(partition) != set(by_name):
        raise ValueError("partition must name every model exactly once")
    for block in set(partition.values()):
        members = [by_name[name] for name, value in partition.items() if value == block]
        reference = interventional_signature(members[0], targets, soft_replacements)
        if any(
            interventional_signature(candidate, targets, soft_replacements) != reference
            for candidate in members[1:]
        ):
            return False
    return True


def rename_mechanism_labels(
    model: CausalModel, labels: Mapping[str, str], *, name: str
) -> CausalModel:
    result = replace(
        model,
        name=name,
        mechanisms=tuple(
            replace(mechanism, label=labels.get(mechanism.target, mechanism.label))
            for mechanism in model.mechanisms
        ),
    )
    validate_causal_model(result)
    return result


def direct_xy_model(name: str = "x-causes-y") -> CausalModel:
    return CausalModel(
        name,
        (Exogenous("U", fair_binary()),),
        (
            copy_mechanism("X", "U", label="x-from-u"),
            copy_mechanism("Y", "X", label="y-from-x"),
        ),
    )


def reverse_yx_model(name: str = "y-causes-x") -> CausalModel:
    return CausalModel(
        name,
        (Exogenous("U", fair_binary()),),
        (
            copy_mechanism("Y", "U", label="y-from-u"),
            copy_mechanism("X", "Y", label="x-from-y"),
        ),
    )


def confounded_xy_model(name: str = "common-cause") -> CausalModel:
    return CausalModel(
        name,
        (Exogenous("U", fair_binary()),),
        (
            copy_mechanism("X", "U", label="x-from-u"),
            copy_mechanism("Y", "U", label="y-from-u"),
        ),
    )


def run_causal_substitution_comparison() -> tuple[CausalResult, ...]:
    direct = direct_xy_model()
    reverse = reverse_yx_model()
    confounded = confounded_xy_model()
    observational = evaluate_model(direct)

    edge_reversal = (
        observational == evaluate_model(reverse)
        and evaluate_model(hard_intervene(direct, "X", "0"))
        != evaluate_model(hard_intervene(reverse, "X", "0"))
    )

    conditioned = condition_joint(evaluate_model(confounded), {"X": "1"})
    intervened = evaluate_model(hard_intervene(confounded, "X", "1"))
    conditioning_not_intervention = (
        joint_probability(conditioned, {"Y": "1"}) == 1
        and joint_probability(intervened, {"Y": "1"}) == Fraction(1, 2)
    )

    common_cause_vs_direct = (
        evaluate_model(direct) == evaluate_model(confounded)
        and evaluate_model(hard_intervene(direct, "X", "0"))
        != evaluate_model(hard_intervene(confounded, "X", "0"))
    )

    target_identity = (
        evaluate_model(hard_intervene(direct, "X", "0"))
        != evaluate_model(hard_intervene(direct, "Y", "0"))
    )

    soft_root = stochastic_root_mechanism("X", Fraction(1, 2), label="soft-x")
    hard_vs_soft = (
        evaluate_model(hard_intervene(direct, "X", "1"))
        != evaluate_model(soft_intervene(direct, "X", soft_root))
    )

    locality = untouched_mechanisms_preserved(
        direct, hard_intervene(direct, "X", "0"), "X"
    )

    derived_table = hard_intervention_table(direct, ("X", "Y"))
    intervention_table_derived = (
        len(derived_table) == 4
        and dict(derived_table)[("X", "0")]
        == evaluate_model(hard_intervene(direct, "X", "0"))
        and dict(derived_table)[("Y", "1")]
        == evaluate_model(hard_intervene(direct, "Y", "1"))
    )

    renamed = rename_mechanism_labels(
        direct,
        {"X": "alpha", "Y": "beta"},
        name="renamed-direct",
    )
    partition = causal_behavior_partition((direct, renamed, reverse), ("X", "Y"))
    quotient = (
        partition[direct.name] == partition[renamed.name]
        and partition[direct.name] != partition[reverse.name]
        and causal_partition_is_representative_independent(
            (direct, renamed, reverse), partition, ("X", "Y")
        )
    )

    fixed_intervention_recovers_law = (
        evaluate_model(hard_intervene(direct, "X", "0"))
        == ((("X", "0"), ("Y", "0")), Fraction(1)),
    )

    return (
        CausalResult(
            "OBSERVATIONAL_EQUIVALENCE_DOES_NOT_IMPLY_INTERVENTIONAL_EQUIVALENCE",
            edge_reversal,
            "edge-reversed exact models share one observational law but differ under X-mechanism replacement",
        ),
        CausalResult(
            "INTERVENTION_IS_NOT_CONDITIONING",
            conditioning_not_intervention,
            "common-cause conditioning selects U while do(X=1) leaves U and Y mechanisms untouched",
        ),
        CausalResult(
            "COMMON_CAUSE_AND_DIRECT_CAUSE_DIFFER_UNDER_SUBSTITUTION",
            common_cause_vs_direct,
            "visible joint probability does not identify whether dependence is direct or latent-common-cause",
        ),
        CausalResult(
            "INTERVENTION_TARGET_IDENTITY_SURVIVES",
            target_identity,
            "replacing X and replacing Y are distinct operations even on the same observational model",
        ),
        CausalResult(
            "HARD_AND_STOCHASTIC_MECHANISM_REPLACEMENT_DIFFER",
            hard_vs_soft,
            "hard do and soft stochastic substitution induce different exact laws",
        ),
        CausalResult(
            "MECHANISM_SUBSTITUTION_IS_LOCAL",
            locality,
            "replacing X preserves exogenous law and every untouched local mechanism",
        ),
        CausalResult(
            "INTERVENTION_TABLE_IS_DERIVED_FROM_WIRING_AND_SUBSTITUTION",
            intervention_table_derived,
            "hard intervention responses are regenerated from mechanisms rather than stored as primitive tables",
        ),
        CausalResult(
            "CAUSAL_BEHAVIOR_QUOTIENT_IS_LABEL_GAUGE_AND_REPRESENTATIVE_INDEPENDENT",
            quotient,
            "mechanism labels melt while intervention-distinguishable factorisations remain separated",
        ),
        CausalResult(
            "FIXED_SUBSTITUTION_RECOVERS_ONE_EXACT_STOCHASTIC_LAW",
            fixed_intervention_recovers_law,
            "after mechanism replacement the modified model composes to one exact joint law",
        ),
    )
