from __future__ import annotations

from collections.abc import Mapping
import argparse
import json
import math
from pathlib import Path
from typing import Any

from relaylm.v2_cognitive_ir_calibration import (
    CALIBRATION_CLAIM_STATUS,
    CALIBRATION_DIFFICULTIES,
    CALIBRATION_MODULUS,
    CALIBRATION_PROBES,
    CALIBRATION_SEEDS,
    CALIBRATION_VECTOR_WIDTH,
    generate_calibration_case,
)
from relaylm.v2_transfer_experiment import VectorRule


FORENSIC_CLAIM_STATUS = "NON_CITABLE_S2_CALIBRATION_FORENSIC"
_RESULT_NAME = "calibration-result.json"
_EVIDENCE_NAME = "request-evidence.jsonl"


class CalibrationForensicError(ValueError):
    """A completed #2211 calibration artifact cannot support bounded forensic analysis."""


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _reject_duplicate_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise CalibrationForensicError(f"duplicate JSON member: {key}")
        value[key] = item
    return value


def _load_json_object_text(text: str, *, label: str) -> dict[str, object]:
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_members)
    except CalibrationForensicError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CalibrationForensicError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise CalibrationForensicError(f"{label} must be a JSON object")
    return value


def _read_json_object(path: Path, *, label: str) -> dict[str, object]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CalibrationForensicError(f"cannot read {label}: {exc}") from exc
    return _load_json_object_text(text, label=label)


def _read_jsonl(path: Path) -> tuple[dict[str, object], ...]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CalibrationForensicError(f"cannot read request evidence: {exc}") from exc
    if not lines:
        raise CalibrationForensicError("request evidence must not be empty")
    return tuple(
        _load_json_object_text(line, label=f"request evidence line {index + 1}")
        for index, line in enumerate(lines)
        if line.strip()
    )


def _expected_call_plan() -> tuple[str, ...]:
    return tuple(
        f"{difficulty}|{seed}|{probe}"
        for difficulty in CALIBRATION_DIFFICULTIES
        for seed in CALIBRATION_SEEDS
        for probe in CALIBRATION_PROBES
    )


def _parse_int_array(value: object, *, label: str, maximum: int) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != CALIBRATION_VECTOR_WIDTH:
        raise CalibrationForensicError(f"{label} must contain exactly four integers")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise CalibrationForensicError(f"{label} must contain only integers")
    parsed = tuple(value)
    if any(item < 0 or item > maximum for item in parsed):
        raise CalibrationForensicError(f"{label} contains an out-of-range value")
    return parsed


def _parse_answer(content: str) -> tuple[int, ...]:
    value = _load_json_object_text(content, label="C0 visible content")
    if set(value) != {"answer"}:
        raise CalibrationForensicError("C0 visible content has unexpected keys")
    return _parse_int_array(
        value.get("answer"),
        label="C0 answer",
        maximum=CALIBRATION_MODULUS - 1,
    )


def _parse_rule_mapping(
    value: Mapping[str, object],
    *,
    expected_keys: set[str],
) -> VectorRule:
    if set(value) != expected_keys:
        raise CalibrationForensicError("structured rule content has unexpected keys")
    permutation = _parse_int_array(
        value.get("permutation"),
        label="permutation",
        maximum=CALIBRATION_VECTOR_WIDTH - 1,
    )
    if tuple(sorted(permutation)) != tuple(range(CALIBRATION_VECTOR_WIDTH)):
        raise CalibrationForensicError("permutation is not a bijection")
    offsets = _parse_int_array(
        value.get("offsets"),
        label="offsets",
        maximum=CALIBRATION_MODULUS - 1,
    )
    modulus = value.get("modulus")
    if modulus != CALIBRATION_MODULUS:
        raise CalibrationForensicError("structured rule content has the wrong modulus")
    try:
        return VectorRule(permutation, offsets, CALIBRATION_MODULUS)
    except (TypeError, ValueError) as exc:
        raise CalibrationForensicError("structured rule content is not a legal rule") from exc


