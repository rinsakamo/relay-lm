from __future__ import annotations

import asyncio
import json

from relaylm.evaluation import (
    NATIVE_EVALUATION_SCENARIOS,
    EvaluationCheck,
    EvaluationReport,
    EvaluationScenarioResult,
    evaluate_provider_failure_safety,
    main,
    run_native_evaluation,
)

EXPECTED_NATIVE_SCENARIO_IDS = (
    "provider_failure_safety",
    "restart_continuity",
    "assistant_self_certification_prevention",
    "comparative_preference_preservation",
    "degree_hint_integrity",
    "working_context_budget_atomicity",
    "persistence_integrity",
    "event_snapshot_reuse",
    "correction_remove_semantics",
    "crystallization_integrity",
    "streaming_safety",
    "state_selection_diagnostics",
    "cross_layer_context_diagnostics",
    "working_context_budget_diagnostics",
    "memory_heading_retrieval",
    "memory_cognitive_projection",
    "ordinary_turn_memory_retrieval",
    "state_memory_authority_filter",
    "targeted_event_retrieval",
    "event_evidence_cognitive_projection",
    "ordinary_turn_event_retrieval",
    "retrieval_stage_diagnostics",
    "boolean_state_memory_authority",
    "retrieval_aggregate_diagnostics",
    "cjk_retrieval_relevance",
    "degree_state_memory_authority",
    "retrieval_query_features",
    "continuity_lifecycle",
    "continuity_turn",
    "continuity_context_retention",
    "continuity_active_task_retention",
    "continuity_cognition_wiring",
    "freeform_current_state_shadow",
    "total_budget_accounting",
    "budget_degradation_plan",
    "budget_owner_controls",
    "serialized_input_fit",
    "openai_serialized_counter",
    "serialized_fit_enforcement",
    "protected_serialized_floor",
    "cognitive_budget_turn_wiring",
    "cognitive_budget_turn_diagnostics",
    "memory_temporal_provenance",
)


def test_provider_failure_evaluation_reports_boundary_invariants() -> None:
    result = asyncio.run(evaluate_provider_failure_safety())

    assert result.scenario_id == "provider_failure_safety"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "provider_failure_observed",
        "provider_called_once",
        "current_user_event_persisted",
        "assistant_event_not_persisted",
        "canonical_state_unchanged",
    }
    assert {check.boundary for check in result.checks} == {
        "provider",
        "event_journal",
        "canonical_state",
    }
    assert result.metrics == {
        "provider_calls": 1,
        "persisted_event_count": 1,
        "persisted_state_count": 0,
    }


def test_native_registry_preserves_exact_current_identity_and_order() -> None:
    assert tuple(spec.scenario_id for spec in NATIVE_EVALUATION_SCENARIOS) == (
        EXPECTED_NATIVE_SCENARIO_IDS
    )
    assert len({spec.scenario_id for spec in NATIVE_EVALUATION_SCENARIOS}) == len(
        NATIVE_EVALUATION_SCENARIOS
    )
    assert {spec.group for spec in NATIVE_EVALUATION_SCENARIOS} == {
        "runtime_safety",
        "authority_state",
        "context_retrieval",
        "continuity",
        "persistence",
        "budget_provider",
    }


def test_native_report_is_machine_readable_without_composite_score() -> None:
    report = asyncio.run(run_native_evaluation())
    payload = json.loads(report.to_json())

    assert payload["format_version"] == 1
    assert payload["suite"] == "relaylm-native"
    assert payload["status"] == "pass"
    assert tuple(scenario["id"] for scenario in payload["scenarios"]) == (
        EXPECTED_NATIVE_SCENARIO_IDS
    )
    assert all(scenario["status"] == "pass" for scenario in payload["scenarios"])
    assert "score" not in payload
    assert "weight" not in report.to_json()


def test_evaluation_cli_prints_report_and_returns_success(capsys) -> None:
    exit_code = main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "pass"
    assert tuple(item["id"] for item in payload["scenarios"]) == EXPECTED_NATIVE_SCENARIO_IDS


def test_failed_check_propagates_to_scenario_and_report_status() -> None:
    scenario = EvaluationScenarioResult(
        scenario_id="synthetic_failure",
        checks=(
            EvaluationCheck(
                check_id="authority_gate",
                boundary="canonical_state",
                passed=False,
                expected=True,
                observed=False,
            ),
        ),
    )
    report = EvaluationReport(scenarios=(scenario,))

    assert scenario.status == "fail"
    assert report.status == "fail"
