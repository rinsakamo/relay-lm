"""Earned finite stochastic / Markov-category slice for Relay Theory #2384.

Research reconstruction only. This module starts from finite exact rational
stochastic kernels and mechanically checks the equations that survive earlier
Grand Null attacks. It is not RelayLM runtime authority and does not claim that
a Markov category is the whole of Relay Theory.
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from fractions import Fraction
from itertools import product

UNIT_VALUE = "__unit__"
UNIT: tuple[Hashable, ...] = (UNIT_VALUE,)


@dataclass(frozen=True)
class ExactKernel:
    """Finite normalized stochastic kernel with exact rational mass."""

    source: tuple[Hashable, ...]
    target: tuple[Hashable, ...]
    matrix: tuple[tuple[Fraction, ...], ...]

    def __post_init__(self) -> None:
        _validate_object(self.source, "source")
        _validate_object(self.target, "target")
        if len(self.matrix) != len(self.source):
            raise ValueError("kernel must contain exactly one row per source value")
        for row in self.matrix:
            if len(row) != len(self.target):
                raise ValueError("kernel row width must match target cardinality")
            if any(not isinstance(mass, Fraction) for mass in row):
                raise TypeError("kernel masses must be fractions.Fraction")
            if any(mass < 0 for mass in row):
                raise ValueError("kernel masses must be non-negative")
            if sum(row, Fraction(0)) != 1:
                raise ValueError("kernel rows must sum exactly to 1")

    def probability(self, source: Hashable, target: Hashable) -> Fraction:
        try:
            source_index = self.source.index(source)
            target_index = self.target.index(target)
        except ValueError as exc:
            raise ValueError("source and target values must be declared") from exc
        return self.matrix[source_index][target_index]

    def row(self, source: Hashable) -> tuple[tuple[Hashable, Fraction], ...]:
        """Return the canonical sparse row after exact zero suppression."""
        try:
            row = self.matrix[self.source.index(source)]
        except ValueError as exc:
            raise ValueError("source value must be declared") from exc
        return tuple(
            (target, mass)
            for target, mass in zip(self.target, row, strict=True)
            if mass
        )


@dataclass(frozen=True)
class ReconstructionResult:
    name: str
    passed: bool
    detail: str = ""


def _validate_object(values: tuple[Hashable, ...], role: str) -> None:
    if not values:
        raise ValueError(f"{role} object must be finite and nonempty")
    try:
        unique = set(values)
    except TypeError as exc:
        raise TypeError(f"{role} values must be hashable") from exc
    if len(unique) != len(values):
        raise ValueError(f"{role} values must be unique")


def exact_kernel(
    source: tuple[Hashable, ...],
    target: tuple[Hashable, ...],
    rows: Mapping[Hashable, Mapping[Hashable, Fraction]],
) -> ExactKernel:
    """Construct an exact kernel from declared sparse rows."""
    _validate_object(source, "source")
    _validate_object(target, "target")
    if set(rows) != set(source):
        raise ValueError("rows must cover every source value exactly once")

    target_set = set(target)
    matrix: list[tuple[Fraction, ...]] = []
    for source_value in source:
        weights = rows[source_value]
        if set(weights) - target_set:
            raise ValueError("kernel row references an undeclared target value")
        if any(not isinstance(mass, Fraction) for mass in weights.values()):
            raise TypeError("kernel masses must be fractions.Fraction")
        matrix.append(
            tuple(weights.get(target_value, Fraction(0)) for target_value in target)
        )
    return ExactKernel(source, target, tuple(matrix))


def identity_kernel(obj: tuple[Hashable, ...]) -> ExactKernel:
    _validate_object(obj, "identity")
    return ExactKernel(
        obj,
        obj,
        tuple(
            tuple(Fraction(int(source == target)) for target in obj)
            for source in obj
        ),
    )


def deterministic_kernel(
    source: tuple[Hashable, ...],
    target: tuple[Hashable, ...],
    mapping: Mapping[Hashable, Hashable],
) -> ExactKernel:
    _validate_object(source, "source")
    _validate_object(target, "target")
    if set(mapping) != set(source):
        raise ValueError("deterministic mapping must cover every source value")
    target_set = set(target)
    if any(value not in target_set for value in mapping.values()):
        raise ValueError("deterministic mapping must land in the declared target")
    return ExactKernel(
        source,
        target,
        tuple(
            tuple(
                Fraction(int(mapping[source_value] == target_value))
                for target_value in target
            )
            for source_value in source
        ),
    )


def distribution_kernel(
    target: tuple[Hashable, ...],
    distribution: tuple[tuple[Hashable, Fraction], ...],
) -> ExactKernel:
    """Lift one exact resolved distribution to a state arrow ``1 -> target``."""
    weights: dict[Hashable, Fraction] = {}
    for value, mass in distribution:
        if value in weights:
            raise ValueError("resolved distribution outcomes must be unique")
        weights[value] = mass
    return exact_kernel(UNIT, target, {UNIT_VALUE: weights})


def compose(after: ExactKernel, before: ExactKernel) -> ExactKernel:
    """Return ``after o before`` by exact finite probability sum/product."""
    if before.target != after.source:
        raise ValueError("kernel composition requires identical intermediate objects")
    rows = tuple(
        tuple(
            sum(
                (
                    before_row[mid_index] * after.matrix[mid_index][target_index]
                    for mid_index in range(len(before.target))
                ),
                Fraction(0),
            )
            for target_index in range(len(after.target))
        )
        for before_row in before.matrix
    )
    return ExactKernel(before.source, after.target, rows)


def product_object(
    left: tuple[Hashable, ...], right: tuple[Hashable, ...]
) -> tuple[Hashable, ...]:
    _validate_object(left, "left product")
    _validate_object(right, "right product")
    return tuple(
        (left_value, right_value)
        for left_value in left
        for right_value in right
    )


def tensor(left: ExactKernel, right: ExactKernel) -> ExactKernel:
    """Independent parallel composition by exact product mass."""
    source = product_object(left.source, right.source)
    target = product_object(left.target, right.target)
    rows = tuple(
        tuple(
            left.probability(left_source, left_target)
            * right.probability(right_source, right_target)
            for left_target, right_target in target
        )
        for left_source, right_source in source
    )
    return ExactKernel(source, target, rows)


def discard_kernel(obj: tuple[Hashable, ...]) -> ExactKernel:
    return ExactKernel(obj, UNIT, tuple((Fraction(1),) for _ in obj))


def copy_kernel(obj: tuple[Hashable, ...]) -> ExactKernel:
    target = product_object(obj, obj)
    return deterministic_kernel(
        obj,
        target,
        {value: (value, value) for value in obj},
    )


def fair_bit_kernel() -> ExactKernel:
    return ExactKernel(
        UNIT,
        ("0", "1"),
        ((Fraction(1, 2), Fraction(1, 2)),),
    )


def shared_fair_pair() -> ExactKernel:
    fair = fair_bit_kernel()
    return compose(copy_kernel(fair.target), fair)


def independent_fair_pair() -> ExactKernel:
    fair = fair_bit_kernel()
    return compose(tensor(fair, fair), copy_kernel(UNIT))


def deterministic_composition_law_holds() -> bool:
    source = ("a", "b", "c")
    middle = ("u", "v")
    target = ("0", "1", "2")
    first_map = {"a": "u", "b": "v", "c": "u"}
    second_map = {"u": "2", "v": "1"}
    first = deterministic_kernel(source, middle, first_map)
    second = deterministic_kernel(middle, target, second_map)
    composed_map = {item: second_map[first_map[item]] for item in source}
    return compose(second, first) == deterministic_kernel(
        source, target, composed_map
    )


def category_laws_hold() -> bool:
    obj_w = ("w0", "w1")
    obj_x = ("x0", "x1")
    obj_y = ("y0", "y1", "y2")
    obj_z = ("z0", "z1")
    first = ExactKernel(
        obj_w,
        obj_x,
        (
            (Fraction(1, 3), Fraction(2, 3)),
            (Fraction(3, 4), Fraction(1, 4)),
        ),
    )
    second = ExactKernel(
        obj_x,
        obj_y,
        (
            (Fraction(1, 2), Fraction(1, 3), Fraction(1, 6)),
            (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
        ),
    )
    third = ExactKernel(
        obj_y,
        obj_z,
        (
            (Fraction(1, 5), Fraction(4, 5)),
            (Fraction(2, 5), Fraction(3, 5)),
            (Fraction(3, 5), Fraction(2, 5)),
        ),
    )
    identity = (
        compose(first, identity_kernel(obj_w)) == first
        and compose(identity_kernel(obj_x), first) == first
    )
    associativity = compose(third, compose(second, first)) == compose(
        compose(third, second), first
    )
    return identity and associativity


def discard_naturality_holds() -> bool:
    kernel = ExactKernel(
        ("x0", "x1"),
        ("y0", "y1", "y2"),
        (
            (Fraction(1, 2), Fraction(1, 3), Fraction(1, 6)),
            (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
        ),
    )
    return compose(discard_kernel(kernel.target), kernel) == discard_kernel(
        kernel.source
    )


def copy_comonoid_laws_hold(obj: tuple[Hashable, ...]) -> bool:
    _validate_object(obj, "copy")
    copy = copy_kernel(obj)
    identity = identity_kernel(obj)
    product2 = product_object(obj, obj)
    product3 = tuple(product(obj, repeat=3))

    left_nested = compose(tensor(copy, identity), copy)
    right_nested = compose(tensor(identity, copy), copy)
    flatten_left = deterministic_kernel(
        left_nested.target,
        product3,
        {((a, b), c): (a, b, c) for a, b, c in product(obj, repeat=3)},
    )
    flatten_right = deterministic_kernel(
        right_nested.target,
        product3,
        {(a, (b, c)): (a, b, c) for a, b, c in product(obj, repeat=3)},
    )
    coassociative = compose(flatten_left, left_nested) == compose(
        flatten_right, right_nested
    )

    swap = deterministic_kernel(
        product2,
        product2,
        {(a, b): (b, a) for a, b in product(obj, repeat=2)},
    )
    cocommutative = compose(swap, copy) == copy

    left_counit = compose(tensor(discard_kernel(obj), identity), copy)
    right_counit = compose(tensor(identity, discard_kernel(obj)), copy)
    project_left = deterministic_kernel(
        left_counit.target,
        obj,
        {(UNIT_VALUE, value): value for value in obj},
    )
    project_right = deterministic_kernel(
        right_counit.target,
        obj,
        {(value, UNIT_VALUE): value for value in obj},
    )
    counital = (
        compose(project_left, left_counit) == identity
        and compose(project_right, right_counit) == identity
    )
    return coassociative and cocommutative and counital


def deterministic_maps_preserve_copy() -> bool:
    source = ("a", "b", "c")
    target = ("0", "1")
    function = deterministic_kernel(
        source, target, {"a": "0", "b": "1", "c": "0"}
    )
    copied_after = compose(copy_kernel(target), function)
    copied_before = compose(tensor(function, function), copy_kernel(source))
    return copied_after == copied_before


def stochastic_copy_naturality_fails() -> bool:
    copied_sample = shared_fair_pair()
    independent_resample = independent_fair_pair()
    return (
        copied_sample != independent_resample
        and copied_sample.row(UNIT_VALUE)
        == ((("0", "0"), Fraction(1, 2)), (("1", "1"), Fraction(1, 2)))
        and independent_resample.row(UNIT_VALUE)
        == (
            (("0", "0"), Fraction(1, 4)),
            (("0", "1"), Fraction(1, 4)),
            (("1", "0"), Fraction(1, 4)),
            (("1", "1"), Fraction(1, 4)),
        )
    )


def tensor_laws_hold() -> bool:
    obj_x = ("x0", "x1")
    obj_y = ("y0", "y1")
    obj_z = ("z0", "z1")
    obj_a = ("a0", "a1")
    obj_b = ("b0", "b1")
    obj_c = ("c0", "c1")
    first_left = ExactKernel(
        obj_x,
        obj_y,
        (
            (Fraction(1, 3), Fraction(2, 3)),
            (Fraction(3, 4), Fraction(1, 4)),
        ),
    )
    second_left = ExactKernel(
        obj_y,
        obj_z,
        (
            (Fraction(2, 5), Fraction(3, 5)),
            (Fraction(1, 5), Fraction(4, 5)),
        ),
    )
    first_right = ExactKernel(
        obj_a,
        obj_b,
        (
            (Fraction(1, 2), Fraction(1, 2)),
            (Fraction(1, 4), Fraction(3, 4)),
        ),
    )
    second_right = ExactKernel(
        obj_b,
        obj_c,
        (
            (Fraction(3, 5), Fraction(2, 5)),
            (Fraction(2, 3), Fraction(1, 3)),
        ),
    )

    identity_compatibility = tensor(
        identity_kernel(obj_x), identity_kernel(obj_a)
    ) == identity_kernel(product_object(obj_x, obj_a))
    interchange = tensor(
        compose(second_left, first_left),
        compose(second_right, first_right),
    ) == compose(
        tensor(second_left, second_right),
        tensor(first_left, first_right),
    )

    swap_source = deterministic_kernel(
        product_object(obj_x, obj_a),
        product_object(obj_a, obj_x),
        {(left, right): (right, left) for left, right in product(obj_x, obj_a)},
    )
    swap_target = deterministic_kernel(
        product_object(obj_y, obj_b),
        product_object(obj_b, obj_y),
        {(left, right): (right, left) for left, right in product(obj_y, obj_b)},
    )
    explicit_symmetry = compose(
        swap_target, tensor(first_left, first_right)
    ) == compose(tensor(first_right, first_left), swap_source)
    normalized = all(
        sum(row, Fraction(0)) == 1
        for row in tensor(first_left, first_right).matrix
    )
    return identity_compatibility and interchange and explicit_symmetry and normalized


def _pair_marginal(kernel: ExactKernel, coordinate: int) -> dict[str, Fraction]:
    return {
        bit: sum(
            (
                kernel.probability(UNIT_VALUE, pair)
                for pair in kernel.target
                if pair[coordinate] == bit
            ),
            Fraction(0),
        )
        for bit in ("0", "1")
    }


def shared_randomness_uses_copy_not_plain_tensor() -> bool:
    shared = shared_fair_pair()
    independent = independent_fair_pair()
    fair_marginal = {"0": Fraction(1, 2), "1": Fraction(1, 2)}
    return (
        _pair_marginal(shared, 0)
        == _pair_marginal(shared, 1)
        == _pair_marginal(independent, 0)
        == _pair_marginal(independent, 1)
        == fair_marginal
        and shared != independent
    )


def resolved_choice_boundary_survives() -> bool:
    """Resolve scheduler choices to arrows without erasing unresolved capability."""
    from tools.relay_theory_scheduler_nondeterminism import (
        Alternative,
        ChoiceState,
        exact_distribution,
        induced_distribution,
        max_outcome_probability,
    )

    outcomes = ("L", "R")
    delta_left = exact_distribution({"L": Fraction(1)})
    delta_right = exact_distribution({"R": Fraction(1)})
    fair = exact_distribution({"L": Fraction(1, 2), "R": Fraction(1, 2)})
    selectable = ChoiceState(
        "selectable",
        (
            Alternative("left", delta_left),
            Alternative("right", delta_right),
        ),
    )
    fixed = ChoiceState("fixed", (Alternative("fair", fair),))

    fixed_left = induced_distribution(selectable, {"left": Fraction(1)})
    fixed_right = induced_distribution(selectable, {"right": Fraction(1)})
    randomized = induced_distribution(
        selectable,
        {"left": Fraction(1, 2), "right": Fraction(1, 2)},
    )
    left_arrow = distribution_kernel(outcomes, fixed_left)
    right_arrow = distribution_kernel(outcomes, fixed_right)
    randomized_arrow = distribution_kernel(outcomes, randomized)
    fixed_fair_arrow = distribution_kernel(outcomes, fair)

    resolutions_recover_arrows = (
        left_arrow.row(UNIT_VALUE) == (("L", Fraction(1)),)
        and right_arrow.row(UNIT_VALUE) == (("R", Fraction(1)),)
        and randomized_arrow == fixed_fair_arrow
    )
    unresolved_capability_survives = (
        max_outcome_probability(selectable, "L", "randomized") == 1
        and max_outcome_probability(fixed, "L", "randomized") == Fraction(1, 2)
    )
    return resolutions_recover_arrows and unresolved_capability_survives


def causal_intervention_boundary_survives() -> bool:
    from tools.relay_theory_causal_substitution import (
        run_causal_substitution_comparison,
    )

    results = {
        result.name: result.passed
        for result in run_causal_substitution_comparison()
    }
    return (
        results[
            "OBSERVATIONAL_EQUIVALENCE_DOES_NOT_IMPLY_INTERVENTIONAL_EQUIVALENCE"
        ]
        and results["FIXED_SUBSTITUTION_RECOVERS_ONE_EXACT_STOCHASTIC_LAW"]
    )


def counterfactual_boundary_survives() -> bool:
    from tools.relay_theory_cross_world_coupling import (
        run_cross_world_coupling_comparison,
    )

    results = {
        result.name: result.passed
        for result in run_cross_world_coupling_comparison()
    }
    return (
        results["COMPLETE_BINARY_HARD_INTERVENTION_FAMILY_MATCHES"]
        and results[
            "ENTIRE_BERNOULLI_SOFT_INTERVENTION_FAMILY_MATCHES_SYMBOLICALLY"
        ]
        and results["SAME_UNIT_CROSS_WORLD_COUPLING_DIFFERS"]
    )


def local_global_gluing_boundary_survives() -> bool:
    from tools.relay_theory_probability_mass_gluing import (
        run_probability_mass_gluing,
    )

    results = {
        result.name: result.passed for result in run_probability_mass_gluing()
    }
    return (
        results["NEGATIVE_LOCAL_LAWS_ARE_OVERLAP_CONSISTENT"]
        and results["NEGATIVE_SUPPORT_IS_MAXIMALLY_PERMISSIVE"]
        and results["MASS_CERTIFICATE_REJECTS_FULL_SUPPORT_NEGATIVE"]
    )


def quotient_representative_independence_survives() -> bool:
    """Lift #2209 bisimilar representatives to the same quotient arrow."""
    from tools.v2_operational_probabilistic_bisimulation import (
        ProbLTS,
        ProbTransition,
        probabilistic_bisimulation_partition,
        state_distribution,
    )

    system = ProbLTS(
        ("x1", "x2", "y0", "y1"),
        (
            ProbTransition("x1", "go", "y0", Fraction(1, 3)),
            ProbTransition("x1", "go", "y1", Fraction(2, 3)),
            ProbTransition("x2", "go", "y0", Fraction(1, 3)),
            ProbTransition("x2", "go", "y1", Fraction(2, 3)),
        ),
    )
    observations = {
        "x1": ("source",),
        "x2": ("source",),
        "y0": ("zero",),
        "y1": ("one",),
    }
    partition = probabilistic_bisimulation_partition(system, observations)
    if partition["x1"] != partition["x2"]:
        return False

    target_blocks = tuple(sorted({partition["y0"], partition["y1"]}))
    label = ("go", 0, 0)

    def representative_kernel(representative: str) -> ExactKernel:
        accumulated = {block: Fraction(0) for block in target_blocks}
        for target, mass in state_distribution(system, representative, label):
            accumulated[partition[target]] += mass
        return exact_kernel(("Q",), target_blocks, {"Q": accumulated})

    left = representative_kernel("x1")
    right = representative_kernel("x2")
    if left != right:
        return False

    output = ("o0", "o1")
    post = deterministic_kernel(
        target_blocks,
        output,
        {
            block: output[index]
            for index, block in enumerate(target_blocks)
        },
    )
    context = fair_bit_kernel()
    return all(
        (
            compose(post, left) == compose(post, right),
            tensor(left, context) == tensor(right, context),
            copy_kernel(left.source) == copy_kernel(right.source),
            discard_kernel(left.source) == discard_kernel(right.source),
            compose(post, left).row("Q") == compose(post, right).row("Q"),
        )
    )