def _parse_rule(content: str) -> VectorRule:
    value = _load_json_object_text(content, label="C1 visible content")
    return _parse_rule_mapping(
        value,
        expected_keys={"permutation", "offsets", "modulus"},
    )


def _parse_end_to_end(content: str) -> tuple[VectorRule, tuple[int, ...]]:
    value = _load_json_object_text(content, label="C2 visible content")
    rule = _parse_rule_mapping(
        value,
        expected_keys={"permutation", "offsets", "modulus", "answer"},
    )
    answer = _parse_int_array(
        value.get("answer"),
        label="C2 answer",
        maximum=CALIBRATION_MODULUS - 1,
    )
    return rule, answer


def _rule_mapping(rule: VectorRule) -> dict[str, object]:
    return {
        "permutation": list(rule.permutation),
        "offsets": list(rule.offsets),
        "modulus": rule.modulus,
    }


def _rule_delta(expected: VectorRule, actual: VectorRule) -> dict[str, object]:
    return {
        "permutation_exact": actual.permutation == expected.permutation,
        "offsets_exact": actual.offsets == expected.offsets,
        "modulus_exact": actual.modulus == expected.modulus,
        "permutation_hamming": sum(
            left != right for left, right in zip(actual.permutation, expected.permutation)
        ),
        "offset_hamming": sum(
            left != right for left, right in zip(actual.offsets, expected.offsets)
        ),
    }


def _answer_delta(expected: tuple[int, ...], actual: tuple[int, ...]) -> dict[str, object]:
    return {
        "exact": actual == expected,
        "hamming": sum(left != right for left, right in zip(actual, expected)),
    }


def _cycle_lengths(permutation: tuple[int, ...]) -> list[int]:
    seen: set[int] = set()
    lengths: list[int] = []
    for start in range(len(permutation)):
        if start in seen:
            continue
        current = start
        length = 0
        while current not in seen:
            seen.add(current)
            current = permutation[current]
            length += 1
        lengths.append(length)
    return sorted(lengths, reverse=True)


def _case_features(case: Any) -> dict[str, object]:
    rule = case.rule
    query_wraparound = sum(
        case.query[rule.permutation[index]] + rule.offsets[index] >= rule.modulus
        for index in range(CALIBRATION_VECTOR_WIDTH)
    )
    example_wraparound = sum(
        example.input_values[rule.permutation[index]] + rule.offsets[index] >= rule.modulus
        for example in case.examples
        for index in range(CALIBRATION_VECTOR_WIDTH)
    )
    identity = tuple(range(CALIBRATION_VECTOR_WIDTH))
    return {
        "permutation_moved_positions": sum(
            left != right for left, right in zip(rule.permutation, identity)
        ),
        "permutation_cycle_lengths": _cycle_lengths(rule.permutation),
        "nonzero_offset_count": sum(value != 0 for value in rule.offsets),
        "offset_sum": sum(rule.offsets),
        "query_wraparound_count": query_wraparound,
        "example_count": len(case.examples),
        "example_wraparound_count": example_wraparound,
    }


def _cell_flags(
    *,
    application_correct: bool,
    formation_correct: bool,
    e2e_rule_correct: bool,
    e2e_answer_correct: bool,
) -> list[str]:
    flags: list[str] = []
    if not application_correct:
        flags.append("APPLICATION_FAILURE")
    if not formation_correct:
        flags.append("FORMATION_FAILURE")
    if not e2e_rule_correct:
        flags.append("END_TO_END_RULE_FAILURE")
    if not e2e_answer_correct:
        flags.append("END_TO_END_ANSWER_FAILURE")
    if not formation_correct and e2e_rule_correct:
        flags.append("FORMATION_GAIN_WITH_QUERY_CANDIDATE")
    if formation_correct and not e2e_rule_correct:
        flags.append("FORMATION_LOSS_WITH_QUERY_CANDIDATE")
    if not e2e_rule_correct and e2e_answer_correct:
        flags.append("ANSWER_CORRECT_UNDER_WRONG_RULE")
    if e2e_rule_correct and not e2e_answer_correct:
        flags.append("RULE_CORRECT_ANSWER_WRONG")
    if not flags:
        flags.append("FULL_CELL_SUCCESS")
    return flags


