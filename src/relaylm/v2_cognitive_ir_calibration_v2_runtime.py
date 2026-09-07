from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from typing import Protocol

from relaylm.v2_cognitive_ir_calibration_v2 import (
    CALIBRATION_V2_CLAIM_STATUS,
    CALIBRATION_V2_PROBES,
    CALIBRATION_V2_REGIMES,
    CALIBRATION_V2_SEED_COUNT,
    CALIBRATION_V2_SEEDS,
    CalibrationV2Error,
    CalibrationV2RegimeSummary,
    build_calibration_v2_messages,
    calibration_v2_schema_for_probe,
    generate_calibration_v2_case,
    select_calibration_v2_regime,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from relaylm.v2_transfer_experiment import VectorRule


class StructuredCalibrationV2Client(Protocol):
    provider_attempts: int
    provider_completions: int

    @property
    def transport_identity(self) -> Mapping[str, object]: ...

    def complete_structured(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        schema_name: str,
        schema: Mapping[str, object],
    ) -> ExperimentCompletion: ...


def _reject_duplicate_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise CalibrationV2Error(f"duplicate JSON member: {key}")
        value[key] = item
    return value


def _load_object(text: str, *, label: str) -> dict[str, object]:
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_members)
    except CalibrationV2Error:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CalibrationV2Error(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise CalibrationV2Error(f"{label} must be a JSON object")
    return value


def _int_array(value: object, *, label: str, maximum: int) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != 4:
        raise CalibrationV2Error(f"{label} must contain exactly four integers")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise CalibrationV2Error(f"{label} must contain only integers")
    parsed = tuple(value)
    if any(item < 0 or item > maximum for item in parsed):
        raise CalibrationV2Error(f"{label} contains an out-of-range value")
    return parsed


def _rule_from_object(value: Mapping[str, object], *, exact_keys: set[str]) -> VectorRule:
    if set(value) != exact_keys:
        raise CalibrationV2Error("structured rule output has unexpected keys")
    permutation = _int_array(value.get("permutation"), label="permutation", maximum=3)
    if len(set(permutation)) != 4:
        raise CalibrationV2Error("permutation must contain each source index exactly once")
    offsets = _int_array(value.get("offsets"), label="offsets", maximum=9)
    if value.get("modulus") != 10:
        raise CalibrationV2Error("structured rule output has the wrong modulus")
    try:
        return VectorRule(permutation, offsets, 10)
    except (TypeError, ValueError) as exc:
        raise CalibrationV2Error("structured rule output is not a legal vector rule") from exc


def _parse_answer(text: str) -> tuple[int, ...]:
    value = _load_object(text, label="application response")
    if set(value) != {"answer"}:
        raise CalibrationV2Error("application response must contain exactly answer")
    return _int_array(value.get("answer"), label="answer", maximum=9)


def _parse_rule(text: str) -> VectorRule:
    value = _load_object(text, label="formation response")
    return _rule_from_object(value, exact_keys={"permutation", "offsets", "modulus"})


def _parse_end_to_end(text: str) -> tuple[VectorRule, tuple[int, ...]]:
    value = _load_object(text, label="end-to-end response")
    rule = _rule_from_object(
        value,
        exact_keys={"permutation", "offsets", "modulus", "answer"},
    )
    answer = _int_array(value.get("answer"), label="answer", maximum=9)
    return rule, answer


@dataclass(frozen=True, slots=True)
class CalibrationV2CellResult:
    seed: int
    regime: str
    application_correct: bool
    formation_correct: bool
    end_to_end_rule_correct: bool
    end_to_end_answer_correct: bool
    input_tokens: int
    output_tokens: int

    @property
    def end_to_end_joint_correct(self) -> bool:
        return self.end_to_end_rule_correct and self.end_to_end_answer_correct


@dataclass(frozen=True, slots=True)
class CalibrationV2MatrixResult:
    cells: tuple[CalibrationV2CellResult, ...]
    summaries: tuple[CalibrationV2RegimeSummary, ...]
    selected_regime: str | None
    provider_calls: int
    claim_status: str = CALIBRATION_V2_CLAIM_STATUS
    citable: bool = False

    @property
    def total_input_tokens(self) -> int:
        return sum(cell.input_tokens for cell in self.cells)

    @property
    def total_output_tokens(self) -> int:
        return sum(cell.output_tokens for cell in self.cells)

    def to_mapping(self) -> dict[str, object]:
        return {
            "claim_status": self.claim_status,
            "citable": self.citable,
            "provider_calls": self.provider_calls,
            "selected_regime": self.selected_regime,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "seeds": list(CALIBRATION_V2_SEEDS),
            "regimes": list(CALIBRATION_V2_REGIMES),
            "probes": list(CALIBRATION_V2_PROBES),
            "summaries": [
                {
                    "regime": item.regime,
                    "sample_count": item.sample_count,
                    "application_correct": item.application_correct,
                    "formation_correct": item.formation_correct,
                    "end_to_end_joint_correct": item.end_to_end_joint_correct,
                    "application_rate": item.application_correct / item.sample_count,
                    "formation_rate": item.formation_correct / item.sample_count,
                    "end_to_end_rate": item.end_to_end_joint_correct / item.sample_count,
                    "admitted": item.admitted,
                }
                for item in self.summaries
            ],
            "cells": [
                {
                    "seed": cell.seed,
                    "regime": cell.regime,
                    "application_correct": cell.application_correct,
                    "formation_correct": cell.formation_correct,
                    "end_to_end_rule_correct": cell.end_to_end_rule_correct,
                    "end_to_end_answer_correct": cell.end_to_end_answer_correct,
                    "end_to_end_joint_correct": cell.end_to_end_joint_correct,
                    "input_tokens": cell.input_tokens,
                    "output_tokens": cell.output_tokens,
                }
                for cell in self.cells
            ],
        }


def run_calibration_v2_matrix(
    client: StructuredCalibrationV2Client,
) -> CalibrationV2MatrixResult:
    """Run the frozen factorized calibration-v2 matrix with no retries or adaptation."""

    cells: list[CalibrationV2CellResult] = []
    for regime in CALIBRATION_V2_REGIMES:
        for seed in CALIBRATION_V2_SEEDS:
            case = generate_calibration_v2_case(seed=seed, regime=regime)
            input_tokens = 0
            output_tokens = 0

            schema_name, schema = calibration_v2_schema_for_probe("C0_APPLICATION_ONLY")
            application_completion = client.complete_structured(
                build_calibration_v2_messages(case, "C0_APPLICATION_ONLY"),
                schema_name=schema_name,
                schema=schema,
            )
            input_tokens += application_completion.input_tokens
            output_tokens += application_completion.output_tokens
            application_answer = _parse_answer(application_completion.content)

            schema_name, schema = calibration_v2_schema_for_probe("C1_FORMATION_ONLY")
            formation_completion = client.complete_structured(
                build_calibration_v2_messages(case, "C1_FORMATION_ONLY"),
                schema_name=schema_name,
                schema=schema,
            )
            input_tokens += formation_completion.input_tokens
            output_tokens += formation_completion.output_tokens
            formation_rule = _parse_rule(formation_completion.content)

            schema_name, schema = calibration_v2_schema_for_probe("C2_END_TO_END")
            e2e_completion = client.complete_structured(
                build_calibration_v2_messages(case, "C2_END_TO_END"),
                schema_name=schema_name,
                schema=schema,
            )
            input_tokens += e2e_completion.input_tokens
            output_tokens += e2e_completion.output_tokens
            e2e_rule, e2e_answer = _parse_end_to_end(e2e_completion.content)

            cells.append(
                CalibrationV2CellResult(
                    seed=seed,
                    regime=regime,
                    application_correct=application_answer == case.expected_output,
                    formation_correct=formation_rule == case.rule,
                    end_to_end_rule_correct=e2e_rule == case.rule,
                    end_to_end_answer_correct=e2e_answer == case.expected_output,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )

    summaries: list[CalibrationV2RegimeSummary] = []
    for regime in CALIBRATION_V2_REGIMES:
        group = tuple(cell for cell in cells if cell.regime == regime)
        if len(group) != CALIBRATION_V2_SEED_COUNT:
            raise CalibrationV2Error("calibration-v2 matrix has an incomplete regime")
        summaries.append(
            CalibrationV2RegimeSummary(
                regime=regime,
                sample_count=len(group),
                application_correct=sum(cell.application_correct for cell in group),
                formation_correct=sum(cell.formation_correct for cell in group),
                end_to_end_joint_correct=sum(cell.end_to_end_joint_correct for cell in group),
            )
        )

    frozen_summaries = tuple(summaries)
    return CalibrationV2MatrixResult(
        cells=tuple(cells),
        summaries=frozen_summaries,
        selected_regime=select_calibration_v2_regime(frozen_summaries),
        provider_calls=client.provider_attempts,
    )
