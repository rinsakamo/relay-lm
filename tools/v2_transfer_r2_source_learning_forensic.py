from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
import math

from relaylm.v2_transfer_experiment import PublicExample, VectorRule
from tools.v2_transfer_r2_prereg import (
    EXAMPLES_VISIBLE_LEVELS,
    MODULUS,
    STEP_INDEX,
    family_specs,
    generate_families,
)


FORENSIC_VERSION = "relaylm2-transfer-r2-source-floor-forensic-v1"
R2_FROZEN_PREREGISTRATION_COMMIT = "aeb8f8d477ba46650cb2f3d97b7154b69366431c"
_VECTOR_WIDTH = 4


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
                source_candidate_counts=source_counts,  # type: ignore[arg-type]
                target_candidate_counts=target_counts,  # type: ignore[arg-type]
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
