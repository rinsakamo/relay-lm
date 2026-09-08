from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
from itertools import permutations
import json
import math
from pathlib import Path
from typing import Mapping, Sequence

from relaylm.v2_transfer_experiment import PublicExample, VectorRule
from tools.v2_transfer_r2_prereg import (
    EXAMPLES_VISIBLE_LEVELS,
    MODULUS,
    STEP_INDEX,
    family_specs,
    generate_families,
)


FORENSIC_VERSION = "relaylm2-transfer-r2-source-floor-forensic-v2"
R2_FROZEN_PREREGISTRATION_COMMIT = "aeb8f8d477ba46650cb2f3d97b7154b69366431c"
_VECTOR_WIDTH = 4
_SOURCE_PHASE = "source-learning"
_MODEL_EXCHANGE_KIND = "model_exchange"


class R2SourceLearningForensicError(ValueError):
    """The deterministic R2 source-learning forensic contract is invalid."""


@dataclass(frozen=True, slots=True)
class FamilyForensic:
    family_index: int
    regime: str
    seed: int
    source_candidate_counts: tuple[int, int, int, int]
    target_candidate_counts: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class R2SourceLearningForensicReport:
    version: str
    preregistration_commit: str
    families: tuple[FamilyForensic, ...]
    source_unique_after_four: int
    source_max_candidates_after_four: int
    target_unique_after_three: int


@dataclass(frozen=True, slots=True)
class SourceResponseForensic:
    family_index: int
    regime: str
    seed: int
    category: str
    canonical_examples_matched: int
    reverse_output_offset_examples_matched: int
    reverse_input_offset_examples_matched: int
    permutation: tuple[int, int, int, int]
    offsets: tuple[int, int, int, int]
    modulus: int


@dataclass(frozen=True, slots=True)
class RawSourceForensicReport:
    version: str
    request_evidence_sha256: str
    source_response_count: int
    exact_canonical_count: int
    reverse_convention_count: int
    other_valid_count: int
    responses: tuple[SourceResponseForensic, ...]


def _candidate_count(
    examples: tuple[PublicExample, ...],
    *,
    modulus: int,
    visible: int,
) -> int:
    if isinstance(visible, bool) or not isinstance(visible, int):
        raise R2SourceLearningForensicError("visible must be an integer")
    if visible < 0 or visible > len(examples):
        raise R2SourceLearningForensicError("visible is outside the example prefix")
    if modulus <= 1:
        raise R2SourceLearningForensicError("modulus must be greater than one")

    if visible == 0:
        return math.factorial(_VECTOR_WIDTH) * modulus**_VECTOR_WIDTH

    prefix = examples[:visible]
    first = prefix[0]
    count = 0
    for permutation in permutations(range(_VECTOR_WIDTH)):
        offsets = tuple(
            (first.output_values[index] - first.input_values[permutation[index]]) % modulus
            for index in range(_VECTOR_WIDTH)
        )
        candidate = VectorRule(tuple(permutation), offsets, modulus)
        if all(candidate.apply(example.input_values) == example.output_values for example in prefix):
            count += 1
    return count


def source_candidate_counts(examples: tuple[PublicExample, ...], *, modulus: int) -> tuple[int, ...]:
    if len(examples) != 4:
        raise R2SourceLearningForensicError("frozen R2 source learning requires four examples")
    return tuple(
        _candidate_count(examples, modulus=modulus, visible=visible)
        for visible in (1, 2, 3, 4)
    )


def target_candidate_counts(examples: tuple[PublicExample, ...], *, modulus: int) -> tuple[int, ...]:
    if len(examples) != 3:
        raise R2SourceLearningForensicError("frozen R2 target step requires three examples")
    if EXAMPLES_VISIBLE_LEVELS != (0, 1, 2, 3):
        raise R2SourceLearningForensicError("R2 visible-evidence levels drifted")
    return tuple(
        _candidate_count(examples, modulus=modulus, visible=visible)
        for visible in EXAMPLES_VISIBLE_LEVELS
    )


