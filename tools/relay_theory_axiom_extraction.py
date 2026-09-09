"""Bounded Relay Theory 0.1 axiom-extraction apparatus for #2396.

This module compresses the first Relay Theory Grand Null cycle into a smaller
public interface basis. It is deterministic research apparatus, not RelayLM
runtime or architecture authority and not a theorem prover.

The candidate basis is intentionally smaller than the vocabulary that produced
it:

- declared access to observations, transformations, and information;
- exact resolved behavior;
- finite public experiment transformations with no opaque payload;
- explicit multi-context alignment input;
- a realizability domain/certificate for partial global construction; and
- exact equality as the identity boundary.

Behavioral quotients, pure observational forgetting/reindexing, and the tested
FinStoch/Markov slice are reconstructed as derived structures.
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction

ExactLaw = tuple[tuple[Hashable, Fraction], ...]


def canonical_exact_law(weights: Mapping[Hashable, Fraction]) -> ExactLaw:
    """Return one normalized finite exact law with zero mass suppressed."""
    if not weights:
        raise ValueError("exact law must contain at least one declared outcome")

    total = Fraction(0)
    cleaned: list[tuple[Hashable, Fraction]] = []
    for outcome, mass in weights.items():
        try:
            hash(outcome)
        except TypeError as exc:
            raise TypeError("exact-law outcomes must be hashable") from exc
        if not isinstance(mass, Fraction):
            raise TypeError("exact-law mass must be fractions.Fraction")
        if mass < 0 or mass > 1:
            raise ValueError("exact-law mass must lie in [0, 1]")
        total += mass
        if mass:
            cleaned.append((outcome, mass))

    if total != 1:
        raise ValueError("exact-law probability mass must sum exactly to 1")
    return tuple(sorted(cleaned, key=lambda item: repr(item[0])))


def _validated_exact_law(law: ExactLaw) -> ExactLaw:
    weights: dict[Hashable, Fraction] = {}
    for outcome, mass in law:
        if outcome in weights:
            raise ValueError("exact-law outcomes must be unique")
        weights[outcome] = mass
    return canonical_exact_law(weights)


def _validate_tokens(values: Sequence[str], role: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{role} entries must be unique")
    if any(not value for value in values):
        raise ValueError(f"{role} entries must be non-empty")


@dataclass(frozen=True)
class TransformCommand:
    """One public finite experiment transformation command.

    Only its read/write contract is public here. Behavior lives in the
    experiment's exact response table; there is deliberately no opaque payload,
    callback, scheduler object, causal graph, or hidden implementation state.
    """

    name: str
    reads: tuple[str, ...] = ()
    writes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("command name must be non-empty")
        _validate_tokens(self.reads, "command reads")
        _validate_tokens(self.writes, "command writes")


@dataclass(frozen=True)
class AccessSpec:
    """Declared operational access used to interpret one finite experiment."""

    name: str
    observations: tuple[str, ...] = ()
    admissible_commands: tuple[str, ...] = ()
    visible_information: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("access name must be non-empty")
        _validate_tokens(self.observations, "observations")
        _validate_tokens(self.admissible_commands, "admissible commands")
        _validate_tokens(self.visible_information, "visible information")


@dataclass(frozen=True)
class FiniteExperiment:
    """Exact behavior plus a finite public transformation response table."""

    name: str
    base_law: ExactLaw
    commands: tuple[TransformCommand, ...] = ()
    responses: tuple[tuple[str, ExactLaw], ...] = ()
    observation_values: tuple[tuple[str, Hashable], ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("experiment name must be non-empty")
        _validated_exact_law(self.base_law)

        command_names = [command.name for command in self.commands]
        if len(command_names) != len(set(command_names)):
            raise ValueError("experiment command names must be unique")

        response_names: set[str] = set()
        for name, law in self.responses:
            if not name:
                raise ValueError("response command name must be non-empty")
            if name in response_names:
                raise ValueError("response command names must be unique")
            response_names.add(name)
            _validated_exact_law(law)
        if response_names != set(command_names):
            raise ValueError(
                "response table must cover every declared command exactly once"
            )

        observation_names = [name for name, _ in self.observation_values]
        if len(observation_names) != len(set(observation_names)):
            raise ValueError("experiment observation names must be unique")
        if any(not name for name in observation_names):
            raise ValueError("experiment observation names must be non-empty")
        for _, value in self.observation_values:
            try:
                hash(value)
            except TypeError as exc:
                raise TypeError("observation values must be hashable") from exc


@dataclass(frozen=True)
class LocalConstraint:
    """Exact marginal law required on a declared coordinate subset."""

    coordinates: tuple[str, ...]
    law: ExactLaw

    def __post_init__(self) -> None:
        if not self.coordinates:
            raise ValueError("local constraint coordinates must be non-empty")
        _validate_tokens(self.coordinates, "local constraint coordinates")
        canonical = _validated_exact_law(self.law)
        for outcome, _ in canonical:
            if not isinstance(outcome, tuple):
                raise TypeError("local-constraint outcomes must be tuples")
            if len(outcome) != len(self.coordinates):
                raise ValueError(
                    "local-constraint outcome arity must match coordinates"
                )


@dataclass(frozen=True)
class AlignmentInput:
    """Explicit candidate joint law over multiple declared contexts."""

    contexts: tuple[str, ...]
    joint: ExactLaw

    def __post_init__(self) -> None:
        if not self.contexts:
            raise ValueError("alignment contexts must be non-empty")
        _validate_tokens(self.contexts, "alignment contexts")
        canonical = _validated_exact_law(self.joint)
        for outcome, _ in canonical:
            if not isinstance(outcome, tuple):
                raise TypeError("alignment outcomes must be tuples")
            if len(outcome) != len(self.contexts):
                raise ValueError("alignment outcome arity must match contexts")


@dataclass(frozen=True)
class RealizabilityCertificate:
    """Finite certificate: an explicit joint candidate that passes all locals."""

    alignment: AlignmentInput


@dataclass(frozen=True)
class ExtractionResult:
    name: str
    passed: bool
    detail: str = ""

    def __post_init__(self) -> None:
        if type(self.passed) is not bool:
            raise TypeError("ExtractionResult.passed must be strict bool")


def access_contract(access: AccessSpec) -> tuple[object, ...]:
    """Forget only the syntactic frame/access name."""
    return (
        tuple(sorted(access.observations)),
        tuple(sorted(access.admissible_commands)),
        tuple(sorted(access.visible_information)),
    )


def access_equivalent(left: AccessSpec, right: AccessSpec) -> bool:
    return access_contract(left) == access_contract(right)


def access_forgetting(coarse: AccessSpec, rich: AccessSpec) -> bool:
    """Derived pure-observation forgetting relation between access bundles."""
    return (
        set(coarse.observations).issubset(rich.observations)
        and tuple(sorted(coarse.admissible_commands))
        == tuple(sorted(rich.admissible_commands))
        and tuple(sorted(coarse.visible_information))
        == tuple(sorted(rich.visible_information))
    )


def command_is_admissible(command: TransformCommand, access: AccessSpec) -> bool:
    return (
        command.name in access.admissible_commands
        and set(command.reads).issubset(access.visible_information)
    )


def resolve(
    experiment: FiniteExperiment,
    access: AccessSpec,
    command_name: str,
) -> ExactLaw:
    commands = {command.name: command for command in experiment.commands}
    if command_name not in commands:
        raise ValueError(f"experiment lacks command {command_name!r}")
    command = commands[command_name]
    if not command_is_admissible(command, access):
        raise ValueError(f"command {command_name!r} is not admissible under access")
    return _validated_exact_law(dict(experiment.responses)[command_name])


def attainable_laws(
    experiment: FiniteExperiment,
    access: AccessSpec,
) -> tuple[ExactLaw, ...]:
    laws = {
        resolve(experiment, access, command.name)
        for command in experiment.commands
        if command_is_admissible(command, access)
    }
    return tuple(sorted(laws, key=repr))


def operational_signature(
    experiment: FiniteExperiment,
    access: AccessSpec,
) -> tuple[object, ...]:
    """Exact public signature; unexposed internal presentation is absent."""
    observation_values = dict(experiment.observation_values)
    missing_observations = set(access.observations) - set(observation_values)
    if missing_observations:
        raise ValueError(
            f"experiment lacks observations: {sorted(missing_observations)}"
        )
    selected_observations = tuple(
        (name, observation_values[name]) for name in sorted(access.observations)
    )

    commands = {command.name: command for command in experiment.commands}
    responses = dict(experiment.responses)
    selected_commands: list[tuple[object, ...]] = []
    for name in sorted(access.admissible_commands):
        command = commands.get(name)
        if command is None:
            selected_commands.append((name, "UNAVAILABLE"))
            continue
        if not set(command.reads).issubset(access.visible_information):
            selected_commands.append(
                (name, "INFORMATION_BLOCKED", command.reads, command.writes)
            )
            continue
        selected_commands.append(
            (
                name,
                "ADMISSIBLE",
                tuple(sorted(command.reads)),
                tuple(sorted(command.writes)),
                _validated_exact_law(responses[name]),
            )
        )

    return (
        _validated_exact_law(experiment.base_law),
        selected_observations,
        tuple(selected_commands),
    )


def derived_behavioral_partition(
    experiments: Sequence[FiniteExperiment],
    access: AccessSpec,
) -> dict[str, str]:
    names = [experiment.name for experiment in experiments]
    if len(names) != len(set(names)):
        raise ValueError("experiment names must be unique")

    signatures: list[tuple[object, ...]] = []
    partition: dict[str, str] = {}
    for experiment in experiments:
        signature = operational_signature(experiment, access)
        try:
            index = signatures.index(signature)
        except ValueError:
            signatures.append(signature)
            index = len(signatures) - 1
        partition[experiment.name] = f"b{index}"
    return partition


def _law_from_distribution(
    distribution: Sequence[tuple[Hashable, Fraction]],
) -> ExactLaw:
    return canonical_exact_law(dict(distribution))


def _scheduler_experiment() -> FiniteExperiment:
    from tools.relay_theory_scheduler_nondeterminism import (
        Alternative,
        ChoiceState,
        exact_distribution,
        induced_distribution,
    )

    delta_l = exact_distribution({"L": Fraction(1)})
    delta_r = exact_distribution({"R": Fraction(1)})
    state = ChoiceState(
        "choice",
        (
            Alternative("left", delta_l),
            Alternative("right", delta_r),
        ),
    )
    base = induced_distribution(
        state,
        {"left": Fraction(1, 2), "right": Fraction(1, 2)},
    )
    return FiniteExperiment(
        "scheduler-adapter",
        _law_from_distribution(base),
        (
            TransformCommand("choose-left", writes=("choice",)),
            TransformCommand("choose-right", writes=("choice",)),
        ),
        (
            ("choose-left", _law_from_distribution(delta_l)),
            ("choose-right", _law_from_distribution(delta_r)),
        ),
    )


def _intervention_experiment() -> FiniteExperiment:
    from tools.relay_theory_causal_substitution import (
        direct_xy_model,
        evaluate_model,
        hard_intervene,
    )

    model = direct_xy_model()
    commands: list[TransformCommand] = []
    responses: list[tuple[str, ExactLaw]] = []
    for target in ("X", "Y"):
        for value in ("0", "1"):
            name = f"set-{target}-{value}"
            commands.append(TransformCommand(name, writes=(target,)))
            responses.append(
                (
                    name,
                    _law_from_distribution(
                        evaluate_model(hard_intervene(model, target, value))
                    ),
                )
            )
    return FiniteExperiment(
        "intervention-adapter",
        _law_from_distribution(evaluate_model(model)),
        tuple(commands),
        tuple(responses),
    )


def transformation_interface_unifies_choice_and_intervention() -> bool:
    scheduler = _scheduler_experiment()
    intervention = _intervention_experiment()

    scheduler_access = AccessSpec(
        "scheduler",
        admissible_commands=("choose-left", "choose-right"),
    )
    intervention_access = AccessSpec(
        "intervention",
        admissible_commands=tuple(command.name for command in intervention.commands),
    )

    fixed = FiniteExperiment("fixed", scheduler.base_law)
    unresolved_survives = (
        scheduler.base_law == fixed.base_law
        and operational_signature(scheduler, scheduler_access)
        != operational_signature(fixed, scheduler_access)
    )

    return (
        isinstance(scheduler.commands[0], TransformCommand)
        and isinstance(intervention.commands[0], TransformCommand)
        and resolve(scheduler, scheduler_access, "choose-left")
        != resolve(scheduler, scheduler_access, "choose-right")
        and resolve(intervention, intervention_access, "set-X-0")
        != intervention.base_law
        and unresolved_survives
    )


def authority_reduces_to_transform_admissibility() -> bool:
    from tools.relay_theory_correlation_authority import (
        ResourceDescription,
        canonical_control_partition,
        full_joint_family,
        resource_operationally_equivalent,
    )

    experiment = _scheduler_experiment()
    read_only = AccessSpec("read-only")
    left_only = AccessSpec(
        "left-only",
        admissible_commands=("choose-left",),
    )
    both = AccessSpec(
        "both",
        admissible_commands=("choose-left", "choose-right"),
    )
    admissibility_changes_power = (
        attainable_laws(experiment, read_only) == ()
        and len(attainable_laws(experiment, left_only)) == 1
        and len(attainable_laws(experiment, both)) == 2
    )

    family = full_joint_family("joint-power")
    nominally_merged = ResourceDescription(
        "merged-owner",
        canonical_control_partition((("A", "B"),)),
        family,
    )
    nominally_split = ResourceDescription(
        "split-owners",
        canonical_control_partition((("A",), ("B",))),
        family,
    )
    owner_partition_is_gauge_once_power_is_explicit = resource_operationally_equivalent(
        nominally_merged,
        nominally_split,
    )
    return admissibility_changes_power and owner_partition_is_gauge_once_power_is_explicit


def information_reduces_to_access_specification() -> bool:
    from tools.relay_theory_scheduler_nondeterminism import policy_is_observation_based

    h0 = ("start", "left")
    h1 = ("start", "right")
    policy = {h0: "a", h1: "b"}
    coarse_observation = {h0: "same", h1: "same"}
    rich_observation = {h0: "left", h1: "right"}

    command = TransformCommand(
        "history-choice",
        reads=("history",),
        writes=("choice",),
    )
    law = canonical_exact_law({"ok": Fraction(1)})
    experiment = FiniteExperiment(
        "history-sensitive",
        law,
        (command,),
        (("history-choice", law),),
    )
    coarse = AccessSpec(
        "coarse",
        admissible_commands=("history-choice",),
    )
    rich = AccessSpec(
        "rich",
        admissible_commands=("history-choice",),
        visible_information=("history",),
    )

    blocked = False
    try:
        resolve(experiment, coarse, "history-choice")
    except ValueError:
        blocked = True

    return (
        not policy_is_observation_based(policy, coarse_observation)
        and policy_is_observation_based(policy, rich_observation)
        and blocked
        and resolve(experiment, rich, "history-choice") == law
    )


def _factorization_experiment(interface: object, *, name: str) -> FiniteExperiment:
    from tools.relay_theory_mechanism_factorization import (
        evaluate_exposed,
        exposed_hard_responses,
        exposed_soft_responses,
        internal_mechanism_count,
    )

    hard = exposed_hard_responses(interface)
    soft = exposed_soft_responses(interface)
    commands: list[TransformCommand] = []
    responses: list[tuple[str, ExactLaw]] = []

    for (target, value), law in hard:
        command_name = f"hard-{target}-{value}"
        commands.append(TransformCommand(command_name, writes=(target,)))
        responses.append((command_name, _law_from_distribution(law)))
    for (target, probability_one), law in soft:
        command_name = f"soft-{target}-{probability_one}"
        commands.append(TransformCommand(command_name, writes=(target,)))
        responses.append((command_name, _law_from_distribution(law)))

    return FiniteExperiment(
        name,
        _law_from_distribution(evaluate_exposed(interface)),
        tuple(commands),
        tuple(responses),
        (("internal-mechanism-count", internal_mechanism_count(interface)),),
    )


def factorization_is_access_relative() -> bool:
    from tools.relay_theory_mechanism_factorization import (
        fused_xy_model,
        split_xy_model,
        xy_interface,
    )

    fused = _factorization_experiment(
        xy_interface(fused_xy_model(), name="fused-interface"),
        name="fused",
    )
    split = _factorization_experiment(
        xy_interface(split_xy_model(), name="split-interface"),
        name="split",
    )
    command_names = tuple(command.name for command in fused.commands)
    if command_names != tuple(command.name for command in split.commands):
        return False

    black_box = AccessSpec(
        "black-box",
        admissible_commands=command_names,
    )
    resource_sensitive = AccessSpec(
        "resource-sensitive",
        observations=("internal-mechanism-count",),
        admissible_commands=command_names,
    )
    return (
        operational_signature(fused, black_box)
        == operational_signature(split, black_box)
        and operational_signature(fused, resource_sensitive)
        != operational_signature(split, resource_sensitive)
    )


def marginalize_alignment(
    alignment: AlignmentInput,
    coordinates: Sequence[str],
) -> ExactLaw:
    requested = tuple(coordinates)
    if not requested:
        raise ValueError("marginal coordinates must be non-empty")
    _validate_tokens(requested, "marginal coordinates")
    index = {context: position for position, context in enumerate(alignment.contexts)}
    if any(context not in index for context in requested):
        raise ValueError("marginal references undeclared alignment context")

    weights: dict[Hashable, Fraction] = {}
    for outcome, mass in _validated_exact_law(alignment.joint):
        assert isinstance(outcome, tuple)
        projected = tuple(outcome[index[context]] for context in requested)
        weights[projected] = weights.get(projected, Fraction(0)) + mass
    return canonical_exact_law(weights)


def construct_from_constraints(
    constraints: Sequence[LocalConstraint],
    alignment: AlignmentInput,
) -> ExactLaw:
    """Validate an explicit joint candidate against every declared local law."""
    if not constraints:
        raise ValueError("global construction requires at least one local constraint")
    for constraint in constraints:
        if marginalize_alignment(alignment, constraint.coordinates) != _validated_exact_law(
            constraint.law
        ):
            raise ValueError(
                f"alignment violates local constraint {constraint.coordinates!r}"
            )
    return _validated_exact_law(alignment.joint)


def _scalar_constraint(
    coordinate: str,
    distribution: Sequence[tuple[str, Fraction]],
) -> LocalConstraint:
    return LocalConstraint(
        (coordinate,),
        canonical_exact_law({(value,): mass for value, mass in distribution}),
    )


def alignment_is_explicit_transform_input() -> bool:
    from tools.relay_theory_cross_world_coupling import (
        flip_response_model,
        invariant_response_model,
        potential_outcome_marginal,
        same_unit_counterfactual_joint,
        single_world_signature,
    )
    from tools.relay_theory_higher_order_coupling import (
        even_parity_model,
        odd_parity_model,
        pairwise_signature,
    )

    invariant = invariant_response_model()
    flip = flip_response_model()
    if single_world_signature(invariant) != single_world_signature(flip):
        return False

    pair_constraints = (
        _scalar_constraint("Y0", potential_outcome_marginal(invariant, "0")),
        _scalar_constraint("Y1", potential_outcome_marginal(invariant, "1")),
    )
    invariant_alignment = AlignmentInput(
        ("Y0", "Y1"),
        _law_from_distribution(same_unit_counterfactual_joint(invariant)),
    )
    flip_alignment = AlignmentInput(
        ("Y0", "Y1"),
        _law_from_distribution(same_unit_counterfactual_joint(flip)),
    )
    cross_world_survives = (
        construct_from_constraints(pair_constraints, invariant_alignment)
        != construct_from_constraints(pair_constraints, flip_alignment)
    )

    even = even_parity_model()
    odd = odd_parity_model()
    if pairwise_signature(even) != pairwise_signature(odd):
        return False
    triple_constraints = tuple(
        LocalConstraint(coordinates, _law_from_distribution(law))
        for coordinates, law in pairwise_signature(even)
    )
    even_alignment = AlignmentInput(
        even.worlds,
        _law_from_distribution(even.joint),
    )
    odd_alignment = AlignmentInput(
        odd.worlds,
        _law_from_distribution(odd.joint),
    )
    higher_order_survives = (
        construct_from_constraints(triple_constraints, even_alignment)
        != construct_from_constraints(triple_constraints, odd_alignment)
    )
    return cross_world_survives and higher_order_survives


def _family_constraints(family: object) -> tuple[LocalConstraint, ...]:
    from tools.relay_theory_local_global_compatibility import (
        canonical_pair_law,
        validate_family,
    )

    validate_family(family)
    return tuple(
        LocalConstraint(
            context_law.context,
            _law_from_distribution(canonical_pair_law(context_law.law)),
        )
        for context_law in family.contexts
    )


def _certificate_from_global_witness(witness: object) -> RealizabilityCertificate:
    from tools.relay_theory_local_global_compatibility import canonical_global_law

    return RealizabilityCertificate(
        AlignmentInput(
            witness.worlds,
            _law_from_distribution(canonical_global_law(witness)),
        )
    )


def construct_global_from_certificate(
    family: object,
    certificate: RealizabilityCertificate,
) -> ExactLaw:
    family_worlds = tuple(family.worlds)
    if set(family_worlds) != set(certificate.alignment.contexts):
        raise ValueError("certificate contexts must match local-family worlds")
    return construct_from_constraints(
        _family_constraints(family),
        certificate.alignment,
    )


def gluing_is_partial_construction_with_certificate() -> bool:
    from tools.relay_theory_local_global_compatibility import (
        anti_triangle,
        equality_witness,
        support_obstruction_proves_nonextendable,
    )
    from tools.relay_theory_probability_mass_gluing import (
        boundary_family,
        disagreement_certificate_rejects,
        negative_family,
        sharp_boundary_witness,
    )

    boundary = boundary_family()
    boundary_certificate = _certificate_from_global_witness(sharp_boundary_witness())
    positive = construct_global_from_certificate(
        boundary,
        boundary_certificate,
    ) == boundary_certificate.alignment.joint

    negative = negative_family()
    rejected_negative = False
    try:
        construct_global_from_certificate(negative, boundary_certificate)
    except ValueError:
        rejected_negative = True

    anti = anti_triangle()
    rejected_support = False
    try:
        construct_global_from_certificate(
            anti,
            _certificate_from_global_witness(equality_witness()),
        )
    except ValueError:
        rejected_support = True

    return (
        positive
        and rejected_negative
        and disagreement_certificate_rejects(negative)
        and rejected_support
        and support_obstruction_proves_nonextendable(anti)
    )


def access_specification_replaces_named_frame() -> bool:
    left = AccessSpec(
        "frame-left",
        observations=("p",),
        admissible_commands=("t",),
        visible_information=("h",),
    )
    renamed = AccessSpec(
        "frame-right",
        observations=("p",),
        admissible_commands=("t",),
        visible_information=("h",),
    )
    coarse = AccessSpec(
        "coarse",
        observations=("p",),
        admissible_commands=("t",),
        visible_information=("h",),
    )
    rich = AccessSpec(
        "rich",
        observations=("p", "q"),
        admissible_commands=("t",),
        visible_information=("h",),
    )
    return (
        access_equivalent(left, renamed)
        and access_forgetting(coarse, rich)
        and not access_forgetting(rich, coarse)
    )


def quotient_is_derived_from_access_and_behavior() -> bool:
    choice = _scheduler_experiment()
    clone = FiniteExperiment(
        "choice-clone",
        choice.base_law,
        choice.commands,
        choice.responses,
        choice.observation_values,
    )
    fixed = FiniteExperiment("fixed", choice.base_law)

    no_choice = AccessSpec("no-choice")
    choice_access = AccessSpec(
        "choice",
        admissible_commands=("choose-left", "choose-right"),
    )
    coarse_partition = derived_behavioral_partition(
        (choice, clone, fixed),
        no_choice,
    )
    rich_partition = derived_behavioral_partition(
        (choice, clone, fixed),
        choice_access,
    )
    return (
        coarse_partition["scheduler-adapter"] == coarse_partition["fixed"]
        and rich_partition["scheduler-adapter"] == rich_partition["choice-clone"]
        and rich_partition["scheduler-adapter"] != rich_partition["fixed"]
    )


def markov_structure_is_derived() -> bool:
    from tools.relay_theory_markov_reconstruction import (
        UNIT_VALUE,
        category_laws_hold,
        copy_comonoid_laws_hold,
        distribution_kernel,
        stochastic_copy_naturality_fails,
    )
    from tools.relay_theory_scheduler_nondeterminism import exact_distribution

    distribution = exact_distribution(
        {"L": Fraction(1, 2), "R": Fraction(1, 2)}
    )
    law = canonical_exact_law(dict(distribution))
    state = distribution_kernel(("L", "R"), distribution)
    return (
        law == distribution
        and state.row(UNIT_VALUE) == distribution
        and category_laws_hold()
        and copy_comonoid_laws_hold(("0", "1"))
        and stochastic_copy_naturality_fails()
    )


def exact_equality_boundary_survives() -> bool:
    same_support_left = canonical_exact_law(
        {"L": Fraction(1, 2), "R": Fraction(1, 2)}
    )
    same_support_right = canonical_exact_law(
        {"L": Fraction(3, 4), "R": Fraction(1, 4)}
    )
    rejected_float = False
    try:
        canonical_exact_law({"L": 0.5, "R": 0.5})  # type: ignore[arg-type]
    except TypeError:
        rejected_float = True
    return same_support_left != same_support_right and rejected_float


def historical_reconstruction_audit() -> dict[str, bool]:
    """Re-run every first-cycle executable family as a dependency audit."""
    from tools.relay_theory_causal_substitution import (
        run_causal_substitution_comparison,
    )
    from tools.relay_theory_correlation_authority import (
        run_correlation_authority_comparison,
    )
    from tools.relay_theory_cross_world_coupling import (
        run_cross_world_coupling_comparison,
    )
    from tools.relay_theory_frame_reindexing import run_frame_reindexing
    from tools.relay_theory_higher_order_coupling import (
        run_higher_order_coupling_comparison,
    )
    from tools.relay_theory_local_global_compatibility import (
        run_local_global_compatibility,
    )
    from tools.relay_theory_markov_reconstruction import run_markov_reconstruction
    from tools.relay_theory_mechanism_factorization import (
        run_mechanism_factorization_comparison,
    )
    from tools.relay_theory_multi_authority_choice import (
        run_multi_authority_comparison,
    )
    from tools.relay_theory_probability_mass_gluing import (
        run_probability_mass_gluing,
    )
    from tools.relay_theory_scheduler_nondeterminism import (
        run_scheduler_comparison,
    )

    runners = {
        "exact-and-selectable": run_scheduler_comparison,
        "multi-authority": run_multi_authority_comparison,
        "correlation-authority": run_correlation_authority_comparison,
        "mechanism-substitution": run_causal_substitution_comparison,
        "hidden-factorization": run_mechanism_factorization_comparison,
        "cross-world-alignment": run_cross_world_coupling_comparison,
        "higher-order-alignment": run_higher_order_coupling_comparison,
        "support-gluing": run_local_global_compatibility,
        "probability-mass-gluing": run_probability_mass_gluing,
        "markov-reconstruction": run_markov_reconstruction,
        "frame-reindexing": run_frame_reindexing,
    }
    return {
        name: bool(results) and all(result.passed for result in results)
        for name, runner in runners.items()
        for results in (runner(),)
    }


def necessity_matrix() -> dict[str, bool]:
    """Bounded witness matrix for every surviving role/law in #2396 A10."""
    return {
        "exact stochastic mass": exact_equality_boundary_survives(),
        "selectable family": transformation_interface_unifies_choice_and_intervention(),
        "information/admissibility": information_reduces_to_access_specification(),
        "experiment transformation": transformation_interface_unifies_choice_and_intervention(),
        "alignment/coupling input": alignment_is_explicit_transform_input(),
        "realizability domain/certificate": gluing_is_partial_construction_with_certificate(),
        "pure forgetting": access_specification_replaces_named_frame(),
        "exact equality boundary": exact_equality_boundary_survives(),
    }


