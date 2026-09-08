"""Exact finite hidden-factorization Grand Null apparatus for Relay Theory #2368.

Research falsification only. This module asks whether different *internal* causal
realisations remain operationally distinct after the observation and mechanism-
substitution interface is fixed. It deliberately reuses the bounded binary causal
fixture from #2364; neither DAG syntax nor the exposed interface defined here is a
claimed Relay Theory primitive.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction

from tools.relay_theory_causal_substitution import (
    CausalModel,
    Exogenous,
    JointLaw,
    copy_mechanism,
    direct_xy_model,
    evaluate_model,
    fair_binary,
    hard_intervene,
    stochastic_root_mechanism,
    substitute_mechanism,
    validate_causal_model,
)


@dataclass(frozen=True)
class ExposedCausalInterface:
    name: str
    model: CausalModel
    visible: tuple[str, ...]
    replaceable: tuple[str, ...]
    soft_probabilities: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(3, 4))


@dataclass(frozen=True)
class FactorizationResult:
    name: str
    passed: bool
    detail: str


def _canonical_names(names: Sequence[str]) -> tuple[str, ...]:
    canonical = tuple(sorted(names))
    if not canonical:
        raise ValueError("interface variable set must be non-empty")
    if len(canonical) != len(set(canonical)):
        raise ValueError("interface variable names must be unique")
    return canonical


def project_joint(law: JointLaw, visible: Sequence[str]) -> JointLaw:
    """Marginalise a full endogenous joint law to declared exposed variables."""
    visible_names = _canonical_names(visible)
    accumulated: dict[tuple[tuple[str, str], ...], Fraction] = {}
    for assignment, mass in law:
        values = dict(assignment)
        missing = [name for name in visible_names if name not in values]
        if missing:
            raise ValueError(f"joint law is missing visible variables: {missing}")
        projected = tuple((name, values[name]) for name in visible_names)
        accumulated[projected] = accumulated.get(projected, Fraction(0)) + mass

    if sum(accumulated.values(), Fraction(0)) != 1:
        raise ValueError("projected joint law must normalize exactly")
    return tuple(sorted(accumulated.items(), key=repr))


def validate_interface(interface: ExposedCausalInterface) -> None:
    validate_causal_model(interface.model)
    visible = _canonical_names(interface.visible)
    replaceable = _canonical_names(interface.replaceable)
    endogenous = {mechanism.target for mechanism in interface.model.mechanisms}

    if not set(visible) <= endogenous:
        raise ValueError("visible variables must be endogenous model targets")
    if not set(replaceable) <= endogenous:
        raise ValueError("replaceable variables must be endogenous model targets")
    for probability_one in interface.soft_probabilities:
        if not isinstance(probability_one, Fraction):
            raise TypeError("soft replacement probabilities must be fractions.Fraction")
        if probability_one < 0 or probability_one > 1:
            raise ValueError("soft replacement probabilities must lie in [0, 1]")


def evaluate_exposed(interface: ExposedCausalInterface) -> JointLaw:
    validate_interface(interface)
    return project_joint(evaluate_model(interface.model), interface.visible)


def exposed_hard_responses(
    interface: ExposedCausalInterface,
) -> tuple[tuple[tuple[str, str], JointLaw], ...]:
    validate_interface(interface)
    return tuple(
        (
            (target, value),
            project_joint(
                evaluate_model(hard_intervene(interface.model, target, value)),
                interface.visible,
            ),
        )
        for target in sorted(interface.replaceable)
        for value in ("0", "1")
    )


def exposed_soft_responses(
    interface: ExposedCausalInterface,
) -> tuple[tuple[tuple[str, Fraction], JointLaw], ...]:
    validate_interface(interface)
    responses: list[tuple[tuple[str, Fraction], JointLaw]] = []
    for target in sorted(interface.replaceable):
        for probability_one in sorted(interface.soft_probabilities):
            replacement = stochastic_root_mechanism(
                target,
                probability_one,
                label=f"soft({target},{probability_one})",
            )
            modified = substitute_mechanism(interface.model, target, replacement)
            responses.append(
                (
                    (target, probability_one),
                    project_joint(evaluate_model(modified), interface.visible),
                )
            )
    return tuple(responses)


def exposed_signature(interface: ExposedCausalInterface) -> tuple[object, ...]:
    """Exact behavior of one model under the declared exposed substitution frame."""
    validate_interface(interface)
    return (
        tuple(sorted(interface.visible)),
        tuple(sorted(interface.replaceable)),
        evaluate_exposed(interface),
        exposed_hard_responses(interface),
        exposed_soft_responses(interface),
    )


def exposed_interfaces_equivalent(
    left: ExposedCausalInterface, right: ExposedCausalInterface
) -> bool:
    return exposed_signature(left) == exposed_signature(right)


def fused_xy_model(name: str = "fused") -> CausalModel:
    return direct_xy_model(name)


def split_xy_model(name: str = "split", mediator: str = "H") -> CausalModel:
    if mediator in {"U", "X", "Y"}:
        raise ValueError("mediator must be a fresh internal variable")
    return CausalModel(
        name,
        (Exogenous("U", fair_binary()),),
        (
            copy_mechanism("X", "U", label="x-from-u"),
            copy_mechanism(mediator, "X", label="hidden-copy"),
            copy_mechanism("Y", mediator, label="y-from-hidden"),
        ),
    )


def xy_interface(model: CausalModel, *, name: str) -> ExposedCausalInterface:
    return ExposedCausalInterface(name, model, ("X", "Y"), ("X", "Y"))


def append_copy_output(
    model: CausalModel,
    source: str,
    target: str,
    *,
    name: str,
) -> CausalModel:
    validate_causal_model(model)
    existing = {mechanism.target for mechanism in model.mechanisms}
    if source not in existing:
        raise ValueError(f"unknown source target {source!r}")
    if target in existing or any(item.name == target for item in model.exogenous):
        raise ValueError("new output target must be fresh")
    result = CausalModel(
        name,
        model.exogenous,
        (*model.mechanisms, copy_mechanism(target, source, label="downstream-copy")),
    )
    validate_causal_model(result)
    return result


def composed_xyz_interface(model: CausalModel, *, name: str) -> ExposedCausalInterface:
    composed = append_copy_output(model, "Y", "Z", name=f"{model.name}-with-z")
    return ExposedCausalInterface(
        name,
        composed,
        ("X", "Y", "Z"),
        ("X", "Y", "Z"),
    )


def fused_fork_model(name: str = "fused-fork") -> CausalModel:
    return CausalModel(
        name,
        (Exogenous("U", fair_binary()),),
        (
            copy_mechanism("X", "U", label="x-from-u"),
            copy_mechanism("Y", "X", label="y-from-x"),
            copy_mechanism("Z", "X", label="z-from-x"),
        ),
    )


def split_fork_model(name: str = "split-fork", mediator: str = "H") -> CausalModel:
    if mediator in {"U", "X", "Y", "Z"}:
        raise ValueError("mediator must be a fresh internal variable")
    return CausalModel(
        name,
        (Exogenous("U", fair_binary()),),
        (
            copy_mechanism("X", "U", label="x-from-u"),
            copy_mechanism(mediator, "X", label="hidden-copy"),
            copy_mechanism("Y", mediator, label="y-from-hidden"),
            copy_mechanism("Z", mediator, label="z-from-hidden"),
        ),
    )


def hidden_mediator_reveal_law(
    model: CausalModel,
    mediator: str,
    value: str,
    visible: Sequence[str] = ("X", "Y", "Z"),
) -> JointLaw:
    return project_joint(
        evaluate_model(hard_intervene(model, mediator, value)),
        visible,
    )


def single_target_hard_laws(interface: ExposedCausalInterface) -> tuple[JointLaw, ...]:
    return tuple(law for _, law in exposed_hard_responses(interface))


def internal_mechanism_count(interface: ExposedCausalInterface) -> int:
    validate_interface(interface)
    return len(interface.model.mechanisms)


def resource_sensitive_signature(interface: ExposedCausalInterface) -> tuple[object, ...]:
    """Example richer frame that charges internal realization size."""
    return exposed_signature(interface), internal_mechanism_count(interface)


def factorization_partition(
    interfaces: Sequence[ExposedCausalInterface],
) -> dict[str, str]:
    names = [interface.name for interface in interfaces]
    if len(names) != len(set(names)):
        raise ValueError("interface names must be unique")

    signatures: list[tuple[object, ...]] = []
    partition: dict[str, str] = {}
    for interface in interfaces:
        signature = exposed_signature(interface)
        try:
            index = signatures.index(signature)
        except ValueError:
            signatures.append(signature)
            index = len(signatures) - 1
        partition[interface.name] = f"b{index}"
    return partition


def partition_is_representative_independent(
    interfaces: Sequence[ExposedCausalInterface],
    partition: Mapping[str, str],
) -> bool:
    by_name = {interface.name: interface for interface in interfaces}
    if set(partition) != set(by_name):
        raise ValueError("partition must name every interface exactly once")

    for block in set(partition.values()):
        members = [by_name[name] for name, value in partition.items() if value == block]
        reference = exposed_signature(members[0])
        if any(exposed_signature(candidate) != reference for candidate in members[1:]):
            return False
    return True


def run_mechanism_factorization_comparison() -> tuple[FactorizationResult, ...]:
    fused = xy_interface(fused_xy_model(), name="fused")
    split = xy_interface(split_xy_model(), name="split")
    renamed_split = xy_interface(
        split_xy_model(name="renamed-split", mediator="M"),
        name="renamed-split",
    )

    observational = evaluate_exposed(fused) == evaluate_exposed(split)
    hard = exposed_hard_responses(fused) == exposed_hard_responses(split)
    soft = exposed_soft_responses(fused) == exposed_soft_responses(split)
    full_black_box = exposed_interfaces_equivalent(fused, split)
    hidden_name_gauge = exposed_interfaces_equivalent(split, renamed_split)

    composed_fused = composed_xyz_interface(fused.model, name="composed-fused")
    composed_split = composed_xyz_interface(split.model, name="composed-split")
    composition = exposed_interfaces_equivalent(composed_fused, composed_split)

    narrower_domain = ExposedCausalInterface(
        "narrower-domain",
        fused.model,
        ("X", "Y"),
        ("X",),
    )
    intervention_domain = not exposed_interfaces_equivalent(fused, narrower_domain)

    fused_fork = ExposedCausalInterface(
        "fused-fork",
        fused_fork_model(),
        ("X", "Y", "Z"),
        ("X", "Y", "Z"),
    )
    split_fork = split_fork_model()
    hidden_do = hidden_mediator_reveal_law(split_fork, "H", "0")
    mediator_reveal = hidden_do not in single_target_hard_laws(fused_fork)

    resource_reveal = (
        exposed_interfaces_equivalent(fused, split)
        and resource_sensitive_signature(fused) != resource_sensitive_signature(split)
    )

    interfaces = (fused, split, renamed_split, narrower_domain)
    partition = factorization_partition(interfaces)
    quotient = (
        partition[fused.name] == partition[split.name]
        and partition[split.name] == partition[renamed_split.name]
        and partition[fused.name] != partition[narrower_domain.name]
        and partition_is_representative_independent(interfaces, partition)
    )

    return (
        FactorizationResult(
            "PROJECTED_OBSERVATIONAL_LAW_IGNORES_HIDDEN_COPY_FACTORIZATION",
            observational,
            "fused and hidden-mediator realizations induce the same exact exposed X/Y law",
        ),
        FactorizationResult(
            "EXPOSED_HARD_SUBSTITUTIONS_IGNORE_HIDDEN_COPY_FACTORIZATION",
            hard,
            "all declared single-target hard substitutions on X/Y agree exactly after projection",
        ),
        FactorizationResult(
            "EXPOSED_SOFT_SUBSTITUTIONS_IGNORE_HIDDEN_COPY_FACTORIZATION",
            soft,
            "exact stochastic root replacements on exposed X/Y agree after projection",
        ),
        FactorizationResult(
            "HIDDEN_FACTORIZATION_IS_GAUGE_WITHIN_TESTED_EXPOSED_INTERFACE",
            full_black_box,
            "the complete bounded exposed signature quotients fused and split realizations",
        ),
        FactorizationResult(
            "HIDDEN_MEDIATOR_NAME_IS_GAUGE",
            hidden_name_gauge,
            "renaming an unexposed mediator does not change exposed substitution behavior",
        ),
        FactorizationResult(
            "EXPOSED_EQUIVALENCE_SURVIVES_COMMON_DOWNSTREAM_COMPOSITION",
            composition,
            "adding the same downstream Z := Y component preserves exact exposed equivalence",
        ),
        FactorizationResult(
            "INTERVENTION_DOMAIN_IS_PART_OF_THE_INTERFACE",
            intervention_domain,
            "removing Y from the declared replaceable domain changes the exact interface signature",
        ),
        FactorizationResult(
            "EXPOSING_HIDDEN_MEDIATOR_ADDS_OPERATIONAL_POWER",
            mediator_reveal,
            "do(H=0) in a hidden-fork realization creates a joint exposed law unavailable to any one fused exposed-target intervention",
        ),
        FactorizationResult(
            "RESOURCE_PROBE_REVEALS_HIDDEN_REALIZATION",
            resource_reveal,
            "black-box substitution equivalence disappears when internal mechanism count is a declared consequence",
        ),
        FactorizationResult(
            "EXPOSED_FACTORIZATION_QUOTIENT_IS_REPRESENTATIVE_INDEPENDENT",
            quotient,
            "equivalent hidden realizations share one exact block while a different intervention domain remains separate",
        ),
    )