def forensic_report(preregistration_commit: str) -> R2SourceLearningForensicReport:
    specs = family_specs(preregistration_commit)
    families = generate_families(preregistration_commit)
    if len(specs) != 16 or len(families) != 16:
        raise R2SourceLearningForensicError("frozen R2 forensic requires exactly 16 families")
    if MODULUS != 10 or STEP_INDEX != 0:
        raise R2SourceLearningForensicError("frozen R2 generator contract drifted")

    items: list[FamilyForensic] = []
    for spec, family in zip(specs, families, strict=True):
        if spec.seed != family.seed or spec.regime != family.regime:
            raise R2SourceLearningForensicError("family specification/generator mismatch")
        source_counts = source_candidate_counts(
            family.source_examples,
            modulus=family.modulus,
        )
        target_counts = target_candidate_counts(
            family.target_steps[STEP_INDEX].examples,
            modulus=family.modulus,
        )
        items.append(
            FamilyForensic(
                family_index=spec.family_index,
                regime=spec.regime,
                seed=spec.seed,
                source_candidate_counts=(
                    source_counts[0], source_counts[1], source_counts[2], source_counts[3]
                ),
                target_candidate_counts=(
                    target_counts[0], target_counts[1], target_counts[2], target_counts[3]
                ),
            )
        )

    frozen = tuple(items)
    return R2SourceLearningForensicReport(
        version=FORENSIC_VERSION,
        preregistration_commit=preregistration_commit,
        families=frozen,
        source_unique_after_four=sum(
            item.source_candidate_counts[-1] == 1 for item in frozen
        ),
        source_max_candidates_after_four=max(
            item.source_candidate_counts[-1] for item in frozen
        ),
        target_unique_after_three=sum(
            item.target_candidate_counts[-1] == 1 for item in frozen
        ),
    )


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise R2SourceLearningForensicError(f"{label} must be an object")
    return value


def _int_tuple(value: object, *, label: str, maximum: int) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != _VECTOR_WIDTH:
        raise R2SourceLearningForensicError(f"{label} must contain exactly four integers")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise R2SourceLearningForensicError(f"{label} must contain exactly four integers")
    result = tuple(value)
    if any(item < 0 or item > maximum for item in result):
        raise R2SourceLearningForensicError(f"{label} value is outside its frozen range")
    return result  # type: ignore[return-value]


def _parse_source_response(content: str) -> tuple[
    tuple[int, int, int, int], tuple[int, int, int, int], int
]:
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError as exc:
        raise R2SourceLearningForensicError("source response is not JSON") from exc
    value = _require_mapping(decoded, "source response")
    if set(value) != {"permutation", "offsets", "modulus"}:
        raise R2SourceLearningForensicError("source response field set drifted")
    permutation = _int_tuple(value["permutation"], label="permutation", maximum=3)
    if tuple(sorted(permutation)) != tuple(range(_VECTOR_WIDTH)):
        raise R2SourceLearningForensicError("source permutation is not a bijection")
    offsets = _int_tuple(value["offsets"], label="offsets", maximum=9)
    modulus = value["modulus"]
    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus != MODULUS:
        raise R2SourceLearningForensicError("source modulus is not the frozen modulus")
    return permutation, offsets, modulus


def _canonical_apply(
    values: tuple[int, ...],
    permutation: tuple[int, ...],
    offsets: tuple[int, ...],
    modulus: int,
) -> tuple[int, ...]:
    return tuple(
        (values[permutation[index]] + offsets[index]) % modulus
        for index in range(_VECTOR_WIDTH)
    )


def _reverse_apply_output_offsets(
    values: tuple[int, ...],
    permutation: tuple[int, ...],
    offsets: tuple[int, ...],
    modulus: int,
) -> tuple[int, ...]:
    output = [0] * _VECTOR_WIDTH
    for input_index, output_index in enumerate(permutation):
        output[output_index] = (values[input_index] + offsets[output_index]) % modulus
    return tuple(output)


def _reverse_apply_input_offsets(
    values: tuple[int, ...],
    permutation: tuple[int, ...],
    offsets: tuple[int, ...],
    modulus: int,
) -> tuple[int, ...]:
    output = [0] * _VECTOR_WIDTH
    for input_index, output_index in enumerate(permutation):
        output[output_index] = (values[input_index] + offsets[input_index]) % modulus
    return tuple(output)


def _matched_examples(
    examples: tuple[PublicExample, ...],
    *,
    apply_fn: object,
    permutation: tuple[int, ...],
    offsets: tuple[int, ...],
    modulus: int,
) -> int:
    function = apply_fn
    if not callable(function):
        raise TypeError("apply_fn must be callable")
    return sum(
        function(example.input_values, permutation, offsets, modulus)
        == example.output_values
        for example in examples
    )


