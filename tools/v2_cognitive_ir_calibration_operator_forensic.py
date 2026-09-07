from __future__ import annotations

from collections.abc import Mapping
import argparse
import json
from pathlib import Path

from relaylm.v2_cognitive_ir_calibration import (
    CALIBRATION_DIFFICULTIES,
    CALIBRATION_MODULUS,
    CALIBRATION_SEEDS,
    CALIBRATION_VECTOR_WIDTH,
    generate_calibration_case,
)
from relaylm.v2_transfer_experiment import VectorRule
from tools.v2_cognitive_ir_calibration_forensic import FORENSIC_CLAIM_STATUS


OPERATOR_FORENSIC_CLAIM_STATUS = "NON_CITABLE_S2_CALIBRATION_OPERATOR_FORENSIC"


class CalibrationOperatorForensicError(ValueError):
    """A calibration forensic report cannot support bounded operator diagnostics."""


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
            raise CalibrationOperatorForensicError(f"duplicate JSON member: {key}")
        value[key] = item
    return value


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        text = path.read_text(encoding="utf-8")
        value = json.loads(text, object_pairs_hook=_reject_duplicate_members)
    except CalibrationOperatorForensicError:
        raise
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CalibrationOperatorForensicError(f"cannot read source forensic report: {exc}") from exc
    if not isinstance(value, dict):
        raise CalibrationOperatorForensicError("source forensic report must be a JSON object")
    return value


def _parse_int_array(value: object, *, label: str, maximum: int) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != CALIBRATION_VECTOR_WIDTH:
        raise CalibrationOperatorForensicError(f"{label} must contain exactly four integers")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise CalibrationOperatorForensicError(f"{label} must contain only integers")
    parsed = tuple(value)
    if any(item < 0 or item > maximum for item in parsed):
        raise CalibrationOperatorForensicError(f"{label} contains an out-of-range value")
    return parsed


def _parse_rule(value: object, *, label: str) -> VectorRule:
    if not isinstance(value, Mapping):
        raise CalibrationOperatorForensicError(f"{label} must be an object")
    if set(value) != {"permutation", "offsets", "modulus"}:
        raise CalibrationOperatorForensicError(f"{label} has unexpected keys")
    permutation = _parse_int_array(
        value.get("permutation"),
        label=f"{label}.permutation",
        maximum=CALIBRATION_VECTOR_WIDTH - 1,
    )
    if tuple(sorted(permutation)) != tuple(range(CALIBRATION_VECTOR_WIDTH)):
        raise CalibrationOperatorForensicError(f"{label}.permutation is not a bijection")
    offsets = _parse_int_array(
        value.get("offsets"),
        label=f"{label}.offsets",
        maximum=CALIBRATION_MODULUS - 1,
    )
    if value.get("modulus") != CALIBRATION_MODULUS:
        raise CalibrationOperatorForensicError(f"{label}.modulus is not the frozen modulus")
    return VectorRule(permutation, offsets, CALIBRATION_MODULUS)


def _inverse_permutation(permutation: tuple[int, ...]) -> tuple[int, ...]:
    inverse = [0] * len(permutation)
    for output_index, input_index in enumerate(permutation):
        inverse[input_index] = output_index
    return tuple(inverse)


def _single_position_swap(expected: tuple[int, ...], actual: tuple[int, ...]) -> bool:
    differing = [index for index, pair in enumerate(zip(expected, actual)) if pair[0] != pair[1]]
    if len(differing) != 2:
        return False
    left, right = differing
    swapped = list(expected)
    swapped[left], swapped[right] = swapped[right], swapped[left]
    return tuple(swapped) == actual


def _cyclic_shifts(expected: tuple[int, ...], actual: tuple[int, ...]) -> list[int]:
    shifts: list[int] = []
    for shift in range(1, len(expected)):
        candidate = expected[shift:] + expected[:shift]
        if candidate == actual:
            shifts.append(shift)
    return shifts


