from __future__ import annotations

import asyncio
import json

from relaylm.evaluation import (
    EvaluationCheck,
    EvaluationReport,
    EvaluationScenarioResult,
    evaluate_provider_failure_safety,
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
        "provider_failure_safety"
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