def classify_source_response(
    *,
    family_index: int,
    content: str,
    preregistration_commit: str = R2_FROZEN_PREREGISTRATION_COMMIT,
) -> SourceResponseForensic:
    families = generate_families(preregistration_commit)
    if family_index < 0 or family_index >= len(families):
        raise R2SourceLearningForensicError("source response family index is outside R2")
    family = families[family_index]
    permutation, offsets, modulus = _parse_source_response(content)
    canonical = _matched_examples(
        family.source_examples,
        apply_fn=_canonical_apply,
        permutation=permutation,
        offsets=offsets,
        modulus=modulus,
    )
    reverse_output = _matched_examples(
        family.source_examples,
        apply_fn=_reverse_apply_output_offsets,
        permutation=permutation,
        offsets=offsets,
        modulus=modulus,
    )
    reverse_input = _matched_examples(
        family.source_examples,
        apply_fn=_reverse_apply_input_offsets,
        permutation=permutation,
        offsets=offsets,
        modulus=modulus,
    )
    exact = (
        permutation == family.source_rule.permutation
        and offsets == family.source_rule.offsets
        and modulus == family.source_rule.modulus
    )
    if exact:
        category = "EXACT_CANONICAL"
    elif reverse_output == len(family.source_examples):
        category = "SEMANTICALLY_EXACT_REVERSE_PERMUTATION_OUTPUT_OFFSETS"
    elif reverse_input == len(family.source_examples):
        category = "SEMANTICALLY_EXACT_REVERSE_PERMUTATION_INPUT_OFFSETS"
    else:
        category = "OTHER_VALID_HYPOTHESIS"
    return SourceResponseForensic(
        family_index=family_index,
        regime=family.regime,
        seed=family.seed,
        category=category,
        canonical_examples_matched=canonical,
        reverse_output_offset_examples_matched=reverse_output,
        reverse_input_offset_examples_matched=reverse_input,
        permutation=permutation,
        offsets=offsets,
        modulus=modulus,
    )


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise R2SourceLearningForensicError(f"cannot read request evidence: {exc}") from exc
    records: list[dict[str, object]] = []
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            decoded = json.loads(line)
        except json.JSONDecodeError as exc:
            raise R2SourceLearningForensicError(
                f"request evidence line {index} is not JSON"
            ) from exc
        if not isinstance(decoded, dict):
            raise R2SourceLearningForensicError(
                f"request evidence line {index} is not an object"
            )
        records.append(decoded)
    return records


def classify_request_evidence(
    path: str | Path,
    *,
    expected_sha256: str | None = None,
    preregistration_commit: str = R2_FROZEN_PREREGISTRATION_COMMIT,
) -> RawSourceForensicReport:
    evidence_path = Path(path)
    try:
        payload = evidence_path.read_bytes()
    except OSError as exc:
        raise R2SourceLearningForensicError(f"cannot read request evidence: {exc}") from exc
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise R2SourceLearningForensicError(
            f"request evidence SHA-256 mismatch: expected {expected_sha256}, got {digest}"
        )

    source_by_family: dict[int, SourceResponseForensic] = {}
    for record in _load_jsonl(evidence_path):
        evidence = _require_mapping(record.get("evidence"), "request evidence payload")
        if evidence.get("kind") != _MODEL_EXCHANGE_KIND:
            continue
        plan = _require_mapping(evidence.get("plan_entry"), "R2 plan entry")
        if plan.get("phase") != _SOURCE_PHASE:
            continue
        family_index = plan.get("family_index")
        if isinstance(family_index, bool) or not isinstance(family_index, int):
            raise R2SourceLearningForensicError("source plan entry has invalid family index")
        response = _require_mapping(evidence.get("response"), "model response")
        content = response.get("content")
        if not isinstance(content, str):
            raise R2SourceLearningForensicError("source model response content is not a string")
        if family_index in source_by_family:
            raise R2SourceLearningForensicError(
                f"family {family_index} has more than one source model exchange"
            )
        source_by_family[family_index] = classify_source_response(
            family_index=family_index,
            content=content,
            preregistration_commit=preregistration_commit,
        )

    expected_families = set(range(len(generate_families(preregistration_commit))))
    if set(source_by_family) != expected_families:
        missing = sorted(expected_families - set(source_by_family))
        extra = sorted(set(source_by_family) - expected_families)
        raise R2SourceLearningForensicError(
            f"source model exchange coverage mismatch: missing={missing}, extra={extra}"
        )
    responses = tuple(source_by_family[index] for index in sorted(source_by_family))
    reverse_categories = {
        "SEMANTICALLY_EXACT_REVERSE_PERMUTATION_OUTPUT_OFFSETS",
        "SEMANTICALLY_EXACT_REVERSE_PERMUTATION_INPUT_OFFSETS",
    }
    return RawSourceForensicReport(
        version=FORENSIC_VERSION,
        request_evidence_sha256=digest,
        source_response_count=len(responses),
        exact_canonical_count=sum(item.category == "EXACT_CANONICAL" for item in responses),
        reverse_convention_count=sum(item.category in reverse_categories for item in responses),
        other_valid_count=sum(item.category == "OTHER_VALID_HYPOTHESIS" for item in responses),
        responses=responses,
    )


def _json_report(value: object) -> str:
    return json.dumps(asdict(value), ensure_ascii=False, sort_keys=True, indent=2)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RelayLM 2.0 Transfer R2 offline forensic")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("identifiability", help="print the frozen deterministic report")
    raw = subparsers.add_parser("raw", help="classify an existing request-evidence.jsonl")
    raw.add_argument("--request-evidence", required=True)
    raw.add_argument("--expected-sha256")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "identifiability":
        print(_json_report(forensic_report(R2_FROZEN_PREREGISTRATION_COMMIT)))
        return 0
    if args.command == "raw":
        print(
            _json_report(
                classify_request_evidence(
                    args.request_evidence,
                    expected_sha256=args.expected_sha256,
                )
            )
        )
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
