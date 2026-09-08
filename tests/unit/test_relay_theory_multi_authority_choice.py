from fractions import Fraction

import pytest

from tools.relay_theory_multi_authority_choice import (
    DecisionPort,
    OutcomeRule,
    PortSystem,
    Scenario,
    action_token,
    anonymous_control_signature,
    authority_gauge_partition,
    authority_partition_is_representative_independent,
    best_profiles_for_outcome,
    canonical_actions,
    cooperative_max_probability,
    deterministic_rule,
    maximin_probability,
    owner_partition,
    parallel_compose,
    port_only_signature,
    reassign_port_owners,
    rename_owners,
    run_multi_authority_comparison,
    signal_token,
    single_scenario_system,
    validate_port_system,
)
from tools.relay_theory_scheduler_nondeterminism import exact_distribution


def test_multi_authority_comparison_passes() -> None:
    results = run_multi_authority_comparison()

    assert [result.name for result in results] == [
        "ONE_OMNIPOTENT_CHOOSER_GRANTS_FALSE_CONTROL",
        "OWNER_NAME_IS_GAUGE",
        "CONTROL_PARTITION_SURVIVES_STRATEGIC_PROBES",
        "INFORMATION_READ_EDGES_SURVIVE",
        "OBJECTIVE_IS_DECISION_SEMANTICS_NOT_TRANSITION_PHYSICS",
        "CONCURRENCY_CAUSAL_ORDER_SURVIVES",
        "PORT_COMPOSITION_PRESERVES_BOUNDARIES",
        "AUTHORITY_GAUGE_QUOTIENT_IS_REPRESENTATIVE_INDEPENDENT",
        "NAMED_STOCHASTIC_GAME_PLAYERS_NOT_YET_EARNED",
    ]
    assert all(result.passed for result in results)


def test_scenario_probability_rejects_float() -> None:
    system = PortSystem(
        "float-scenario",
        (DecisionPort("p", "SELF", 0, ("go",)),),
        (Scenario("s", 1.0),),  # type: ignore[arg-type]
        (deterministic_rule("s", {"p": "go"}, "DONE"),),
    )

    with pytest.raises(TypeError, match="fractions.Fraction"):
        validate_port_system(system)


def test_same_stage_action_read_is_rejected() -> None:
    system = PortSystem(
        "illegal-concurrency",
        (
            DecisionPort("world", "WORLD", 0, ("0", "1")),
            DecisionPort(
                "self",
                "SELF",
                0,
                ("0", "1"),
                reads=(action_token("world"),),
            ),
        ),
        (Scenario("s", Fraction(1)),),
        tuple(
            deterministic_rule(
                "s",
                {"world": world, "self": self_action},
                "MATCH" if world == self_action else "MISS",
            )
            for world in ("0", "1")
            for self_action in ("0", "1")
        ),
    )

    with pytest.raises(ValueError, match="strictly earlier"):
        validate_port_system(system)


def test_owner_name_is_gauge_but_control_partition_is_not() -> None:
    system = single_scenario_system(
        "base",
        (
            DecisionPort("x", "LEFT", 0, ("0", "1")),
            DecisionPort("y", "RIGHT", 0, ("0", "1")),
        ),
        lambda actions: "MATCH" if actions["x"] == actions["y"] else "MISS",
    )
    renamed = rename_owners(
        system,
        {"LEFT": "Alice", "RIGHT": "Bob"},
        name="renamed",
    )
    merged = reassign_port_owners(
        system,
        {"x": "TEAM", "y": "TEAM"},
        name="merged",
    )

    assert anonymous_control_signature(system) == anonymous_control_signature(renamed)
    assert port_only_signature(system) == port_only_signature(merged)
    assert anonymous_control_signature(system) != anonymous_control_signature(merged)
    assert maximin_probability(system, "LEFT", "MATCH") == 0
    assert maximin_probability(merged, "TEAM", "MATCH") == 1


def test_information_read_edge_changes_attainable_behavior() -> None:
    scenarios = (
        Scenario("h0", Fraction(1, 2), (("hidden", "0"),)),
        Scenario("h1", Fraction(1, 2), (("hidden", "1"),)),
    )

    def build(name: str, reads: tuple[str, ...]) -> PortSystem:
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
        system = PortSystem(name, (port,), scenarios, tuple(rules))
        validate_port_system(system)
        return system

    informed = build("informed", (signal_token("hidden"),))
    blind = build("blind", ())

    assert maximin_probability(informed, "SELF", "CORRECT") == 1
    assert maximin_probability(blind, "SELF", "CORRECT") == Fraction(1, 2)


def test_flattening_sequential_authority_grants_false_self_control() -> None:
    separate = single_scenario_system(
        "separate",
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
        separate,
        {"respond": "SELF"},
        name="flattened",
    )

    assert maximin_probability(separate, "SELF", "GOOD") == 0
    assert maximin_probability(flattened, "SELF", "GOOD") == 1
    assert cooperative_max_probability(separate, "GOOD") == 1


def test_concurrent_choice_cannot_gain_current_action_by_serialization() -> None:
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

    assert maximin_probability(concurrent, "SELF", "MATCH") == 0
    assert maximin_probability(serialized, "SELF", "MATCH") == 1


def test_objective_changes_policy_not_transition_interface() -> None:
    system = single_scenario_system(
        "objective",
        (DecisionPort("pick", "SELF", 0, ("L", "R")),),
        lambda actions: actions["pick"],
    )
    signature = anonymous_control_signature(system)

    assert best_profiles_for_outcome(system, "L") != best_profiles_for_outcome(
        system, "R"
    )
    assert anonymous_control_signature(system) == signature


def test_parallel_composition_preserves_anonymous_control_boundaries() -> None:
    component = single_scenario_system(
        "component",
        (DecisionPort("p", "OWNER", 0, ("0", "1")),),
        lambda actions: actions["p"],
    )
    renamed = rename_owners(component, {"OWNER": "OTHER"}, name="renamed")
    left = parallel_compose(component, component, name="left")
    right = parallel_compose(renamed, renamed, name="right")

    assert anonymous_control_signature(left) == anonymous_control_signature(right)
    assert owner_partition(left) == (("L.p",), ("R.p",))


def test_authority_name_quotient_is_representative_independent() -> None:
    base = single_scenario_system(
        "base",
        (
            DecisionPort("x", "LEFT", 0, ("0", "1")),
            DecisionPort("y", "RIGHT", 0, ("0", "1")),
        ),
        lambda actions: "MATCH" if actions["x"] == actions["y"] else "MISS",
    )
    renamed = rename_owners(
        base,
        {"LEFT": "Alice", "RIGHT": "Bob"},
        name="renamed",
    )
    merged = reassign_port_owners(
        base,
        {"x": "TEAM", "y": "TEAM"},
        name="merged",
    )
    systems = (base, renamed, merged)
    partition = authority_gauge_partition(systems)

    assert partition["base"] == partition["renamed"]
    assert partition["base"] != partition["merged"]
    assert authority_partition_is_representative_independent(
        systems,
        partition,
        ("MATCH", "MISS"),
    )


def test_exact_stochastic_terminal_law_is_preserved() -> None:
    system = PortSystem(
        "stochastic",
        (DecisionPort("p", "SELF", 0, ("go",)),),
        (Scenario("s", Fraction(1)),),
        (
            OutcomeRule(
                "s",
                canonical_actions({"p": "go"}),
                exact_distribution(
                    {"L": Fraction(1, 3), "R": Fraction(2, 3)}
                ),
            ),
        ),
    )
    validate_port_system(system)

    assert cooperative_max_probability(system, "L") == Fraction(1, 3)
