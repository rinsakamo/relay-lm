"""Exact finite multi-authority / causal-port Grand Null apparatus for #2357.

Research falsification only. This is not RelayLM runtime or architecture
authority. The bounded model exposes decision ports, exact stochastic terminal
laws, information read edges, causal stages, concurrency, and named control.
It then asks which parts of named player identity survive operational probes.

Scope:
- finite scenarios with exact ``fractions.Fraction`` mass;
- finite decision ports with deterministic local policies;
- reads from scenario signals or strictly earlier decision ports;
- pure-strategy cooperative and maximin probes;
- owner-name gauge versus anonymous control-domain partition.

No claim is made that stochastic games, open games, ports, or deterministic
policies are universal Relay Theory primitives.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import product

from tools.relay_theory_scheduler_nondeterminism import (
    Distribution,
    exact_distribution,
    probability,
)

InfoKey = tuple[tuple[str, str], ...]
PortPolicy = tuple[tuple[InfoKey, str], ...]
OwnerStrategy = tuple[tuple[str, PortPolicy], ...]
PolicyProfile = tuple[tuple[str, PortPolicy], ...]
ActionAssignment = tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class DecisionPort:
    name: str
    owner: str
    stage: int
    actions: tuple[str, ...]
    reads: tuple[str, ...] = ()


@dataclass(frozen=True)
class Scenario:
    name: str
    probability: Fraction
    signals: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class OutcomeRule:
    scenario: str
    actions: ActionAssignment
    distribution: Distribution


@dataclass(frozen=True)
class PortSystem:
    name: str
    ports: tuple[DecisionPort, ...]
    scenarios: tuple[Scenario, ...]
    rules: tuple[OutcomeRule, ...]


@dataclass(frozen=True)
class AuthorityResult:
    name: str
    passed: bool
    detail: str


def signal_token(name: str) -> str:
    return f"signal:{name}"


def action_token(name: str) -> str:
    return f"action:{name}"


def canonical_actions(actions: Mapping[str, str]) -> ActionAssignment:
    return tuple(sorted(actions.items()))


def _scenario_signals(scenario: Scenario) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, value in scenario.signals:
        if name in result:
            raise ValueError(f"duplicate scenario signal {name!r}")
        result[name] = value
    return result


def validate_port_system(system: PortSystem) -> None:
    if not system.ports:
        raise ValueError("port system must declare at least one decision port")
    if not system.scenarios:
        raise ValueError("port system must declare at least one scenario")

    ports = {port.name: port for port in system.ports}
    if len(ports) != len(system.ports):
        raise ValueError("decision port names must be unique")

    for port in system.ports:
        if not port.owner:
            raise ValueError("decision port owner must be non-empty")
        if port.stage < 0:
            raise ValueError("decision port stage must be non-negative")
        if not port.actions or len(set(port.actions)) != len(port.actions):
            raise ValueError("decision port actions must be non-empty and unique")
        if len(set(port.reads)) != len(port.reads):
            raise ValueError("decision port reads must be unique")
        for token in port.reads:
            kind, sep, target = token.partition(":")
            if not sep or not target:
                raise ValueError(f"invalid read token {token!r}")
            if kind == "signal":
                continue
            if kind != "action" or target not in ports:
                raise ValueError(f"unknown read target {token!r}")
            if ports[target].stage >= port.stage:
                raise ValueError(
                    "a decision port may read only strictly earlier action ports"
                )

    scenario_names: set[str] = set()
    scenario_total = Fraction(0)
    for scenario in system.scenarios:
        if scenario.name in scenario_names:
            raise ValueError("scenario names must be unique")
        scenario_names.add(scenario.name)
        if not isinstance(scenario.probability, Fraction):
            raise TypeError("scenario probability must be fractions.Fraction")
        if scenario.probability <= 0 or scenario.probability > 1:
            raise ValueError("scenario probabilities must lie in (0, 1]")
        scenario_total += scenario.probability
        _scenario_signals(scenario)
    if scenario_total != 1:
        raise ValueError("scenario probabilities must sum exactly to 1")

    port_names = tuple(port.name for port in system.ports)
    expected_assignments = tuple(
        canonical_actions(dict(zip(port_names, choices, strict=True)))
        for choices in product(*(port.actions for port in system.ports))
    )
    expected_keys = {
        (scenario.name, assignment)
        for scenario in system.scenarios
        for assignment in expected_assignments
    }

    seen: set[tuple[str, ActionAssignment]] = set()
    for rule in system.rules:
        key = (rule.scenario, rule.actions)
        if key in seen:
            raise ValueError("outcome rules must be unique per scenario/action profile")
        seen.add(key)
        if rule.scenario not in scenario_names:
            raise ValueError(f"unknown rule scenario {rule.scenario!r}")
        if rule.actions not in expected_assignments:
            raise ValueError("outcome rule must assign every port exactly once")
        exact_distribution(dict(rule.distribution))
    if seen != expected_keys:
        raise ValueError("outcome rules must be total over scenarios and actions")


def _prior_assignments(
    system: PortSystem, port: DecisionPort
) -> tuple[dict[str, str], ...]:
    prior = tuple(candidate for candidate in system.ports if candidate.stage < port.stage)
    if not prior:
        return ({},)
    names = tuple(candidate.name for candidate in prior)
    return tuple(
        dict(zip(names, choices, strict=True))
        for choices in product(*(candidate.actions for candidate in prior))
    )


def information_key(
    system: PortSystem,
    port: DecisionPort,
    scenario: Scenario,
    prior_actions: Mapping[str, str],
) -> InfoKey:
    scenario_signals = _scenario_signals(scenario)
    values: list[tuple[str, str]] = []
    for token in sorted(port.reads):
        kind, _, target = token.partition(":")
        if kind == "signal":
            if target not in scenario_signals:
                raise ValueError(
                    f"scenario {scenario.name!r} lacks readable signal {target!r}"
                )
            values.append((token, scenario_signals[target]))
        elif kind == "action":
            if target not in prior_actions:
                raise ValueError(f"prior action {target!r} is unavailable")
            values.append((token, prior_actions[target]))
        else:
            raise ValueError(f"invalid read token {token!r}")
    return tuple(values)


def port_information_sets(system: PortSystem, port_name: str) -> tuple[InfoKey, ...]:
    validate_port_system(system)
    by_name = {port.name: port for port in system.ports}
    if port_name not in by_name:
        raise ValueError(f"unknown port {port_name!r}")
    port = by_name[port_name]
    keys = {
        information_key(system, port, scenario, prior)
        for scenario in system.scenarios
        for prior in _prior_assignments(system, port)
    }
    return tuple(sorted(keys, key=repr))


def enumerate_port_policies(system: PortSystem, port_name: str) -> tuple[PortPolicy, ...]:
    port = next(port for port in system.ports if port.name == port_name)
    info_sets = port_information_sets(system, port_name)
    return tuple(
        tuple(zip(info_sets, choices, strict=True))
        for choices in product(port.actions, repeat=len(info_sets))
    )


def owners(system: PortSystem) -> tuple[str, ...]:
    validate_port_system(system)
    return tuple(sorted({port.owner for port in system.ports}))


def enumerate_owner_strategies(system: PortSystem, owner: str) -> tuple[OwnerStrategy, ...]:
    validate_port_system(system)
    controlled = tuple(port for port in system.ports if port.owner == owner)
    if not controlled:
        raise ValueError(f"owner {owner!r} controls no decision ports")
    spaces = tuple(enumerate_port_policies(system, port.name) for port in controlled)
    return tuple(
        tuple((controlled[index].name, policy) for index, policy in enumerate(policies))
        for policies in product(*spaces)
    )


def _combine_owner_strategies(strategies: Sequence[OwnerStrategy]) -> PolicyProfile:
    combined: dict[str, PortPolicy] = {}
    for strategy in strategies:
        for port_name, policy in strategy:
            if port_name in combined:
                raise ValueError(f"multiple strategies control port {port_name!r}")
            combined[port_name] = policy
    return tuple(sorted(combined.items()))


def action_profile_for_scenario(
    system: PortSystem, profile: PolicyProfile, scenario: Scenario
) -> ActionAssignment:
    validate_port_system(system)
    policies = dict(profile)
    if set(policies) != {port.name for port in system.ports}:
        raise ValueError("policy profile must control every decision port exactly once")

    assignments: dict[str, str] = {}
    for stage in sorted({port.stage for port in system.ports}):
        stage_ports = sorted(
            (port for port in system.ports if port.stage == stage),
            key=lambda item: item.name,
        )
        prior_snapshot = dict(assignments)
        stage_actions: dict[str, str] = {}
        for port in stage_ports:
            key = information_key(system, port, scenario, prior_snapshot)
            policy = dict(policies[port.name])
            if key not in policy:
                raise ValueError(f"policy lacks information set {key!r}")
            action = policy[key]
            if action not in port.actions:
                raise ValueError(f"invalid action {action!r} for port {port.name!r}")
            stage_actions[port.name] = action
        assignments.update(stage_actions)
    return canonical_actions(assignments)


def outcome_distribution_for_profile(
    system: PortSystem, profile: PolicyProfile
) -> Distribution:
    validate_port_system(system)
    rules = {(rule.scenario, rule.actions): rule.distribution for rule in system.rules}
    mass: dict[str, Fraction] = {}
    for scenario in system.scenarios:
        actions = action_profile_for_scenario(system, profile, scenario)
        for outcome, probability_mass in rules[(scenario.name, actions)]:
            mass[outcome] = mass.get(outcome, Fraction(0)) + (
                scenario.probability * probability_mass
            )
    return exact_distribution(mass)


def all_policy_profiles(system: PortSystem) -> tuple[PolicyProfile, ...]:
    owner_names = owners(system)
    spaces = tuple(enumerate_owner_strategies(system, owner) for owner in owner_names)
    return tuple(
        _combine_owner_strategies(strategies) for strategies in product(*spaces)
    )


def cooperative_max_probability(system: PortSystem, outcome: str) -> Fraction:
    return max(
        probability(outcome_distribution_for_profile(system, profile), outcome)
        for profile in all_policy_profiles(system)
    )


def maximin_probability(system: PortSystem, owner: str, outcome: str) -> Fraction:
    target_space = enumerate_owner_strategies(system, owner)
    opponents = tuple(candidate for candidate in owners(system) if candidate != owner)
    opponent_spaces = tuple(
        enumerate_owner_strategies(system, candidate) for candidate in opponents
    )
    opponent_profiles = tuple(product(*opponent_spaces)) if opponent_spaces else ((),)

    guarantees: list[Fraction] = []
    for target in target_space:
        worst = Fraction(1)
        for opponent_tuple in opponent_profiles:
            profile = _combine_owner_strategies((target, *opponent_tuple))
            value = probability(
                outcome_distribution_for_profile(system, profile), outcome
            )
            worst = min(worst, value)
        guarantees.append(worst)
    return max(guarantees)


def owner_partition(system: PortSystem) -> tuple[tuple[str, ...], ...]:
    return tuple(
        sorted(
            tuple(sorted(port.name for port in system.ports if port.owner == owner))
            for owner in owners(system)
        )
    )


def port_only_signature(system: PortSystem) -> tuple[object, ...]:
    """Forget ownership while preserving ports, information, causality and laws."""
    validate_port_system(system)
    return (
        tuple(
            sorted(
                (port.name, port.stage, port.actions, tuple(sorted(port.reads)))
                for port in system.ports
            )
        ),
        tuple(
            sorted(
                (scenario.name, scenario.probability, tuple(sorted(scenario.signals)))
                for scenario in system.scenarios
            )
        ),
        tuple(
            sorted(
                (rule.scenario, rule.actions, rule.distribution)
                for rule in system.rules
            )
        ),
    )


def anonymous_control_signature(system: PortSystem) -> tuple[object, ...]:
    """Forget owner names while preserving anonymous control-domain partition."""
    return (*port_only_signature(system), owner_partition(system))


def rename_owners(
    system: PortSystem,
    renaming: Mapping[str, str],
    *,
    name: str | None = None,
) -> PortSystem:
    validate_port_system(system)
    unknown = set(renaming) - set(owners(system))
    if unknown:
        raise ValueError(f"unknown owners in renaming: {sorted(unknown)}")
    result = replace(
        system,
        name=name or system.name,
        ports=tuple(
            replace(port, owner=renaming.get(port.owner, port.owner))
            for port in system.ports
        ),
    )
    validate_port_system(result)
    return result


def reassign_port_owners(
    system: PortSystem,
    assignment: Mapping[str, str],
    *,
    name: str | None = None,
) -> PortSystem:
    validate_port_system(system)
    unknown = set(assignment) - {port.name for port in system.ports}
    if unknown:
        raise ValueError(f"unknown ports in ownership assignment: {sorted(unknown)}")
    result = replace(
        system,
        name=name or system.name,
        ports=tuple(
            replace(port, owner=assignment.get(port.name, port.owner))
            for port in system.ports
        ),
    )
    validate_port_system(result)
    return result


def best_profiles_for_outcome(system: PortSystem, outcome: str) -> tuple[PolicyProfile, ...]:
    scored = tuple(
        (
            probability(outcome_distribution_for_profile(system, profile), outcome),
            profile,
        )
        for profile in all_policy_profiles(system)
    )
    best = max(score for score, _ in scored)
    return tuple(profile for score, profile in scored if score == best)


def _namespace_read(token: str, prefix: str) -> str:
    kind, _, target = token.partition(":")
    return f"{kind}:{prefix}{target}"


def parallel_compose(
    left: PortSystem, right: PortSystem, *, name: str = "parallel"
) -> PortSystem:
    """Compose independent components while preserving read/write boundaries."""
    validate_port_system(left)
    validate_port_system(right)
    lp = "L."
    rp = "R."
    ports = tuple(
        replace(
            port,
            name=f"{lp}{port.name}",
            owner=f"{lp}{port.owner}",
            reads=tuple(_namespace_read(token, lp) for token in port.reads),
        )
        for port in left.ports
    ) + tuple(
        replace(
            port,
            name=f"{rp}{port.name}",
            owner=f"{rp}{port.owner}",
            reads=tuple(_namespace_read(token, rp) for token in port.reads),
        )
        for port in right.ports
    )
    scenarios = tuple(
        Scenario(
            f"{lp}{ls.name}|{rp}{rs.name}",
            ls.probability * rs.probability,
            tuple((f"{lp}{key}", value) for key, value in ls.signals)
            + tuple((f"{rp}{key}", value) for key, value in rs.signals),
        )
        for ls in left.scenarios
        for rs in right.scenarios
    )

    left_rules = {(rule.scenario, rule.actions): rule for rule in left.rules}
    right_rules = {(rule.scenario, rule.actions): rule for rule in right.rules}
    left_names = tuple(port.name for port in left.ports)
    right_names = tuple(port.name for port in right.ports)
    rules: list[OutcomeRule] = []

    for ls in left.scenarios:
        for rs in right.scenarios:
            scenario_name = f"{lp}{ls.name}|{rp}{rs.name}"
            for left_choices in product(*(port.actions for port in left.ports)):
                la = canonical_actions(dict(zip(left_names, left_choices, strict=True)))
                lr = left_rules[(ls.name, la)]
                for right_choices in product(*(port.actions for port in right.ports)):
                    ra = canonical_actions(
                        dict(zip(right_names, right_choices, strict=True))
                    )
                    rr = right_rules[(rs.name, ra)]
                    actions = canonical_actions(
                        {
                            **{f"{lp}{key}": value for key, value in la},
                            **{f"{rp}{key}": value for key, value in ra},
                        }
                    )
                    mass: dict[str, Fraction] = {}
                    for left_outcome, left_mass in lr.distribution:
                        for right_outcome, right_mass in rr.distribution:
                            outcome = f"{lp}{left_outcome}|{rp}{right_outcome}"
                            mass[outcome] = mass.get(outcome, Fraction(0)) + (
                                left_mass * right_mass
                            )
                    rules.append(
                        OutcomeRule(scenario_name, actions, exact_distribution(mass))
                    )

    result = PortSystem(name, ports, scenarios, tuple(rules))
    validate_port_system(result)
    return result


def authority_gauge_partition(systems: Sequence[PortSystem]) -> dict[str, str]:
    representatives: list[tuple[object, ...]] = []
    partition: dict[str, str] = {}
    for system in systems:
        signature = anonymous_control_signature(system)
        try:
            index = representatives.index(signature)
        except ValueError:
            representatives.append(signature)
            index = len(representatives) - 1
        partition[system.name] = f"b{index}"
    return partition


def _canonical_control_probe(
    system: PortSystem, outcome: str
) -> tuple[tuple[tuple[str, ...], Fraction], ...]:
    values = []
    for owner in owners(system):
        block = tuple(sorted(port.name for port in system.ports if port.owner == owner))
        values.append((block, maximin_probability(system, owner, outcome)))
    return tuple(sorted(values))


def authority_partition_is_representative_independent(
    systems: Sequence[PortSystem],
    partition: Mapping[str, str],
    probe_outcomes: Sequence[str],
) -> bool:
    by_name = {system.name: system for system in systems}
    if set(partition) != set(by_name):
        raise ValueError("partition must name every system exactly once")
    for block in set(partition.values()):
        members = [by_name[name] for name, value in partition.items() if value == block]
        reference = members[0]
        signature = anonymous_control_signature(reference)
        for candidate in members[1:]:
            if anonymous_control_signature(candidate) != signature:
                return False
        for outcome in probe_outcomes:
            probe = _canonical_control_probe(reference, outcome)
            if any(
                _canonical_control_probe(candidate, outcome) != probe
                for candidate in members[1:]
            ):
                return False
    return True


def deterministic_rule(
    scenario: str, actions: Mapping[str, str], outcome: str
) -> OutcomeRule:
    return OutcomeRule(
        scenario,
        canonical_actions(actions),
        exact_distribution({outcome: Fraction(1)}),
    )


def single_scenario_system(
    name: str,
    ports: tuple[DecisionPort, ...],
    outcome_fn,
) -> PortSystem:
    scenario = Scenario("s", Fraction(1))
    rules = []
    names = tuple(port.name for port in ports)
    for choices in product(*(port.actions for port in ports)):
        actions = dict(zip(names, choices, strict=True))
        rules.append(deterministic_rule("s", actions, outcome_fn(actions)))
    system = PortSystem(name, ports, (scenario,), tuple(rules))
    validate_port_system(system)
    return system


def run_multi_authority_comparison() -> tuple[AuthorityResult, ...]:
    """Run the bounded #2357 A0-A8 exact falsification transaction."""
    sequential = single_scenario_system(
        "sequential",
        (
            DecisionPort("act", "SELF", 0, ("A", "B")),
            DecisionPort(
                "respond",
                "WORLD",
                1,
                ("allow", "deny"),
                reads=(action_token("act"),),
            ),
        ),
        lambda actions: "GOOD" if actions["respond"] == "allow" else "BAD",
    )
    flattened = reassign_port_owners(
        sequential, {"respond": "SELF"}, name="flattened"
    )
    one_chooser_fails = (
        maximin_probability(sequential, "SELF", "GOOD") == 0
        and maximin_probability(flattened, "SELF", "GOOD") == 1
    )

    renamed = rename_owners(
        sequential, {"SELF": "Alice", "WORLD": "Bob"}, name="renamed"
    )
    owner_name_gauge = (
        anonymous_control_signature(sequential)
        == anonymous_control_signature(renamed)
    )

    merged_control = single_scenario_system(
        "merged-control",
        (
            DecisionPort("x", "TEAM", 0, ("0", "1")),
            DecisionPort("y", "TEAM", 0, ("0", "1")),
        ),
        lambda actions: "MATCH" if actions["x"] == actions["y"] else "MISS",
    )
    split_control = reassign_port_owners(
        merged_control,
        {"x": "LEFT", "y": "RIGHT"},
        name="split-control",
    )
    control_partition_survives = (
        port_only_signature(merged_control) == port_only_signature(split_control)
        and anonymous_control_signature(merged_control)
        != anonymous_control_signature(split_control)
        and maximin_probability(merged_control, "TEAM", "MATCH") == 1
        and maximin_probability(split_control, "LEFT", "MATCH") == 0
    )

    scenarios = (
        Scenario("h0", Fraction(1, 2), (("hidden", "0"),)),
        Scenario("h1", Fraction(1, 2), (("hidden", "1"),)),
    )

    def guessing_system(name: str, reads: tuple[str, ...]) -> PortSystem:
        port = DecisionPort("guess", "SELF", 0, ("0", "1"), reads=reads)
        rules = []
        for scenario in scenarios:
            hidden = dict(scenario.signals)["hidden"]
            for action in port.actions:
                rules.append(
                    deterministic_rule(
                        scenario.name,
                        {"guess": action},
                        "CORRECT" if action == hidden else "WRONG",
                    )
                )
        result = PortSystem(name, (port,), scenarios, tuple(rules))
        validate_port_system(result)
        return result

    informed = guessing_system("informed", (signal_token("hidden"),))
    blind = guessing_system("blind", ())
    information_survives = (
        maximin_probability(informed, "SELF", "CORRECT") == 1
        and maximin_probability(blind, "SELF", "CORRECT") == Fraction(1, 2)
    )

    objective_system = single_scenario_system(
        "objective",
        (DecisionPort("pick", "SELF", 0, ("L", "R")),),
        lambda actions: actions["pick"],
    )
    objective_external = (
        best_profiles_for_outcome(objective_system, "L")
        != best_profiles_for_outcome(objective_system, "R")
    )

    concurrent = single_scenario_system(
        "concurrent",
        (
            DecisionPort("world", "WORLD", 0, ("0", "1")),
            DecisionPort("self", "SELF", 0, ("0", "1")),
        ),
        lambda actions: "MATCH" if actions["self"] == actions["world"] else "MISS",
    )
    serialized = single_scenario_system(
        "serialized",
        (
            DecisionPort("world", "WORLD", 0, ("0", "1")),
            DecisionPort(
                "self",
                "SELF",
                1,
                ("0", "1"),
                reads=(action_token("world"),),
            ),
        ),
        lambda actions: "MATCH" if actions["self"] == actions["world"] else "MISS",
    )
    concurrency_survives = (
        maximin_probability(concurrent, "SELF", "MATCH") == 0
        and maximin_probability(serialized, "SELF", "MATCH") == 1
    )

    component = single_scenario_system(
        "component",
        (DecisionPort("p", "OWNER", 0, ("0", "1")),),
        lambda actions: actions["p"],
    )
    component_renamed = rename_owners(
        component, {"OWNER": "RENAMED"}, name="component-renamed"
    )
    composed_a = parallel_compose(component, component, name="composed-a")
    composed_b = parallel_compose(
        component_renamed, component_renamed, name="composed-b"
    )
    composition_survives = (
        anonymous_control_signature(composed_a)
        == anonymous_control_signature(composed_b)
        and owner_partition(composed_a) == (("L.p",), ("R.p",))
    )

    systems = (sequential, renamed, split_control)
    partition = authority_gauge_partition(systems)
    quotient_survives = (
        partition["sequential"] == partition["renamed"]
        and partition["sequential"] != partition["split-control"]
        and authority_partition_is_representative_independent(
            systems, partition, ("GOOD", "BAD", "MATCH")
        )
    )

    port_control_sufficient = all(
        (
            one_chooser_fails,
            owner_name_gauge,
            control_partition_survives,
            information_survives,
            objective_external,
            concurrency_survives,
            composition_survives,
            quotient_survives,
        )
    )

    return (
        AuthorityResult(
            "ONE_OMNIPOTENT_CHOOSER_GRANTS_FALSE_CONTROL",
            one_chooser_fails,
            "flattening WORLD write authority into SELF changes a SELF guarantee",
        ),
        AuthorityResult(
            "OWNER_NAME_IS_GAUGE",
            owner_name_gauge,
            "renaming owners preserves anonymous control and exact port semantics",
        ),
        AuthorityResult(
            "CONTROL_PARTITION_SURVIVES_STRATEGIC_PROBES",
            control_partition_survives,
            "same port dynamics with merged versus split control changes maximin capability",
        ),
        AuthorityResult(
            "INFORMATION_READ_EDGES_SURVIVE",
            information_survives,
            "declared visibility changes exact attainable correctness",
        ),
        AuthorityResult(
            "OBJECTIVE_IS_DECISION_SEMANTICS_NOT_TRANSITION_PHYSICS",
            objective_external,
            "objective changes optimal policy without changing the port process",
        ),
        AuthorityResult(
            "CONCURRENCY_CAUSAL_ORDER_SURVIVES",
            concurrency_survives,
            "serializing simultaneous choice with a new read edge grants illegal control",
        ),
        AuthorityResult(
            "PORT_COMPOSITION_PRESERVES_BOUNDARIES",
            composition_survives,
            "parallel composition preserves namespaced control/information boundaries",
        ),
        AuthorityResult(
            "AUTHORITY_GAUGE_QUOTIENT_IS_REPRESENTATIVE_INDEPENDENT",
            quotient_survives,
            "owner-name quotient preserves anonymous control and exact control probes",
        ),
        AuthorityResult(
            "NAMED_STOCHASTIC_GAME_PLAYERS_NOT_YET_EARNED",
            port_control_sufficient,
            "tested discriminators need anonymous control domains, read edges, causal order and exact laws, not concrete player names",
        ),
    )