def _require_bool(value: object, *, label: str) -> bool:
    if not isinstance(value, bool):
        raise CalibrationForensicError(f"{label} must be boolean")
    return value


def _validate_result_header(result: Mapping[str, object]) -> None:
    expected_calls = len(_expected_call_plan())
    if result.get("claim_status") != CALIBRATION_CLAIM_STATUS:
        raise CalibrationForensicError("source result has the wrong claim_status")
    if result.get("citable") is not False:
        raise CalibrationForensicError("source result must remain non-citable")
    if result.get("provider_calls") != expected_calls:
        raise CalibrationForensicError("source result does not contain the frozen 72 calls")
    if result.get("seeds") != list(CALIBRATION_SEEDS):
        raise CalibrationForensicError("source result seed set differs from the frozen calibration")
    if result.get("difficulties") != list(CALIBRATION_DIFFICULTIES):
        raise CalibrationForensicError("source result difficulty set differs from the frozen calibration")
    if result.get("probes") != list(CALIBRATION_PROBES):
        raise CalibrationForensicError("source result probe set differs from the frozen calibration")


def _result_cells(result: Mapping[str, object]) -> dict[tuple[str, int], Mapping[str, object]]:
    raw = result.get("cells")
    if not isinstance(raw, list):
        raise CalibrationForensicError("source result must contain cells")
    expected_count = len(CALIBRATION_DIFFICULTIES) * len(CALIBRATION_SEEDS)
    if len(raw) != expected_count:
        raise CalibrationForensicError("source result does not contain all calibration cells")
    indexed: dict[tuple[str, int], Mapping[str, object]] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            raise CalibrationForensicError("source result cell must be an object")
        difficulty = item.get("difficulty")
        seed = item.get("seed")
        if difficulty not in CALIBRATION_DIFFICULTIES or seed not in CALIBRATION_SEEDS:
            raise CalibrationForensicError("source result cell has unknown coordinates")
        key = (str(difficulty), int(seed))
        if key in indexed:
            raise CalibrationForensicError("source result contains a duplicate cell")
        indexed[key] = item
    return indexed


def _validate_evidence(
    evidence: tuple[dict[str, object], ...],
) -> tuple[str | None, str | None, dict[str, str]]:
    plan = _expected_call_plan()
    if len(evidence) != len(plan):
        raise CalibrationForensicError("request evidence does not contain exactly 72 records")
    contents: dict[str, str] = {}
    run_ids: set[str] = set()
    fingerprints: set[str] = set()
    for index, (record, expected_question) in enumerate(zip(evidence, plan)):
        if record.get("order") != index:
            raise CalibrationForensicError("request evidence order does not match the frozen plan")
        if record.get("question_id") != expected_question:
            raise CalibrationForensicError("request evidence question_id does not match the frozen plan")
        if record.get("classification") != "instrumentation_only":
            raise CalibrationForensicError("request evidence classification is not instrumentation_only")
        content = record.get("content")
        if not isinstance(content, str) or not content.strip():
            raise CalibrationForensicError("request evidence visible content must be non-empty")
        contents[expected_question] = content
        run_id = record.get("run_id")
        fingerprint = record.get("identity_fingerprint")
        if isinstance(run_id, str) and run_id:
            run_ids.add(run_id)
        if isinstance(fingerprint, str) and fingerprint:
            fingerprints.add(fingerprint)
    if len(run_ids) > 1 or len(fingerprints) > 1:
        raise CalibrationForensicError("request evidence spans multiple execution identities")
    return (
        next(iter(run_ids), None),
        next(iter(fingerprints), None),
        contents,
    )