def minimal_interface_basis_0_1() -> tuple[str, ...]:
    return (
        "ACCESS_SPECIFICATION",
        "EXACT_RESOLVED_BEHAVIOR",
        "EXPERIMENT_TRANSFORMATION",
        "EXPLICIT_ALIGNMENT_INPUT",
        "REALIZABILITY_DOMAIN_CERTIFICATE",
        "EXACT_EQUALITY_BOUNDARY",
    )


def derived_structures_0_1() -> tuple[str, ...]:
    return (
        "BEHAVIORAL_QUOTIENT",
        "PURE_FORGETTING_REINDEXING",
        "FINSTOCH_MARKOV_SLICE",
    )


def axiom_extraction_verdicts() -> tuple[str, ...]:
    checks = (
        (
            "TRANSFORMATION_INTERFACE_UNIFIES_CHOICE_AND_INTERVENTION",
            transformation_interface_unifies_choice_and_intervention(),
        ),
        (
            "AUTHORITY_REDUCES_TO_TRANSFORM_ADMISSIBILITY",
            authority_reduces_to_transform_admissibility(),
        ),
        (
            "INFORMATION_REDUCES_TO_ACCESS_SPECIFICATION",
            information_reduces_to_access_specification(),
        ),
        (
            "ALIGNMENT_IS_EXPLICIT_TRANSFORM_INPUT",
            alignment_is_explicit_transform_input(),
        ),
        (
            "GLUING_IS_PARTIAL_CONSTRUCTION_WITH_CERTIFICATE",
            gluing_is_partial_construction_with_certificate(),
        ),
        (
            "FRAME_REDUCES_TO_ACCESS_SPECIFICATION",
            access_specification_replaces_named_frame(),
        ),
        (
            "QUOTIENT_IS_DERIVED",
            quotient_is_derived_from_access_and_behavior(),
        ),
        ("MARKOV_STRUCTURE_IS_DERIVED", markov_structure_is_derived()),
        (
            "EXACT_EQUALITY_BOUNDARY_SURVIVES",
            exact_equality_boundary_survives(),
        ),
    )
    verdicts = tuple(name for name, passed in checks if passed)
    if (
        len(verdicts) == len(checks)
        and all(necessity_matrix().values())
        and all(historical_reconstruction_audit().values())
    ):
        verdicts = (*verdicts, "MINIMAL_INTERFACE_BASIS_0_1")
    return verdicts


