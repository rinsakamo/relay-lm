from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import permutations
import json
from typing import Mapping

from relaylm.v2_cognitive_ir_calibration import (
    ANSWER_SCHEMA,
    END_TO_END_SCHEMA,
    RULE_SCHEMA,
)
from relaylm.v2_transfer_experiment import PublicExample, VectorRule


CALIBRATION_V2_LABEL = "relaylm2-cognitive-ir-calibration-v2-factorized"
CALIBRATION_V2_CLAIM_STATUS = "NON_CITABLE_S2_CALIBRATION_V2"
CALIBRATION_V2_MODULUS = 10
CALIBRATION_V2_VECTOR_WIDTH = 4
CALIBRATION_V2_SEED_COUNT = 6
CALIBRATION_V2_PROBES = (
    "C0_APPLICATION_ONLY",
    "C1_FORMATION_ONLY",
    "C2_END_TO_END",
)
CALIBRATION_V2_REGIMES = (
    "V2_SINGLE_SWAP_ZERO_OFFSET",
    "V2_IDENTITY_OFFSET_NO_WRAP",
    "V2_IDENTITY_OFFSET_WRAP",
    "V2_SINGLE_SWAP_OFFSET_NO_WRAP",
)
CALIBRATION_V2_SELECTION_PRIORITY = (
    "V2_SINGLE_SWAP_OFFSET_NO_WRAP",
    "V2_SINGLE_SWAP_ZERO_OFFSET",
    "V2_IDENTITY_OFFSET_NO_WRAP",
    "V2_IDENTITY_OFFSET_WRAP",
)
CALIBRATION_V2_PROVIDER_CALLS = (
    CALIBRATION_V2_SEED_COUNT * len(CALIBRATION_V2_REGIMES) * len(CALIBRATION_V2_PROBES)
)
_SHARED_SWAP_LABEL = "factor:single-swap"
_SHARED_OFFSET_LABEL = "factor:offsets"

_OPERATOR_CONTRACT = (
    "Use source-index-for-output semantics exactly: for every output position i, "
    "output[i] = (input[permutation[i]] + offsets[i]) modulo modulus. "
    "Equivalently, permutation=[p0,p1,p2,p3] means output positions 0..3 read "
    "input[p0],input[p1],input[p2],input[p3] respectively. Do not assume identity mapping; "
    "infer or apply every source index and offset, and check the rule against all supplied examples."
)


class CalibrationV2Error(ValueError):
    """The factorized #2211 calibration-v2 contract cannot be satisfied."""


def _seed_bytes(seed: int, label: str) -> bytes:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if not isinstance(label, str) or not label:
        raise TypeError("seed label must be non-empty")
    return hashlib.sha256(f"{CALIBRATION_V2_LABEL}|{seed}|{label}".encode("utf-8")).digest()


def calibration_v2_seeds() -> tuple[int, ...]:
    values: list[int] = []
    for index in range(CALIBRATION_V2_SEED_COUNT):
        raw = hashlib.sha256(
            f"{CALIBRATION_V2_LABEL}|seed|{index}".encode("utf-8")
        ).digest()
        values.append(int.from_bytes(raw[:4], "big") & 0x7FFFFFFF)
    seeds = tuple(values)
    if len(set(seeds)) != CALIBRATION_V2_SEED_COUNT or 2211 in seeds:
        raise AssertionError("calibration-v2 seed rule produced an invalid seed set")
    return seeds


CALIBRATION_V2_SEEDS = calibration_v2_seeds()