def _permutation_relations(expected: tuple[int, ...], actual: tuple[int, ...]) -> dict[str, object]:
    inverse = _inverse_permutation(expected)
    shifts = _cyclic_shifts(expected, actual)
    relations: list[str] = []
    if actual == expected:
        relations.append("EXACT")
    if actual == tuple(range(CALIBRATION_VECTOR_WIDTH)) and actual != expected:
        relations.append("IDENTITY_COLLAPSE_CANDIDATE")
    if actual == inverse and actual != expected:
        relations.append("INVERSE_MAPPING_CANDIDATE")
    if _single_position_swap(expected, actual):
        relations.append("SINGLE_POSITION_SWAP_CANDIDATE")
    if shifts:
        relations.append("CYCLIC_SHIFT_CANDIDATE")
    if not relations:
        relations.append("OTHER")
    return {
        "relations": relations,
        "inverse_true": list(inverse),
        "cyclic_shift_amounts": shifts,
    }


def _apply(
    query: tuple[int, ...],
    permutation: tuple[int, ...],
    offsets: tuple[int, ...],
    modulus: int,
) -> tuple[int, ...]:
    return tuple(
        (query[permutation[index]] + offsets[index]) % modulus
        for index in range(CALIBRATION_VECTOR_WIDTH)
    )


def _inverse_mapping_rule(rule: VectorRule) -> VectorRule:
    inverse = _inverse_permutation(rule.permutation)
    # If permutation[i] is instead read as the destination of input i, then
    # output[j] receives input[inverse[j]] and the offset attached to that input.
    offsets = tuple(rule.offsets[inverse[index]] for index in range(CALIBRATION_VECTOR_WIDTH))
    return VectorRule(inverse, offsets, rule.modulus)


def _candidate_answers(
    *,
    query: tuple[int, ...],
    true_rule: VectorRule,
    actual: tuple[int, ...],
    reported_rule: VectorRule | None = None,
) -> dict[str, object]:
    candidates: dict[str, tuple[int, ...]] = {
        "TRUE_RULE": true_rule.apply(query),
        "INVERSE_MAPPING_CONVENTION": _inverse_mapping_rule(true_rule).apply(query),
        "INVERSE_PERM_KEEP_OUTPUT_OFFSETS": _apply(
            query,
            _inverse_permutation(true_rule.permutation),
            true_rule.offsets,
            true_rule.modulus,
        ),
        "NEGATIVE_OFFSETS": _apply(
            query,
            true_rule.permutation,
            tuple((-value) % true_rule.modulus for value in true_rule.offsets),
            true_rule.modulus,
        ),
        "ZERO_OFFSETS": _apply(
            query,
            true_rule.permutation,
            (0,) * CALIBRATION_VECTOR_WIDTH,
            true_rule.modulus,
        ),
    }
    if reported_rule is not None:
        candidates["REPORTED_RULE"] = reported_rule.apply(query)
        candidates["REPORTED_RULE_INVERSE_MAPPING"] = _inverse_mapping_rule(reported_rule).apply(query)

    exact_matches = [name for name, answer in candidates.items() if answer == actual]
    wrong_modulus_matches: list[int] = []
    for modulus in range(2, 17):
        if modulus == true_rule.modulus:
            continue
        candidate = _apply(query, true_rule.permutation, true_rule.offsets, modulus)
        if candidate == actual:
            wrong_modulus_matches.append(modulus)

    return {
        "exact_named_matches": exact_matches,
        "wrong_modulus_matches": wrong_modulus_matches,
        "reported_rule_self_consistent": (
            reported_rule is not None and reported_rule.apply(query) == actual
        ),
    }


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise CalibrationOperatorForensicError(f"{label} must be an object")
    return value


def _validate_source_header(source: Mapping[str, object]) -> None:
    if source.get("claim_status") != FORENSIC_CLAIM_STATUS:
        raise CalibrationOperatorForensicError("source report is not the #2211 calibration forensic")
    if source.get("citable") is not False:
        raise CalibrationOperatorForensicError("source forensic must remain non-citable")
    if source.get("provider_calls_added") != 0:
        raise CalibrationOperatorForensicError("source forensic unexpectedly added provider calls")
    boundary = _mapping(source.get("interpretation_boundary"), label="interpretation_boundary")
    if boundary.get("causal_effect_claims") is not False:
        raise CalibrationOperatorForensicError("source forensic causal boundary is not intact")
    if boundary.get("s2_authorized") is not False:
        raise CalibrationOperatorForensicError("source forensic unexpectedly authorizes S2")
    if boundary.get("architecture_consequence") != "NONE":
        raise CalibrationOperatorForensicError("source forensic has architecture consequence")


