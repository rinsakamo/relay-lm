"""Exact finite cross-world-coupling Grand Null apparatus for Relay Theory #2370.

Research falsification only. The fixture intentionally strips away causal-graph
syntax and represents only a finite response-type law. It asks whether the full
declared *single-world* intervention interface determines how mutually exclusive
outcomes are coupled when the same exogenous response type is aligned across
worlds. No counterfactual, SCM, or identity ontology is assumed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Literal

Assignment = tuple[tuple[str, str], ...]
JointLaw = tuple[tuple[Assignment, Fraction], ...]
PotentialPairLaw = tuple[tuple[tuple[str, str], Fraction], ...]
AffineSignature = tuple[tuple[Assignment, Fraction, Fraction], ...]
Frame = Literal["single_world", "cross_world"]


@dataclass(frozen=True)
class ResponseType:
    label: str
    y0: str
    y1: str


@dataclass(frozen=True)
class ResponseModel:
    name: str
    response_types: tuple[tuple[ResponseType, Fraction], ...]
    observational_x_one: Fraction = Fraction(1, 2)


@dataclass(frozen=True)
class CrossWorldResult:
    name: str
    passed: bool
    detail: str


def _validate_probability(value: Fraction, *, field: str) -> None:
    if not isinstance(value, Fraction):
        raise TypeError(f"{field} must be fractions.Fraction")
    if value < 0 or value > 1:
        raise ValueError(f"{field} must lie in [0, 1]")


def validate_response_model(model: ResponseModel) -> None:
    _validate_probability(model.observational_x_one, field="observational_x_one")
    if not model.response_types:
        raise ValueError("response model must contain at least one response type")

    labels: set[str] = set()
    total = Fraction(0)
    for response_type, mass in model.response_types:
        if not response_type.label:
            raise ValueError("response type label must be non-empty")
        if response_type.label in labels:
            raise ValueError("response type labels must be unique")
        labels.add(response_type.label)
        if response_type.y0 not in {"0", "1"} or response_type.y1 not in {"0", "1"}:
            raise ValueError("potential outcomes must be binary")
        _validate_probability(mass, field="response-type mass")
        total += mass
    if total != 1:
        raise ValueError("response-type masses must sum exactly to 1")


def _binary_mass(probability_one: Fraction) -> tuple[tuple[str, Fraction], ...]:
    _validate_probability(probability_one, field="binary probability")
    return (("0", 1 - probability_one), ("1", probability_one))


def _canonical_law(weights: Mapping[Assignment, Fraction]) -> JointLaw:
    cleaned = tuple(
        sorted(
            ((assignment, mass) for assignment, mass in weights.items() if mass),
            key=repr,
        )
    )
    if not cleaned or sum((mass for _, mass in cleaned), Fraction(0)) != 1:
        raise ValueError("joint law must normalize exactly")
    return cleaned


def _response_value(response_type: ResponseType, x_value: str) -> str:
    if x_value == "0":
        return response_type.y0
    if x_value == "1":
        return response_type.y1
    raise ValueError("X must be binary")


def _law_with_x_source(model: ResponseModel, x_one: Fraction) -> JointLaw:
    """Evaluate one world with an exogenous Bernoulli X replacement/source."""
    validate_response_model(model)
    _validate_probability(x_one, field="X probability")
    weights: dict[Assignment, Fraction] = {}
    for x_value, x_mass in _binary_mass(x_one):
        for response_type, type_mass in model.response_types:
            y_value = _response_value(response_type, x_value)
            assignment = (("X", x_value), ("Y", y_value))
            weights[assignment] = weights.get(assignment, Fraction(0)) + x_mass * type_mass
    return _canonical_law(weights)


def observational_law(model: ResponseModel) -> JointLaw:
    return _law_with_x_source(model, model.observational_x_one)


def hard_intervention_law(model: ResponseModel, target: str, value: str) -> JointLaw:
    validate_response_model(model)
    if value not in {"0", "1"}:
        raise ValueError("hard intervention value must be binary")
    if target == "X":
        return _law_with_x_source(model, Fraction(int(value)))
    if target != "Y":
        raise ValueError(f"unknown intervention target {target!r}")

    weights: dict[Assignment, Fraction] = {}
    for x_value, x_mass in _binary_mass(model.observational_x_one):
        assignment = (("X", x_value), ("Y", value))
        weights[assignment] = weights.get(assignment, Fraction(0)) + x_mass
    return _canonical_law(weights)


def soft_intervention_law(
    model: ResponseModel, target: str, probability_one: Fraction
) -> JointLaw:
    """Replace X or Y by an exact Bernoulli root in one world."""
    validate_response_model(model)
    _validate_probability(probability_one, field="soft intervention probability")
    if target == "X":
        return _law_with_x_source(model, probability_one)
    if target != "Y":
        raise ValueError(f"unknown intervention target {target!r}")

    weights: dict[Assignment, Fraction] = {}
    for x_value, x_mass in _binary_mass(model.observational_x_one):
        for y_value, y_mass in _binary_mass(probability_one):
            assignment = (("X", x_value), ("Y", y_value))
            weights[assignment] = weights.get(assignment, Fraction(0)) + x_mass * y_mass
    return _canonical_law(weights)


def _all_assignments() -> tuple[Assignment, ...]:
    return tuple(
        (("X", x_value), ("Y", y_value))
        for x_value in ("0", "1")
        for y_value in ("0", "1")
    )


def affine_soft_signature(model: ResponseModel, target: str) -> AffineSignature:
    """Encode the entire Bernoulli(q) soft-intervention family symbolically.

    Every assignment mass is affine in q. Returning its exact constant and slope
    proves equality for all q once these coefficients match; no finite q sweep is
    misrepresented as exhaustion of a continuous/rational intervention family.
    """
    law_zero = dict(soft_intervention_law(model, target, Fraction(0)))
    law_one = dict(soft_intervention_law(model, target, Fraction(1)))
    return tuple(
        (
            assignment,
            law_zero.get(assignment, Fraction(0)),
            law_one.get(assignment, Fraction(0))
            - law_zero.get(assignment, Fraction(0)),
        )
        for assignment in _all_assignments()
    )


def hard_single_world_signature(
    model: ResponseModel,
) -> tuple[tuple[tuple[str, str], JointLaw], ...]:
    return tuple(
        ((target, value), hard_intervention_law(model, target, value))
        for target in ("X", "Y")
        for value in ("0", "1")
    )


def single_world_signature(model: ResponseModel) -> tuple[object, ...]:
    return (
        observational_law(model),
        hard_single_world_signature(model),
        affine_soft_signature(model, "X"),
        affine_soft_signature(model, "Y"),
    )


def same_unit_counterfactual_joint(model: ResponseModel) -> PotentialPairLaw:
    """Couple Y_0 and Y_1 by reusing the same declared response type."""
    validate_response_model(model)
    weights: dict[tuple[str, str], Fraction] = {}
    for response_type, mass in model.response_types:
        pair = (response_type.y0, response_type.y1)
        weights[pair] = weights.get(pair, Fraction(0)) + mass
    return tuple(sorted(((pair, mass) for pair, mass in weights.items() if mass), key=repr))


def potential_outcome_marginal(model: ResponseModel, x_value: str) -> tuple[tuple[str, Fraction], ...]:
    if x_value not in {"0", "1"}:
        raise ValueError("potential-outcome intervention must be binary")
    weights = {"0": Fraction(0), "1": Fraction(0)}
    for response_type, mass in model.response_types:
        weights[_response_value(response_type, x_value)] += mass
    return tuple((value, mass) for value, mass in sorted(weights.items()) if mass)


def independent_world_counterfactual_joint(model: ResponseModel) -> PotentialPairLaw:
    """Anti-model: redraw the response type independently in each world."""
    y0 = dict(potential_outcome_marginal(model, "0"))
    y1 = dict(potential_outcome_marginal(model, "1"))
    return tuple(
        ((left, right), y0.get(left, Fraction(0)) * y1.get(right, Fraction(0)))
        for left in ("0", "1")
        for right in ("0", "1")
        if y0.get(left, Fraction(0)) * y1.get(right, Fraction(0))
    )


def counterfactual_equality_probability(model: ResponseModel) -> Fraction:
    return sum(
        (mass for (y0, y1), mass in same_unit_counterfactual_joint(model) if y0 == y1),
        Fraction(0),
    )


def cross_world_signature(model: ResponseModel) -> tuple[object, ...]:
    return single_world_signature(model), same_unit_counterfactual_joint(model)


def frame_signature(model: ResponseModel, frame: Frame) -> tuple[object, ...]:
    if frame == "single_world":
        return single_world_signature(model)
    if frame == "cross_world":
        return cross_world_signature(model)
    raise ValueError(f"unknown frame {frame!r}")


def behavior_equivalent(left: ResponseModel, right: ResponseModel, frame: Frame) -> bool:
    return frame_signature(left, frame) == frame_signature(right, frame)


def rename_response_type_labels(
    model: ResponseModel, labels: Mapping[str, str], *, name: str
) -> ResponseModel:
    renamed = tuple(
        (replace(response_type, label=labels.get(response_type.label, response_type.label)), mass)
        for response_type, mass in model.response_types
    )
    result = replace(model, name=name, response_types=renamed)
    validate_response_model(result)
    return result


def downstream_copy_single_world_signature(model: ResponseModel) -> tuple[object, ...]:
    """Apply the same deterministic downstream Z := Y context to all one-world laws."""

    def add_z(law: JointLaw) -> tuple[tuple[Assignment, Fraction], ...]:
        return tuple(
            (
                tuple(sorted((*assignment, ("Z", dict(assignment)["Y"])))),
                mass,
            )
            for assignment, mass in law
        )

    observation = add_z(observational_law(model))
    hard = tuple((key, add_z(law)) for key, law in hard_single_world_signature(model))
    soft_samples = tuple(
        (
            (target, q),
            add_z(soft_intervention_law(model, target, q)),
        )
        for target in ("X", "Y")
        for q in (Fraction(1, 4), Fraction(3, 4))
    )
    return observation, hard, soft_samples


def downstream_copy_counterfactual_joint(model: ResponseModel) -> tuple[tuple[tuple[str, str], Fraction], ...]:
    """Z := Y inherits exactly the Y_0/Y_1 same-unit coupling."""
    return same_unit_counterfactual_joint(model)


def behavior_partition(
    models: Sequence[ResponseModel], frame: Frame
) -> dict[str, str]:
    names = [model.name for model in models]
    if len(names) != len(set(names)):
        raise ValueError("model names must be unique")

    signatures: list[tuple[object, ...]] = []
    partition: dict[str, str] = {}
    for model in models:
        signature = frame_signature(model, frame)
        try:
            index = signatures.index(signature)
        except ValueError:
            signatures.append(signature)
            index = len(signatures) - 1
        partition[model.name] = f"b{index}"
    return partition


def partition_is_representative_independent(
    models: Sequence[ResponseModel], partition: Mapping[str, str], frame: Frame
) -> bool:
    by_name = {model.name: model for model in models}
    if set(partition) != set(by_name):
        raise ValueError("partition must name every model exactly once")
    for block in set(partition.values()):
        members = [by_name[name] for name, value in partition.items() if value == block]
        reference = frame_signature(members[0], frame)
        if any(frame_signature(candidate, frame) != reference for candidate in members[1:]):
            return False
    return True


def invariant_response_model(name: str = "invariant") -> ResponseModel:
    return ResponseModel(
        name,
        (
            (ResponseType("u0", "0", "0"), Fraction(1, 2)),
            (ResponseType("u1", "1", "1"), Fraction(1, 2)),
        ),
    )


def flip_response_model(name: str = "flip") -> ResponseModel:
    return ResponseModel(
        name,
        (
            (ResponseType("u0", "0", "1"), Fraction(1, 2)),
            (ResponseType("u1", "1", "0"), Fraction(1, 2)),
        ),
    )


def run_cross_world_coupling_comparison() -> tuple[CrossWorldResult, ...]:
    invariant = invariant_response_model()
    flip = flip_response_model()
    renamed = rename_response_type_labels(
        invariant,
        {"u0": "alpha", "u1": "beta"},
        name="renamed-invariant",
    )

    observational = observational_law(invariant) == observational_law(flip)
    hard = hard_single_world_signature(invariant) == hard_single_world_signature(flip)
    soft_symbolic = (
        affine_soft_signature(invariant, "X") == affine_soft_signature(flip, "X")
        and affine_soft_signature(invariant, "Y") == affine_soft_signature(flip, "Y")
    )
    marginals = (
        potential_outcome_marginal(invariant, "0") == potential_outcome_marginal(flip, "0")
        and potential_outcome_marginal(invariant, "1") == potential_outcome_marginal(flip, "1")
    )
    coupling = (
        same_unit_counterfactual_joint(invariant) != same_unit_counterfactual_joint(flip)
        and counterfactual_equality_probability(invariant) == 1
        and counterfactual_equality_probability(flip) == 0
    )
    alignment = (
        independent_world_counterfactual_joint(invariant)
        == independent_world_counterfactual_joint(flip)
        and independent_world_counterfactual_joint(invariant)
        != same_unit_counterfactual_joint(invariant)
    )
    frame_relative = (
        behavior_equivalent(invariant, flip, "single_world")
        and not behavior_equivalent(invariant, flip, "cross_world")
    )
    label_gauge = behavior_equivalent(invariant, renamed, "cross_world")
    composition = (
        downstream_copy_single_world_signature(invariant)
        == downstream_copy_single_world_signature(flip)
        and downstream_copy_counterfactual_joint(invariant)
        != downstream_copy_counterfactual_joint(flip)
    )

    models = (invariant, renamed, flip)
    single_partition = behavior_partition(models, "single_world")
    cross_partition = behavior_partition(models, "cross_world")
    quotient = (
        single_partition[invariant.name] == single_partition[flip.name]
        and cross_partition[invariant.name] == cross_partition[renamed.name]
        and cross_partition[invariant.name] != cross_partition[flip.name]
        and partition_is_representative_independent(
            models, single_partition, "single_world"
        )
        and partition_is_representative_independent(
            models, cross_partition, "cross_world"
        )
    )

    return (
        CrossWorldResult(
            "OBSERVATIONAL_LAW_MATCHES",
            observational,
            "both response models induce the same exact intact P(X,Y)",
        ),
        CrossWorldResult(
            "COMPLETE_BINARY_HARD_INTERVENTION_FAMILY_MATCHES",
            hard,
            "all declared do(X=x) and do(Y=y) one-world laws agree exactly",
        ),
        CrossWorldResult(
            "ENTIRE_BERNOULLI_SOFT_INTERVENTION_FAMILY_MATCHES_SYMBOLICALLY",
            soft_symbolic,
            "exact affine coefficients match for every Bernoulli(q) X/Y root replacement",
        ),
        CrossWorldResult(
            "POTENTIAL_OUTCOME_MARGINALS_MATCH",
            marginals,
            "Y_0 and Y_1 are both fair in both models",
        ),
        CrossWorldResult(
            "SAME_UNIT_CROSS_WORLD_COUPLING_DIFFERS",
            coupling,
            "P(Y_0=Y_1) is exactly one versus zero under shared response-type alignment",
        ),
        CrossWorldResult(
            "UNIT_ALIGNMENT_IS_OPERATIONAL_STRUCTURE",
            alignment,
            "redrawing response type independently erases the discriminator that same-unit reuse preserves",
        ),
        CrossWorldResult(
            "COUPLING_IS_GAUGE_ONLY_IN_SINGLE_WORLD_FRAME",
            frame_relative,
            "the models quotient under one-world probes and separate once cross-world probes are admitted",
        ),
        CrossWorldResult(
            "RESPONSE_TYPE_LABELS_ARE_GAUGE",
            label_gauge,
            "latent labels can rename without changing aligned response behavior",
        ),
        CrossWorldResult(
            "DOWNSTREAM_CONTEXT_PRESERVES_FRAME_RELATIVE_DISTINCTION",
            composition,
            "Z := Y preserves one-world equivalence and inherits the cross-world split",
        ),
        CrossWorldResult(
            "FRAME_RELATIVE_QUOTIENTS_ARE_REPRESENTATIVE_INDEPENDENT",
            quotient,
            "each exact quotient preserves every query declared by its own frame",
        ),
    )
