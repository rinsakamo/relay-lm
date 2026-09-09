"""Exact bounded frame-change Grand Null apparatus for Relay Theory #2392.

This module does not assume that Operational Frames form a category or that
Relay Theory is a fibration. It first earns one smaller class of frame changes:
pure observational forgetting between finite probe families. It then reuses
previous Relay Theory counterexamples to show where scheduler semantics,
authority, intervention, counterfactual alignment, and gluing are not the same
operation as forgetting information.

Research apparatus only; no RelayLM runtime authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

from tools.relay_theory_markov_reconstruction import (
    ExactKernel,
    compose,
    copy_kernel,
    deterministic_kernel,
    discard_kernel,
    exact_kernel,
    identity_kernel,
    tensor,
)

SchedulerClass = Literal["deterministic", "randomized"]


@dataclass(frozen=True)
class OperationalFrame:
    """Declared bounded access surface used by this transaction."""

    name: str
    probes: tuple[str, ...] = ()
    scheduler_visible: tuple[str, ...] = ()
    scheduler_class: SchedulerClass = "deterministic"
    writable_ports: tuple[str, ...] = ()
    interventions: tuple[str, ...] = ()
    alignment_arity: int = 1

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("frame name must be non-empty")
        for field_name, values in (
            ("probes", self.probes),
            ("scheduler_visible", self.scheduler_visible),
            ("writable_ports", self.writable_ports),
            ("interventions", self.interventions),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} entries must be unique")
            if any(not value for value in values):
                raise ValueError(f"{field_name} entries must be non-empty")
        if self.scheduler_class not in {"deterministic", "randomized"}:
            raise ValueError("unsupported scheduler class")
        if self.alignment_arity < 1:
            raise ValueError("alignment arity must be positive")


@dataclass(frozen=True)
class FrameResult:
    name: str
    passed: bool
    detail: str = ""

    def __post_init__(self) -> None:
        if type(self.passed) is not bool:
            raise TypeError("FrameResult.passed must be strict bool")


@dataclass(frozen=True)
class ProbeSystem:
    """Finite state set with exact declared probe values."""

    states: tuple[str, ...]
    values: Mapping[str, Mapping[str, str]]

    def __post_init__(self) -> None:
        if not self.states or len(set(self.states)) != len(self.states):
            raise ValueError("states must be finite, non-empty, and unique")
        if set(self.values) != set(self.states):
            raise ValueError("probe values must cover every declared state")
        for state in self.states:
            if any(not probe or not value for probe, value in self.values[state].items()):
                raise ValueError("probe names and values must be non-empty")


def _signature(system: ProbeSystem, state: str, frame: OperationalFrame) -> tuple[str, ...]:
    if state not in system.values:
        raise ValueError(f"undeclared state: {state!r}")
    missing = set(frame.probes) - set(system.values[state])
    if missing:
        raise ValueError(f"missing declared probes for {state!r}: {sorted(missing)}")
    return tuple(system.values[state][probe] for probe in frame.probes)


def behavioral_partition(
    system: ProbeSystem, frame: OperationalFrame
) -> dict[str, str]:
    """Canonical exact quotient by equality of declared probe signatures."""
    signatures = {_signature(system, state, frame) for state in system.states}
    block_for = {
        signature: f"b{index}"
        for index, signature in enumerate(sorted(signatures))
    }
    return {
        state: block_for[_signature(system, state, frame)]
        for state in system.states
    }


def pure_forgetting(coarse: OperationalFrame, rich: OperationalFrame) -> bool:
    """Whether rich->coarse changes only by forgetting observational probes."""
    return (
        set(coarse.probes).issubset(rich.probes)
        and coarse.scheduler_visible == rich.scheduler_visible
        and coarse.scheduler_class == rich.scheduler_class
        and coarse.writable_ports == rich.writable_ports
        and coarse.interventions == rich.interventions
        and coarse.alignment_arity == rich.alignment_arity
    )


def quotient_forgetting_map(
    system: ProbeSystem,
    rich: OperationalFrame,
    coarse: OperationalFrame,
) -> dict[str, str]:
    """Map rich quotient blocks to coarse blocks, failing if not well-defined."""
    if not pure_forgetting(coarse, rich):
        raise ValueError("frame change is not pure observational forgetting")
    rich_partition = behavioral_partition(system, rich)
    coarse_partition = behavioral_partition(system, coarse)
    mapping: dict[str, str] = {}
    for state in system.states:
        source = rich_partition[state]
        target = coarse_partition[state]
        existing = mapping.setdefault(source, target)
        if existing != target:
            raise ValueError("forgetting map is not representative-independent")
    return mapping


def compose_block_maps(
    after: Mapping[str, str], before: Mapping[str, str]
) -> dict[str, str]:
    if set(before.values()) - set(after):
        raise ValueError("block maps are not composable")
    return {source: after[mid] for source, mid in before.items()}


def probe_refinement_fixture() -> tuple[
    ProbeSystem, OperationalFrame, OperationalFrame, OperationalFrame
]:
    system = ProbeSystem(
        states=("s0", "s1", "s2", "s3"),
        values={
            "s0": {"coarse": "A", "detail": "0", "audit": "left"},
            "s1": {"coarse": "A", "detail": "1", "audit": "left"},
            "s2": {"coarse": "B", "detail": "0", "audit": "right"},
            "s3": {"coarse": "B", "detail": "0", "audit": "left"},
        },
    )
    omega0 = OperationalFrame("omega0", probes=("coarse",))
    omega1 = OperationalFrame("omega1", probes=("coarse", "detail"))
    omega2 = OperationalFrame(
        "omega2", probes=("coarse", "detail", "audit")
    )
    return system, omega0, omega1, omega2


def probe_refinement_is_monotone() -> bool:
    system, coarse, rich, _ = probe_refinement_fixture()
    coarse_partition = behavioral_partition(system, coarse)
    rich_partition = behavioral_partition(system, rich)
    for left in system.states:
        for right in system.states:
            if rich_partition[left] == rich_partition[right]:
                if coarse_partition[left] != coarse_partition[right]:
                    return False
    return len(set(rich_partition.values())) > len(set(coarse_partition.values()))


def probe_forgetting_is_functorial() -> bool:
    system, omega0, omega1, omega2 = probe_refinement_fixture()
    f10 = quotient_forgetting_map(system, omega1, omega0)
    f21 = quotient_forgetting_map(system, omega2, omega1)
    f20 = quotient_forgetting_map(system, omega2, omega0)
    identity = quotient_forgetting_map(system, omega2, omega2)
    return (
        compose_block_maps(f10, f21) == f20
        and identity == {block: block for block in identity}
    )


def noncomparable_probe_frames_survive() -> bool:
    left = OperationalFrame("left", probes=("p",))
    right = OperationalFrame("right", probes=("q",))
    return not pure_forgetting(left, right) and not pure_forgetting(right, left)


def scheduler_information_changes_policy_space() -> bool:
    from tools.relay_theory_scheduler_nondeterminism import policy_is_observation_based

    h0 = ("start", "left-history")
    h1 = ("start", "right-history")
    policy = {h0: "a", h1: "b"}
    coarse_observation = {h0: "same", h1: "same"}
    rich_observation = {h0: "left", h1: "right"}
    coarse = OperationalFrame("hidden", scheduler_visible=("public",))
    rich = OperationalFrame("visible", scheduler_visible=("public", "history"))
    return (
        not policy_is_observation_based(policy, coarse_observation)
        and policy_is_observation_based(policy, rich_observation)
        and not pure_forgetting(coarse, rich)
    )


def scheduler_class_is_not_probe_forgetting() -> bool:
    from tools.relay_theory_scheduler_nondeterminism import (
        Alternative,
        ChoiceState,
        behavior_equivalent,
        exact_distribution,
    )

    delta_l = exact_distribution({"L": Fraction(1)})
    delta_r = exact_distribution({"R": Fraction(1)})
    half = exact_distribution({"L": Fraction(1, 2), "R": Fraction(1, 2)})
    endpoints = ChoiceState(
        "endpoints",
        (Alternative("l", delta_l), Alternative("r", delta_r)),
    )
    explicit_mix = ChoiceState(
        "explicit-mix",
        (
            Alternative("l", delta_l),
            Alternative("r", delta_r),
            Alternative("m", half),
        ),
    )
    deterministic = OperationalFrame("det", scheduler_class="deterministic")
    randomized = OperationalFrame("rand", scheduler_class="randomized")
    return (
        not behavior_equivalent(endpoints, explicit_mix, "deterministic")
        and behavior_equivalent(endpoints, explicit_mix, "randomized")
        and not pure_forgetting(deterministic, randomized)
        and not pure_forgetting(randomized, deterministic)
    )


def authority_change_is_not_probe_forgetting() -> bool:
    """Adding write authority creates attainable interventions, not observations."""
    read_only = OperationalFrame("read-only", writable_ports=())
    write_x = OperationalFrame("write-x", writable_ports=("X",))
    initial = ("0", "0")

    def reachable(frame: OperationalFrame) -> set[tuple[str, str]]:
        results = {initial}
        if "X" in frame.writable_ports:
            results.add(("1", initial[1]))
        if "Y" in frame.writable_ports:
            results.add((initial[0], "1"))
        return results

    return (
        reachable(read_only) < reachable(write_x)
        and not pure_forgetting(read_only, write_x)
    )


def intervention_requires_transformation_layer() -> bool:
    from tools.relay_theory_causal_substitution import run_causal_substitution_comparison

    results = {
        result.name: result.passed
        for result in run_causal_substitution_comparison()
    }
    observational = OperationalFrame("obs")
    interventional = OperationalFrame("do-x", interventions=("do(X)",))
    return (
        results[
            "OBSERVATIONAL_EQUIVALENCE_DOES_NOT_IMPLY_INTERVENTIONAL_EQUIVALENCE"
        ]
        and results["FIXED_SUBSTITUTION_RECOVERS_ONE_EXACT_STOCHASTIC_LAW"]
        and not pure_forgetting(observational, interventional)
    )


def counterfactual_requires_alignment_layer() -> bool:
    from tools.relay_theory_cross_world_coupling import (
        run_cross_world_coupling_comparison,
    )

    results = {
        result.name: result.passed
        for result in run_cross_world_coupling_comparison()
    }
    single = OperationalFrame("single", alignment_arity=1)
    pair = OperationalFrame("pair", alignment_arity=2)
    return (
        results["COMPLETE_BINARY_HARD_INTERVENTION_FAMILY_MATCHES"]
        and results[
            "ENTIRE_BERNOULLI_SOFT_INTERVENTION_FAMILY_MATCHES_SYMBOLICALLY"
        ]
        and results["SAME_UNIT_CROSS_WORLD_COUPLING_DIFFERS"]
        and not pure_forgetting(single, pair)
    )


def gluing_requires_realizability_certificate() -> bool:
    from tools.relay_theory_probability_mass_gluing import run_probability_mass_gluing

    results = {
        result.name: result.passed for result in run_probability_mass_gluing()
    }
    return (
        results["NEGATIVE_LOCAL_LAWS_ARE_OVERLAP_CONSISTENT"]
        and results["NEGATIVE_SUPPORT_IS_MAXIMALLY_PERMISSIVE"]
        and results["MASS_CERTIFICATE_REJECTS_FULL_SUPPORT_NEGATIVE"]
    )


def coarse_graining_kernel() -> ExactKernel:
    rich = ("a0", "a1", "b0")
    coarse = ("A", "B")
    return deterministic_kernel(
        rich,
        coarse,
        {"a0": "A", "a1": "A", "b0": "B"},
    )


def pure_forgetting_preserves_markov_slice() -> bool:
    """Bounded preservation law for a genuine deterministic coarse graining."""
    source = ("x0", "x1")
    rich_target = ("a0", "a1", "b0")
    channel = exact_kernel(
        source,
        rich_target,
        {
            "x0": {"a0": Fraction(1, 2), "a1": Fraction(1, 4), "b0": Fraction(1, 4)},
            "x1": {"a0": Fraction(1, 6), "a1": Fraction(1, 3), "b0": Fraction(1, 2)},
        },
    )
    forget = coarse_graining_kernel()
    coarse_channel = compose(forget, channel)

    context = exact_kernel(
        ("c",),
        ("u", "v"),
        {"c": {"u": Fraction(2, 5), "v": Fraction(3, 5)}},
    )
    tensor_left = compose(
        tensor(forget, identity_kernel(context.target)),
        tensor(channel, context),
    )
    tensor_right = tensor(coarse_channel, context)

    copy_preserved = compose(copy_kernel(forget.target), forget) == compose(
        tensor(forget, forget), copy_kernel(forget.source)
    )
    discard_preserved = compose(discard_kernel(forget.target), forget) == discard_kernel(
        forget.source
    )
    identity_preserved = compose(identity_kernel(forget.target), forget) == forget
    return tensor_left == tensor_right and copy_preserved and discard_preserved and identity_preserved


def anti_smuggling_fail_closed() -> bool:
    """Capability-changing frames must not be accepted as pure reindexing."""
    base = OperationalFrame("base", probes=("p",))
    changed = (
        OperationalFrame("scheduler", probes=("p",), scheduler_class="randomized"),
        OperationalFrame("visible", probes=("p",), scheduler_visible=("h",)),
        OperationalFrame("writer", probes=("p",), writable_ports=("X",)),
        OperationalFrame("do", probes=("p",), interventions=("do(X)",)),
        OperationalFrame("worlds", probes=("p",), alignment_arity=2),
    )
    return all(not pure_forgetting(base, frame) for frame in changed)


def frame_reindexing_core_survives() -> bool:
    return all(
        (
            probe_refinement_is_monotone(),
            probe_forgetting_is_functorial(),
            noncomparable_probe_frames_survive(),
            pure_forgetting_preserves_markov_slice(),
            anti_smuggling_fail_closed(),
        )
    )


def heterogeneous_outer_changes_survive() -> bool:
    return all(
        (
            scheduler_information_changes_policy_space(),
            scheduler_class_is_not_probe_forgetting(),
            authority_change_is_not_probe_forgetting(),
            intervention_requires_transformation_layer(),
            counterfactual_requires_alignment_layer(),
            gluing_requires_realizability_certificate(),
        )
    )


def frame_change_verdicts() -> tuple[str, ...]:
    verdicts: list[str] = []
    if probe_forgetting_is_functorial():
        verdicts.append("FRAME_REFINEMENT_IS_FUNCTORIAL")
    if frame_reindexing_core_survives():
        verdicts.append("FRAME_INDEXED_MARKOV_SLICES_SURVIVE")
    if intervention_requires_transformation_layer():
        verdicts.append("INTERVENTION_REQUIRES_TRANSFORMATION_LAYER")
    if counterfactual_requires_alignment_layer():
        verdicts.append("COUNTERFACTUAL_EXTENSION_REQUIRES_ALIGNMENT_LAYER")
    if gluing_requires_realizability_certificate():
        verdicts.append("GLUING_REQUIRES_REALIZABILITY_CERTIFICATE")
    if not verdicts:
        return ("UNDERDETERMINED",)
    return tuple(verdicts)


def run_frame_reindexing() -> tuple[FrameResult, ...]:
    checks = (
        FrameResult("RICH_PROBE_EQUIVALENCE_IMPLIES_COARSE_EQUIVALENCE", probe_refinement_is_monotone()),
        FrameResult("PURE_PROBE_FORGETTING_COMPOSES", probe_forgetting_is_functorial()),
        FrameResult("NONCOMPARABLE_FRAMES_ARE_NOT_FORCED_INTO_TOTAL_ORDER", noncomparable_probe_frames_survive()),
        FrameResult("SCHEDULER_INFORMATION_CHANGES_POLICY_SPACE", scheduler_information_changes_policy_space()),
        FrameResult("SCHEDULER_CLASS_CHANGE_IS_NOT_PROBE_FORGETTING", scheduler_class_is_not_probe_forgetting()),
        FrameResult("WRITE_AUTHORITY_CHANGE_IS_NOT_PROBE_FORGETTING", authority_change_is_not_probe_forgetting()),
        FrameResult("INTERVENTION_REQUIRES_TRANSFORMATION_LAYER", intervention_requires_transformation_layer()),
        FrameResult("COUNTERFACTUAL_EXTENSION_REQUIRES_ALIGNMENT_LAYER", counterfactual_requires_alignment_layer()),
        FrameResult("GLUING_REQUIRES_REALIZABILITY_CERTIFICATE", gluing_requires_realizability_certificate()),
        FrameResult("PURE_FORGETTING_PRESERVES_BOUNDED_MARKOV_SLICE", pure_forgetting_preserves_markov_slice()),
        FrameResult("CAPABILITY_CHANGES_FAIL_CLOSED_AS_REINDEXING", anti_smuggling_fail_closed()),
    )
    verdicts = frame_change_verdicts()
    return (
        *checks,
        FrameResult(
            "FRAME_INDEXED_MARKOV_SLICES_SURVIVE",
            "FRAME_INDEXED_MARKOV_SLICES_SURVIVE" in verdicts,
            ",".join(verdicts),
        ),
    )