def _source_cells(source: Mapping[str, object]) -> dict[tuple[str, int], Mapping[str, object]]:
    raw_cells = source.get("cells")
    if not isinstance(raw_cells, list):
        raise CalibrationOperatorForensicError("source forensic must contain cells")
    expected_count = len(CALIBRATION_DIFFICULTIES) * len(CALIBRATION_SEEDS)
    if len(raw_cells) != expected_count:
        raise CalibrationOperatorForensicError("source forensic does not contain all 24 cells")
    indexed: dict[tuple[str, int], Mapping[str, object]] = {}
    for raw in raw_cells:
        cell = _mapping(raw, label="source cell")
        difficulty = cell.get("difficulty")
        seed = cell.get("seed")
        if difficulty not in CALIBRATION_DIFFICULTIES or seed not in CALIBRATION_SEEDS:
            raise CalibrationOperatorForensicError("source cell has unknown coordinates")
        key = (str(difficulty), int(seed))
        if key in indexed:
            raise CalibrationOperatorForensicError("source forensic has duplicate cell coordinates")
        indexed[key] = cell
    return indexed


def analyze_operator_conventions(source: Mapping[str, object]) -> dict[str, object]:
    """Classify already-observed wrong rules/answers under bounded alternative operators."""

    _validate_source_header(source)
    indexed = _source_cells(source)
    cells: list[dict[str, object]] = []

    for difficulty in CALIBRATION_DIFFICULTIES:
        for seed in CALIBRATION_SEEDS:
            cell = indexed[(difficulty, seed)]
            case = generate_calibration_case(seed=seed, difficulty=difficulty)
            true_rule = _parse_rule(cell.get("true_rule"), label="true_rule")
            if true_rule != case.rule:
                raise CalibrationOperatorForensicError("source forensic true rule drifted from generator")
            query = _parse_int_array(
                cell.get("query"),
                label="query",
                maximum=CALIBRATION_MODULUS - 1,
            )
            if query != case.query:
                raise CalibrationOperatorForensicError("source forensic query drifted from generator")
            expected_answer = _parse_int_array(
                cell.get("expected_answer"),
                label="expected_answer",
                maximum=CALIBRATION_MODULUS - 1,
            )
            if expected_answer != case.expected_output:
                raise CalibrationOperatorForensicError("source forensic expected answer drifted")

            c0 = _mapping(cell.get("C0"), label="C0")
            c1 = _mapping(cell.get("C1"), label="C1")
            c2 = _mapping(cell.get("C2"), label="C2")
            c0_answer = _parse_int_array(
                c0.get("answer"),
                label="C0.answer",
                maximum=CALIBRATION_MODULUS - 1,
            )
            c1_rule = _parse_rule(c1.get("rule"), label="C1.rule")
            c2_rule = _parse_rule(c2.get("rule"), label="C2.rule")
            c2_answer = _parse_int_array(
                c2.get("answer"),
                label="C2.answer",
                maximum=CALIBRATION_MODULUS - 1,
            )

            cells.append(
                {
                    "difficulty": difficulty,
                    "seed": seed,
                    "C0": {
                        "correct": c0_answer == expected_answer,
                        "answer_hypotheses": _candidate_answers(
                            query=query,
                            true_rule=true_rule,
                            actual=c0_answer,
                        ),
                    },
                    "C1": {
                        "rule_correct": c1_rule == true_rule,
                        "permutation_relation": _permutation_relations(
                            true_rule.permutation,
                            c1_rule.permutation,
                        ),
                        "offsets_exact": c1_rule.offsets == true_rule.offsets,
                    },
                    "C2": {
                        "rule_correct": c2_rule == true_rule,
                        "answer_correct": c2_answer == expected_answer,
                        "permutation_relation": _permutation_relations(
                            true_rule.permutation,
                            c2_rule.permutation,
                        ),
                        "offsets_exact": c2_rule.offsets == true_rule.offsets,
                        "answer_hypotheses": _candidate_answers(
                            query=query,
                            true_rule=true_rule,
                            actual=c2_answer,
                            reported_rule=c2_rule,
                        ),
                    },
                }
            )

    summaries: list[dict[str, object]] = []
    for difficulty in CALIBRATION_DIFFICULTIES:
        group = [cell for cell in cells if cell["difficulty"] == difficulty]

        def relation_count(probe: str, relation: str) -> int:
            return sum(
                relation in cell[probe]["permutation_relation"]["relations"]  # type: ignore[index]
                for cell in group
            )

        wrong_c0 = [cell for cell in group if not cell["C0"]["correct"]]  # type: ignore[index]
        wrong_c2_answers = [cell for cell in group if not cell["C2"]["answer_correct"]]  # type: ignore[index]
        summaries.append(
            {
                "difficulty": difficulty,
                "C1_permutation_relations": {
                    relation: relation_count("C1", relation)
                    for relation in (
                        "EXACT",
                        "IDENTITY_COLLAPSE_CANDIDATE",
                        "INVERSE_MAPPING_CANDIDATE",
                        "SINGLE_POSITION_SWAP_CANDIDATE",
                        "CYCLIC_SHIFT_CANDIDATE",
                        "OTHER",
                    )
                },
                "C2_permutation_relations": {
                    relation: relation_count("C2", relation)
                    for relation in (
                        "EXACT",
                        "IDENTITY_COLLAPSE_CANDIDATE",
                        "INVERSE_MAPPING_CANDIDATE",
                        "SINGLE_POSITION_SWAP_CANDIDATE",
                        "CYCLIC_SHIFT_CANDIDATE",
                        "OTHER",
                    )
                },
                "C0_wrong_answer_cells": len(wrong_c0),
                "C0_wrong_answer_explained_by_named_candidate": sum(
                    bool(cell["C0"]["answer_hypotheses"]["exact_named_matches"])  # type: ignore[index]
                    or bool(cell["C0"]["answer_hypotheses"]["wrong_modulus_matches"])  # type: ignore[index]
                    for cell in wrong_c0
                ),
                "C2_wrong_answer_cells": len(wrong_c2_answers),
                "C2_reported_rule_self_consistent_answers": sum(
                    bool(cell["C2"]["answer_hypotheses"]["reported_rule_self_consistent"])  # type: ignore[index]
                    for cell in group
                ),
                "C2_exact_rule_but_wrong_answer": sum(
                    bool(cell["C2"]["rule_correct"]) and not bool(cell["C2"]["answer_correct"])  # type: ignore[index]
                    for cell in group
                ),
            }
        )

    return {
        "claim_status": OPERATOR_FORENSIC_CLAIM_STATUS,
        "citable": False,
        "provider_calls_added": 0,
        "source_claim_status": source.get("claim_status"),
        "source_run_id": source.get("run_id"),
        "source_identity_fingerprint": source.get("identity_fingerprint"),
        "source_selected_difficulty": source.get("source_selected_difficulty"),
        "interpretation_boundary": {
            "descriptive_hypothesis_matching_only": True,
            "operator_error_cause_proven": False,
            "model_capability_ordering_proven": False,
            "threshold_retuning_authorized": False,
            "s2_authorized": False,
            "architecture_consequence": "NONE",
        },
        "difficulty_summaries": summaries,
        "cells": cells,
    }


def analyze_operator_forensic_file(path: str | Path) -> dict[str, object]:
    return analyze_operator_conventions(_load_json_object(Path(path)))


def _write_output(path: Path, report: Mapping[str, object]) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_json(dict(report)))
            handle.write("\n")
    except OSError as exc:
        raise CalibrationOperatorForensicError(f"cannot write operator forensic output: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Zero-provider operator-convention forensic for one #2211 calibration forensic report."
    )
    parser.add_argument("--forensic", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = analyze_operator_forensic_file(args.forensic)
    if args.output:
        _write_output(Path(args.output), report)
    else:
        print(_canonical_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
