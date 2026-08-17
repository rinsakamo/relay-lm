from __future__ import annotations

import asyncio
import json

from relaylm.evaluation import (
    EvaluationCheck,
    EvaluationReport,
    EvaluationScenarioResult,
    evaluate_assistant_self_certification_prevention,
    evaluate_boolean_state_memory_authority,
    evaluate_budget_degradation_plan,
    evaluate_budget_owner_controls,
    evaluate_cjk_retrieval_relevance,
    evaluate_comparative_preference_preservation,
    evaluate_continuity_active_task_retention,
    evaluate_continuity_cognition_wiring,
    evaluate_continuity_context_retention,
    evaluate_continuity_lifecycle,
    evaluate_continuity_turn,
    evaluate_correction_remove_semantics,
    evaluate_crystallization_integrity,
    evaluate_degree_hint_integrity,
    evaluate_degree_state_memory_authority,
    evaluate_event_snapshot_reuse,
    evaluate_freeform_current_state_shadow,
    evaluate_openai_serialized_counter,
    evaluate_persistence_integrity,
    evaluate_protected_serialized_floor,
    evaluate_provider_failure_safety,
    evaluate_restart_continuity,
    evaluate_retrieval_aggregate_diagnostics,
    evaluate_retrieval_query_features,
    evaluate_retrieval_stage_diagnostics,
    evaluate_serialized_fit_enforcement,
    evaluate_serialized_input_fit,
    evaluate_state_selection_diagnostics,
    evaluate_streaming_safety,
    evaluate_total_budget_accounting,
    evaluate_working_context_budget_atomicity,
    main,
    run_native_evaluation,
)


def test_provider_failure_evaluation_reports_boundary_invariants() -> None:
    result = asyncio.run(evaluate_provider_failure_safety())
    assert result.scenario_id == "provider_failure_safety"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_native_report_is_machine_readable_without_composite_score() -> None:
    report = asyncio.run(run_native_evaluation())
    payload = json.loads(report.to_json())
    assert payload["format_version"] == 1
    assert payload["suite"] == "relaylm-native"
    assert payload["status"] == "pass"
    assert [scenario["id"] for scenario in payload["scenarios"]] == [
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
    ]
    assert "score" not in payload
    assert "weight" not in report.to_json()


def test_evaluation_cli_prints_report_and_returns_success(capsys) -> None:
    exit_code = main()
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "pass"


def test_failed_check_propagates_to_scenario_and_report_status() -> None:
    scenario = EvaluationScenarioResult(
        scenario_id="synthetic_failure",
        checks=(EvaluationCheck("authority_gate", "canonical_state", False, True, False),),
    )
    report = EvaluationReport(scenarios=(scenario,))
    assert scenario.status == "fail"
    assert report.status == "fail"


def test_registered_scenarios_pass_individually() -> None:
    evaluators = (
        evaluate_restart_continuity,
        evaluate_assistant_self_certification_prevention,
        evaluate_comparative_preference_preservation,
        evaluate_degree_hint_integrity,
        evaluate_working_context_budget_atomicity,
        evaluate_persistence_integrity,
        evaluate_event_snapshot_reuse,
        evaluate_correction_remove_semantics,
        evaluate_crystallization_integrity,
        evaluate_streaming_safety,
        evaluate_state_selection_diagnostics,
        evaluate_retrieval_stage_diagnostics,
        evaluate_boolean_state_memory_authority,
        evaluate_retrieval_aggregate_diagnostics,
        evaluate_cjk_retrieval_relevance,
        evaluate_degree_state_memory_authority,
        evaluate_retrieval_query_features,
        evaluate_continuity_lifecycle,
        evaluate_continuity_turn,
        evaluate_continuity_context_retention,
        evaluate_continuity_active_task_retention,
        evaluate_continuity_cognition_wiring,
        evaluate_freeform_current_state_shadow,
        evaluate_total_budget_accounting,
        evaluate_budget_degradation_plan,
        evaluate_budget_owner_controls,
        evaluate_serialized_input_fit,
        evaluate_openai_serialized_counter,
        evaluate_serialized_fit_enforcement,
        evaluate_protected_serialized_floor,
    )
    results = tuple(asyncio.run(evaluate()) for evaluate in evaluators)
    assert all(result.status == "pass" for result in results)
