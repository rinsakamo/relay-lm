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
    assert {check.check_id for check in result.checks} == {
        "provider_failure_observed",
        "provider_called_once",
        "current_user_event_persisted",
        "assistant_event_not_persisted",
        "canonical_state_unchanged",
    }
    assert all(check.passed for check in result.checks)
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
    ]
    assert "score" not in payload
    assert "weight" not in report.to_json()


def test_evaluation_cli_prints_report_and_returns_success(capsys) -> None:
    exit_code = main()
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "pass"
    assert payload["scenarios"][0]["status"] == "pass"


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


def test_restart_continuity_evaluation_uses_persisted_state_and_events() -> None:
    result = asyncio.run(evaluate_restart_continuity())

    assert result.scenario_id == "restart_continuity"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "client_api",
        "provider",
        "canonical_state",
        "event_journal",
        "context_compiler",
    }
    assert result.metrics == {
        "provider_calls": 2,
        "pre_restart_event_count": 2,
        "restart_context_count": 2,
    }


def test_assistant_self_certification_evaluation_preserves_context_but_rejects_state() -> None:
    result = asyncio.run(evaluate_assistant_self_certification_prevention())

    assert result.scenario_id == "assistant_self_certification_prevention"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "context_compiler",
        "validator",
        "canonical_state",
    }
    assert result.metrics == {
        "working_context_count": 2,
        "rejected_candidate_count": 1,
        "accepted_state_count": 0,
    }


def test_comparative_preference_evaluation_preserves_weaker_positive_state() -> None:
    result = asyncio.run(evaluate_comparative_preference_preservation())

    assert result.scenario_id == "comparative_preference_preservation"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "validator",
        "canonical_state",
        "event_provenance",
    }
    assert result.metrics == {
        "accepted_candidate_count": 2,
        "final_preference_state_count": 3,
        "preserved_existing_state_count": 1,
    }


def test_degree_hint_evaluation_treats_weakening_as_set_and_rejects_invalid_envelopes() -> None:
    result = asyncio.run(evaluate_degree_hint_integrity())

    assert result.scenario_id == "degree_hint_integrity"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "validator",
        "canonical_state",
        "event_provenance",
    }
    assert result.metrics == {
        "accepted_candidate_count": 1,
        "rejected_candidate_count": 2,
        "final_state_count": 1,
    }


def test_working_context_budget_evaluation_keeps_complete_exchange_and_provenance() -> None:
    result = asyncio.run(evaluate_working_context_budget_atomicity())

    assert result.scenario_id == "working_context_budget_atomicity"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "context_compiler",
        "event_provenance",
    }
    assert result.metrics == {
        "event_window_context_count": 2,
        "character_budget_context_count": 2,
        "selected_source_count": 2,
    }


def test_persistence_integrity_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_persistence_integrity())

    assert result.scenario_id == "persistence_integrity"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_event_snapshot_reuse_evaluation_is_registered_in_core_suite() -> None:
    result = asyncio.run(evaluate_event_snapshot_reuse())

    assert result.scenario_id == "event_snapshot_reuse"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_correction_remove_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_correction_remove_semantics())

    assert result.scenario_id == "correction_remove_semantics"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_crystallization_integrity_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_crystallization_integrity())

    assert result.scenario_id == "crystallization_integrity"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_streaming_safety_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_streaming_safety())

    assert result.scenario_id == "streaming_safety"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_state_selection_diagnostics_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_state_selection_diagnostics())

    assert result.scenario_id == "state_selection_diagnostics"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "context_compiler",
        "diagnostics",
    }
    assert result.metrics == {
        "eligible_state_count": 4,
        "selected_state_count": 2,
        "evicted_state_count": 2,
        "selected_fallback_count": 2,
    }


def test_retrieval_stage_diagnostics_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_retrieval_stage_diagnostics())

    assert result.scenario_id == "retrieval_stage_diagnostics"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_boolean_state_memory_authority_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_boolean_state_memory_authority())

    assert result.scenario_id == "boolean_state_memory_authority"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_retrieval_aggregate_diagnostics_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_retrieval_aggregate_diagnostics())

    assert result.scenario_id == "retrieval_aggregate_diagnostics"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_cjk_retrieval_relevance_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_cjk_retrieval_relevance())

    assert result.scenario_id == "cjk_retrieval_relevance"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_degree_state_memory_authority_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_degree_state_memory_authority())

    assert result.scenario_id == "degree_state_memory_authority"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_retrieval_query_features_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_retrieval_query_features())

    assert result.scenario_id == "retrieval_query_features"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_continuity_lifecycle_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_continuity_lifecycle())

    assert result.scenario_id == "continuity_lifecycle"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_continuity_turn_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_continuity_turn())

    assert result.scenario_id == "continuity_turn"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_continuity_context_retention_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_continuity_context_retention())

    assert result.scenario_id == "continuity_context_retention"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_continuity_active_task_retention_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_continuity_active_task_retention())

    assert result.scenario_id == "continuity_active_task_retention"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)


def test_post_continuity_evaluations_are_registered() -> None:
    results = tuple(
        asyncio.run(evaluate())
        for evaluate in (
            evaluate_continuity_cognition_wiring,
            evaluate_freeform_current_state_shadow,
            evaluate_total_budget_accounting,
            evaluate_budget_degradation_plan,
            evaluate_budget_owner_controls,
            evaluate_serialized_input_fit,
            evaluate_openai_serialized_counter,
            evaluate_serialized_fit_enforcement,
        )
    )

    assert tuple(result.scenario_id for result in results) == (
        "continuity_cognition_wiring",
        "freeform_current_state_shadow",
        "total_budget_accounting",
        "budget_degradation_plan",
        "budget_owner_controls",
        "serialized_input_fit",
        "openai_serialized_counter",
        "serialized_fit_enforcement",
    )
    assert all(result.status == "pass" for result in results)