def _admission_counts(sample_count: int) -> dict[str, int]:
    return {
        "application_min": math.ceil(9 * sample_count / 10),
        "formation_min": math.ceil(2 * sample_count / 5),
        "formation_max": math.floor(9 * sample_count / 10),
        "end_to_end_min": math.ceil(sample_count / 5),
        "end_to_end_max": math.floor(4 * sample_count / 5),
    }


def analyze_calibration_payloads(
    result: Mapping[str, object],
    evidence: tuple[dict[str, object], ...],
) -> dict[str, object]:
    """Reconstruct failure geometry from one completed calibration without provider calls."""

    _validate_result_header(result)
    source_cells = _result_cells(result)
    run_id, identity_fingerprint, contents = _validate_evidence(evidence)

    cells: list[dict[str, object]] = []
    for difficulty in CALIBRATION_DIFFICULTIES:
        for seed in CALIBRATION_SEEDS:
            case = generate_calibration_case(seed=seed, difficulty=difficulty)
            prefix = f"{difficulty}|{seed}|"
            application_answer = _parse_answer(contents[prefix + "C0_APPLICATION_ONLY"])
            formation_rule = _parse_rule(contents[prefix + "C1_FORMATION_ONLY"])
            e2e_rule, e2e_answer = _parse_end_to_end(contents[prefix + "C2_END_TO_END"])

            application_correct = application_answer == case.expected_output
            formation_correct = formation_rule == case.rule
            e2e_rule_correct = e2e_rule == case.rule
            e2e_answer_correct = e2e_answer == case.expected_output
            e2e_joint_correct = e2e_rule_correct and e2e_answer_correct

            source = source_cells[(difficulty, seed)]
            expected_bools = {
                "application_correct": application_correct,
                "formation_correct": formation_correct,
                "end_to_end_rule_correct": e2e_rule_correct,
                "end_to_end_answer_correct": e2e_answer_correct,
                "end_to_end_joint_correct": e2e_joint_correct,
            }
            for key, expected in expected_bools.items():
                observed = _require_bool(source.get(key), label=f"source cell {key}")
                if observed != expected:
                    raise CalibrationForensicError(
                        f"source result disagrees with visible evidence for {difficulty}/{seed}/{key}"
                    )

            cells.append(
                {
                    "seed": seed,
                    "difficulty": difficulty,
                    "true_rule": _rule_mapping(case.rule),
                    "query": list(case.query),
                    "expected_answer": list(case.expected_output),
                    "case_features": _case_features(case),
                    "C0": {
                        "answer": list(application_answer),
                        "answer_delta": _answer_delta(case.expected_output, application_answer),
                    },
                    "C1": {
                        "rule": _rule_mapping(formation_rule),
                        "rule_delta": _rule_delta(case.rule, formation_rule),
                    },
                    "C2": {
                        "rule": _rule_mapping(e2e_rule),
                        "rule_delta": _rule_delta(case.rule, e2e_rule),
                        "answer": list(e2e_answer),
                        "answer_delta": _answer_delta(case.expected_output, e2e_answer),
                        "joint_correct": e2e_joint_correct,
                    },
                    "flags": _cell_flags(
                        application_correct=application_correct,
                        formation_correct=formation_correct,
                        e2e_rule_correct=e2e_rule_correct,
                        e2e_answer_correct=e2e_answer_correct,
                    ),
                }
            )

    summaries: list[dict[str, object]] = []
    application_counts: dict[str, int] = {}
    for difficulty in CALIBRATION_DIFFICULTIES:
        group = [cell for cell in cells if cell["difficulty"] == difficulty]
        application_correct = sum(bool(cell["C0"]["answer_delta"]["exact"]) for cell in group)  # type: ignore[index]
        formation_correct = sum(bool(cell["C1"]["rule_delta"]["permutation_exact"]) and bool(cell["C1"]["rule_delta"]["offsets_exact"]) for cell in group)  # type: ignore[index]
        e2e_joint_correct = sum(bool(cell["C2"]["joint_correct"]) for cell in group)  # type: ignore[index]
        application_counts[difficulty] = application_correct
        thresholds = _admission_counts(len(group))
        summaries.append(
            {
                "difficulty": difficulty,
                "sample_count": len(group),
                "application_correct": application_correct,
                "formation_correct": formation_correct,
                "end_to_end_joint_correct": e2e_joint_correct,
                "application_floor": application_correct == 0,
                "admission_count_thresholds": thresholds,
                "admission_margins": {
                    "application_shortfall": max(0, thresholds["application_min"] - application_correct),
                    "formation_lower_shortfall": max(0, thresholds["formation_min"] - formation_correct),
                    "formation_upper_excess": max(0, formation_correct - thresholds["formation_max"]),
                    "end_to_end_lower_shortfall": max(0, thresholds["end_to_end_min"] - e2e_joint_correct),
                    "end_to_end_upper_excess": max(0, e2e_joint_correct - thresholds["end_to_end_max"]),
                },
            }
        )

    nonmonotonic_pairs: list[dict[str, object]] = []
    for earlier_index, earlier in enumerate(CALIBRATION_DIFFICULTIES):
        for later in CALIBRATION_DIFFICULTIES[earlier_index + 1 :]:
            if application_counts[later] > application_counts[earlier]:
                nonmonotonic_pairs.append(
                    {
                        "earlier": earlier,
                        "later": later,
                        "earlier_application_correct": application_counts[earlier],
                        "later_application_correct": application_counts[later],
                    }
                )

    gain_cells = [
        f"{cell['difficulty']}|{cell['seed']}"
        for cell in cells
        if "FORMATION_GAIN_WITH_QUERY_CANDIDATE" in cell["flags"]
    ]
    loss_cells = [
        f"{cell['difficulty']}|{cell['seed']}"
        for cell in cells
        if "FORMATION_LOSS_WITH_QUERY_CANDIDATE" in cell["flags"]
    ]

    return {
        "claim_status": FORENSIC_CLAIM_STATUS,
        "citable": False,
        "provider_calls_added": 0,
        "source_claim_status": result.get("claim_status"),
        "source_provider_calls": result.get("provider_calls"),
        "source_selected_difficulty": result.get("selected_difficulty"),
        "run_id": run_id,
        "identity_fingerprint": identity_fingerprint,
        "interpretation_boundary": {
            "descriptive_only": True,
            "causal_effect_claims": False,
            "threshold_retuning_authorized": False,
            "s2_authorized": False,
            "architecture_consequence": "NONE",
        },
        "difficulty_summaries": summaries,
        "cross_difficulty": {
            "application_nonmonotonic_pairs": nonmonotonic_pairs,
            "formation_gain_with_query_candidates": gain_cells,
            "formation_loss_with_query_candidates": loss_cells,
            "application_floor_difficulties": [
                item["difficulty"] for item in summaries if item["application_floor"]
            ],
        },
        "cells": cells,
    }


def analyze_calibration_artifact(artifact_root: str | Path) -> dict[str, object]:
    root = Path(artifact_root)
    result = _read_json_object(root / _RESULT_NAME, label=_RESULT_NAME)
    evidence = _read_jsonl(root / _EVIDENCE_NAME)
    return analyze_calibration_payloads(result, evidence)


def _write_output(path: Path, report: Mapping[str, object]) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(dict(report)))
            handle.write("\n")
    except OSError as exc:
        raise CalibrationForensicError(f"cannot write forensic output: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Zero-provider forensic analysis of one completed #2211 calibration artifact."
    )
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = analyze_calibration_artifact(args.artifact_root)
    if args.output:
        _write_output(Path(args.output), report)
    else:
        print(_canonical_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