def run_axiom_extraction() -> tuple[ExtractionResult, ...]:
    checks = (
        (
            "TRANSFORMATION_INTERFACE_UNIFIES_CHOICE_AND_INTERVENTION",
            transformation_interface_unifies_choice_and_intervention(),
        ),
        (
            "AUTHORITY_REDUCES_TO_TRANSFORM_ADMISSIBILITY",
            authority_reduces_to_transform_admissibility(),
        ),
        (
            "INFORMATION_REDUCES_TO_ACCESS_SPECIFICATION",
            information_reduces_to_access_specification(),
        ),
        ("HIDDEN_FACTORIZATION_IS_ACCESS_RELATIVE", factorization_is_access_relative()),
        (
            "ALIGNMENT_IS_EXPLICIT_TRANSFORM_INPUT",
            alignment_is_explicit_transform_input(),
        ),
        (
            "GLUING_IS_PARTIAL_CONSTRUCTION_WITH_CERTIFICATE",
            gluing_is_partial_construction_with_certificate(),
        ),
        (
            "FRAME_REDUCES_TO_ACCESS_SPECIFICATION",
            access_specification_replaces_named_frame(),
        ),
        (
            "QUOTIENT_IS_DERIVED",
            quotient_is_derived_from_access_and_behavior(),
        ),
        ("MARKOV_STRUCTURE_IS_DERIVED", markov_structure_is_derived()),
        (
            "EXACT_EQUALITY_BOUNDARY_SURVIVES",
            exact_equality_boundary_survives(),
        ),
        (
            "FIRST_CYCLE_RECONSTRUCTS",
            all(historical_reconstruction_audit().values()),
        ),
        (
            "NECESSITY_MATRIX_COVERED",
            all(necessity_matrix().values()),
        ),
    )
    results = tuple(ExtractionResult(name, passed) for name, passed in checks)
    minimum = all(result.passed for result in results)
    return (
        *results,
        ExtractionResult(
            "MINIMAL_INTERFACE_BASIS_0_1",
            minimum,
            ",".join(minimal_interface_basis_0_1()) if minimum else "",
        ),
    )
