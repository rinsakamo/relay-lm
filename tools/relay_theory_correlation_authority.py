"""Exact finite correlation-authority Grand Null apparatus for Relay Theory #2361.

Research falsification only. This is not RelayLM runtime or architecture
authority. The bounded model attacks the anonymous control-domain residue earned
by #2357 and asks whether it reduces to admissible joint interventions,
correlation resources, information flow, and conditional write constraints.

The implementation deliberately distinguishes independent local randomization
from convex closure. Convexifying independent product laws would itself add an
external correlating device and would therefore beg the question under test.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Literal

from tools.relay_theory_scheduler_nondeterminism import (
    Distribution,
    exact_convex_hulls_equal,
    exact_distribution,
    in_exact_convex_hull,
    probability,
)

Closure = Literal["discrete", "convex"]
ControlPartition = tuple[tuple[str, ...], ...]
ReadEdges = tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class InterventionFamily:
    """Finite generators plus declared closure semantics."""

    name: str
    generators: tuple[Distribution, ...]
    closure: Closure = "convex"


@dataclass(frozen=True)
class ResourceDescription:
    """One implementation description of the same operational interface."""

    name: str
    control_partition: ControlPartition
    family: InterventionFamily
    read_edges: ReadEdges = ()
    causal_stages: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class ConditionalFamily:
    """History/context-indexed admissible joint intervention family."""

    name: str
    by_context: tuple[tuple[str, InterventionFamily], ...]


@dataclass(frozen=True)
class CorrelationResult:
    name: str
    passed: bool
    detail: str


def _validate_distribution(distribution: Distribution) -> Distribution:
    return exact_distribution(dict(distribution))


def joint_outcome(left: str, right: str) -> str:
    if left not in {"0", "1"} or right not in {"0", "1"}:
        raise ValueError("bounded joint outcomes require binary actions '0' or '1'")
    return f"{left}{right}"


def _split_joint(outcome: str) -> tuple[str, str]:
    if len(outcome) != 2 or any(value not in {"0", "1"} for value in outcome):
        raise ValueError(f"invalid bounded joint outcome {outcome!r}")
    return outcome[0], outcome[1]


def binary_distribution(p_one: Fraction) -> Distribution:
    if not isinstance(p_one, Fraction):
        raise TypeError("binary probability must be fractions.Fraction")
    if p_one < 0 or p_one > 1:
        raise ValueError("binary probability must lie in [0, 1]")
    return exact_distribution({"0": 1 - p_one, "1": p_one})


def deterministic_joint(left: str, right: str) -> Distribution:
    return exact_distribution({joint_outcome(left, right): Fraction(1)})


def joint_vertices() -> tuple[Distribution, ...]:
    return tuple(
        deterministic_joint(left, right)
        for left, right in product(("0", "1"), repeat=2)
    )


def independent_joint(
    left: Distribution,
    right: Distribution,
) -> Distribution:
    left = _validate_distribution(left)
    right = _validate_distribution(right)
    if any(outcome not in {"0", "1"} for outcome, _ in left + right):
        raise ValueError("independent_joint expects binary marginal distributions")

    mass: dict[str, Fraction] = {}
    for left_action, left_mass in left:
        for right_action, right_mass in right:
            outcome = joint_outcome(left_action, right_action)
            mass[outcome] = mass.get(outcome, Fraction(0)) + left_mass * right_mass
    return exact_distribution(mass)


def joint_marginal(distribution: Distribution, index: int) -> Distribution:
    if index not in {0, 1}:
        raise ValueError("joint marginal index must be 0 or 1")
    distribution = _validate_distribution(distribution)
    mass = {"0": Fraction(0), "1": Fraction(0)}
    for outcome, probability_mass in distribution:
        action = _split_joint(outcome)[index]
        mass[action] += probability_mass
    return exact_distribution(mass)


def match_probability(distribution: Distribution) -> Fraction:
    distribution = _validate_distribution(distribution)
    return sum(
        (
            probability_mass
            for outcome, probability_mass in distribution
            if _split_joint(outcome)[0] == _split_joint(outcome)[1]
        ),
        Fraction(0),
    )


def shared_fair_bit_joint() -> Distribution:
    return exact_distribution({"00": Fraction(1, 2), "11": Fraction(1, 2)})


def is_independent_binary_joint(distribution: Distribution) -> bool:
    """Exact 2x2 rank-one discriminator for binary product distributions."""
    distribution = _validate_distribution(distribution)
    mass = dict(distribution)
    p00 = mass.get("00", Fraction(0))
    p01 = mass.get("01", Fraction(0))
    p10 = mass.get("10", Fraction(0))
    p11 = mass.get("11", Fraction(0))
    for outcome in mass:
        _split_joint(outcome)
    return p00 * p11 == p01 * p10


def validate_family(family: InterventionFamily) -> None:
    if family.closure not in {"discrete", "convex"}:
        raise ValueError(f"unknown intervention closure {family.closure!r}")
    if not family.generators:
        raise ValueError("intervention family must contain at least one generator")
    for generator in family.generators:
        _validate_distribution(generator)


def family_contains(family: InterventionFamily, law: Distribution) -> bool:
    validate_family(family)
    law = _validate_distribution(law)
    generators = tuple(_validate_distribution(item) for item in family.generators)
    if family.closure == "discrete":
        return law in generators
    return in_exact_convex_hull(law, generators)


def intervention_families_equivalent(
    left: InterventionFamily,
    right: InterventionFamily,
) -> bool:
    validate_family(left)
    validate_family(right)
    left_generators = tuple(_validate_distribution(item) for item in left.generators)
    right_generators = tuple(_validate_distribution(item) for item in right.generators)
    if left.closure != right.closure:
        return False
    if left.closure == "discrete":
        return set(left_generators) == set(right_generators)
    return exact_convex_hulls_equal(left_generators, right_generators)


def resolve_convex_family(
    family: InterventionFamily,
    weights: Mapping[int, Fraction],
) -> Distribution:
    """Resolve a declared convex family into one exact stochastic joint law."""
    validate_family(family)
    if family.closure != "convex":
        raise ValueError("only convex families admit randomized generator weights")
    if not weights:
        raise ValueError("resolution must assign at least one generator weight")
    unknown = set(weights) - set(range(len(family.generators)))
    if unknown:
        raise ValueError(f"unknown generator indices: {sorted(unknown)}")

    total = Fraction(0)
    mass: dict[str, Fraction] = {}
    for index, weight in weights.items():
        if not isinstance(weight, Fraction):
            raise TypeError("resolution weights must be fractions.Fraction")
        if weight < 0 or weight > 1:
            raise ValueError("resolution weights must lie in [0, 1]")
        total += weight
        for outcome, probability_mass in _validate_distribution(
            family.generators[index]
        ):
            mass[outcome] = mass.get(outcome, Fraction(0)) + weight * probability_mass
    if total != 1:
        raise ValueError("resolution weights must sum exactly to 1")
    return exact_distribution(mass)


def full_joint_family(name: str) -> InterventionFamily:
    """All binary joint laws via convex mixtures of deterministic joint plans."""
    return InterventionFamily(name, joint_vertices(), "convex")


def private_fair_randomizers_joint() -> Distribution:
    fair = binary_distribution(Fraction(1, 2))
    return independent_joint(fair, fair)


def best_remote_guess_probability(
    *,
    can_read_hidden: bool,
    shared_seed: bool,
) -> Fraction:
    """Enumerate exact deterministic policies for a fair hidden bit.

    Hidden bit H is fair. When ``shared_seed`` is true, an independent fair
    common seed R is also available. The remote output may depend on R and,
    only when explicitly allowed, on H. This separates common randomness from
    a communication/information edge.
    """
    hidden_values = ("0", "1")
    seed_values = ("0", "1") if shared_seed else ("unit",)
    inputs = tuple(
        (hidden, seed) if can_read_hidden else (seed,)
        for hidden in hidden_values
        for seed in seed_values
    )
    information_sets = tuple(sorted(set(inputs), key=repr))

    best = Fraction(0)
    for choices in product(("0", "1"), repeat=len(information_sets)):
        policy = dict(zip(information_sets, choices, strict=True))
        success = Fraction(0)
        atom_mass = Fraction(1, len(hidden_values) * len(seed_values))
        for hidden in hidden_values:
            for seed in seed_values:
                key = (hidden, seed) if can_read_hidden else (seed,)
                if policy[key] == hidden:
                    success += atom_mass
        best = max(best, success)
    return best


def canonical_control_partition(
    partition: Sequence[Sequence[str]],
) -> ControlPartition:
    blocks = tuple(sorted((tuple(sorted(block)) for block in partition)))
    flattened = [port for block in blocks for port in block]
    if not blocks or any(not block for block in blocks):
        raise ValueError("control partition blocks must be non-empty")
    if len(flattened) != len(set(flattened)):
        raise ValueError("each port may occur in only one control block")
    return blocks


def validate_resource_description(description: ResourceDescription) -> None:
    validate_family(description.family)
    canonical_control_partition(description.control_partition)
    if len(set(description.read_edges)) != len(description.read_edges):
        raise ValueError("read edges must be unique")
    if len(dict(description.causal_stages)) != len(description.causal_stages):
        raise ValueError("causal stage ports must be unique")


def resource_operationally_equivalent(
    left: ResourceDescription,
    right: ResourceDescription,
) -> bool:
    """Forget nominal control partition after joint intervention power is explicit."""
    validate_resource_description(left)
    validate_resource_description(right)
    return (
        intervention_families_equivalent(left.family, right.family)
        and tuple(sorted(left.read_edges)) == tuple(sorted(right.read_edges))
        and tuple(sorted(left.causal_stages)) == tuple(sorted(right.causal_stages))
    )


def resource_behavior_partition(
    descriptions: Sequence[ResourceDescription],
) -> dict[str, str]:
    if len({description.name for description in descriptions}) != len(descriptions):
        raise ValueError("resource description names must be unique")
    representatives: list[ResourceDescription] = []
    partition: dict[str, str] = {}
    for description in descriptions:
        validate_resource_description(description)
        block: str | None = None
        for index, representative in enumerate(representatives):
            if resource_operationally_equivalent(description, representative):
                block = f"b{index}"
                break
        if block is None:
            representatives.append(description)
            block = f"b{len(representatives) - 1}"
        partition[description.name] = block
    return partition


def resource_partition_is_representative_independent(
    descriptions: Sequence[ResourceDescription],
    partition: Mapping[str, str],
) -> bool:
    by_name = {description.name: description for description in descriptions}
    if set(partition) != set(by_name):
        raise ValueError("partition must name every resource description")
    for block in set(partition.values()):
        members = [by_name[name] for name, value in partition.items() if value == block]
        reference = members[0]
        if any(
            not resource_operationally_equivalent(reference, candidate)
            for candidate in members[1:]
        ):
            return False
    return True


def validate_conditional_family(conditional: ConditionalFamily) -> None:
    if not conditional.by_context:
        raise ValueError("conditional family must declare at least one context")
    contexts = [context for context, _ in conditional.by_context]
    if len(contexts) != len(set(contexts)):
        raise ValueError("conditional family contexts must be unique")
    for _, family in conditional.by_context:
        validate_family(family)


def conditional_best_target_probability(
    conditional: ConditionalFamily,
    context_probability: Mapping[str, Fraction],
    target_outcome: Mapping[str, str],
) -> Fraction:
    """Best linear target probability with context-visible admissible families."""
    validate_conditional_family(conditional)
    families = dict(conditional.by_context)
    if set(context_probability) != set(families):
        raise ValueError("context probabilities must match conditional contexts")
    if set(target_outcome) != set(families):
        raise ValueError("target outcomes must match conditional contexts")

    total_context_mass = Fraction(0)
    result = Fraction(0)
    for context, context_mass in context_probability.items():
        if not isinstance(context_mass, Fraction):
            raise TypeError("context probabilities must be fractions.Fraction")
        if context_mass < 0 or context_mass > 1:
            raise ValueError("context probabilities must lie in [0, 1]")
        total_context_mass += context_mass
        family = families[context]
        target = target_outcome[context]
        best = max(probability(generator, target) for generator in family.generators)
        result += context_mass * best
    if total_context_mass != 1:
        raise ValueError("context probabilities must sum exactly to 1")
    return result


def tensor_independent(
    left: Distribution,
    right: Distribution,
) -> Distribution:
    """Independent binary parallel composition."""
    return independent_joint(left, right)


def common_cause_coupling(
    marginal: Distribution,
) -> Distribution:
    """Couple equal binary marginals by one shared common cause."""
    marginal = _validate_distribution(marginal)
    weights = dict(marginal)
    if set(weights) - {"0", "1"}:
        raise ValueError("common_cause_coupling expects a binary marginal")
    return exact_distribution(
        {
            "00": weights.get("0", Fraction(0)),
            "11": weights.get("1", Fraction(0)),
        }
    )


def run_correlation_authority_comparison() -> tuple[CorrelationResult, ...]:
    """Run the bounded #2361 C0-C9 exact falsification transaction."""
    independent_fair = private_fair_randomizers_joint()
    shared_fair = shared_fair_bit_joint()
    same_marginals = (
        joint_marginal(independent_fair, 0) == joint_marginal(shared_fair, 0)
        and joint_marginal(independent_fair, 1) == joint_marginal(shared_fair, 1)
    )
    same_marginals_lose_correlation = (
        same_marginals
        and is_independent_binary_joint(independent_fair)
        and not is_independent_binary_joint(shared_fair)
        and match_probability(independent_fair) == Fraction(1, 2)
        and match_probability(shared_fair) == 1
    )

    merged = full_joint_family("merged-joint-randomizer")
    split_common = full_joint_family("split-plus-common-source")
    common_reconstructs_joint_family = intervention_families_equivalent(
        merged, split_common
    )

    common_is_not_communication = (
        best_remote_guess_probability(can_read_hidden=False, shared_seed=True)
        == Fraction(1, 2)
        and best_remote_guess_probability(can_read_hidden=True, shared_seed=True) == 1
    )

    private_vs_shared = (
        joint_marginal(independent_fair, 0) == binary_distribution(Fraction(1, 2))
        and joint_marginal(independent_fair, 1) == binary_distribution(Fraction(1, 2))
        and joint_marginal(shared_fair, 0) == binary_distribution(Fraction(1, 2))
        and joint_marginal(shared_fair, 1) == binary_distribution(Fraction(1, 2))
        and independent_fair != shared_fair
    )

    private_information_requires_flow = common_is_not_communication

    merged_description = ResourceDescription(
        "merged",
        canonical_control_partition((("x", "y"),)),
        merged,
        causal_stages=(("x", 0), ("y", 0)),
    )
    split_correlated_description = ResourceDescription(
        "split-correlated",
        canonical_control_partition((("x",), ("y",))),
        split_common,
        causal_stages=(("x", 0), ("y", 0)),
    )
    partition_gauge_when_joint_family_matches = (
        merged_description.control_partition
        != split_correlated_description.control_partition
        and resource_operationally_equivalent(
            merged_description, split_correlated_description
        )
    )

    dynamic = ConditionalFamily(
        "dynamic",
        (
            (
                "h0",
                InterventionFamily(
                    "h0-only-00", (deterministic_joint("0", "0"),), "discrete"
                ),
            ),
            (
                "h1",
                InterventionFamily(
                    "h1-only-11", (deterministic_joint("1", "1"),), "discrete"
                ),
            ),
        ),
    )
    static = ConditionalFamily(
        "static",
        (
            (
                "h0",
                InterventionFamily(
                    "static-h0", (deterministic_joint("0", "0"),), "discrete"
                ),
            ),
            (
                "h1",
                InterventionFamily(
                    "static-h1", (deterministic_joint("0", "0"),), "discrete"
                ),
            ),
        ),
    )
    contexts = {"h0": Fraction(1, 2), "h1": Fraction(1, 2)}
    targets = {"h0": "00", "h1": "11"}
    dynamic_intervention_survives = (
        conditional_best_target_probability(dynamic, contexts, targets) == 1
        and conditional_best_target_probability(static, contexts, targets)
        == Fraction(1, 2)
    )

    fair = binary_distribution(Fraction(1, 2))
    independent_composition = tensor_independent(fair, fair)
    correlated_composition = common_cause_coupling(fair)
    correlated_composition_required = (
        joint_marginal(independent_composition, 0)
        == joint_marginal(correlated_composition, 0)
        and joint_marginal(independent_composition, 1)
        == joint_marginal(correlated_composition, 1)
        and independent_composition != correlated_composition
    )

    descriptions = (merged_description, split_correlated_description)
    quotient = resource_behavior_partition(descriptions)
    quotient_survives = (
        quotient["merged"] == quotient["split-correlated"]
        and resource_partition_is_representative_independent(descriptions, quotient)
    )

    resolved = resolve_convex_family(
        split_common,
        {0: Fraction(1, 2), 3: Fraction(1, 2)},
    )
    fixed_resolution_recovers_kernel = (
        resolved == shared_fair
        and resolved != independent_fair
        and joint_marginal(resolved, 0) == joint_marginal(independent_fair, 0)
        and joint_marginal(resolved, 1) == joint_marginal(independent_fair, 1)
    )

    return (
        CorrelationResult(
            "SAME_MARGINALS_LOSE_CORRELATION",
            same_marginals_lose_correlation,
            "independent fair bits and a shared fair bit have identical marginals but different exact joint laws",
        ),
        CorrelationResult(
            "COMMON_RANDOMNESS_RECONSTRUCTS_MERGED_JOINT_LAW_FAMILY",
            common_reconstructs_joint_family,
            "split ports with an unrestricted common correlating source generate the same binary joint simplex as one joint randomizer",
        ),
        CorrelationResult(
            "COMMON_RANDOMNESS_IS_NOT_COMMUNICATION",
            common_is_not_communication,
            "an independent shared seed does not transmit a newly observed hidden bit",
        ),
        CorrelationResult(
            "PRIVATE_VS_SHARED_RANDOMNESS_DIFFER",
            private_vs_shared,
            "equal local fair-randomization capacity does not determine the joint coupling",
        ),
        CorrelationResult(
            "PRIVATE_INFORMATION_REQUIRES_FLOW_FOR_REMOTE_CONDITIONING",
            private_information_requires_flow,
            "remote conditioning on private information requires a declared read/communication path",
        ),
        CorrelationResult(
            "CONTROL_PARTITION_IS_GAUGE_WHEN_JOINT_INTERVENTION_FAMILY_MATCHES",
            partition_gauge_when_joint_family_matches,
            "different control partitions quotient when exact joint intervention power, reads and causality match",
        ),
        CorrelationResult(
            "DYNAMIC_INTERVENTION_SET_SURVIVES_STATIC_PARTITION",
            dynamic_intervention_survives,
            "history/context-indexed admissible interventions change exact attainable behavior beyond a nominal static partition",
        ),
        CorrelationResult(
            "CORRELATED_COMPOSITION_DIFFERS_FROM_INDEPENDENT_TENSOR",
            correlated_composition_required,
            "a cross-component common cause changes the joint law without changing component marginals",
        ),
        CorrelationResult(
            "CORRELATION_RESOURCE_QUOTIENT_IS_REPRESENTATIVE_INDEPENDENT",
            quotient_survives,
            "partition labels can be removed once the exact joint intervention resource is preserved",
        ),
        CorrelationResult(
            "FIXED_RESOLUTION_RECOVERS_EXACT_STOCHASTIC_LAW",
            fixed_resolution_recovers_kernel,
            "a resolved joint intervention is again one exact stochastic law while unresolved correlation remains extra structure",
        ),
    )