def reconstructed_core_survives() -> bool:
    return all(
        (
            category_laws_hold(),
            deterministic_composition_law_holds(),
            discard_naturality_holds(),
            copy_comonoid_laws_hold(("0", "1")),
            deterministic_maps_preserve_copy(),
            stochastic_copy_naturality_fails(),
            tensor_laws_hold(),
            shared_randomness_uses_copy_not_plain_tensor(),
            quotient_representative_independence_survives(),
        )
    )


def outer_relay_boundaries_survive() -> bool:
    return all(
        (
            resolved_choice_boundary_survives(),
            causal_intervention_boundary_survives(),
            counterfactual_boundary_survives(),
            local_global_gluing_boundary_survives(),
        )
    )


def reconstruction_verdict() -> str:
    if not category_laws_hold():
        return "CATEGORY_LAWS_FAIL"
    if not tensor_laws_hold():
        return "UNDERDETERMINED"
    if not copy_comonoid_laws_hold(("0", "1")) or not discard_naturality_holds():
        return "SYMMETRIC_MONOIDAL_STOCHASTIC_SLICE_SURVIVES"
    if not deterministic_composition_law_holds() or not deterministic_maps_preserve_copy():
        return "COPY_DISCARD_STRUCTURE_SURVIVES"
    if not stochastic_copy_naturality_fails():
        return "DETERMINISTIC_SUBCATEGORY_SURVIVES"
    if not reconstructed_core_survives():
        return "UNDERDETERMINED"
    if outer_relay_boundaries_survive():
        return "MARKOV_CATEGORY_IS_DERIVED_SLICE_ONLY"
    return "FINSTOCH_MARKOV_SLICE_RECONSTRUCTED"


