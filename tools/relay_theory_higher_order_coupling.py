"""Exact finite higher-order cross-world coupling apparatus for Relay Theory #2374.

Research falsification only. This graph-free fixture asks whether all singleton and
pairwise marginals determine a three-world joint. It deliberately uses exact finite
probability laws and frame-relative quotients; no n-world ontology, counterfactual
store, or projective-family primitive is assumed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from typing import Literal

Outcome = tuple[str, ...]
JointLaw = tuple[tuple[Outcome, Fraction], ...]
MarginalLaw = tuple[tuple[Outcome, Fraction], ...]
Frame = Literal["pairwise", "triple"]


@dataclass(frozen=True)
class MultiWorldModel:
    name: str
    worlds: tuple[str, ...]
    joint: JointLaw


@dataclass(frozen=True)
class HigherOrderResult:
    name: str
    passed: bool
    detail: str


def validate_multi_world_model(model: MultiWorldModel) -> None:
    if len(model.worlds) != 3:
        raise ValueError("bounded #2374 fixture requires exactly three worlds")
    if len(set(model.worlds)) != len(model.worlds):
        raise ValueError("world labels must be unique")
    if not model.joint:
        raise ValueError("joint law must contain at least one outcome")

    seen: set[Outcome] = set()
    total = Fraction(0)
    for outcome, mass in model.joint:
        if len(outcome) != len(model.worlds):
            raise ValueError("outcome arity must match world arity")
        if any(value not in {"0", "1"} for value in outcome):
            raise ValueError("bounded outcomes must be binary")
        if outcome in seen:
            raise ValueError("joint outcomes must be unique")
        seen.add(outcome)
        if not isinstance(mass, Fraction):
            raise TypeError("joint probability mass must be fractions.Fraction")
        if mass < 0 or mass > 1:
            raise ValueError("joint probability mass must lie in [0, 1]")
        total += mass
    if total != 1:
        raise ValueError("joint probability mass must sum exactly to 1")


def _canonical_law(weights: Mapping[Outcome, Fraction]) -> MarginalLaw:
    cleaned = tuple(
        sorted(
            ((outcome, mass) for outcome, mass in weights.items() if mass),
            key=repr,
        )
    )
    if not cleaned:
        raise ValueError("marginal law must contain positive mass")
    if sum((mass for _, mass in cleaned), Fraction(0)) != 1:
        raise ValueError("marginal law must normalize exactly")
    return cleaned


def marginal(model: MultiWorldModel, subset: Sequence[str]) -> MarginalLaw:
    """Project the exact full joint to an ordered declared world subset."""
    validate_multi_world_model(model)
    subset_tuple = tuple(subset)
    if not subset_tuple:
        raise ValueError("marginal subset must be non-empty")
    if len(subset_tuple) != len(set(subset_tuple)):
        raise ValueError("marginal subset labels must be unique")

    index_by_world = {world: index for index, world in enumerate(model.worlds)}
    unknown = [world for world in subset_tuple if world not in index_by_world]
    if unknown:
        raise ValueError(f"unknown marginal worlds: {unknown}")

    indices = tuple(index_by_world[world] for world in subset_tuple)
    weights: dict[Outcome, Fraction] = {}
    for outcome, mass in model.joint:
        projected = tuple(outcome[index] for index in indices)
        weights[projected] = weights.get(projected, Fraction(0)) + mass
    return _canonical_law(weights)


def singleton_signature(model: MultiWorldModel) -> tuple[tuple[str, MarginalLaw], ...]:
    return tuple((world, marginal(model, (world,))) for world in model.worlds)


def pairwise_signature(
    model: MultiWorldModel,
) -> tuple[tuple[tuple[str, str], MarginalLaw], ...]:
    return tuple(
        ((left, right), marginal(model, (left, right)))
        for left, right in combinations(model.worlds, 2)
    )


def lower_arity_signature(model: MultiWorldModel) -> tuple[object, ...]:
    return singleton_signature(model), pairwise_signature(model)


def full_signature(model: MultiWorldModel) -> tuple[object, ...]:
    validate_multi_world_model(model)
    return lower_arity_signature(model), model.joint


def frame_signature(model: MultiWorldModel, frame: Frame) -> tuple[object, ...]:
    if frame == "pairwise":
        return lower_arity_signature(model)
    if frame == "triple":
        return full_signature(model)
    raise ValueError(f"unknown frame {frame!r}")


def behavior_equivalent(left: MultiWorldModel, right: MultiWorldModel, frame: Frame) -> bool:
    return frame_signature(left, frame) == frame_signature(right, frame)


def uniform_pair_law() -> MarginalLaw:
    quarter = Fraction(1, 4)
    return (
        (("0", "0"), quarter),
        (("0", "1"), quarter),
        (("1", "0"), quarter),
        (("1", "1"), quarter),
    )


def fair_single_law() -> MarginalLaw:
    half = Fraction(1, 2)
    return (("0", half), ("1", half))


def all_pairs_are_independent_fair(model: MultiWorldModel) -> bool:
    return all(law == uniform_pair_law() for _, law in pairwise_signature(model))


def parity_probability(model: MultiWorldModel, parity: int) -> Fraction:
    validate_multi_world_model(model)
    if parity not in {0, 1}:
        raise ValueError("parity must be 0 or 1")
    return sum(
        (
            mass
            for outcome, mass in model.joint
            if sum(int(value) for value in outcome) % 2 == parity
        ),
        Fraction(0),
    )


def even_parity_model(name: str = "even") -> MultiWorldModel:
    quarter = Fraction(1, 4)
    return MultiWorldModel(
        name,
        ("Y0", "Y1", "Y2"),
        (
            (("0", "0", "0"), quarter),
            (("0", "1", "1"), quarter),
            (("1", "0", "1"), quarter),
            (("1", "1", "0"), quarter),
        ),
    )


def odd_parity_model(name: str = "odd") -> MultiWorldModel:
    quarter = Fraction(1, 4)
    return MultiWorldModel(
        name,
        ("Y0", "Y1", "Y2"),
        (
            (("0", "0", "1"), quarter),
            (("0", "1", "0"), quarter),
            (("1", "0", "0"), quarter),
            (("1", "1", "1"), quarter),
        ),
    )


def rename_worlds(
    model: MultiWorldModel,
    mapping: Mapping[str, str],
    *,
    name: str,
) -> MultiWorldModel:
    validate_multi_world_model(model)
    if set(mapping) != set(model.worlds):
        raise ValueError("world rename mapping must cover every world exactly once")
    renamed_worlds = tuple(mapping[world] for world in model.worlds)
    if len(set(renamed_worlds)) != len(renamed_worlds):
        raise ValueError("renamed world labels must be unique")
    result = MultiWorldModel(name, renamed_worlds, model.joint)
    validate_multi_world_model(result)
    return result


def world_renaming_equivalent(
    source: MultiWorldModel,
    target: MultiWorldModel,
    mapping: Mapping[str, str],
) -> bool:
    """Compare two models under an explicit transported world-coordinate map."""
    validate_multi_world_model(source)
    validate_multi_world_model(target)
    if set(mapping) != set(source.worlds):
        return False
    if tuple(mapping[world] for world in source.worlds) != target.worlds:
        return False
    return source.joint == target.joint


def downstream_copy_model(model: MultiWorldModel, *, name: str) -> MultiWorldModel:
    """Bounded deterministic context Zi := Yi, represented by coordinate transport."""
    mapping = {world: f"Z{index}" for index, world in enumerate(model.worlds)}
    return rename_worlds(model, mapping, name=name)


def behavior_partition(
    models: Sequence[MultiWorldModel], frame: Frame
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
    models: Sequence[MultiWorldModel],
    partition: Mapping[str, str],
    frame: Frame,
) -> bool:
    by_name = {model.name: model for model in models}
    if set(partition) != set(by_name):
        raise ValueError("partition must name every model exactly once")
    for block in set(partition.values()):
        members = [by_name[name] for name, value in partition.items() if value == block]
        reference = frame_signature(members[0], frame)
        if any(
            frame_signature(candidate, frame) != reference for candidate in members[1:]
        ):
            return False
    return True


def run_higher_order_coupling_comparison() -> tuple[HigherOrderResult, ...]:
    even = even_parity_model()
    odd = odd_parity_model()
    renamed_even = rename_worlds(
        even,
        {"Y0": "A", "Y1": "B", "Y2": "C"},
        name="renamed-even",
    )

    singles = (
        singleton_signature(even) == singleton_signature(odd)
        and all(law == fair_single_law() for _, law in singleton_signature(even))
    )
    pairs = pairwise_signature(even) == pairwise_signature(odd)
    pairwise_independence = (
        all_pairs_are_independent_fair(even) and all_pairs_are_independent_fair(odd)
    )
    triple = (
        even.joint != odd.joint
        and parity_probability(even, 0) == 1
        and parity_probability(odd, 0) == 0
    )
    frame_relative = (
        behavior_equivalent(even, odd, "pairwise")
        and not behavior_equivalent(even, odd, "triple")
    )
    rename_gauge = world_renaming_equivalent(
        even,
        renamed_even,
        {"Y0": "A", "Y1": "B", "Y2": "C"},
    )
    projection_consistency = all(
        marginal(even, subset) == marginal(odd, subset)
        for subset in (
            ("Y0",),
            ("Y1",),
            ("Y2",),
            ("Y0", "Y1"),
            ("Y0", "Y2"),
            ("Y1", "Y2"),
        )
    )

    even_z = downstream_copy_model(even, name="even-z")
    odd_z = downstream_copy_model(odd, name="odd-z")
    context = (
        behavior_equivalent(even_z, odd_z, "pairwise")
        and not behavior_equivalent(even_z, odd_z, "triple")
        and parity_probability(even_z, 0) == 1
        and parity_probability(odd_z, 0) == 0
    )

    even_clone = MultiWorldModel("even-clone", even.worlds, even.joint)
    models = (even, even_clone, odd)
    pair_partition = behavior_partition(models, "pairwise")
    triple_partition = behavior_partition(models, "triple")
    quotient = (
        pair_partition[even.name] == pair_partition[odd.name]
        and triple_partition[even.name] == triple_partition[even_clone.name]
        and triple_partition[even.name] != triple_partition[odd.name]
        and partition_is_representative_independent(models, pair_partition, "pairwise")
        and partition_is_representative_independent(models, triple_partition, "triple")
    )

    return (
        HigherOrderResult(
            "ALL_SINGLETON_MARGINALS_MATCH",
            singles,
            "every world is exactly fair in both parity models",
        ),
        HigherOrderResult(
            "ALL_PAIRWISE_JOINTS_MATCH",
            pairs,
            "all three two-world marginals are exactly identical",
        ),
        HigherOrderResult(
            "EVERY_PAIR_IS_INDEPENDENT_FAIR",
            pairwise_independence,
            "each pair is uniform despite deterministic third-order parity structure",
        ),
        HigherOrderResult(
            "TRIPLE_PARITY_DISTINGUISHES_FULL_JOINT",
            triple,
            "even parity has probability one versus zero for the same triple probe",
        ),
        HigherOrderResult(
            "EQUIVALENCE_IS_ARITY_RELATIVE",
            frame_relative,
            "the models quotient under singleton/pairwise probes and split under a triple frame",
        ),
        HigherOrderResult(
            "WORLD_LABEL_RENAMING_IS_GAUGE_UNDER_EXPLICIT_TRANSPORT",
            rename_gauge,
            "coordinate labels may rename when the joint and frame are transported consistently",
        ),
        HigherOrderResult(
            "LOWER_ARITY_SIGNATURES_ARE_DERIVED_FROM_FULL_JOINT",
            projection_consistency,
            "all pairwise-frame laws are exact marginals of the same full models",
        ),
        HigherOrderResult(
            "DOWNSTREAM_COPY_PRESERVES_ARITY_RELATIVE_DISTINCTION",
            context,
            "Zi := Yi retains pairwise equivalence and the triple parity split",
        ),
        HigherOrderResult(
            "PAIRWISE_AND_TRIPLE_QUOTIENTS_ARE_REPRESENTATIVE_INDEPENDENT",
            quotient,
            "each frame preserves every exact query admitted by its own signature",
        ),
    )
