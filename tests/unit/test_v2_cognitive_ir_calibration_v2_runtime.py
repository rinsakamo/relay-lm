from __future__ import annotations

from collections.abc import Mapping
import json

import pytest

from relaylm.v2_cognitive_ir_calibration_v2 import (
    CALIBRATION_V2_CLAIM_STATUS,
    CALIBRATION_V2_PROBES,
    CALIBRATION_V2_REGIMES,
    CALIBRATION_V2_SEEDS,
    CalibrationV2Error,
    generate_calibration_v2_case,
)
from relaylm.v2_cognitive_ir_calibration_v2_runtime import run_calibration_v2_matrix
from relaylm.v2_transfer_actual_model import ExperimentCompletion


def _rule_mapping(case) -> dict[str, object]:
    return {
        "permutation": list(case.rule.permutation),
        "offsets": list(case.rule.offsets),
        "modulus": case.rule.modulus,
    }


class ExactQueueClient:
    def __init__(self, *, corrupt_first_formation: bool = False) -> None:
        self.provider_attempts = 0
        self.provider_completions = 0
        self.corrupt_first_formation = corrupt_first_formation

    @property
    def transport_identity(self) -> dict[str, object]:
        return {"synthetic": True}

    def complete_structured(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        schema_name: str,
        schema: Mapping[str, object],
    ) -> ExperimentCompletion:
        del schema_name, schema
        call_index = self.provider_completions
        cell_index = call_index // len(CALIBRATION_V2_PROBES)
        regime_index = cell_index // len(CALIBRATION_V2_SEEDS)
        seed_index = cell_index % len(CALIBRATION_V2_SEEDS)
        probe_index = call_index % len(CALIBRATION_V2_PROBES)
        case = generate_calibration_v2_case(
            seed=CALIBRATION_V2_SEEDS[seed_index],
            regime=CALIBRATION_V2_REGIMES[regime_index],
        )

        self.provider_attempts += 1
        if probe_index == 0:
            content = json.dumps({"answer": list(case.expected_output)}, separators=(",", ":"))
        elif probe_index == 1:
            payload = _rule_mapping(case)
            if self.corrupt_first_formation and call_index == 1:
                payload["permutation"] = [0, 1, 2, 3]
            content = json.dumps(payload, separators=(",", ":"))
        else:
            payload = _rule_mapping(case)
            payload["answer"] = list(case.expected_output)
            content = json.dumps(payload, separators=(",", ":"))
        self.provider_completions += 1
        return ExperimentCompletion(
            content=content,
            input_tokens=10,
            output_tokens=5,
            response_id=f"resp-{self.provider_completions}",
        )


def test_runtime_executes_exact_72_call_matrix_and_preserves_ceiling_rejection() -> None:
    client = ExactQueueClient()
    result = run_calibration_v2_matrix(client)

    assert client.provider_attempts == client.provider_completions == 72
    assert result.provider_calls == 72
    assert result.claim_status == CALIBRATION_V2_CLAIM_STATUS
    assert result.citable is False
    assert result.selected_regime is None
    assert len(result.cells) == 24
    assert all(item.application_correct == 6 for item in result.summaries)
    assert all(item.formation_correct == 6 for item in result.summaries)
    assert all(item.end_to_end_joint_correct == 6 for item in result.summaries)
    assert result.total_input_tokens == 720
    assert result.total_output_tokens == 360


def test_runtime_records_wrong_formation_without_rescue() -> None:
    client = ExactQueueClient(corrupt_first_formation=True)
    result = run_calibration_v2_matrix(client)

    first = result.cells[0]
    assert first.application_correct is True
    assert first.formation_correct is False
    assert first.end_to_end_joint_correct is True
    assert client.provider_attempts == client.provider_completions == 72


def test_runtime_rejects_duplicate_json_members() -> None:
    class DuplicateClient(ExactQueueClient):
        def complete_structured(self, messages, *, schema_name, schema):
            completion = super().complete_structured(
                messages,
                schema_name=schema_name,
                schema=schema,
            )
            if self.provider_completions == 1:
                return ExperimentCompletion(
                    content='{"answer":[0,0,0,0],"answer":[0,0,0,0]}',
                    input_tokens=completion.input_tokens,
                    output_tokens=completion.output_tokens,
                    response_id=completion.response_id,
                )
            return completion

    with pytest.raises(CalibrationV2Error, match="duplicate JSON member"):
        run_calibration_v2_matrix(DuplicateClient())


def test_runtime_result_mapping_keeps_frozen_coordinates() -> None:
    result = run_calibration_v2_matrix(ExactQueueClient()).to_mapping()
    assert result["seeds"] == list(CALIBRATION_V2_SEEDS)
    assert result["regimes"] == list(CALIBRATION_V2_REGIMES)
    assert result["probes"] == list(CALIBRATION_V2_PROBES)
    assert result["selected_regime"] is None
