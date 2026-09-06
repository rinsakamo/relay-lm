from __future__ import annotations

import json

import httpx

from relaylm.v2_cognitive_ir_calibration import (
    ANSWER_SCHEMA,
    CALIBRATION_DIFFICULTIES,
    CALIBRATION_PROBES,
    CALIBRATION_SEEDS,
    CalibrationCellResult,
    OpenAICompatibleStructuredCalibrationClient,
    build_calibration_messages,
    generate_calibration_case,
    run_calibration_matrix,
    summarize_calibration,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from relaylm.v2_transfer_experiment import VectorRule


class QueueStructuredClient:
    def __init__(self, completions: list[ExperimentCompletion]) -> None:
        self.completions = list(completions)
        self.provider_attempts = 0
        self.provider_completions = 0
        self.calls: list[tuple[tuple[dict[str, str], ...], str, dict[str, object]]] = []

    @property
    def transport_identity(self) -> dict[str, object]:
        return {"api": "test-json-schema"}

    def complete_structured(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        schema_name: str,
        schema,
    ) -> ExperimentCompletion:
        self.provider_attempts += 1
        self.calls.append((messages, schema_name, dict(schema)))
        if not self.completions:
            raise AssertionError("unexpected calibration provider call")
        completion = self.completions.pop(0)
        self.provider_completions += 1
        return completion


def _completion(value: object) -> ExperimentCompletion:
    return ExperimentCompletion(
        content=json.dumps(value, separators=(",", ":")),
        input_tokens=11,
        output_tokens=7,
    )


def _rule_mapping(rule: VectorRule) -> dict[str, object]:
    return {
        "permutation": list(rule.permutation),
        "offsets": list(rule.offsets),
        "modulus": rule.modulus,
    }


def test_calibration_seed_rule_is_frozen_independent_and_excludes_failed_s2_seed():
    assert CALIBRATION_SEEDS == (
        474248863,
        1128891870,
        1617203301,
        1004246133,
        567650019,
        841092688,
    )
    assert len(set(CALIBRATION_SEEDS)) == 6
    assert 2211 not in CALIBRATION_SEEDS


def test_calibration_cases_are_deterministic_identifiable_and_truth_preserving():
    for difficulty in CALIBRATION_DIFFICULTIES:
        for seed in CALIBRATION_SEEDS:
            first = generate_calibration_case(seed=seed, difficulty=difficulty)
            second = generate_calibration_case(seed=seed, difficulty=difficulty)
            assert first == second
            assert first.rule.apply(first.query) == first.expected_output
            assert all(
                first.rule.apply(example.input_values) == example.output_values
                for example in first.examples
            )


def test_calibration_formation_and_end_to_end_prompts_do_not_receive_oracle_rule():
    case = generate_calibration_case(
        seed=CALIBRATION_SEEDS[0],
        difficulty="D3_FULL_RANDOM",
    )

    c0 = json.loads(build_calibration_messages(case, "C0_APPLICATION_ONLY")[1]["content"])
    c1 = json.loads(build_calibration_messages(case, "C1_FORMATION_ONLY")[1]["content"])
    c2 = json.loads(build_calibration_messages(case, "C2_END_TO_END")[1]["content"])

    assert c0["rule"] == _rule_mapping(case.rule)
    assert set(c1) == {"modulus", "examples"}
    assert set(c2) == {"modulus", "examples", "query"}
    assert "rule" not in c1
    assert "rule" not in c2
    assert "permutation" not in c1
    assert "offsets" not in c1
    assert "permutation" not in c2
    assert "offsets" not in c2


def test_calibration_selection_uses_only_frozen_thresholds_and_prefers_hardest_admitted():
    cells: list[CalibrationCellResult] = []
    for difficulty in CALIBRATION_DIFFICULTIES:
        for index, seed in enumerate(CALIBRATION_SEEDS):
            if difficulty == "D0_OFFSET_ONLY_RANDOM":
                formation = True
                e2e = True
                application = True
            elif difficulty == "D1_PERMUTATION_ONLY_RANDOM":
                formation = index < 3
                e2e = index < 2
                application = True
            elif difficulty == "D2_FULL_DIAGNOSTIC":
                formation = index < 4
                e2e = index < 3
                application = True
            else:
                formation = index < 3
                e2e = index < 3
                application = index < 5
            cells.append(
                CalibrationCellResult(
                    seed=seed,
                    difficulty=difficulty,
                    application_correct=application,
                    formation_correct=formation,
                    end_to_end_rule_correct=e2e,
                    end_to_end_answer_correct=e2e,
                    input_tokens=1,
                    output_tokens=1,
                )
            )

    summaries, selected = summarize_calibration(tuple(cells))

    assert [summary.admitted for summary in summaries] == [False, True, True, False]
    assert selected == "D2_FULL_DIAGNOSTIC"


def test_calibration_matrix_is_non_adaptive_72_call_ceiling_when_oracle_fake_is_perfect():
    completions: list[ExperimentCompletion] = []
    for difficulty in CALIBRATION_DIFFICULTIES:
        for seed in CALIBRATION_SEEDS:
            case = generate_calibration_case(seed=seed, difficulty=difficulty)
            rule = _rule_mapping(case.rule)
            completions.extend(
                [
                    _completion({"answer": list(case.expected_output)}),
                    _completion(rule),
                    _completion({**rule, "answer": list(case.expected_output)}),
                ]
            )
    client = QueueStructuredClient(completions)

    result = run_calibration_matrix(client)

    assert result.provider_calls == 72
    assert client.provider_attempts == 72
    assert client.provider_completions == 72
    assert len(client.calls) == 72
    assert result.selected_difficulty is None
    assert all(not summary.admitted for summary in result.summaries)
    assert all(cell.application_correct for cell in result.cells)
    assert all(cell.formation_correct for cell in result.cells)
    assert all(cell.end_to_end_joint_correct for cell in result.cells)
    assert [call[1] for call in client.calls[:3]] == [
        "relaylm2_calibration_application",
        "relaylm2_calibration_formation",
        "relaylm2_calibration_end_to_end",
    ]


def test_openai_compatible_calibration_client_sends_strict_json_schema_without_reasoning():
    observed: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        observed.append(body)
        return httpx.Response(
            200,
            json={
                "id": "calibration-response",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"answer":[1,2,3,4]}'},
                    }
                ],
                "usage": {"prompt_tokens": 9, "completion_tokens": 6},
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = OpenAICompatibleStructuredCalibrationClient(
        base_url="http://lmstudio:1234/v1",
        model="google/gemma-4-12b",
        http_client=http_client,
    )
    messages = (
        {"role": "system", "content": "Return the structured answer."},
        {"role": "user", "content": "{}"},
    )

    completion = client.complete_structured(
        messages,
        schema_name="relaylm2_calibration_application",
        schema=ANSWER_SCHEMA,
    )

    assert completion.content == '{"answer":[1,2,3,4]}'
    assert completion.input_tokens == 9
    assert completion.output_tokens == 6
    assert client.provider_attempts == 1
    assert client.provider_completions == 1
    assert len(observed) == 1
    body = observed[0]
    assert body["model"] == "google/gemma-4-12b"
    assert body["stream"] is False
    assert body["temperature"] == 0.0
    assert body["max_tokens"] == 128
    assert "reasoning" not in body
    response_format = body["response_format"]
    assert isinstance(response_format, dict)
    assert response_format["type"] == "json_schema"
    json_schema = response_format["json_schema"]
    assert isinstance(json_schema, dict)
    assert json_schema["name"] == "relaylm2_calibration_application"
    assert json_schema["strict"] is True
    assert json_schema["schema"] == ANSWER_SCHEMA


def test_calibration_protocol_declares_exact_three_probe_order():
    assert CALIBRATION_PROBES == (
        "C0_APPLICATION_ONLY",
        "C1_FORMATION_ONLY",
        "C2_END_TO_END",
    )