def _json_text(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _identity() -> tuple[int, ...]:
    return tuple(range(CALIBRATION_V2_VECTOR_WIDTH))


def _single_swap(seed: int, label: str) -> tuple[int, ...]:
    raw = _seed_bytes(seed, f"{label}:swap")
    left = raw[0] % CALIBRATION_V2_VECTOR_WIDTH
    right = raw[1] % (CALIBRATION_V2_VECTOR_WIDTH - 1)
    if right >= left:
        right += 1
    permutation = list(_identity())
    permutation[left], permutation[right] = permutation[right], permutation[left]
    return tuple(permutation)


def _small_nonzero_offsets(seed: int, label: str) -> tuple[int, ...]:
    return tuple(
        1 + (_seed_bytes(seed, f"{label}:offset:{index}")[0] % 3)
        for index in range(CALIBRATION_V2_VECTOR_WIDTH)
    )


def _rule_for_regime(seed: int, regime: str) -> VectorRule:
    zeros = (0,) * CALIBRATION_V2_VECTOR_WIDTH
    shared_swap = _single_swap(seed, _SHARED_SWAP_LABEL)
    shared_offsets = _small_nonzero_offsets(seed, _SHARED_OFFSET_LABEL)
    if regime == "V2_SINGLE_SWAP_ZERO_OFFSET":
        return VectorRule(shared_swap, zeros, CALIBRATION_V2_MODULUS)
    if regime in {"V2_IDENTITY_OFFSET_NO_WRAP", "V2_IDENTITY_OFFSET_WRAP"}:
        return VectorRule(_identity(), shared_offsets, CALIBRATION_V2_MODULUS)
    if regime == "V2_SINGLE_SWAP_OFFSET_NO_WRAP":
        return VectorRule(shared_swap, shared_offsets, CALIBRATION_V2_MODULUS)
    raise CalibrationV2Error(f"unsupported calibration-v2 regime: {regime}")


def _bounded_vector(
    seed: int,
    label: str,
    *,
    rule: VectorRule,
    forbid_wrap: bool,
) -> tuple[int, ...]:
    raw = _seed_bytes(seed, label)
    maximum_by_input = [CALIBRATION_V2_MODULUS - 1] * CALIBRATION_V2_VECTOR_WIDTH
    if forbid_wrap:
        for output_index, input_index in enumerate(rule.permutation):
            maximum_by_input[input_index] = (
                CALIBRATION_V2_MODULUS - 1 - rule.offsets[output_index]
            )
    return tuple(
        raw[index] % (maximum_by_input[index] + 1)
        for index in range(CALIBRATION_V2_VECTOR_WIDTH)
    )


def _wrap_count(rule: VectorRule, values: tuple[int, ...]) -> int:
    return sum(
        values[rule.permutation[index]] + rule.offsets[index] >= rule.modulus
        for index in range(CALIBRATION_V2_VECTOR_WIDTH)
    )


def _candidate_rules_global(examples: tuple[PublicExample, ...]) -> tuple[VectorRule, ...]:
    if not examples:
        return ()
    first = examples[0]
    candidates: list[VectorRule] = []
    for permutation in permutations(range(CALIBRATION_V2_VECTOR_WIDTH)):
        offsets = tuple(
            (
                first.output_values[index]
                - first.input_values[permutation[index]]
            )
            % CALIBRATION_V2_MODULUS
            for index in range(CALIBRATION_V2_VECTOR_WIDTH)
        )
        candidate = VectorRule(tuple(permutation), offsets, CALIBRATION_V2_MODULUS)
        if all(candidate.apply(item.input_values) == item.output_values for item in examples):
            candidates.append(candidate)
    return tuple(candidates)


def _examples_for_case(
    seed: int,
    regime: str,
    *,
    rule: VectorRule,
) -> tuple[PublicExample, ...]:
    forbid_wrap = regime in {
        "V2_IDENTITY_OFFSET_NO_WRAP",
        "V2_SINGLE_SWAP_OFFSET_NO_WRAP",
    }
    for salt in range(64):
        examples = tuple(
            PublicExample(
                values := _bounded_vector(
                    seed,
                    f"{regime}:salt:{salt}:example:{index}",
                    rule=rule,
                    forbid_wrap=forbid_wrap,
                ),
                rule.apply(values),
            )
            for index in range(4)
        )
        if _candidate_rules_global(examples) != (rule,):
            continue
        if forbid_wrap and any(_wrap_count(rule, item.input_values) for item in examples):
            raise AssertionError("no-wrap calibration-v2 example unexpectedly wraps")
        return examples
    raise CalibrationV2Error("failed to generate globally identifiable calibration-v2 examples")


def _query_for_case(seed: int, regime: str, *, rule: VectorRule) -> tuple[int, ...]:
    if regime in {"V2_IDENTITY_OFFSET_NO_WRAP", "V2_SINGLE_SWAP_OFFSET_NO_WRAP"}:
        query = _bounded_vector(
            seed,
            f"{regime}:query",
            rule=rule,
            forbid_wrap=True,
        )
        if _wrap_count(rule, query):
            raise AssertionError("no-wrap calibration-v2 query unexpectedly wraps")
        return query
    if regime == "V2_IDENTITY_OFFSET_WRAP":
        values = list(
            _bounded_vector(
                seed,
                f"{regime}:query",
                rule=rule,
                forbid_wrap=False,
            )
        )
        for output_index in range(2):
            input_index = rule.permutation[output_index]
            values[input_index] = CALIBRATION_V2_MODULUS - rule.offsets[output_index]
        query = tuple(values)
        if _wrap_count(rule, query) < 2:
            raise AssertionError("wrap-control query must contain at least two wrap coordinates")
        return query
    return _bounded_vector(
        seed,
        f"{regime}:query",
        rule=rule,
        forbid_wrap=False,
    )


@dataclass(frozen=True, slots=True)
class CalibrationV2Case:
    seed: int
    regime: str
    rule: VectorRule
    examples: tuple[PublicExample, ...]
    query: tuple[int, ...]

    @property
    def expected_output(self) -> tuple[int, ...]:
        return self.rule.apply(self.query)

    @property
    def query_wrap_count(self) -> int:
        return _wrap_count(self.rule, self.query)

    def public_examples(self) -> list[dict[str, object]]:
        return [
            {"input": list(example.input_values), "output": list(example.output_values)}
            for example in self.examples
        ]


def generate_calibration_v2_case(*, seed: int, regime: str) -> CalibrationV2Case:
    if seed not in CALIBRATION_V2_SEEDS:
        raise CalibrationV2Error("seed is outside the frozen calibration-v2 seed set")
    if regime not in CALIBRATION_V2_REGIMES:
        raise CalibrationV2Error("regime is outside the frozen calibration-v2 matrix")
    rule = _rule_for_regime(seed, regime)
    examples = _examples_for_case(seed, regime, rule=rule)
    if _candidate_rules_global(examples) != (rule,):
        raise CalibrationV2Error(
            "public calibration-v2 examples must identify exactly one rule in the full legal class"
        )
    query = _query_for_case(seed, regime, rule=rule)
    return CalibrationV2Case(seed=seed, regime=regime, rule=rule, examples=examples, query=query)


def _rule_mapping(rule: VectorRule) -> dict[str, object]:
    return {
        "permutation": list(rule.permutation),
        "offsets": list(rule.offsets),
        "modulus": rule.modulus,
    }


def build_calibration_v2_messages(
    case: CalibrationV2Case,
    probe: str,
) -> tuple[dict[str, str], ...]:
    if probe == "C0_APPLICATION_ONLY":
        system = _OPERATOR_CONTRACT + " Apply the explicit rule to the query."
        payload = {"rule": _rule_mapping(case.rule), "query": list(case.query)}
    elif probe == "C1_FORMATION_ONLY":
        system = _OPERATOR_CONTRACT + " Infer the one rule consistent with all examples."
        payload = {"modulus": case.rule.modulus, "examples": case.public_examples()}
    elif probe == "C2_END_TO_END":
        system = (
            _OPERATOR_CONTRACT
            + " Infer the one rule consistent with all examples, then apply it to the query."
        )
        payload = {
            "modulus": case.rule.modulus,
            "examples": case.public_examples(),
            "query": list(case.query),
        }
    else:
        raise CalibrationV2Error(f"unsupported calibration-v2 probe: {probe}")
    return (
        {"role": "system", "content": system},
        {"role": "user", "content": _json_text(payload)},
    )


def calibration_v2_schema_for_probe(probe: str) -> tuple[str, Mapping[str, object]]:
    if probe == "C0_APPLICATION_ONLY":
        return "relaylm2_calibration_v2_application", ANSWER_SCHEMA
    if probe == "C1_FORMATION_ONLY":
        return "relaylm2_calibration_v2_formation", RULE_SCHEMA
    if probe == "C2_END_TO_END":
        return "relaylm2_calibration_v2_end_to_end", END_TO_END_SCHEMA
    raise CalibrationV2Error(f"unsupported calibration-v2 probe: {probe}")


def calibration_v2_call_plan() -> tuple[str, ...]:
    return tuple(
        f"{regime}|{seed}|{probe}"
        for regime in CALIBRATION_V2_REGIMES
        for seed in CALIBRATION_V2_SEEDS
        for probe in CALIBRATION_V2_PROBES
    )


@dataclass(frozen=True, slots=True)
class CalibrationV2RegimeSummary:
    regime: str
    sample_count: int
    application_correct: int
    formation_correct: int
    end_to_end_joint_correct: int

    @property
    def admitted(self) -> bool:
        return (
            self.application_correct / self.sample_count >= 0.90
            and 0.40 <= self.formation_correct / self.sample_count <= 0.90
            and 0.20 <= self.end_to_end_joint_correct / self.sample_count <= 0.80
        )


def select_calibration_v2_regime(
    summaries: tuple[CalibrationV2RegimeSummary, ...],
) -> str | None:
    if len(summaries) != len(CALIBRATION_V2_REGIMES):
        raise CalibrationV2Error("calibration-v2 summaries must cover every frozen regime exactly once")
    indexed = {item.regime: item for item in summaries}
    if set(indexed) != set(CALIBRATION_V2_REGIMES):
        raise CalibrationV2Error("calibration-v2 summaries must cover every frozen regime exactly once")
    if any(item.sample_count != CALIBRATION_V2_SEED_COUNT for item in summaries):
        raise CalibrationV2Error("calibration-v2 summary has the wrong sample count")
    for regime in CALIBRATION_V2_SELECTION_PRIORITY:
        if indexed[regime].admitted:
            return regime
    return None