def run_markov_reconstruction() -> tuple[ReconstructionResult, ...]:
    checks = (
        ReconstructionResult(
            "CATEGORY_IDENTITY_AND_ASSOCIATIVITY_SURVIVE",
            category_laws_hold(),
        ),
        ReconstructionResult(
            "DETERMINISTIC_DIRAC_SUBCATEGORY_SURVIVES",
            deterministic_composition_law_holds()
            and deterministic_maps_preserve_copy(),
        ),
        ReconstructionResult(
            "COPY_DISCARD_COMONOID_STRUCTURE_SURVIVES",
            discard_naturality_holds()
            and copy_comonoid_laws_hold(("0", "1")),
        ),
        ReconstructionResult(
            "INDEPENDENT_TENSOR_AND_INTERCHANGE_SURVIVE",
            tensor_laws_hold(),
        ),
        ReconstructionResult(
            "STOCHASTIC_COPY_NONNATURALITY_SURVIVES",
            stochastic_copy_naturality_fails(),
            "copying one fair draw differs exactly from two independent fair draws",
        ),
        ReconstructionResult(
            "SHARED_RANDOMNESS_IS_WIRING_NOT_PLAIN_TENSOR",
            shared_randomness_uses_copy_not_plain_tensor(),
        ),
        ReconstructionResult(
            "RESOLVED_CHOICE_RECOVERS_ONE_ARROW_UNRESOLVED_CHOICE_DOES_NOT",
            resolved_choice_boundary_survives(),
        ),
        ReconstructionResult(
            "INTERVENTION_ALGEBRA_REMAINS_OUTSIDE_OBSERVATIONAL_ARROW",
            causal_intervention_boundary_survives(),
        ),
        ReconstructionResult(
            "COUNTERFACTUAL_COUPLING_REMAINS_OUTSIDE_SINGLE_WORLD_ARROWS",
            counterfactual_boundary_survives(),
        ),
        ReconstructionResult(
            "LOCAL_STOCHASTIC_PIECES_DO_NOT_GLUE_BY_FIAT",
            local_global_gluing_boundary_survives(),
        ),
        ReconstructionResult(
            "EXACT_BEHAVIORAL_QUOTIENT_IS_REPRESENTATIVE_INDEPENDENT",
            quotient_representative_independence_survives(),
        ),
    )
    verdict = reconstruction_verdict()
    return (
        *checks,
        ReconstructionResult(
            "FINSTOCH_MARKOV_SINGLE_WORLD_SLICE_IS_RECONSTRUCTED",
            reconstructed_core_survives(),
        ),
        ReconstructionResult(
            "MARKOV_CATEGORY_IS_DERIVED_SLICE_ONLY",
            verdict == "MARKOV_CATEGORY_IS_DERIVED_SLICE_ONLY",
            verdict,
        ),
    )
